"""P3 - one disk cache for every external HTTP response. Owner: Ritik.

    make_key(url, params) -> str
    cache_get(key)        -> dict | None      None if missing OR TTL-expired
    cache_set(key, payload)

Two functions and a key builder, deliberately. Every external lookup in the pipeline
goes through here, so if we ever want Redis or a shared cache, **this file is the only
one that changes.** Nothing above it knows what the storage is.

Why it exists at all: rate-limit protection (Crossref will throttle a rerun of 40
lookups), instant re-runs, and demo insurance - a cached corpus resolves with the
network unplugged.

**The TTL is a read-time rule, not a write-time one.** Rows are never deleted on expiry;
``cache_get`` simply reports a miss for anything older than
``resolvers.cache_ttl_hours``. That keeps writes cheap and means shortening the TTL takes
effect immediately on data already stored, rather than after a sweep.

**``schema_version`` is inside the key**, not a column. Bumping
``cache.schema_version`` in ``config.yaml`` therefore changes every key at once and
orphans the old rows instead of serving them - which is what that setting is documented
to do. The orphans are dead weight in a gitignored file; deleting them is not worth code.

Payloads are dicts because callers hand us parsed JSON. A non-JSON body - arXiv returns
Atom XML - is stored as ``{"_text": body}`` by its provider, so this layer stays
JSON-only and the provider owns knowing its own content type.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from src import settings

_DB_FILENAME = "resolver_cache.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at REAL NOT NULL
)
"""

#: Seconds a busy writer will wait rather than raising "database is locked".
_BUSY_TIMEOUT_MS = 5000


def database_path() -> Path:
    """The cache file. Under ``resolvers.cache_dir``, which .gitignore excludes."""
    return settings.cache_dir() / _DB_FILENAME


def _now() -> float:
    """Indirected so tests can hand it a fake clock and exercise real expiry."""
    return time.time()


def _connect() -> sqlite3.Connection:
    """A fresh connection per call, in WAL mode.

    Per-call rather than a module-level singleton: a cached connection is not safe to
    share across threads, and Streamlit reruns this process's callables from a thread
    pool. WAL lets a reader and a writer coexist instead of blocking each other, which
    matters the moment two lookups overlap.
    """
    connection = sqlite3.connect(database_path(), timeout=_BUSY_TIMEOUT_MS / 1000)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(_SCHEMA)
    return connection


def make_key(url: str, params: dict[str, Any] | None = None) -> str:
    """Stable hash of a request, including the cache schema version.

    Params are sorted, so the same query built in a different order is the same key -
    otherwise a dict-ordering change would silently halve the hit rate.
    """
    material = json.dumps(
        {
            "url": url,
            "params": dict(sorted((params or {}).items())),
            "schema_version": settings.cache_settings().get("schema_version"),
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def cache_get(key: str) -> dict[str, Any] | None:
    """The stored payload, or None if it is missing, expired, or unreadable.

    Never raises. A cache that cannot be read is a slow pipeline; a cache that throws is
    a broken one, and the whole point of this layer is to be invisible when it fails.
    """
    ttl_hours = float(settings.resolver_settings()["cache_ttl_hours"])
    try:
        with _connect() as connection:
            row = connection.execute(
                "SELECT payload, fetched_at FROM responses WHERE cache_key = ?", (key,)
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None

    payload_text, fetched_at = row
    if _now() - float(fetched_at) > ttl_hours * 3600:
        return None  # expired: a miss, not a deletion
    try:
        payload = json.loads(payload_text)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def cache_set(key: str, payload: dict[str, Any]) -> None:
    """Store a payload against a key, replacing any previous value. Never raises."""
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO responses (cache_key, payload, fetched_at) VALUES (?, ?, ?) "
                "ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload, "
                "fetched_at=excluded.fetched_at",
                (key, text, _now()),
            )
    except sqlite3.Error:
        return
