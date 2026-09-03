"""P4 - the arXiv provider. Owner: Ritik. Atom XML, not JSON.

Reached FIRST for anything carrying an arXiv id or a ``10.48550/*`` DOI, per D-037:
arXiv DOIs are registered with DataCite, so Crossref returns 404 for the entire
``10.48550`` prefix - every time, for every such DOI. The recorded fixture
``crossref_404.json`` is that 404.

Why the ordering is load-bearing rather than tidy: a correctly-cited preprint that falls
through to ``unresolvable`` is byte-identical, in the ledger, to a reference the judge
would call hallucinated. Getting this wrong inflates our own recall numbers in our own
favour, which is the one direction of error nobody catches by reading the output.

Anything this module resolves is a preprint by construction, so ``is_preprint`` is True
here without consulting any string.

One field is worth knowing about: an arXiv entry may carry ``arxiv:doi`` and
``arxiv:journal_ref``, the DOI and citation of the **published** version, when the
author registered them. ``is_preprint`` stays True - the record we resolved is still the
preprint - but ``doi`` is then the published DOI, which is precisely the input P5's
``version_mismatch`` rule needs. Most entries have neither field; ``tests/data/
resolver_fixtures/arxiv_atom_published.xml`` is one that has both.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from typing import Any

from src.contract import ResolvedSource
from src.resolvers import http

_QUERY = "http://export.arxiv.org/api/query"
# Two namespaces, and the difference matters: `doi` and `journal_ref` live in arXiv's
# own namespace, not Atom's. Reading them as `atom:doi` finds nothing, silently, on
# every entry - which is what the first version of this file did.
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
_ATOM = _NS

#: "10.48550/arXiv.1706.03762" -> "1706.03762". The whole prefix is arXiv's.
_ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(?P<id>.+)$", re.IGNORECASE)
#: Strip a version suffix for lookup: 1607.06450v1 -> 1607.06450.
_VERSION_RE = re.compile(r"v\d+$", re.IGNORECASE)

ARXIV_DOI_PREFIX = "10.48550/"


def arxiv_id_from_doi(doi: str | None) -> str | None:
    """The arXiv id inside a DataCite arXiv DOI, or None if it is not one."""
    if not doi:
        return None
    match = _ARXIV_DOI_RE.match(doi.strip())
    return match.group("id") if match else None


def _text(entry: ElementTree.Element, tag: str) -> str | None:
    """Text of a child element. ``tag`` carries its own prefix: "title", "arxiv:doi"."""
    path = tag if ":" in tag else f"atom:{tag}"
    found = entry.find(path, _NS)
    if found is None or found.text is None:
        return None
    return re.sub(r"\s+", " ", found.text).strip() or None


def normalise(entry: ElementTree.Element, url: str, requested_id: str) -> ResolvedSource:
    entry_id = _text(entry, "id") or ""
    published = _text(entry, "published") or ""
    year: int | None = None
    if len(published) >= 4 and published[:4].isdigit():
        year = int(published[:4])

    authors = [
        name
        for name in (
            _text(author, "name")
            for author in entry.findall("atom:author", _ATOM)
        )
        if name
    ]

    # Prefer the id arXiv echoed back (it carries the resolved version), fall back to
    # what we asked for.
    resolved_id = entry_id.rsplit("/abs/", 1)[-1] if "/abs/" in entry_id else requested_id

    # OPTIONAL, and the reason this is read at all: when an author registers the
    # published version, arXiv reports its DOI and journal reference. A preprint that
    # carries a published DOI is exactly P5's version_mismatch signal - the paper cited
    # the preprint when a published version exists. Most entries have neither field.
    published_doi = _text(entry, "arxiv:doi")
    journal_ref = _text(entry, "arxiv:journal_ref")

    return ResolvedSource(
        provider="arxiv",
        title=_text(entry, "title"),
        authors=authors,
        year=year,
        doi=published_doi,
        venue="arXiv",
        is_retracted=False,  # arXiv has no retraction feed; OpenAlex enriches when a DOI exists.
        is_preprint=True,  # By construction: arXiv only hosts preprints. D-036.
        arxiv_id=resolved_id,
        url=entry_id or url,
        raw={
            "_lookup_url": url,
            "requested_id": requested_id,
            "id": entry_id,
            "published": published,
            # Kept even though ResolvedSource has no field for it: it is the published
            # venue of a preprint, which P5 may want alongside the published DOI.
            "arxiv_journal_ref": journal_ref,
            "arxiv_doi": published_doi,
            "author_count": len(authors),
        },
    )


def lookup_arxiv(arxiv_id: str, notes: list[str] | None = None) -> ResolvedSource | None:
    """Look up one arXiv id. None on outage, timeout, or an empty feed."""
    bare = _VERSION_RE.sub("", arxiv_id.strip())
    if not bare:
        return None
    params = {"id_list": bare, "max_results": 1}
    payload = http.get_text(_QUERY, params, None, notes)
    body = (payload or {}).get("_text")
    if not body:
        return None
    try:
        feed = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        if notes is not None:
            notes.append(f"arxiv {bare}: Atom feed did not parse")
        return None

    entry = feed.find("atom:entry", _ATOM)
    if entry is None:
        return None
    # arXiv answers an unknown id with an entry whose title is "Error".
    title = _text(entry, "title")
    if title and title.lower().startswith("error"):
        if notes is not None:
            notes.append(f"arxiv {bare}: no such record")
        return None
    return normalise(entry, _QUERY, bare)
