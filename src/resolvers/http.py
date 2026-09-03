"""Cached GET with a timeout and one retry. Owner: Ritik. Internal to src/resolvers/.

**Not in the P4 card's file list**, and here anyway: all three providers need the same
cached-fetch-with-timeout-and-one-retry loop, and three copies of it is three places for
the retry count to drift out of step with ``config.yaml``. Same argument the layout test
makes for shared infrastructure - written once, or it diverges silently.

**Nothing here raises.** A timeout, a 404, a 500, a connection reset, an unparseable
body: all of them return ``None`` and append a line to ``notes``. A registry outage has
to become ``unresolvable`` downstream with the app still running, not a traceback in
someone's demo.
"""

from __future__ import annotations

from typing import Any

import requests

from src import settings
from src.resolvers import cache

#: One attempt, then one retry. The plan's per-provider budget.
_RETRIES = 1


def _note(notes: list[str] | None, message: str) -> None:
    if notes is not None:
        notes.append(message)


def _timeout() -> float:
    return float(settings.resolver_settings()["timeout_seconds"])


def _fetch(
    url: str,
    params: dict[str, Any] | None,
    headers: dict[str, str] | None,
    notes: list[str] | None,
    as_text: bool,
) -> dict[str, Any] | None:
    """Cache lookup, then network. Returns a dict payload or None."""
    key = cache.make_key(url, params)
    cached = cache.cache_get(key)
    if cached is not None:
        return cached

    timeout = _timeout()
    for attempt in range(_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - every requests failure mode
            if attempt >= _RETRIES:
                _note(notes, f"{url}: {type(exc).__name__} after {attempt + 1} attempt(s)")
                return None
            continue

        if response.status_code == 404:
            # Not an error worth retrying: the record is not there. Cached as a miss
            # would be wrong (a DOI can be registered later), so just report it.
            _note(notes, f"{url}: HTTP 404, no record")
            return None
        if not response.ok:
            if attempt >= _RETRIES:
                _note(notes, f"{url}: HTTP {response.status_code}")
                return None
            continue

        try:
            payload = {"_text": response.text} if as_text else response.json()
        except ValueError:
            if attempt >= _RETRIES:
                _note(notes, f"{url}: response was not valid JSON")
                return None
            continue

        if not isinstance(payload, dict):
            _note(notes, f"{url}: response JSON was a {type(payload).__name__}, not an object")
            return None

        cache.cache_set(key, payload)
        return payload
    return None


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any] | None:
    return _fetch(url, params, headers, notes, as_text=False)


def get_text(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any] | None:
    """For a non-JSON body. Comes back as ``{"_text": body}`` - see cache.py."""
    return _fetch(url, params, headers, notes, as_text=True)
