"""P4 - the Crossref provider. Owner: Ritik.

``crossref_mailto()`` is called AT MODULE IMPORT, on purpose and per D-007: without a
mailto Crossref silently demotes you out of the polite pool - slower answers and tighter
rate limits, with no error anywhere. A silent degradation has to be converted into a loud
one at the earliest possible moment, and the earliest possible moment is import.

The consequence is that ``import src.resolvers.crossref`` fails on a clone with no
``CROSSREF_MAILTO`` in ``.env``. That is the intended behaviour, and the message names
the fix.
"""

from __future__ import annotations

from typing import Any

from src import settings
from src.contract import ResolvedSource
from src.resolvers import http

_WORKS = "https://api.crossref.org/works"

# D-007: fail at import, not at first call. Do not wrap this in a try.
MAILTO = settings.crossref_mailto()

_HEADERS = {"User-Agent": f"ForkTheSource/0.1 (https://github.com/CASI-IFH-Lab; mailto:{MAILTO})"}

#: Crossref's own work types, which is the ONLY preprint signal we take from it.
#: D-036: never infer this from the venue - a Crossref preprint returns an empty
#: container-title, which the recorded fixture in tests/data/resolver_fixtures proves.
_PREPRINT_TYPES = {"posted-content"}
_PUBLISHED_TYPES = {"journal-article"}


def _first(values: Any) -> str | None:
    if isinstance(values, list) and values:
        text = str(values[0]).strip()
        return text or None
    if isinstance(values, str):
        return values.strip() or None
    return None


def _authors(message: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for author in message.get("author") or []:
        if not isinstance(author, dict):
            continue
        given, family = author.get("given"), author.get("family")
        full = " ".join(part for part in (given, family) if part) or author.get("name")
        if full:
            names.append(str(full).strip())
    return names


def _year(message: dict[str, Any]) -> int | None:
    for field in ("issued", "published", "published-print", "published-online", "created"):
        parts = (message.get(field) or {}).get("date-parts") or []
        if parts and isinstance(parts[0], list) and parts[0] and isinstance(parts[0][0], int):
            return parts[0][0]
    return None


def is_preprint_from_type(work_type: str | None) -> bool | None:
    """Tri-state, from Crossref's ``type`` and nothing else. D-036.

    ``None`` means Crossref did not say, and must NOT be read as False - that would
    assert "definitely the published version" on missing data, which D-020 forbids.
    """
    if work_type in _PREPRINT_TYPES:
        return True
    if work_type in _PUBLISHED_TYPES:
        return False
    return None


def normalise(message: dict[str, Any], url: str) -> ResolvedSource:
    """One Crossref ``message`` into a ResolvedSource. ``raw`` is trimmed, not the 13 KB."""
    work_type = message.get("type")
    return ResolvedSource(
        provider="crossref",
        title=_first(message.get("title")),
        authors=_authors(message),
        year=_year(message),
        doi=message.get("DOI"),
        venue=_first(message.get("container-title")),
        is_retracted=False,  # Crossref does not carry this; OpenAlex enriches it.
        is_preprint=is_preprint_from_type(work_type),
        arxiv_id=None,
        url=message.get("URL") or url,
        raw={
            "_lookup_url": url,
            "type": work_type,
            "DOI": message.get("DOI"),
            "title": message.get("title"),
            "container-title": message.get("container-title"),
            "issued": message.get("issued"),
            "publisher": message.get("publisher"),
            "author_count": len(message.get("author") or []),
        },
    )


def lookup_doi(doi: str, notes: list[str] | None = None) -> ResolvedSource | None:
    """GET /works/{doi}. None on 404, timeout, outage or unusable payload."""
    url = f"{_WORKS}/{doi}"
    payload = http.get_json(url, {"mailto": MAILTO}, _HEADERS, notes)
    message = (payload or {}).get("message")
    if not isinstance(message, dict):
        return None
    return normalise(message, url)


def search_title(title: str, notes: list[str] | None = None) -> ResolvedSource | None:
    """Bibliographic search, best single hit. None when nothing comes back."""
    params = {"query.bibliographic": title, "rows": 1, "select": "DOI,title,author,issued,container-title,type,publisher,URL", "mailto": MAILTO}
    payload = http.get_json(_WORKS, params, _HEADERS, notes)
    items = ((payload or {}).get("message") or {}).get("items") or []
    if not items or not isinstance(items[0], dict):
        return None
    return normalise(items[0], _WORKS)
