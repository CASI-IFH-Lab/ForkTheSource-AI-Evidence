"""P2 - reference extractor and in-text citation mapping.

Everything here runs OFFLINE with no API key: the model is injected as a stub that
replays canned JSON and counts its own calls, which is what lets the cache-hit and
determinism assertions be about the code rather than about the gateway's mood. The one
live test is skipped without credentials.

The pre-splitter is tested hardest and first, on both real papers, because it is the
part no prompt can fix: the model is called once per entry, so a boundary in the wrong
place produces a confidently extracted reference that does not exist.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src import settings
from src.contract import Claim, Reference
from src.ingest import claims as claims_mod
from src.ingest import extractor, prompts
from src.ingest.pdf_parser import ParsedDocument, parse_pdf

# src.llm.get_client() loads .env itself, but the skipif below is evaluated at
# COLLECTION time, before any client exists - so without this the live test skips on a
# machine that has perfectly good credentials sitting in .env.
load_dotenv()

DATA = Path(__file__).parent / "data"
SAMPLE = DATA / "sample.pdf"
PLOS = DATA / "plos_sample.pdf"
IMAGE_ONLY = DATA / "image_only.pdf"

#: Reference counts a human read off the two real papers. If a change to the splitter
#: moves either of these, the ref_ids shift and every one of Roy's golden labels after
#: the divergence scores against the wrong entry - see eval/golden/FORMAT.md.
SAMPLE_ENTRIES = 40
PLOS_ENTRIES = 34


@pytest.fixture(scope="module")
def sample_doc() -> ParsedDocument:
    return parse_pdf(SAMPLE)


@pytest.fixture(scope="module")
def plos_doc() -> ParsedDocument:
    return parse_pdf(PLOS)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Never let a test read or write the real cache/ directory.

    Without this, the cache-hit test would pass on a stale entry from a live run and
    the determinism test would pass without exercising anything.
    """
    monkeypatch.setattr(extractor, "cache_path", lambda: tmp_path / "extractor_cache.json")


# ---------------------------------------------------------------------------
# Step 1: the pre-splitter, on the real papers
# ---------------------------------------------------------------------------
def test_split_entries_counts_the_arxiv_paper(sample_doc):
    entries = extractor.split_entries(sample_doc.references_text)
    assert len(entries) == SAMPLE_ENTRIES
    assert extractor.marker_style(sample_doc.references_text) == "bracketed"
    # Monotonic from 1: position n really is the entry printed as [n].
    for index, entry in enumerate(entries, start=1):
        assert entry.startswith(f"[{index}] "), f"entry {index} starts {entry[:20]!r}"


def test_split_entries_counts_the_plos_paper(plos_doc):
    entries = extractor.split_entries(plos_doc.references_text)
    assert len(entries) == PLOS_ENTRIES
    assert extractor.marker_style(plos_doc.references_text) == "numbered"
    for index, entry in enumerate(entries, start=1):
        assert entry.startswith(f"{index}. "), f"entry {index} starts {entry[:20]!r}"


def test_the_appendix_tail_is_truncated(sample_doc):
    """26% of sample.pdf's references_text is appendix. None of it may survive."""
    entries = extractor.split_entries(sample_doc.references_text)
    joined = "\n".join(entries)
    for artifact in ("Attention Visualizations", "Input-Input Layer", "siht"):
        assert artifact not in joined, f"appendix artifact {artifact!r} leaked into an entry"
    # The last entry ends where the bibliography ends.
    assert entries[-1].endswith("ACL, August 2013.")
    # And nothing degenerate came through: reference entries are prose-length.
    assert min(len(entry) for entry in entries) > 50


def test_page_furniture_is_dropped(sample_doc, plos_doc):
    """Both papers interleave furniture BETWEEN entries, so it lands mid-bibliography."""
    lines = sample_doc.references_text.splitlines()
    _kept, dropped = extractor._drop_page_furniture(lines)
    assert [d.strip() for d in dropped if d.strip().isdigit()], "bare page numbers not dropped"

    plos_entries = extractor.split_entries(plos_doc.references_text)
    assert not any("PLOS Biology | DOI" in entry for entry in plos_entries), (
        "the running footer was glued onto an entry"
    )


def test_a_repeated_short_line_is_not_mistaken_for_furniture(sample_doc):
    """"arXiv:1607.06450, 2016." repeats five times in sample.pdf and is real text."""
    entries = extractor.split_entries(sample_doc.references_text)
    assert sum(1 for e in entries if "arXiv:" in e) > 10, "arXiv id lines were eaten"


def test_wrapped_lines_are_rejoined_with_a_space():
    text = "[1] A. Author. A title that runs\nover two lines. Journal, 2021.\n[2] B. Writer. Short. 2020."
    entries = extractor.split_entries(text)
    assert entries[0] == "[1] A. Author. A title that runs over two lines. Journal, 2021."
    assert "\n" not in entries[0]


def test_a_line_break_hyphen_is_dropped_and_a_mid_line_hyphen_is_kept():
    """FIX A. Both hyphens in ONE entry, so only the join position can tell them apart.

    "im-" at a line end is syllabic hyphenation and becomes "image"; "short-term" is
    printed that way and stays. A rule over the joined string sees the same two
    characters in both and cannot make this call - ``_rejoin`` can, because it knows
    where it joined.
    """
    text = (
        "[1] A. Author. Deep residual learning for im-\n"
        "age recognition with short-term memory. 2015.\n"
        "[2] B. B. Short. 2020."
    )
    entries = extractor.split_entries(text)
    assert "image recognition" in entries[0], entries[0]
    assert "im-age" not in entries[0]
    assert "im age" not in entries[0]
    assert "short-term" in entries[0], "a mid-line hyphen is printed text, not an artifact"


def test_a_hyphen_after_a_digit_survives_a_line_break():
    """A DOI split across a break keeps its hyphen - plos_sample.pdf really does this.

    A corrupted title finds nothing. A corrupted DOI can find somebody else's paper and
    assert it confidently, so this one exception is worth the branch.
    """
    text = (
        "[1] A. Author. A title. Lancet 383: 166-175. doi: 10.1016/S0140-\n"
        "6736(13)62227-8 PMID: 24411643.\n"
        "[2] B. B. Short. 2020."
    )
    entries = extractor.split_entries(text)
    assert "10.1016/S0140-6736(13)62227-8" in entries[0], entries[0]


def test_line_break_hyphens_are_healed_in_both_real_papers(sample_doc, plos_doc):
    """The measured payoff: the words that poisoned the title search are whole again."""
    arxiv = " || ".join(extractor.split_entries(sample_doc.references_text))
    assert "image recognition" in arxiv and "im-age" not in arxiv
    assert "Convolutional sequence" in arxiv and "Convolu-tional" not in arxiv

    plos = " || ".join(extractor.split_entries(plos_doc.references_text))
    assert "reproducibility of science" in plos and "sci-ence" not in plos
    assert "Pharmaceutical Research" in plos and "Pharma-ceutical" not in plos


def test_a_genuine_compound_broken_at_its_own_hyphen_loses_it(sample_doc, plos_doc):
    """The measured COST of the rule above, asserted so it cannot regress silently.

    "attention-"/"based" and "pre-"/"clinical" are genuine compounds that happen to
    break at their own hyphen, and the join position cannot tell them from "im-"/"age".
    2 words across 74 references against ~26 repaired ones. Separating them needs a
    dictionary. If this test ever fails, someone has added one - update the count.
    """
    arxiv = " || ".join(extractor.split_entries(sample_doc.references_text))
    assert "attentionbased" in arxiv and "attention-based" not in arxiv

    plos = " || ".join(extractor.split_entries(plos_doc.references_text))
    assert "preclinical research" in plos


def test_a_wrapped_line_starting_with_a_number_is_not_a_marker():
    """"2014. Some title" is not entry 2014 - the number must be the one due next."""
    text = "1. A. Author. A title. Journal 12:\n2014. Some continuation here.\n2. B. Writer. Another. 2020."
    entries = extractor.split_entries(text)
    assert len(entries) == 2
    assert "2014. Some continuation here." in entries[0]


def test_paren_markers_are_accepted():
    text = "1) A. Author. A title. 2021.\n2) B. Writer. Another title. 2020."
    assert len(extractor.split_entries(text)) == 2


def test_blank_line_fallback_for_author_year_styles():
    text = (
        "Author, A. (2021). A title without any marker. Journal of Things.\n\n"
        "Writer, B. (2020). Another unmarked title. Review of Stuff.\n\n"
        "Coder, C. (2019). A third one. Proceedings."
    )
    entries = extractor.split_entries(text)
    assert len(entries) == 3
    assert extractor.marker_style(text) == "blank-line"
    assert entries[0].startswith("Author, A. (2021)")


def test_empty_references_text_gives_no_entries():
    assert extractor.split_entries("") == []
    assert extractor.split_entries("   \n\n  ") == []


def test_image_only_pdf_splits_to_nothing():
    """An image-only PDF reaches the splitter as "" and must not raise."""
    doc = parse_pdf(IMAGE_ONLY)
    assert extractor.split_entries(doc.references_text) == []


# ---------------------------------------------------------------------------
# ref_id - the coupling point with Roy's golden labels
# ---------------------------------------------------------------------------
def test_ref_id_format_matches_the_golden_spec():
    """eval/golden/FORMAT.md owns this format. Ids are compared as opaque strings."""
    assert extractor.ref_id_for(1, 40) == "R01"
    assert extractor.ref_id_for(9, 40) == "R09"
    assert extractor.ref_id_for(40, 40) == "R40"
    # Width is decided by the DOCUMENT, so one file never mixes widths.
    assert extractor.ref_id_for(1, 120) == "R001"
    assert extractor.ref_id_for(99, 120) == "R099"


def test_claim_id_format_matches_the_b1_fixture():
    assert claims_mod.claim_id_for(1, 8) == "C01"
    assert claims_mod.claim_id_for(1, 150) == "C001"


# ---------------------------------------------------------------------------
# The stub model
# ---------------------------------------------------------------------------
class _Reply:
    def __init__(self, content: str) -> None:
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class StubClient:
    """Replays a canned reply per entry and counts calls, so tests can assert on both.

    Shaped like the OpenAI client only where extractor touches it - one method - which
    is the whole reason extract_references takes an injectable client.
    """

    def __init__(self, replies: dict[str, str] | None = None, default: str | None = None) -> None:
        self.replies = replies or {}
        self.default = default if default is not None else json.dumps(
            {
                "title": "A stubbed title",
                "authors": ["A. Author"],
                "year": 2021,
                "doi": None,
                "arxiv_id": None,
                "venue": "Journal of Stubs",
            }
        )
        self.calls: list[str] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, *, model, temperature, messages, timeout):  # noqa: ANN001
        entry = messages[-1]["content"]
        self.calls.append(entry)
        for needle, reply in self.replies.items():
            if needle in entry:
                return _Reply(reply)
        return _Reply(self.default)


def _tiny_doc(references_text: str, body_text: str = "", pages: list[str] | None = None) -> ParsedDocument:
    return ParsedDocument(
        name="tiny.pdf",
        pages=pages if pages is not None else [body_text or "body", references_text],
        body_text=body_text,
        references_text=references_text,
        ref_start_page=2,
    )


TWO_ENTRIES = "[1] A. Author. First title. Journal, 2021.\n[2] B. Writer. Second title. Review, 2020."


# ---------------------------------------------------------------------------
# Step 3: extraction never drops an entry
# ---------------------------------------------------------------------------
def test_every_entry_comes_back():
    doc = _tiny_doc(TWO_ENTRIES)
    client = StubClient()
    refs, malformed = extractor.extract_references(doc, client=client)
    assert len(refs) == 2 == len(extractor.split_entries(doc.references_text))
    assert [r.ref_id for r in refs] == ["R01", "R02"]
    assert malformed == frozenset()
    assert len(client.calls) == 2, "one call per entry, not one for the block"


def test_forty_entries_yield_forty_references(sample_doc):
    client = StubClient()
    refs, _malformed = extractor.extract_references(sample_doc, client=client)
    assert len(refs) == SAMPLE_ENTRIES
    assert [r.ref_id for r in refs] == [f"R{n:02d}" for n in range(1, SAMPLE_ENTRIES + 1)]


def test_raw_text_is_always_the_split_entry_not_the_model():
    doc = _tiny_doc(TWO_ENTRIES)
    entries = extractor.split_entries(doc.references_text)
    refs, _ = extractor.extract_references(doc, client=StubClient())
    assert [r.raw_text for r in refs] == entries


@pytest.mark.parametrize(
    "bad_reply",
    [
        "not json at all",
        "",
        "[1, 2, 3]",
        '{"title": "T", "surprise": "extra key"}',
        '{"title": "T", "authors": "not a list"}',
        '{"title": "T", "authors": [1, 2]}',
        '{"title": ',
    ],
    ids=["prose", "empty", "array", "extra-key", "authors-str", "authors-ints", "truncated"],
)
def test_a_mangled_reply_yields_malformed_with_raw_text_preserved(bad_reply):
    doc = _tiny_doc(TWO_ENTRIES)
    client = StubClient(replies={"First title": bad_reply})
    refs, malformed = extractor.extract_references(doc, client=client)

    assert len(refs) == 2, "a bad reply must never drop the entry"
    bad, good = refs[0], refs[1]
    assert malformed == {"R01"}, "the failure is recorded in the side-channel"
    assert bad.ref_id == "R01"
    assert bad.raw_text.startswith("[1] A. Author.")
    assert bad.title is None and bad.authors == [] and bad.year is None
    assert good.ref_id not in malformed
    # Retried once before giving up: config says max_retries 1.
    retries = settings.llm_settings()["max_retries"]
    assert sum(1 for c in client.calls if "First title" in c) == retries + 1


def test_a_raising_client_still_returns_every_entry():
    """A dead gateway is a malformed run, not a crash."""

    class Dead(StubClient):
        def create(self, **kwargs):  # noqa: ANN003
            self.calls.append(kwargs["messages"][-1]["content"])
            raise RuntimeError("gateway down")

    doc = _tiny_doc(TWO_ENTRIES)
    refs, malformed = extractor.extract_references(doc, client=Dead())
    assert len(refs) == 2
    assert malformed == {"R01", "R02"}
    assert [r.raw_text[:7] for r in refs] == ["[1] A. ", "[2] B. "]


def test_fields_are_parsed_off_the_reply():
    reply = json.dumps(
        {
            "title": "Layer normalization",
            "authors": ["Jimmy Lei Ba", "Jamie Ryan Kiros"],
            "year": "2016",
            "doi": "https://doi.org/10.1000/XYZ",
            "arxiv_id": "1607.06450",
            "venue": "arXiv preprint",
        }
    )
    # Both identifiers are PRINTED in the entry. They have to be: since D-109 the
    # extractor drops an identifier it cannot point to on the page, so an entry with no
    # ids printed would test the guard rather than the field parsing.
    doc = _tiny_doc(
        "[1] Jimmy Lei Ba, Jamie Ryan Kiros. Layer normalization. arXiv preprint "
        "arXiv:1607.06450, 2016. doi: 10.1000/XYZ.\n"
        "[2] B. Writer. Second title. Review, 2020."
    )
    refs, _ = extractor.extract_references(doc, client=StubClient(default=reply))
    ref = refs[0]
    assert ref.title == "Layer normalization"
    assert ref.authors == ["Jimmy Lei Ba", "Jamie Ryan Kiros"]
    assert ref.year == 2016, "a year given as a string is still a year"
    # The contract normalises the DOI; the extractor does not invent one. The reply
    # prints it as a doi.org URL and the entry prints it bare and upper-cased - D-109
    # compares provenance, not format, so both survive.
    assert ref.doi == "10.1000/xyz"
    assert ref.arxiv_id == "1607.06450"


def test_a_fenced_reply_is_still_parsed():
    reply = '```json\n{"title": "T", "authors": [], "year": null, "doi": null, "arxiv_id": null, "venue": null}\n```'
    doc = _tiny_doc(TWO_ENTRIES)
    refs, malformed = extractor.extract_references(doc, client=StubClient(default=reply))
    assert refs[0].title == "T"
    assert malformed == frozenset()


def test_no_entries_means_no_calls_and_no_references():
    doc = _tiny_doc("")
    client = StubClient()
    references, malformed = extractor.extract_references(doc, client=client)
    assert references == [] and malformed == frozenset()
    assert client.calls == []


# ---------------------------------------------------------------------------
# Cache and determinism
# ---------------------------------------------------------------------------
def test_the_second_run_is_a_cache_hit_and_makes_no_calls():
    doc = _tiny_doc(TWO_ENTRIES)
    client = StubClient()

    first, _ = extractor.extract_references(doc, client=client)
    assert len(client.calls) == 2

    second, _ = extractor.extract_references(doc, client=client)
    assert len(client.calls) == 2, "the second run called the model again"
    assert [r.model_dump() for r in first] == [r.model_dump() for r in second]
    assert extractor.cache_path().exists()


def test_two_runs_produce_byte_identical_json():
    """The determinism gate, with the model held constant by the stub."""
    doc = _tiny_doc(TWO_ENTRIES)
    client = StubClient()

    def dump(result):
        return json.dumps([r.model_dump() for r in result.references], sort_keys=True, indent=2)

    assert dump(extractor.extract_references(doc, client=client)) == dump(
        extractor.extract_references(doc, client=client)
    )


def test_the_cache_key_depends_on_the_prompt_version(monkeypatch):
    """A reworded prompt must not be served an answer from the old wording."""
    before = extractor.cache_key("entry", "m", 0.1, 1)
    monkeypatch.setattr(prompts, "PROMPT_VERSION", "p2-extractor-vNEXT")
    assert extractor.cache_key("entry", "m", 0.1, 1) != before


@pytest.mark.parametrize(
    "kwargs",
    [
        {"entry": "other"},
        {"model": "other-model"},
        {"temperature": 0.9},
        {"schema_version": 99},
    ],
    ids=["entry", "model", "temperature", "schema_version"],
)
def test_every_cache_key_input_changes_the_key(kwargs):
    base = {"entry": "e", "model": "m", "temperature": 0.1, "schema_version": 1}
    assert extractor.cache_key(**base) != extractor.cache_key(**{**base, **kwargs})


def test_a_corrupt_cache_file_is_a_miss_not_a_crash():
    extractor.cache_path().write_text("{ this is not json", encoding="utf-8")
    doc = _tiny_doc(TWO_ENTRIES)
    refs, _ = extractor.extract_references(doc, client=StubClient())
    assert len(refs) == 2


def test_a_stale_cached_reply_is_re_fetched():
    """A cached reply that no longer validates is a miss, not a malformed reference."""
    doc = _tiny_doc(TWO_ENTRIES)
    client = StubClient()
    extractor.extract_references(doc, client=client)
    cache = json.loads(extractor.cache_path().read_text(encoding="utf-8"))
    poisoned = {key: "no longer valid json" for key in cache}
    extractor.cache_path().write_text(json.dumps(poisoned), encoding="utf-8")

    calls_before = len(client.calls)
    refs, malformed = extractor.extract_references(doc, client=client)
    assert len(client.calls) > calls_before, "a stale cached reply must be re-fetched"
    assert malformed == frozenset()


# ---------------------------------------------------------------------------
# Step 4: claims
# ---------------------------------------------------------------------------
def test_claims_map_to_ref_ids_in_both_directions(sample_doc):
    entries = extractor.split_entries(sample_doc.references_text)
    refs = [
        Reference(ref_id=extractor.ref_id_for(i, len(entries)), raw_text=e)
        for i, e in enumerate(entries, start=1)
    ]
    found = claims_mod.extract_claims(sample_doc, refs)

    assert found, "sample.pdf cites 63 markers; zero claims means the regex is broken"
    assert all(isinstance(c, Claim) for c in found)
    assert [c.claim_id for c in found] == [f"C{n:02d}" for n in range(1, len(found) + 1)]

    by_id = {r.ref_id: r for r in refs}
    for claim in found:
        for ref_id in claim.ref_ids:
            assert ref_id in by_id, f"{claim.claim_id} cites unknown {ref_id}"
            assert claim.claim_id in by_id[ref_id].cited_by_claims, (
                f"{ref_id} does not point back at {claim.claim_id}"
            )
    # And the reverse direction has no ids that no claim actually made.
    for ref in refs:
        for claim_id in ref.cited_by_claims:
            claim = next(c for c in found if c.claim_id == claim_id)
            assert ref.ref_id in claim.ref_ids


def test_claim_pages_are_body_pages_only(sample_doc):
    entries = extractor.split_entries(sample_doc.references_text)
    refs = [Reference(ref_id=extractor.ref_id_for(i, len(entries)), raw_text=e) for i, e in enumerate(entries, 1)]
    found = claims_mod.extract_claims(sample_doc, refs)
    assert sample_doc.ref_start_page == 10
    assert all(c.page is not None and 1 <= c.page < 10 for c in found), (
        "a claim was found in the reference list itself"
    )


def test_marker_forms_are_all_expanded():
    doc = _tiny_doc(
        "[1] A. 2021.\n[2] B. 2020.\n[3] C. 2019.\n[4] D. 2018.",
        body_text="",
        pages=["We cite one thing [1]. We cite two [2, 3]. We cite a range [1-3]. And [4].", "refs"],
    )
    refs = [Reference(ref_id=f"R0{n}", raw_text=f"[{n}] x") for n in range(1, 5)]
    found = claims_mod.extract_claims(doc, refs)
    cited = [c.ref_ids for c in found]
    assert ["R01"] in cited
    assert ["R02", "R03"] in cited
    assert ["R01", "R02", "R03"] in cited, "a range [1-3] must expand, not read as [1, 3]"
    assert ["R04"] in cited


def test_a_marker_past_the_end_of_the_list_is_ignored():
    doc = _tiny_doc("[1] A. 2021.\n[2] B. 2020.", pages=["Table [99] is not a citation, but [2] is.", "refs"])
    refs = [Reference(ref_id="R01", raw_text="[1] A"), Reference(ref_id="R02", raw_text="[2] B")]
    found = claims_mod.extract_claims(doc, refs)
    assert [c.ref_ids for c in found] == [["R02"]]


def test_a_bracket_that_is_not_numeric_is_not_a_marker():
    doc = _tiny_doc("[1] A. 2021.\n[2] B. 2020.", pages=["See [Fig. 1] and [] and [1].", "refs"])
    refs = [Reference(ref_id="R01", raw_text="[1] A"), Reference(ref_id="R02", raw_text="[2] B")]
    found = claims_mod.extract_claims(doc, refs)
    assert [c.ref_ids for c in found] == [["R01"]]


def test_uncited_entries_are_recorded_as_uncited_not_dropped(sample_doc):
    """orphan is P5's to stamp. P2 only records the map."""
    entries = extractor.split_entries(sample_doc.references_text)
    refs = [Reference(ref_id=extractor.ref_id_for(i, len(entries)), raw_text=e) for i, e in enumerate(entries, 1)]
    claims_mod.extract_claims(sample_doc, refs)
    assert len(refs) == SAMPLE_ENTRIES, "no reference may be dropped for being uncited"
    assert any(not r.cited_by_claims for r in refs), "sample.pdf has entries cited by nothing"
    assert any(r.cited_by_claims for r in refs)


def test_extract_claims_is_idempotent(sample_doc):
    """Called twice, cited_by_claims must not accumulate duplicates."""
    entries = extractor.split_entries(sample_doc.references_text)
    refs = [Reference(ref_id=extractor.ref_id_for(i, len(entries)), raw_text=e) for i, e in enumerate(entries, 1)]
    first = claims_mod.extract_claims(sample_doc, refs)
    snapshot = [list(r.cited_by_claims) for r in refs]
    second = claims_mod.extract_claims(sample_doc, refs)
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]
    assert [list(r.cited_by_claims) for r in refs] == snapshot


def test_no_refs_means_no_claims(sample_doc):
    assert claims_mod.extract_claims(sample_doc, []) == []


# ---------------------------------------------------------------------------
# Ground rules
# ---------------------------------------------------------------------------
def test_the_stage_reads_its_model_from_config():
    assert extractor._STAGE == "extractor"
    assert settings.model_for("extractor")  # raises if the key is gone


@pytest.mark.parametrize("module", [extractor, claims_mod, prompts])
def test_no_model_name_is_hardcoded(module):
    """The ground-rule grep as a test, so it fails locally before CI says so."""
    source = Path(module.__file__).read_text(encoding="utf-8")
    banned = re.compile(r"qwen|glm|gemma|gpt-4|claude-|sk-[A-Za-z0-9_-]{8,}", re.IGNORECASE)
    assert not banned.search(source), f"{module.__name__} names a model or a key"


def test_no_network_library_is_imported():
    """P2 talks to the gateway through src.llm and to nothing else."""
    for module in (extractor, claims_mod, prompts):
        source = Path(module.__file__).read_text(encoding="utf-8")
        for library in ("requests", "urllib", "httpx", "aiohttp", "socket"):
            assert not re.search(rf"^\s*(?:import|from)\s+{library}\b", source, re.M), (
                f"{module.__name__} imports {library}"
            )


# ---------------------------------------------------------------------------
# The one live test
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not (os.getenv("AIR_API_KEY") and os.getenv("AIR_BASE_URL")),
    reason="needs AIR credentials; the rest of this file runs offline",
)
def test_live_smoke_one_entry_through_the_real_gateway(monkeypatch, tmp_path):
    """One real call, one entry. Proves the wiring, not the model's quality."""
    monkeypatch.setattr(extractor, "cache_path", lambda: tmp_path / "live.json")
    doc = _tiny_doc(
        "[1] Jimmy Lei Ba, Jamie Ryan Kiros, and Geoffrey E Hinton. Layer normalization. "
        "arXiv preprint arXiv:1607.06450, 2016.\n"
        "[2] Dzmitry Bahdanau, Kyunghyun Cho, and Yoshua Bengio. Neural machine translation "
        "by jointly learning to align and translate. CoRR, abs/1409.0473, 2014."
    )
    refs, malformed = extractor.extract_references(doc)
    assert len(refs) == 2
    assert malformed == frozenset(), f"live extraction failed on {sorted(malformed)}"
    assert refs[0].title is not None, f"live extraction returned nothing usable: {refs[0]}"
    # Both printed forms of an arXiv id must come back, per the prompt's rule 3.
    assert refs[0].arxiv_id == "1607.06450"
    assert refs[1].arxiv_id == "1409.0473"
    # And nothing was invented: neither entry prints a DOI.
    assert refs[0].doi is None and refs[1].doi is None


def test_both_extraction_entry_points_import_from_extractor():
    """The P2 card names these two as one public interface, and the agreed interface
    table in scripts/update_status.py looks for both on src.ingest.extractor."""
    from src.ingest.extractor import extract_claims as reexported
    from src.ingest.extractor import extract_references  # noqa: F401

    assert reexported is claims_mod.extract_claims


# ---------------------------------------------------------------------------
# The reason malformed is a side-channel and not a predicate - D-102
# ---------------------------------------------------------------------------
def test_a_titleless_but_correctly_parsed_reference_is_NOT_malformed():
    """The bug the side-channel exists to prevent.

    A standard, a dataset, a "personal communication" genuinely has no title. That is a
    successful extraction of a titleless work, not a failed extraction - and the old
    ``is_malformed(ref) == (ref.title is None)`` predicate could not tell the two apart.
    Roy's corpus carries a genuine-unresolvable row to exercise this path; stamping
    ``malformed`` on an ``injected: false`` entry costs a row of recall that presents as
    a P5 bug.
    """
    titleless = json.dumps(
        {
            "title": None,
            "authors": ["International Organization for Standardization"],
            "year": 2015,
            "doi": None,
            "arxiv_id": None,
            "venue": "ISO 9001:2015",
        }
    )
    doc = _tiny_doc(TWO_ENTRIES)
    references, malformed = extractor.extract_references(
        doc, client=StubClient(replies={"First title": titleless})
    )

    assert references[0].title is None, "the fixture is only meaningful with a null title"
    assert references[0].authors == ["International Organization for Standardization"]
    assert references[0].year == 2015
    assert "R01" not in malformed, (
        "a well-formed reply with a null title is a titleless work, not a failure"
    )
    assert malformed == frozenset()


def test_malformed_is_reported_by_id_not_by_inspecting_fields():
    """A malformed entry and a titleless one are indistinguishable by field, on purpose:
    that is why the truth has to come from the extraction attempt."""
    all_null = json.dumps(
        {"title": None, "authors": [], "year": None, "doi": None, "arxiv_id": None, "venue": None}
    )
    doc = _tiny_doc(TWO_ENTRIES)
    references, malformed = extractor.extract_references(
        doc, client=StubClient(replies={"First title": all_null, "Second title": "garbage"})
    )
    parsed_as_empty, failed = references[0], references[1]
    # Field-identical...
    assert parsed_as_empty.title is None and failed.title is None
    assert parsed_as_empty.authors == failed.authors == []
    # ...and still correctly distinguished.
    assert malformed == {"R02"}


def test_the_result_is_tuple_compatible_and_named():
    doc = _tiny_doc(TWO_ENTRIES)
    result = extractor.extract_references(doc, client=StubClient())
    references, malformed = result
    assert result.references is references
    assert result.malformed_ref_ids is malformed
    assert isinstance(malformed, frozenset)


def test_is_malformed_is_gone():
    """Deleted rather than deprecated: a predicate that is wrong on real data should not
    stay importable where P5 might reach for it. See D-102."""
    assert not hasattr(extractor, "is_malformed")


# ---------------------------------------------------------------------------
# The invented-identifier guard - D-109
#
# Our pitch is that a tool can catch citations that look real and are not. An extractor
# that invents an identifier is that exact failure inside our own tool, so this is a
# structural guarantee rather than a prompt instruction.
# ---------------------------------------------------------------------------

#: paper1 R24, verbatim off the page. There is NO identifier in this text - "arXiv
#: preprint (2017)" and nothing else - and the extractor returned 1706.05555, which is a
#: real arXiv paper about BCS-BEC hydrodynamics. It resolved, disagreed with every field
#: of the reference, and scored our only false `conflict` on the demo paper.
#: The marker is renumbered [24] -> [1] and only the marker: `split_entries` accepts a
#: numbered style only when the markers run monotonically from 1, so a two-entry fixture
#: starting at 24 falls through to the blank-line split and comes back as one entry.
R24_RAW = (
    "[1] M. Smieja, B. C. Geiger, Semi-supervised cross-entropy clustering with "
    "information bottleneck constraint, arXiv preprint (2017)."
)

R24_REPLY = json.dumps(
    {
        "title": "Semi-supervised cross-entropy clustering with information bottleneck constraint",
        "authors": ["M. Smieja", "B. C. Geiger"],
        "year": 2017,
        "doi": None,
        "arxiv_id": "1706.05555",
        "venue": "arXiv preprint",
    }
)


def test_an_identifier_not_in_the_printed_text_is_dropped():
    """The R24 case, verbatim. The invention must not reach the resolver."""
    notes: list[str] = []
    doc = _tiny_doc(R24_RAW + "\n[2] B. Writer. Second title. Review, 2020.")
    with pytest.warns(RuntimeWarning, match="does not appear in the printed reference"):
        refs, malformed = extractor.extract_references(
            doc, client=StubClient(replies={"Semi-supervised": R24_REPLY}), notes=notes
        )

    ref = refs[0]
    assert ref.arxiv_id is None, "an identifier we cannot point to on the page is dropped"
    assert ref.title, "the rest of the extraction is untouched - this is not a bad entry"
    assert ref.authors == ["M. Smieja", "B. C. Geiger"]
    assert ref.year == 2017
    assert ref.raw_text == R24_RAW, "the printed text is preserved either way"


def test_a_dropped_identifier_is_recorded_in_notes():
    notes: list[str] = []
    doc = _tiny_doc(R24_RAW + "\n[2] B. Writer. Second title. Review, 2020.")
    with pytest.warns(RuntimeWarning):
        extractor.extract_references(
            doc, client=StubClient(replies={"Semi-supervised": R24_REPLY}), notes=notes
        )
    assert len(notes) == 1, notes
    assert "1706.05555" in notes[0]
    assert "R01" in notes[0]
    assert "D-109" in notes[0]


def test_a_dropped_identifier_is_NOT_malformed():
    """D-102's indicator means the extraction attempt produced nothing usable.

    An entry whose title, authors and year are perfect and whose id was invented is a
    good extraction with one bad field. Once the field is gone it resolves by title like
    any other reference that printed no identifier - marking it malformed would cost it
    a row of recall and tell a reviewer something untrue.
    """
    doc = _tiny_doc(R24_RAW + "\n[2] B. Writer. Second title. Review, 2020.")
    with pytest.warns(RuntimeWarning):
        _refs, malformed = extractor.extract_references(
            doc, client=StubClient(replies={"Semi-supervised": R24_REPLY})
        )
    assert malformed == frozenset(), "a nulled identifier is not a failed extraction"


def test_notes_are_optional_and_a_dropped_identifier_still_warns():
    """`notes` may be discarded by a caller, so this event is never only a note."""
    doc = _tiny_doc(R24_RAW + "\n[2] B. Writer. Second title. Review, 2020.")
    with pytest.warns(RuntimeWarning, match="1706.05555"):
        extractor.extract_references(doc, client=StubClient(replies={"Semi-supervised": R24_REPLY}))


@pytest.mark.parametrize(
    ("printed", "returned"),
    [
        # The two forms both real papers actually print, off sample.pdf.
        ("arXiv preprint arXiv:1607.06450, 2016.", "1607.06450"),
        ("CoRR, abs/1409.0473, 2014.", "1409.0473"),
        # And the forms a model is liable to hand back for them.
        ("arXiv preprint arXiv:1607.06450, 2016.", "arXiv:1607.06450"),
        ("CoRR, abs/1409.0473, 2014.", "abs/1409.0473"),
        # A version suffix the printed reference omits is the same identifier.
        ("arXiv preprint arXiv:1706.05555, 2017.", "1706.05555v1"),
        # pdfplumber renders a real PLOS DOI with a space after the registrant prefix.
        ("doi: 10. 1016/j.ajpath.2014.11.001 PMID: 25451152", "10.1016/j.ajpath.2014.11.001"),
        # A doi.org URL against a bare printed DOI, and the reverse.
        ("doi:10.1038/505483f", "https://doi.org/10.1038/505483F"),
        ("Available at https://doi.org/10.1038/505483f", "10.1038/505483f"),
    ],
)
def test_a_printed_identifier_survives_untouched(printed, returned):
    """False positives cost a resolution, so the matcher compares provenance, not format."""
    assert extractor._identifier_is_printed(returned, f"[1] A. Author. A title. {printed}")


def test_both_real_printed_forms_still_extract(sample_doc):
    """End to end on the real paper: the guard must not eat sample.pdf's identifiers.

    22 of 40 entries carry an arXiv id and the arxiv_id branch resolves them - if this
    guard were too strict it would silently push them onto the title search, which is
    the branch D-108 exists because of.
    """
    reply_for = lambda ident: json.dumps(  # noqa: E731
        {"title": "T", "authors": ["A. Author"], "year": 2016,
         "doi": None, "arxiv_id": ident, "venue": "arXiv"}
    )
    entries = extractor.split_entries(sample_doc.references_text)
    ba = next(e for e in entries if "arXiv:1607.06450" in e)
    bahdanau = next(e for e in entries if "abs/1409.0473" in e)

    for entry, ident in ((ba, "1607.06450"), (bahdanau, "1409.0473")):
        ref = extractor._reference_from_reply(reply_for(ident), "R01", entry)
        assert ref.arxiv_id == ident, f"the guard ate a printed identifier in {entry[:40]!r}"


def test_the_guard_rejects_an_identifier_that_merely_looks_similar():
    """Armed, not vacuously true: a near-miss digit is still an invention."""
    entry = "[1] A. Author. A title. arXiv preprint arXiv:1607.06450, 2016."
    assert not extractor._identifier_is_printed("1607.06451", entry)
    assert not extractor._identifier_is_printed("10.1000/xyz", entry)


def test_year_is_deliberately_not_guarded():
    """Recorded as a decision, not an oversight - D-109.

    A year cannot cause a wrong resolution, which is the harm the guard exists to
    prevent, and a containment test over it would fire on correct extractions.
    """
    reply = json.dumps(
        {"title": "T", "authors": [], "year": 2016, "doi": None, "arxiv_id": None, "venue": None}
    )
    ref = extractor._reference_from_reply(reply, "R01", "[1] A. Author. A title. No year printed.")
    assert ref.year == 2016
