"""P4 - the resolver waterfall and the three providers.

**No live network in this file.** Real responses were recorded once into
tests/data/resolver_fixtures/ and are replayed by patching the HTTP layer. Recording
them was the point: every normaliser and every ``is_preprint`` rule here is written
against a payload a registry actually returned, not against a guess about its shape.

What the fixtures prove, before a single assertion runs:

    crossref_journal_article.json  type "journal-article", container-title ["PLOS Biology"]
    crossref_posted_content.json   type "posted-content",  container-title []   <- EMPTY
    crossref_404.json              HTTP 404 for 10.48550/arXiv.1706.03762
    openalex_article.json          is_retracted false, type "article", source.type "journal"
    openalex_retracted.json        is_retracted TRUE  (Retraction Watch, via OpenAlex)
    arxiv_atom.xml                 Atom feed for 1607.06450

The empty ``container-title`` on the preprint is D-036's whole argument in one field: a
venue string cannot tell you something is a preprint, because for preprints Crossref
does not send one.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.contract import Reference, ResolvedSource
from src.resolvers import arxiv, cache, http, openalex
from src.resolvers import resolver as resolver_mod

FIXTURES = Path(__file__).parent / "data" / "resolver_fixtures"

CROSSREF_ARTICLE = json.loads((FIXTURES / "crossref_journal_article.json").read_text(encoding="utf-8"))
CROSSREF_PREPRINT = json.loads((FIXTURES / "crossref_posted_content.json").read_text(encoding="utf-8"))
OPENALEX_ARTICLE = json.loads((FIXTURES / "openalex_article.json").read_text(encoding="utf-8"))
OPENALEX_RETRACTED = json.loads((FIXTURES / "openalex_retracted.json").read_text(encoding="utf-8"))
ARXIV_ATOM = (FIXTURES / "arxiv_atom.xml").read_text(encoding="utf-8")

# D-007 makes src/resolvers/crossref.py raise at IMPORT without CROSSREF_MAILTO, and
# that runtime behaviour is deliberate and unchanged. But it meant 21 tests in this file
# FAILED rather than skipped on a clone that had not written .env yet - so a judge, or a
# teammate on their first pull, saw 21 red before touching anything. Arsha caught it in
# the A2 review. These tests skip cleanly instead, with a reason that names the variable
# and the file to copy. Nothing about the resolver's behaviour is relaxed: the import
# still raises, and every test below still runs the moment the variable is set.
load_dotenv()
HAVE_CROSSREF_MAILTO = bool(os.getenv("CROSSREF_MAILTO"))
needs_crossref_mailto = pytest.mark.skipif(
    not HAVE_CROSSREF_MAILTO,
    reason=(
        "CROSSREF_MAILTO is not set. Copy .env.example to .env and put your own ASU "
        "address in CROSSREF_MAILTO. src/resolvers/crossref.py raises at import without "
        "it, by design (D-007) - so these skip rather than fail on a fresh clone."
    ),
)

PLOS_DOI = "10.1371/journal.pbio.1002165"
RETRACTED_DOI = "10.1016/s0140-6736(97)11096-0"
ARXIV_DOI = "10.48550/arXiv.1706.03762"


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "database_path", lambda: tmp_path / "resolver_cache.sqlite")


class FakeHTTP:
    """Replays recorded payloads by URL substring, and counts requests.

    Patched in at the ``http.get_json`` / ``http.get_text`` seam rather than at
    ``requests.get``, so a test that asserts "no network" is asserting about the only
    place a request can come from.
    """

    def __init__(self, routes: dict[str, object] | None = None) -> None:
        self.routes = routes or {}
        self.requests: list[str] = []

    def install(self, monkeypatch) -> "FakeHTTP":
        monkeypatch.setattr(http, "get_json", self._get)
        monkeypatch.setattr(http, "get_text", self._get)
        return self

    def _get(self, url, params=None, headers=None, notes=None):  # noqa: ANN001
        self.requests.append(url)
        for needle, payload in self.routes.items():
            if needle in url:
                if isinstance(payload, Exception):
                    raise payload
                if payload is None and notes is not None:
                    notes.append(f"{url}: fixture says no record")
                return payload
        if notes is not None:
            notes.append(f"{url}: no fixture route")
        return None


def _crossref_routes() -> dict[str, object]:
    return {"api.crossref.org/works/" + PLOS_DOI: CROSSREF_ARTICLE}


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------
@needs_crossref_mailto
def test_crossref_normalises_a_journal_article(monkeypatch):
    FakeHTTP(_crossref_routes()).install(monkeypatch)
    from src.resolvers import crossref

    resolved = crossref.lookup_doi(PLOS_DOI)
    assert isinstance(resolved, ResolvedSource)
    assert resolved.provider == "crossref"
    assert resolved.title == "The Economics of Reproducibility in Preclinical Research"
    assert resolved.year == 2015
    assert resolved.doi == PLOS_DOI
    assert resolved.venue == "PLOS Biology"
    assert resolved.authors[0] == "Leonard P. Freedman"
    assert resolved.is_preprint is False
    assert resolved.is_retracted is False
    assert resolved.url, "every result carries a lookup URL"
    assert resolved.raw["_lookup_url"].endswith(PLOS_DOI)
    # raw is TRIMMED, not the 13 KB payload.
    assert len(json.dumps(resolved.raw)) < 1500


@needs_crossref_mailto
def test_crossref_normalises_a_posted_content_preprint(monkeypatch):
    FakeHTTP({"api.crossref.org/works/10.1101": CROSSREF_PREPRINT}).install(monkeypatch)
    from src.resolvers import crossref

    resolved = crossref.lookup_doi("10.1101/2020.03.03.20029983")
    assert resolved is not None
    assert resolved.is_preprint is True
    # THE POINT: this preprint's venue is empty, so a venue string could never have
    # produced that True. D-036.
    assert resolved.venue is None
    assert CROSSREF_PREPRINT["message"]["container-title"] == []


@needs_crossref_mailto
def test_crossref_search_returns_the_first_hit(monkeypatch):
    payload = {"message": {"items": [CROSSREF_ARTICLE["message"]]}}
    FakeHTTP({"api.crossref.org/works": payload}).install(monkeypatch)
    from src.resolvers import crossref

    resolved = crossref.search_title("The Economics of Reproducibility in Preclinical Research")
    assert resolved is not None and resolved.doi == PLOS_DOI


@needs_crossref_mailto
def test_crossref_404_is_none_not_an_exception(monkeypatch):
    FakeHTTP({"api.crossref.org": None}).install(monkeypatch)
    from src.resolvers import crossref

    assert crossref.lookup_doi(ARXIV_DOI) is None


@needs_crossref_mailto
def test_crossref_mailto_is_read_at_import():
    """D-007: the polite-pool demotion is silent, so the failure has to be loud.

    Asserted by reading the module rather than by re-importing it, because forcing the
    raising path would need the credential removed from the environment mid-suite.
    """
    from src.resolvers import crossref

    source = Path(crossref.__file__).read_text(encoding="utf-8")
    assert "MAILTO = settings.crossref_mailto()" in source
    module_level = [
        line for line in source.splitlines() if line.startswith("MAILTO = settings.crossref_mailto()")
    ]
    assert module_level, "crossref_mailto() must be called at module level, not lazily"
    assert crossref.MAILTO and "@" in crossref.MAILTO


def test_the_mailto_failure_message_is_actionable():
    """If it fires on a teammate's clone, the message has to say what to do."""
    from src import settings as settings_mod

    source = Path(settings_mod.__file__).read_text(encoding="utf-8")
    assert "CROSSREF_MAILTO" in source
    assert ".env" in source


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------
def test_openalex_normalises_an_article(monkeypatch):
    FakeHTTP({"api.openalex.org/works/doi:" + PLOS_DOI: OPENALEX_ARTICLE}).install(monkeypatch)
    resolved = openalex.lookup_doi(PLOS_DOI)
    assert resolved is not None
    assert resolved.provider == "openalex"
    assert resolved.title == "The Economics of Reproducibility in Preclinical Research"
    assert resolved.year == 2015
    assert resolved.doi == PLOS_DOI, "the contract strips the https://doi.org/ prefix"
    assert resolved.venue == "PLoS Biology"
    assert resolved.is_retracted is False
    assert resolved.is_preprint is False, "type article + journal source means not a preprint"
    assert resolved.url.startswith("https://openalex.org/")


def test_openalex_reports_a_retraction(monkeypatch):
    """is_retracted drives the highest-severity indicator the pipeline emits."""
    FakeHTTP({"api.openalex.org": OPENALEX_RETRACTED}).install(monkeypatch)
    resolved = openalex.lookup_doi(RETRACTED_DOI)
    assert resolved is not None
    assert resolved.is_retracted is True
    assert OPENALEX_RETRACTED["is_retracted"] is True, "the fixture must really be retracted"


def test_the_retraction_flag_helper_distinguishes_false_from_unknown(monkeypatch):
    fake = FakeHTTP({"api.openalex.org": OPENALEX_ARTICLE}).install(monkeypatch)
    assert openalex.retraction_flag(PLOS_DOI) is False

    fake.routes = {"api.openalex.org": None}
    assert openalex.retraction_flag("10.9999/nope") is None, (
        "no record must be None, not False - False would claim OpenAlex checked"
    )


def test_openalex_search_returns_the_first_result(monkeypatch):
    FakeHTTP({"api.openalex.org/works": {"results": [OPENALEX_ARTICLE]}}).install(monkeypatch)
    resolved = openalex.search_title("The Economics of Reproducibility")
    assert resolved is not None and resolved.doi == PLOS_DOI


def test_openalex_never_fails_on_a_missing_mailto(monkeypatch):
    """Unlike Crossref, OpenAlex's polite pool is optional - absence must not raise."""
    from src import settings as settings_mod

    def boom(*_a, **_k):
        raise RuntimeError("CROSSREF_MAILTO is not set")

    monkeypatch.setattr(settings_mod, "crossref_mailto", boom)
    monkeypatch.setattr(openalex.settings, "crossref_mailto", boom)
    assert openalex._mailto() is None
    assert "mailto" not in openalex._params()


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------
def test_arxiv_normalises_an_atom_entry(monkeypatch):
    FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    resolved = arxiv.lookup_arxiv("1607.06450")
    assert resolved is not None
    assert resolved.provider == "arxiv"
    assert resolved.title == "Layer Normalization"
    assert resolved.year == 2016
    assert resolved.authors and "Jimmy Lei Ba" in resolved.authors[0]
    assert resolved.is_preprint is True, "arXiv hosts only preprints - True by construction"
    assert resolved.arxiv_id == "1607.06450v1", "arxiv_id is set when arXiv resolved it"
    assert resolved.url and "arxiv.org/abs/" in resolved.url


def test_a_version_suffix_is_stripped_for_lookup(monkeypatch):
    fake = FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    assert arxiv.lookup_arxiv("1607.06450v3") is not None
    assert fake.requests, "a request was made"


@pytest.mark.parametrize(
    ("doi", "expected"),
    [
        ("10.48550/arXiv.1706.03762", "1706.03762"),
        ("10.48550/ARXIV.2005.14165", "2005.14165"),
        ("10.1371/journal.pbio.1002165", None),
        (None, None),
        ("", None),
    ],
)
def test_arxiv_ids_are_recognised_inside_datacite_dois(doi, expected):
    assert arxiv.arxiv_id_from_doi(doi) == expected


def test_an_empty_atom_feed_is_none(monkeypatch):
    empty = "<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"
    FakeHTTP({"export.arxiv.org": {"_text": empty}}).install(monkeypatch)
    assert arxiv.lookup_arxiv("0000.00000") is None


def test_an_unparseable_atom_feed_is_none_with_a_note(monkeypatch):
    FakeHTTP({"export.arxiv.org": {"_text": "<not xml"}}).install(monkeypatch)
    notes: list[str] = []
    assert arxiv.lookup_arxiv("1607.06450", notes) is None
    assert any("did not parse" in note for note in notes)


# ---------------------------------------------------------------------------
# The waterfall - D-037
# ---------------------------------------------------------------------------
def test_an_arxiv_id_goes_to_arxiv_first_and_never_to_crossref(monkeypatch):
    fake = FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R01", raw_text="x", arxiv_id="1607.06450"))
    assert resolved is not None and resolved.provider == "arxiv"
    assert not any("crossref" in url for url in fake.requests), (
        "an arXiv id must not be sent to Crossref - D-037"
    )


def test_an_arxiv_doi_resolves_and_does_not_return_none(monkeypatch):
    """THE D-037 TRIPWIRE. Roy has a clean 10.48550 row planted for exactly this.

    A correctly-cited preprint that falls through to unresolvable is byte-identical, in
    the ledger, to a hallucinated reference - so this regression would inflate our own
    recall in our own favour.
    """
    fake = FakeHTTP(
        {
            "export.arxiv.org": {"_text": ARXIV_ATOM},
            # Crossref really does 404 the whole 10.48550 prefix. If the waterfall ever
            # asks it, this route makes the answer None and the assertions below fail.
            "api.crossref.org": None,
        }
    ).install(monkeypatch)

    resolved = resolver_mod.resolve(Reference(ref_id="R02", raw_text="x", doi=ARXIV_DOI))
    assert resolved is not None, "a 10.48550 DOI must resolve, not return None"
    assert resolved.provider == "arxiv"
    assert resolved.is_preprint is True
    assert resolved.arxiv_id is not None
    assert not any("crossref" in url for url in fake.requests)


def test_the_recorded_crossref_404_is_a_real_404():
    """The fixture is the evidence for D-037, so assert it says what the entry claims."""
    recorded = json.loads((FIXTURES / "crossref_404.json").read_text(encoding="utf-8"))
    assert recorded["_status"] == 404


@needs_crossref_mailto
def test_a_plain_doi_goes_to_crossref(monkeypatch):
    fake = FakeHTTP(
        {"api.crossref.org/works/" + PLOS_DOI: CROSSREF_ARTICLE, "api.openalex.org": OPENALEX_ARTICLE}
    ).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R03", raw_text="x", doi=PLOS_DOI))
    assert resolved is not None and resolved.provider == "crossref"
    assert not any("export.arxiv.org" in url for url in fake.requests)


def test_a_doi_that_crossref_misses_falls_through_to_openalex(monkeypatch):
    FakeHTTP({"api.crossref.org": None, "api.openalex.org": OPENALEX_ARTICLE}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R04", raw_text="x", doi=PLOS_DOI))
    assert resolved is not None and resolved.provider == "openalex"


@needs_crossref_mailto
def test_title_only_uses_the_search_endpoints(monkeypatch):
    payload = {"message": {"items": [CROSSREF_ARTICLE["message"]]}}
    FakeHTTP({"api.crossref.org/works": payload, "api.openalex.org": OPENALEX_ARTICLE}).install(monkeypatch)
    resolved = resolver_mod.resolve(
        Reference(ref_id="R05", raw_text="x", title="The Economics of Reproducibility")
    )
    assert resolved is not None and resolved.doi == PLOS_DOI


@needs_crossref_mailto
def test_crossref_resolution_is_enriched_with_the_openalex_retraction_flag(monkeypatch):
    """Crossref does not carry retraction status; OpenAlex does. Always read it."""
    fake = FakeHTTP(
        {
            "api.crossref.org/works/" + PLOS_DOI: CROSSREF_ARTICLE,
            "api.openalex.org": OPENALEX_RETRACTED,
        }
    ).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R06", raw_text="x", doi=PLOS_DOI))
    assert resolved is not None
    assert resolved.provider == "crossref", "the resolving provider is still reported"
    assert resolved.is_retracted is True, "the retraction flag came from OpenAlex"
    assert resolved.raw["_retraction_from"] == "openalex"
    assert any("openalex" in url for url in fake.requests)


@needs_crossref_mailto
def test_enrichment_failure_leaves_the_result_intact(monkeypatch):
    FakeHTTP({"api.crossref.org/works/" + PLOS_DOI: CROSSREF_ARTICLE, "api.openalex.org": None}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R07", raw_text="x", doi=PLOS_DOI))
    assert resolved is not None and resolved.is_retracted is False
    assert "_retraction_from" not in resolved.raw


def test_a_reference_with_nothing_to_look_up_is_none(monkeypatch):
    FakeHTTP().install(monkeypatch)
    notes: list[str] = []
    assert resolver_mod.resolve(Reference(ref_id="R08", raw_text="just some text"), notes) is None
    assert any("nothing to look up" in note for note in notes)


# ---------------------------------------------------------------------------
# Failure is never an exception
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "boom",
    [
        TimeoutError("read timed out"),
        ConnectionError("connection reset"),
        RuntimeError("registry on fire"),
        ValueError("garbage payload"),
    ],
    ids=["timeout", "connreset", "runtime", "value"],
)
def test_every_provider_raising_still_returns_none(monkeypatch, boom):
    """A registry outage becomes unresolvable downstream, and the app stays alive."""
    FakeHTTP({"api.": boom, "export.arxiv.org": boom}).install(monkeypatch)
    for ref in (
        Reference(ref_id="R09", raw_text="x", arxiv_id="1607.06450"),
        Reference(ref_id="R10", raw_text="x", doi=PLOS_DOI),
        Reference(ref_id="R11", raw_text="x", title="Some title"),
        Reference(ref_id="R12", raw_text="x", doi=ARXIV_DOI, title="Attention Is All You Need"),
    ):
        notes: list[str] = []
        assert resolver_mod.resolve(ref, notes) is None, f"{ref.ref_id} raised instead of None"
        assert notes, f"{ref.ref_id} failed silently - a failure must leave a note"


def test_a_provider_module_that_explodes_is_contained(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("normaliser bug")

    monkeypatch.setattr(arxiv, "lookup_arxiv", boom)
    monkeypatch.setattr(openalex, "lookup_doi", boom)
    monkeypatch.setattr(openalex, "search_title", boom)
    FakeHTTP({"api.crossref.org": None}).install(monkeypatch)
    notes: list[str] = []
    assert resolver_mod.resolve(Reference(ref_id="R13", raw_text="x", arxiv_id="1607.06450", title="T"), notes) is None
    assert any("normaliser bug" in note for note in notes)


# ---------------------------------------------------------------------------
# Caching, at the resolver level
# ---------------------------------------------------------------------------
@needs_crossref_mailto
def test_a_second_lookup_of_the_same_doi_makes_no_request_and_is_fast(monkeypatch):
    """The DoD's <50ms second lookup, asserted on request count as well as clock."""
    calls = {"n": 0}

    class CountingResponse:
        status_code = 200
        ok = True
        text = json.dumps(CROSSREF_ARTICLE)

        def json(self):
            return CROSSREF_ARTICLE

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ANN001
        calls["n"] += 1
        return CountingResponse()

    monkeypatch.setattr(http.requests, "get", fake_get)
    from src.resolvers import crossref

    first = crossref.lookup_doi(PLOS_DOI)
    assert first is not None and calls["n"] == 1

    started = time.perf_counter()
    second = crossref.lookup_doi(PLOS_DOI)
    elapsed = time.perf_counter() - started

    assert second is not None
    assert calls["n"] == 1, "the second lookup hit the network"
    assert elapsed < 0.05, f"second lookup took {elapsed * 1000:.0f}ms, budget is 50ms"
    assert first.model_dump() == second.model_dump()


def test_the_timeout_comes_from_config(monkeypatch):
    from src import settings

    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ANN001
        seen["timeout"] = timeout
        raise TimeoutError("boom")

    monkeypatch.setattr(http.requests, "get", fake_get)
    assert http.get_json("https://api.example.org/x") is None
    assert seen["timeout"] == float(settings.resolver_settings()["timeout_seconds"]) == 10.0


def test_a_failed_fetch_is_retried_exactly_once(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ANN001
        calls["n"] += 1
        raise TimeoutError("boom")

    monkeypatch.setattr(http.requests, "get", fake_get)
    notes: list[str] = []
    assert http.get_json("https://api.example.org/x", notes=notes) is None
    assert calls["n"] == 2, "one attempt plus one retry"
    assert any("2 attempt" in note for note in notes)


def test_a_404_is_not_retried(monkeypatch):
    calls = {"n": 0}

    class NotFound:
        status_code = 404
        ok = False
        text = "Resource not found."

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ANN001
        calls["n"] += 1
        return NotFound()

    monkeypatch.setattr(http.requests, "get", fake_get)
    notes: list[str] = []
    assert http.get_json("https://api.example.org/x", notes=notes) is None
    assert calls["n"] == 1, "a 404 means the record is absent; retrying cannot help"
    assert any("404" in note for note in notes)


# ---------------------------------------------------------------------------
# is_preprint, all three values
# ---------------------------------------------------------------------------
def test_is_preprint_true_from_arxiv(monkeypatch):
    FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    assert arxiv.lookup_arxiv("1607.06450").is_preprint is True


@needs_crossref_mailto
def test_is_preprint_true_from_crossref_posted_content(monkeypatch):
    FakeHTTP({"api.crossref.org": CROSSREF_PREPRINT}).install(monkeypatch)
    from src.resolvers import crossref

    assert crossref.lookup_doi("10.1101/2020.03.03.20029983").is_preprint is True


@needs_crossref_mailto
def test_is_preprint_false_from_crossref_journal_article(monkeypatch):
    FakeHTTP({"api.crossref.org": CROSSREF_ARTICLE}).install(monkeypatch)
    from src.resolvers import crossref

    assert crossref.lookup_doi(PLOS_DOI).is_preprint is False


@needs_crossref_mailto
def test_is_preprint_none_when_the_provider_did_not_say(monkeypatch):
    """None is NOT False. Collapsing them asserts "definitely published" on no data."""
    from src.resolvers import crossref

    chapter = {"message": {**CROSSREF_ARTICLE["message"], "type": "book-chapter"}}
    FakeHTTP({"api.crossref.org": chapter}).install(monkeypatch)
    resolved = crossref.lookup_doi(PLOS_DOI)
    assert resolved.is_preprint is None
    assert resolved.is_preprint is not False


@pytest.mark.parametrize(
    ("work_type", "expected"),
    [("posted-content", True), ("journal-article", False), ("book-chapter", None),
     ("proceedings-article", None), ("dataset", None), (None, None)],
)
@needs_crossref_mailto
def test_crossref_preprint_rules(work_type, expected):
    from src.resolvers import crossref

    assert crossref.is_preprint_from_type(work_type) is expected


@pytest.mark.parametrize(
    ("work", "expected"),
    [
        ({"type": "article", "primary_location": {"source": {"type": "journal"}}}, False),
        # PROMOTED: OpenAlex's own type and its own source type are provider-native
        # fields, which is what D-036 permits. The P4 card's three-signal list was
        # examples, not an enumeration.
        ({"type": "preprint", "primary_location": {"source": {"type": "repository"}}}, True),
        ({"type": "article", "primary_location": {"source": {"type": "repository"}}}, True),
        ({"type": "preprint", "primary_location": {}}, True),
        # Still None: OpenAlex genuinely did not say.
        ({"type": "article", "primary_location": {}}, None),
        ({"type": "book-chapter", "primary_location": {"source": {"type": "book"}}}, None),
        ({}, None),
    ],
)
def test_openalex_preprint_rules(work, expected):
    assert openalex.is_preprint_from_work(work) is expected


def test_openalex_preprint_promotion_never_guesses_from_venue():
    """The promotion added TYPE signals, not string matching. D-036 still holds."""
    disguised = {
        "type": "article",
        "primary_location": {"source": {"type": "journal", "display_name": "arXiv preprint"}},
    }
    assert openalex.is_preprint_from_work(disguised) is False, (
        "a venue reading 'arXiv preprint' must not flip the decision - only type does"
    )


@needs_crossref_mailto
def test_no_preprint_decision_is_ever_taken_from_a_venue_string():
    """D-036, as a source check: neither module may branch on venue text."""
    for module in (openalex, arxiv):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "venue.lower()" not in source
        assert 'venue ==' not in source
    from src.resolvers import crossref

    source = Path(crossref.__file__).read_text(encoding="utf-8")
    assert "container-title" in source  # it is READ, for the venue field
    # ...but the preprint decision is made only from `type`.
    assert "_PREPRINT_TYPES = {" in source
    assert "def is_preprint_from_type(work_type: str | None)" in source


# ---------------------------------------------------------------------------
# Every result carries a URL
# ---------------------------------------------------------------------------
@needs_crossref_mailto
def test_every_provider_result_carries_a_lookup_url(monkeypatch):
    """The dashboard's one-click evidence link depends on this."""
    from src.resolvers import crossref

    FakeHTTP(
        {
            "api.crossref.org": CROSSREF_ARTICLE,
            "api.openalex.org": OPENALEX_ARTICLE,
            "export.arxiv.org": {"_text": ARXIV_ATOM},
        }
    ).install(monkeypatch)
    for resolved in (
        crossref.lookup_doi(PLOS_DOI),
        openalex.lookup_doi(PLOS_DOI),
        arxiv.lookup_arxiv("1607.06450"),
    ):
        assert resolved is not None
        assert resolved.url and resolved.url.startswith("http"), resolved.provider
        assert resolved.raw.get("_lookup_url"), resolved.provider


# ---------------------------------------------------------------------------
# arXiv's published-version fields - P5's version_mismatch input
# ---------------------------------------------------------------------------
ARXIV_ATOM_PUBLISHED = (FIXTURES / "arxiv_atom_published.xml").read_text(encoding="utf-8")


def test_a_preprint_that_was_published_reports_the_published_doi(monkeypatch):
    """The namespace bug this test exists to prevent.

    `doi` and `journal_ref` are in arXiv's OWN namespace, not Atom's. Read as
    `atom:doi` they come back None on every entry, silently, and the version_mismatch
    signal P5 needs would simply never appear. arXiv:1207.7214 has both fields set.
    """
    FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM_PUBLISHED}}).install(monkeypatch)
    resolved = arxiv.lookup_arxiv("1207.7214")
    assert resolved is not None
    assert resolved.doi == "10.1016/j.physletb.2012.08.020", (
        "the published version's DOI must survive - it is P5's version_mismatch input"
    )
    assert resolved.raw["arxiv_journal_ref"] == "Phys.Lett. B716 (2012) 1-29"
    # It is still the preprint record we resolved.
    assert resolved.is_preprint is True
    assert resolved.arxiv_id.startswith("1207.7214")


def test_an_entry_without_the_optional_fields_has_no_doi(monkeypatch):
    """Most arXiv entries carry neither field, and that must stay None, not blank."""
    FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    resolved = arxiv.lookup_arxiv("1607.06450")
    assert resolved is not None
    assert resolved.doi is None
    assert resolved.raw["arxiv_doi"] is None
    assert resolved.raw["arxiv_journal_ref"] is None


def test_a_published_preprint_still_gets_its_retraction_enriched(monkeypatch):
    """With a published DOI in hand, the OpenAlex retraction pass can run on a preprint."""
    FakeHTTP(
        {"export.arxiv.org": {"_text": ARXIV_ATOM_PUBLISHED}, "api.openalex.org": OPENALEX_RETRACTED}
    ).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R14", raw_text="x", arxiv_id="1207.7214"))
    assert resolved is not None
    assert resolved.provider == "arxiv"
    assert resolved.is_retracted is True
    assert resolved.raw["_retraction_from"] == "openalex"


def test_a_missing_mailto_warns_once_and_falls_through_to_openalex(monkeypatch):
    """D-007's silent-degradation rule, at the resolver level.

    A note in a list the caller may discard is not loud enough for "Crossref is off
    entirely". The first failure warns on stderr; the rest stay quiet, because forty
    identical warnings get filtered and then so does the first one.
    """
    import sys

    monkeypatch.setitem(sys.modules, "src.resolvers.crossref", None)
    monkeypatch.setattr(resolver_mod, "_crossref_warned", False)

    def raising_import():
        raise RuntimeError("CROSSREF_MAILTO is not set. Copy .env.example to .env")

    monkeypatch.setattr(resolver_mod, "_crossref", lambda: raising_import())
    FakeHTTP({"api.openalex.org": OPENALEX_ARTICLE}).install(monkeypatch)

    notes: list[str] = []
    resolved = resolver_mod.resolve(Reference(ref_id="R15", raw_text="x", doi=PLOS_DOI), notes)
    assert resolved is not None and resolved.provider == "openalex", (
        "a missing mailto must degrade to OpenAlex, not kill the run"
    )
    assert any("CROSSREF_MAILTO" in note for note in notes)


def _break_crossref_import(monkeypatch, message="CROSSREF_MAILTO is not set. Copy .env.example to .env"):
    def raising():
        raise RuntimeError(message)

    monkeypatch.setattr(resolver_mod, "_crossref_warned", False)
    monkeypatch.setattr(resolver_mod, "_import_crossref", raising)


def test_the_warning_names_what_to_fix(monkeypatch, recwarn):
    """The message has to say what to add and what the run is doing instead."""
    _break_crossref_import(monkeypatch)
    with pytest.raises(RuntimeError):
        resolver_mod._crossref()

    messages = [str(warning.message) for warning in recwarn.list]
    assert any("CROSSREF_MAILTO" in m for m in messages), messages
    assert any("DISABLED" in m and "OpenAlex" in m for m in messages), messages


def test_the_warning_fires_only_once(monkeypatch, recwarn):
    """Forty identical warnings get filtered, and then so does the first one."""
    _break_crossref_import(monkeypatch)
    for _ in range(5):
        with pytest.raises(RuntimeError):
            resolver_mod._crossref()

    runtime_warnings = [w for w in recwarn.list if issubclass(w.category, RuntimeWarning)]
    assert len(runtime_warnings) == 1, f"warned {len(runtime_warnings)} times"


def test_a_broken_crossref_import_still_resolves_via_openalex(monkeypatch):
    """D-007's degradation, end to end: loud, but the run continues."""
    _break_crossref_import(monkeypatch)
    FakeHTTP({"api.openalex.org": OPENALEX_ARTICLE}).install(monkeypatch)
    notes: list[str] = []
    with pytest.warns(RuntimeWarning, match="DISABLED"):
        resolved = resolver_mod.resolve(Reference(ref_id="R16", raw_text="x", doi=PLOS_DOI), notes)
    assert resolved is not None and resolved.provider == "openalex"
    assert any("CROSSREF_MAILTO" in note for note in notes)


# ---------------------------------------------------------------------------
# _lookup_branch - D-104. P5's classifier gates on this.
# ---------------------------------------------------------------------------
def test_the_arxiv_branch_is_stamped(monkeypatch):
    FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R20", raw_text="x", arxiv_id="1607.06450"))
    assert resolved.raw["_lookup_branch"] == resolver_mod.BRANCH_ARXIV == "arxiv_id"


@needs_crossref_mailto
def test_the_doi_branch_is_stamped(monkeypatch):
    FakeHTTP({"api.crossref.org/works/" + PLOS_DOI: CROSSREF_ARTICLE}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R21", raw_text="x", doi=PLOS_DOI))
    assert resolved.raw["_lookup_branch"] == resolver_mod.BRANCH_DOI == "doi"


@needs_crossref_mailto
def test_the_title_search_branch_is_stamped(monkeypatch):
    """The branch P5 must not let reach `verified` on title similarity alone."""
    payload = {"message": {"items": [CROSSREF_ARTICLE["message"]]}}
    FakeHTTP({"api.crossref.org/works": payload}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R22", raw_text="x", title="Some title"))
    assert resolved.raw["_lookup_branch"] == resolver_mod.BRANCH_TITLE == "title_search"


def test_the_openalex_fallback_keeps_the_branch_that_was_attempted(monkeypatch):
    """A DOI that Crossref misses is still a DOI lookup, not a title search."""
    FakeHTTP({"api.crossref.org": None, "api.openalex.org": OPENALEX_ARTICLE}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R23", raw_text="x", doi=PLOS_DOI))
    assert resolved.provider == "openalex"
    assert resolved.raw["_lookup_branch"] == "doi"


def test_the_branch_stamp_does_not_disturb_the_rest_of_raw(monkeypatch):
    FakeHTTP({"export.arxiv.org": {"_text": ARXIV_ATOM}}).install(monkeypatch)
    resolved = resolver_mod.resolve(Reference(ref_id="R24", raw_text="x", arxiv_id="1607.06450"))
    assert resolved.raw["_lookup_url"]
    assert resolved.raw["requested_id"] == "1607.06450"
