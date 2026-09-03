"""Stage 1 - intake. Reads tests/data/sample.pdf and checks what comes out."""

from pathlib import Path

from src.pipeline import intake

SAMPLE = Path(__file__).parent / "data" / "sample.pdf"


def test_sample_fixture_is_present():
    assert SAMPLE.exists(), "Run: python tests/data/make_sample_pdf.py"


def test_extract_text_reads_the_body():
    text = intake.extract_text(SAMPLE)
    assert "ForkTheSource Sample Document" in text
    assert "This is a sample document for intake tests." in text


def test_extract_text_reads_the_reference_list():
    text = intake.extract_text(SAMPLE)
    assert "References" in text
    assert "Journal of Tests, 12(3):45-67, 2021" in text
    assert "Review of Examples, 5(1):10-20, 2023" in text


def test_bytes_and_path_give_the_same_text():
    assert intake.extract_text(SAMPLE.read_bytes()) == intake.extract_text(SAMPLE)


def test_extract_pages_keeps_one_entry_per_page():
    assert len(intake.extract_pages(SAMPLE)) == 1


def test_run_reports_what_it_read():
    result = intake.run(SAMPLE)
    assert result["page_count"] == 1
    assert result["text"] == intake.extract_text(SAMPLE)
    assert len(result["pages"]) == 1
