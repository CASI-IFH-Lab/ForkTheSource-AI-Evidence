"""P4 - the OpenAlex provider. Owner: Ritik.

OpenAlex is the only provider that carries **retraction status** (it ingests Retraction
Watch), and ``is_retracted`` powers the highest-severity indicator the pipeline emits. So
this module is read for two different reasons: as a resolver in its own right, and as an
enrichment pass over a DOI another provider already resolved.

Preprint signal, per D-036 and the P4 card: OpenAlex says "not a preprint" only when its
``type`` is ``article`` AND its primary location is a **journal** source. Everything else
is ``None`` - including OpenAlex's own ``preprint`` type and ``repository`` source, which
are deliberately NOT read as True here because the card enumerated the signals that may
produce a boolean and those are not among them. See the note in docs/pr/P3-P4.md.
"""

from __future__ import annotations

from typing import Any

from src import settings
from src.contract import ResolvedSource
from src.resolvers import http

_WORKS = "https://api.openalex.org/works"


def _mailto() -> str | None:
    """OpenAlex's polite pool is optional, unlike Crossref's - never fail on its absence.

    Read lazily rather than at import: D-007's loud-failure rule is about Crossref,
    where the demotion is silent and costly. Here a missing address only means the
    anonymous pool, so raising would be a worse trade than a slightly slower lookup.
    """
    try:
        return settings.crossref_mailto()
    except RuntimeError:
        return None


def _params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    params = dict(extra or {})
    mailto = _mailto()
    if mailto:
        params["mailto"] = mailto
    return params


def _authors(work: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for authorship in work.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            names.append(str(name).strip())
    return names


def _source(work: dict[str, Any]) -> dict[str, Any]:
    return ((work.get("primary_location") or {}).get("source") or {}) or {}


#: OpenAlex's own work type for a preprint, and its own source type for a preprint
#: server. Both are provider-native fields, which is what D-036 permits - the earlier
#: three-signal list in the P4 card was examples, not an enumeration.
_PREPRINT_TYPES = {"preprint"}
_PREPRINT_SOURCE_TYPES = {"repository"}


def is_preprint_from_work(work: dict[str, Any]) -> bool | None:
    """Tri-state, from OpenAlex's own fields only. D-036.

    True  - OpenAlex types the work a preprint, or its primary location is a repository
    False - an article in a journal
    None  - anything else: OpenAlex did not say, and None is NOT False
    """
    if work.get("type") in _PREPRINT_TYPES:
        return True
    if _source(work).get("type") in _PREPRINT_SOURCE_TYPES:
        return True
    if work.get("type") == "article" and _source(work).get("type") == "journal":
        return False
    return None


def normalise(work: dict[str, Any], url: str) -> ResolvedSource:
    source = _source(work)
    return ResolvedSource(
        provider="openalex",
        title=work.get("display_name") or work.get("title"),
        authors=_authors(work),
        year=work.get("publication_year"),
        doi=work.get("doi"),  # arrives as https://doi.org/...; the contract strips it
        venue=source.get("display_name"),
        # Read ALWAYS, and defaulted to False only because the field is a plain bool in
        # the contract: absence means "OpenAlex did not flag it", which is the same
        # operational meaning as not retracted.
        is_retracted=bool(work.get("is_retracted")),
        is_preprint=is_preprint_from_work(work),
        arxiv_id=None,
        url=work.get("id") or url,
        raw={
            "_lookup_url": url,
            "id": work.get("id"),
            "type": work.get("type"),
            "doi": work.get("doi"),
            "is_retracted": work.get("is_retracted"),
            "publication_year": work.get("publication_year"),
            "source": {"display_name": source.get("display_name"), "type": source.get("type")},
            "authorship_count": len(work.get("authorships") or []),
        },
    )


def lookup_doi(doi: str, notes: list[str] | None = None) -> ResolvedSource | None:
    url = f"{_WORKS}/doi:{doi}"
    work = http.get_json(url, _params(), None, notes)
    if not isinstance(work, dict) or not work.get("id"):
        return None
    return normalise(work, url)


def search_title(title: str, notes: list[str] | None = None) -> ResolvedSource | None:
    params = _params({"search": title, "per-page": 1})
    payload = http.get_json(_WORKS, params, None, notes)
    results = (payload or {}).get("results") or []
    if not results or not isinstance(results[0], dict):
        return None
    return normalise(results[0], _WORKS)


def retraction_flag(doi: str, notes: list[str] | None = None) -> bool | None:
    """Just the retraction bit for a DOI. None when OpenAlex has no record at all.

    Separate from ``lookup_doi`` so the enrichment pass reads as what it is at the call
    site, and so a caller can tell "not retracted" from "OpenAlex has never heard of
    this DOI" - which ``False`` would hide.
    """
    resolved = lookup_doi(doi, notes)
    return None if resolved is None else resolved.is_retracted
