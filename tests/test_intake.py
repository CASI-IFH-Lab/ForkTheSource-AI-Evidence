"""P1 - PDF intake. What comes out of parse_pdf, on real papers and on hard fixtures.

FIXTURE PROVENANCE. The two real papers are committed so the heading regex and the
body/references split are exercised against real typesetting rather than against a
fixture written to make them pass.

    tests/data/sample.pdf
        "Attention Is All You Need", Vaswani et al., arXiv:1706.03762v7.
        https://arxiv.org/pdf/1706.03762v7
        Licence: arXiv.org perpetual, non-exclusive licence 1.0
        https://arxiv.org/licenses/nonexclusive-distrib/1.0/
        Chosen because it is single-column, has bracketed [1] reference numbering -
        the shape P2's pre-splitter is written against - and a plain "References"
        heading. 15 pages, 2.2 MB.

    tests/data/plos_sample.pdf
        "The Economics of Reproducibility in Preclinical Research", Freedman, Cockburn
        and Simcoe, PLOS Biology 13(6):e1002165, 2015. doi:10.1371/journal.pbio.1002165
        https://journals.plos.org/plosbiology/article/file?id=10.1371/journal.pbio.1002165&type=printable
        Licence: CC BY 4.0 - https://creativecommons.org/licenses/by/4.0/
        A second real paper, unambiguously redistributable, and numbered "1." rather
        than "[1]" so the suite covers both real-world reference styles. 9 pages, 356 KB.

The four synthetic fixtures are built by tests/data/make_fixtures.py; each one pins
down a behaviour a real paper cannot. See that file for what and why.
"""

import ast
from pathlib import Path

import pdfplumber
import pytest

from src.ingest import pdf_parser as intake
from src.ingest.pdf_parser import ParsedDocument, parse_pdf

DATA = Path(__file__).parent / "data"
SAMPLE = DATA / "sample.pdf"
PLOS = DATA / "plos_sample.pdf"
SYNTHETIC = DATA / "synthetic.pdf"
NO_HEADING = DATA / "no_heading.pdf"
FALSE_HEADING = DATA / "false_heading.pdf"
IMAGE_ONLY = DATA / "image_only.pdf"

# A third real PDF, already in the repo, for the "runs on 3 real PDFs" check. Not a
# paper - which is the point: it is real output from a real typesetter and nothing
# about it was chosen to suit this module.
PLAN = Path(__file__).resolve().parents[1] / "docs" / "module_implementation_plan.pdf"

# The first numbered entry of sample.pdf's reference list, as it actually comes out.
SAMPLE_FIRST_REF = (
    "[1] Jimmy Lei Ba, Jamie Ryan Kiros, and Geoffrey E Hinton. Layer normalization."
)


# Parsing a 15-page paper costs about a second, and a dozen tests read the same result.
# Session-scoped so the suite pays for each real paper once. Tests that are ABOUT calling
# parse_pdf - determinism, name handling - call it directly instead.
@pytest.fixture(scope="session")
def sample_doc() -> ParsedDocument:
    return parse_pdf(SAMPLE)


@pytest.fixture(scope="session")
def plos_doc() -> ParsedDocument:
    return parse_pdf(PLOS)


@pytest.fixture(scope="session")
def sample_pages() -> list[str]:
    return intake.extract_pages(SAMPLE)


@pytest.mark.parametrize(
    "fixture",
    [SAMPLE, PLOS, SYNTHETIC, NO_HEADING, FALSE_HEADING, IMAGE_ONLY],
    ids=lambda p: p.name,
)
def test_fixtures_are_present(fixture: Path):
    assert fixture.exists(), f"missing fixture - run: python {DATA / 'make_fixtures.py'}"


# ---------------------------------------------------------------------------
# The B0 assertions, moved rather than deleted.
#
# B0 asserted on the hand-written one-page fixture that used to be sample.pdf. P1
# replaced sample.pdf with a real paper, so those two assertions now read the same
# fixture under its new name, synthetic.pdf, with their strings unchanged. Nothing was
# weakened: the same claims are still made about the same bytes.
# ---------------------------------------------------------------------------
def test_extract_text_reads_the_body():
    text = intake.extract_text(SYNTHETIC)
    assert "ForkTheSource Sample Document" in text
    assert "This is a sample document for intake tests." in text


def test_extract_text_reads_the_reference_list():
    text = intake.extract_text(SYNTHETIC)
    assert "References" in text
    assert "Journal of Tests, 12(3):45-67, 2021" in text
    assert "Review of Examples, 5(1):10-20, 2023" in text


def test_bytes_and_path_give_the_same_text():
    assert intake.extract_text(SYNTHETIC.read_bytes()) == intake.extract_text(SYNTHETIC)


def test_extract_pages_keeps_one_entry_per_page(sample_pages):
    assert len(intake.extract_pages(SYNTHETIC)) == 1
    assert len(sample_pages) == 15


def test_run_reports_what_it_read():
    result = intake.run(SYNTHETIC, None)
    assert result["page_count"] == 1
    assert result["text"] == intake.extract_text(SYNTHETIC)
    assert len(result["pages"]) == 1


def test_run_requires_a_config_argument():
    """Every stage entry point takes (input, config) so P6 can call them uniformly."""
    with pytest.raises(TypeError):
        intake.run(SYNTHETIC)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# The real paper: the split, and the reading order P2 depends on
# ---------------------------------------------------------------------------
def test_parse_pdf_on_the_real_sample(sample_doc):
    doc = sample_doc
    assert isinstance(doc, ParsedDocument)
    assert doc.name == "sample.pdf"
    assert len(doc.pages) == 15
    assert doc.notes == [], f"the sample should read cleanly, got: {doc.notes}"


def test_references_text_is_not_empty_and_starts_at_the_first_entry(sample_doc):
    doc = sample_doc
    assert doc.references_text.strip(), "references_text must never be silently empty"
    assert SAMPLE_FIRST_REF in doc.references_text
    # The heading is a separator and belongs to neither side, so the block opens on
    # the first entry rather than on the word "References".
    assert doc.references_text.lstrip().startswith("[1]")


def test_ref_start_page_is_the_page_the_heading_is_on(sample_doc):
    doc = sample_doc
    assert doc.ref_start_page == 10
    # 1-based, so this is the indexing contract downstream relies on.
    assert "References" in doc.pages[doc.ref_start_page - 1]


def test_the_body_stops_where_the_references_start(sample_doc):
    doc = sample_doc
    assert "Attention Is All You Need" in doc.body_text
    assert SAMPLE_FIRST_REF not in doc.body_text
    assert "Attention Is All You Need" not in doc.references_text


def test_reference_entries_come_out_in_reading_order(sample_doc):
    """The entries must be sequential. P2's pre-splitter is written against this."""
    doc = sample_doc
    positions = [doc.references_text.find(f"[{n}] ") for n in range(1, 11)]
    assert all(p != -1 for p in positions), f"missing entry markers: {positions}"
    assert positions == sorted(positions), f"reference entries are out of order: {positions}"


def test_word_spacing_survives_extraction(sample_doc, plos_doc):
    """The x_tolerance_ratio guard, and the reason it is a test rather than a constant.

    pdfplumber's default x_tolerance glues this paper into
    'JimmyLeiBa,JamieRyanKiros,andGeoffreyEHinton'. If someone removes the ratio, the
    text still extracts, the split still works, and every other test still passes -
    while P2 silently receives unsplittable garbage. This is the only thing that fails.
    """
    doc = sample_doc
    assert "Jimmy Lei Ba" in doc.references_text
    assert "JimmyLeiBa" not in doc.references_text
    plos = plos_doc
    assert "Collins FS" in plos.references_text
    assert "CollinsFS" not in plos.references_text


def test_the_second_real_paper_splits_too(plos_doc):
    """PLOS numbers references "1." not "[1]" - both styles are real and must work."""
    doc = plos_doc
    assert doc.ref_start_page == 7
    assert doc.notes == [], f"the PLOS sample should read cleanly, got: {doc.notes}"
    assert doc.references_text.lstrip().startswith("1. Collins FS")


def test_parse_pdf_runs_on_three_real_pdfs_without_raising(sample_doc, plos_doc):
    """Three real PDFs from three different typesetters, none of them ours."""
    for doc in (sample_doc, plos_doc, parse_pdf(PLAN)):
        assert doc.pages
        assert isinstance(doc.references_text, str)
        assert isinstance(doc.notes, list)


# ---------------------------------------------------------------------------
# The hard fixtures
# ---------------------------------------------------------------------------
def test_no_heading_takes_the_fallback_and_says_so():
    doc = parse_pdf(NO_HEADING)
    assert len(doc.pages) == 8
    # int(8 * 0.15) == 1, so the window is exactly the last page - a pass means the
    # fallback found the references, not that it cast a wide enough net to get lucky.
    assert doc.ref_start_page == 8
    assert doc.references_text.lstrip().startswith("[1]")
    assert "Annals of Recursion" in doc.references_text
    assert any("no references heading found" in note for note in doc.notes), doc.notes
    assert any("last 1 of 8" in note for note in doc.notes), doc.notes
    # And the body did not come along for the ride.
    assert "[1] A. Author" not in doc.body_text
    assert doc.body_text.strip()


def test_the_fallback_is_never_silently_empty():
    doc = parse_pdf(NO_HEADING)
    assert doc.references_text.strip()
    assert doc.notes, "the fallback firing must always be recorded"


def test_false_heading_splits_at_the_later_heading():
    doc = parse_pdf(FALSE_HEADING)
    # "References" appears alone on a line in the contents list on page 1 and again as
    # the real heading on page 3. The split belongs on page 3.
    assert doc.ref_start_page == 3
    assert doc.references_text.lstrip().startswith("[1]")
    assert "Contents" in doc.body_text
    assert "1 Introduction" in doc.body_text
    assert any("split at the last one" in note for note in doc.notes), doc.notes


def test_the_word_inside_a_sentence_is_not_a_heading():
    """"...consult the references listed at the end..." must not split anything."""
    doc = parse_pdf(FALSE_HEADING)
    assert "references listed at the end" in doc.body_text
    assert doc.ref_start_page == 3


def test_image_only_returns_a_valid_document_and_does_not_raise():
    doc = parse_pdf(IMAGE_ONLY)
    assert isinstance(doc, ParsedDocument)
    assert len(doc.pages) == 2
    assert doc.pages == ["", ""], "a page with no text layer is empty, never dropped"
    assert doc.body_text == ""
    assert doc.references_text == ""
    assert doc.ref_start_page is None
    assert any("no extractable text" in note for note in doc.notes), doc.notes


def test_a_page_that_raises_is_skipped_with_a_note(monkeypatch):
    """One unreadable page must not cost the other seven."""
    real_extract = pdfplumber.page.Page.extract_text

    def flaky(self, *args, **kwargs):
        if self.page_number == 2:
            raise RuntimeError("synthetic font failure")
        return real_extract(self, *args, **kwargs)

    monkeypatch.setattr(pdfplumber.page.Page, "extract_text", flaky)

    doc = parse_pdf(NO_HEADING)
    assert len(doc.pages) == 8, "the failed page is kept as empty text, not dropped"
    assert doc.pages[1] == ""
    assert any("page 2" in note and "RuntimeError" in note for note in doc.notes), doc.notes
    # Every other page still came back, including the reference list on page 8.
    assert doc.pages[0].strip()
    assert "Annals of Recursion" in doc.pages[7]
    assert doc.references_text.strip()


# ---------------------------------------------------------------------------
# Contract properties
# ---------------------------------------------------------------------------
def test_two_calls_produce_equal_documents():
    assert parse_pdf(SAMPLE) == parse_pdf(SAMPLE)


def test_tables_ship_empty_in_phase_one(sample_doc, plos_doc):
    assert sample_doc.tables == []
    assert plos_doc.tables == []
    for fixture in (SYNTHETIC, NO_HEADING, FALSE_HEADING, IMAGE_ONLY):
        assert parse_pdf(fixture).tables == [], fixture.name


def test_nothing_calls_extract_tables():
    """Phase 1 ships tables == []. extract_tables is the slowest call in pdfplumber
    and no consumer reads the result yet, so calling it would be pure cost."""
    source = Path(intake.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "extract_tables" not in called


def test_bytes_get_a_placeholder_name_and_an_override_wins():
    assert parse_pdf(SYNTHETIC.read_bytes()).name == "<bytes>"
    assert parse_pdf(SYNTHETIC.read_bytes(), name="upload.pdf").name == "upload.pdf"
    assert parse_pdf(str(SYNTHETIC)).name == "synthetic.pdf"


def test_an_open_file_object_keeps_its_filename():
    with SYNTHETIC.open("rb") as handle:
        assert parse_pdf(handle).name == "synthetic.pdf"


def test_page_index_is_page_number_minus_one():
    doc = parse_pdf(FALSE_HEADING)
    assert len(doc.pages) == 3
    assert "Contents" in doc.pages[0]
    assert "2 Method" in doc.pages[1]
    assert doc.pages[2].lstrip().startswith("References")


def test_locate_bibliography_returns_the_reference_pages():
    """Kept exported since B0. It no longer raises; parse_pdf is the real interface."""
    pages = intake.extract_pages(FALSE_HEADING)
    assert intake.locate_bibliography(pages) == pages[2:]
    assert intake.locate_bibliography(intake.extract_pages(IMAGE_ONLY)) == []
