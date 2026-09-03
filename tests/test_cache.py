"""P3 - the resolver cache. Set, get, expiry on a fake clock, and never raising.

No network anywhere in this file: the cache does not know what an HTTP request is.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from src import settings
from src.resolvers import cache

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Never touch the real cache/ directory - a stale row there would fake a pass."""
    monkeypatch.setattr(cache, "database_path", lambda: tmp_path / "resolver_cache.sqlite")


@pytest.fixture
def clock(monkeypatch):
    """A fake clock, so TTL expiry is tested for real instead of with a sleep."""

    class Clock:
        now = 1_000_000.0

        def advance(self, hours: float) -> None:
            self.now += hours * 3600

    fake = Clock()
    monkeypatch.setattr(cache, "_now", lambda: fake.now)
    return fake


# ---------------------------------------------------------------------------
# make_key
# ---------------------------------------------------------------------------
def test_the_key_is_stable_and_param_order_does_not_matter():
    first = cache.make_key("https://api.example.org/works", {"a": 1, "b": 2})
    second = cache.make_key("https://api.example.org/works", {"b": 2, "a": 1})
    assert first == second, "a dict-ordering change must not halve the hit rate"
    assert first == cache.make_key("https://api.example.org/works", {"a": 1, "b": 2})
    assert len(first) == 64


def test_the_key_changes_with_url_and_params():
    base = cache.make_key("https://api.example.org/works", {"doi": "10.1/a"})
    assert base != cache.make_key("https://api.example.org/other", {"doi": "10.1/a"})
    assert base != cache.make_key("https://api.example.org/works", {"doi": "10.1/b"})
    assert base != cache.make_key("https://api.example.org/works", None)


def test_the_schema_version_is_inside_the_key(monkeypatch):
    """Bumping cache.schema_version must orphan every row, not serve stale payloads."""
    before = cache.make_key("https://api.example.org/works", {"doi": "10.1/a"})
    monkeypatch.setattr(settings, "cache_settings", lambda config=None: {"schema_version": 99})
    assert cache.make_key("https://api.example.org/works", {"doi": "10.1/a"}) != before


# ---------------------------------------------------------------------------
# set / get
# ---------------------------------------------------------------------------
def test_set_then_get_round_trips():
    key = cache.make_key("https://api.example.org/works/10.1", None)
    cache.cache_set(key, {"message": {"title": ["A Title"], "type": "journal-article"}})
    assert cache.cache_get(key) == {"message": {"title": ["A Title"], "type": "journal-article"}}


def test_a_missing_key_is_none():
    assert cache.cache_get("never-stored") is None


def test_set_replaces_a_previous_value():
    key = "k"
    cache.cache_set(key, {"v": 1})
    cache.cache_set(key, {"v": 2})
    assert cache.cache_get(key) == {"v": 2}


def test_non_json_bodies_round_trip_as_text():
    """arXiv answers in Atom XML. It is stored transparently as {"_text": body}."""
    key = "arxiv"
    body = "<?xml version='1.0'?><feed><entry><title>Layer Normalization</title></entry></feed>"
    cache.cache_set(key, {"_text": body})
    assert cache.cache_get(key) == {"_text": body}


def test_unicode_survives():
    cache.cache_set("u", {"title": "Über Präprints — 612–613"})
    assert cache.cache_get("u")["title"] == "Über Präprints — 612–613"


# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------
def test_a_fresh_row_is_a_hit_and_an_expired_row_is_a_miss(clock):
    ttl = float(settings.resolver_settings()["cache_ttl_hours"])
    assert ttl == 72, "config.yaml's TTL changed; this test documents the expected value"

    cache.cache_set("k", {"v": 1})
    assert cache.cache_get("k") == {"v": 1}

    clock.advance(ttl - 1)
    assert cache.cache_get("k") == {"v": 1}, "still inside the TTL"

    clock.advance(2)
    assert cache.cache_get("k") is None, "past the TTL: a miss"


def test_expiry_does_not_delete_the_row(clock):
    """The TTL is a read-time rule, so shortening it takes effect on stored data."""
    cache.cache_set("k", {"v": 1})
    clock.advance(100)
    assert cache.cache_get("k") is None

    with sqlite3.connect(cache.database_path()) as connection:
        rows = connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    assert rows == 1, "expiry must not delete; it reports a miss"

    # And re-writing the same key makes it fresh again.
    cache.cache_set("k", {"v": 2})
    assert cache.cache_get("k") == {"v": 2}


def test_a_shortened_ttl_applies_to_rows_already_stored(clock, monkeypatch):
    cache.cache_set("k", {"v": 1})
    clock.advance(10)
    assert cache.cache_get("k") == {"v": 1}
    monkeypatch.setattr(
        settings, "resolver_settings", lambda config=None: {"cache_ttl_hours": 1, "timeout_seconds": 10}
    )
    assert cache.cache_get("k") is None


# ---------------------------------------------------------------------------
# It must never raise
# ---------------------------------------------------------------------------
def test_a_corrupt_payload_is_a_miss_not_a_crash():
    cache.cache_set("k", {"v": 1})
    with sqlite3.connect(cache.database_path()) as connection:
        connection.execute("UPDATE responses SET payload = ? WHERE cache_key = ?", ("{not json", "k"))
    assert cache.cache_get("k") is None


def test_a_non_dict_payload_is_a_miss():
    with sqlite3.connect(cache.database_path()) as connection:
        connection.execute(cache._SCHEMA)
        connection.execute(
            "INSERT INTO responses VALUES (?, ?, ?)", ("k", json.dumps([1, 2, 3]), cache._now())
        )
    assert cache.cache_get("k") is None


def test_an_unwritable_database_is_slow_not_fatal(monkeypatch, tmp_path):
    """A cache that cannot be written is a slow pipeline, not a broken one."""
    monkeypatch.setattr(cache, "database_path", lambda: tmp_path / "nope" / "deep" / "x.sqlite")
    cache.cache_set("k", {"v": 1})  # must not raise
    assert cache.cache_get("k") is None


def test_an_unserialisable_payload_is_dropped_not_raised():
    cache.cache_set("k", {"bad": object()})
    # default=str makes most things serialisable; the contract is only "does not raise".
    assert cache.cache_get("k") is None or isinstance(cache.cache_get("k"), dict)


def test_the_table_is_created_on_first_use():
    cache.cache_set("k", {"v": 1})
    with sqlite3.connect(cache.database_path()) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(responses)")]
    assert columns == ["cache_key", "payload", "fetched_at"]


def test_wal_mode_is_on():
    """Concurrent readers and a writer must not corrupt or block each other."""
    cache.cache_set("k", {"v": 1})
    with sqlite3.connect(cache.database_path()) as connection:
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


# ---------------------------------------------------------------------------
# The cache directory must not reach git
# ---------------------------------------------------------------------------
def test_the_cache_directory_is_gitignored():
    probe = "cache/resolver_cache.sqlite"
    result = subprocess.run(
        ["git", "check-ignore", "-v", probe],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, f"{probe} is NOT gitignored - it would be committed"
    assert "cache/" in result.stdout


def test_the_real_cache_lives_under_the_configured_directory(monkeypatch):
    """database_path() must follow config, not a hardcoded path."""
    monkeypatch.undo()
    assert cache.database_path().parent == settings.cache_dir()
    assert cache.database_path().name == "resolver_cache.sqlite"
