"""P4 - the resolver waterfall. Owner: Ritik.

    resolve(ref: Reference) -> ResolvedSource | None

**The order is D-037 and it is load-bearing, not tidy.**

    1. ref.arxiv_id set, OR ref.doi starts with 10.48550/   ->  arXiv, then OpenAlex
    2. else ref.doi                                          ->  Crossref, then OpenAlex
    3. else ref.title                                        ->  Crossref search, then OpenAlex search

arXiv DOIs are DataCite-registered, so Crossref returns **404 for the whole
``10.48550/*`` prefix** - every time. Sending those to Crossref first means a correctly
cited preprint resolves to nothing, and in the ledger "resolved to nothing" is
byte-identical to what Roy's labels call a hallucinated reference. The error would
therefore inflate our own recall in our own favour, which is the one direction nobody
catches by reading the output. Roy has planted a clean ``10.48550`` row as a tripwire.

Both hot paths are hot on real input, measured by P2: ``sample.pdf`` yields 22/40 arXiv
ids and 0/40 DOIs, so branch 1 carries over half that paper; ``plos_sample.pdf`` yields
20/34 DOIs and no arXiv ids, so branches 2 and 3 carry that one. Neither is an edge case.

**Retraction is always read from OpenAlex.** It is the only provider carrying Retraction
Watch data, and ``is_retracted`` drives the highest-severity indicator the pipeline
emits. So whenever another provider resolves a work that has a DOI, this module makes a
second OpenAlex call for that one field and merges it in. The result still reports the
provider that actually resolved it.

**Nothing here raises.** Every failure - timeout, 404, 500, garbage payload, a provider
module blowing up outright - becomes ``None`` plus a line in ``notes``. A registry outage
has to degrade to ``unresolvable`` downstream with the app still serving.
"""

from __future__ import annotations

import warnings
from typing import Any, Callable

from src.contract import Reference, ResolvedSource
from src.resolvers import arxiv, openalex
from src.resolvers.arxiv import ARXIV_DOI_PREFIX


def _guarded(
    label: str,
    call: Callable[[], ResolvedSource | None],
    notes: list[str] | None,
) -> ResolvedSource | None:
    """Run one provider call so that no failure of any kind escapes.

    Broad by intent: a provider that raises is a provider that is down, and the
    difference between a socket error and a bug in a normaliser does not change what
    this function has to do about it.
    """
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - see docstring
        if notes is not None:
            notes.append(f"{label}: {type(exc).__name__}: {exc}")
        return None


_crossref_warned = False


def _import_crossref() -> Any:
    """The bare import, as its own seam so the warning path above is testable without
    monkeypatching Python's import machinery."""
    from src.resolvers import crossref

    return crossref


def _crossref() -> Any:
    """Imported lazily so a missing CROSSREF_MAILTO fails at the call, not at import.

    ``src.resolvers.crossref`` reads the mailto at import and raises without it (D-007).
    Importing it at the top of THIS module would make that failure hit anything that so
    much as touches the resolver package - pytest collection, and the status tool's
    interface probe, neither of which makes a request. So the raise stays where the card
    put it and this module defers the import.

    The cost of deferring is that the failure would otherwise only reach a ``notes``
    list the caller is free to discard - and "running OpenAlex-only while the operator
    believes Crossref is live" is precisely the silent degradation D-007 exists to
    prevent. So the first failure also emits a warning to stderr. Once, not per
    reference: forty identical warnings is noise, and noise gets filtered.
    """
    global _crossref_warned
    try:
        crossref = _import_crossref()
    except RuntimeError as exc:
        if not _crossref_warned:
            _crossref_warned = True
            warnings.warn(
                f"Crossref is DISABLED for this run: {exc} "
                "Every DOI lookup will fall through to OpenAlex only.",
                RuntimeWarning,
                stacklevel=2,
            )
        raise
    return crossref


def _enrich_retraction(resolved: ResolvedSource, notes: list[str] | None) -> ResolvedSource:
    """Add OpenAlex's retraction flag to a result another provider produced.

    Skipped when OpenAlex resolved it (the flag is already there) or when there is no
    DOI to look up. A failed enrichment leaves the result untouched rather than
    downgrading it - a missing retraction flag is a weaker answer, not a wrong one.
    """
    if resolved.provider == "openalex" or not resolved.doi:
        return resolved
    flag = _guarded(
        "openalex retraction enrichment",
        lambda: openalex.retraction_flag(resolved.doi or "", notes),
        notes,
    )
    if not flag:
        return resolved
    enriched = resolved.model_copy(deep=True)
    enriched.is_retracted = True
    enriched.raw = {**enriched.raw, "_retraction_from": "openalex"}
    return enriched


def resolve(ref: Reference, notes: list[str] | None = None) -> ResolvedSource | None:
    """Resolve one reference against the scholarly registries, or None.

    ``notes`` is optional and append-only: pass a list to collect why a lookup failed
    (P5 puts them on ``MatchEvidence.notes``), or leave it out and they are discarded.
    The signature stays ``resolve(ref) -> ResolvedSource | None`` for callers that do
    not care.
    """
    doi = (ref.doi or "").strip() or None
    arxiv_id = (ref.arxiv_id or "").strip() or None

    # Branch 1 - anything arXiv-shaped. D-037.
    from_doi = arxiv.arxiv_id_from_doi(doi)
    if arxiv_id or from_doi or (doi and doi.startswith(ARXIV_DOI_PREFIX)):
        candidate = arxiv_id or from_doi
        if candidate:
            resolved = _guarded(
                f"arxiv {candidate}", lambda: arxiv.lookup_arxiv(candidate, notes), notes
            )
            if resolved is not None:
                return _enrich_retraction(resolved, notes)
        if doi:
            resolved = _guarded(
                f"openalex {doi}", lambda: openalex.lookup_doi(doi, notes), notes
            )
            if resolved is not None:
                return resolved
        if notes is not None:
            notes.append(f"arxiv-first branch exhausted for {ref.ref_id}")
        # Fall through to the title search rather than giving up: an arXiv id that does
        # not resolve is often a typo in the printed reference, and the title may still
        # find the published version.

    # Branch 2 - a DOI that is not an arXiv DOI.
    elif doi:
        crossref = _guarded("crossref import", _crossref, notes)
        if crossref is not None:
            resolved = _guarded(
                f"crossref {doi}", lambda: crossref.lookup_doi(doi, notes), notes
            )
            if resolved is not None:
                return _enrich_retraction(resolved, notes)
        resolved = _guarded(f"openalex {doi}", lambda: openalex.lookup_doi(doi, notes), notes)
        if resolved is not None:
            return resolved

    # Branch 3 - title search, and the last resort for the two branches above.
    title = (ref.title or "").strip()
    if not title:
        if notes is not None:
            notes.append(f"{ref.ref_id}: no doi, no arxiv_id and no title - nothing to look up")
        return None

    crossref = _guarded("crossref import", _crossref, notes)
    if crossref is not None:
        resolved = _guarded(
            f"crossref search {title[:60]!r}", lambda: crossref.search_title(title, notes), notes
        )
        if resolved is not None:
            return _enrich_retraction(resolved, notes)
    resolved = _guarded(
        f"openalex search {title[:60]!r}", lambda: openalex.search_title(title, notes), notes
    )
    if resolved is not None:
        return _enrich_retraction(resolved, notes)
    return None
