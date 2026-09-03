"""The whole app, end to end: drop a PDF in, get its raw text back.

This is the M0 definition of done written as a test. It runs the real app.py the
same way `streamlit run app.py` does, but with no browser.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"
SAMPLE = Path(__file__).parent / "data" / "sample.pdf"


def start_app() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    return app


def test_app_starts_with_a_drop_zone():
    app = start_app()
    assert not app.exception
    assert len(app.file_uploader) == 1
    assert "PDF" in app.file_uploader[0].label


def test_dropping_a_pdf_renders_its_raw_text():
    app = start_app()
    app.file_uploader[0].upload("sample.pdf", SAMPLE.read_bytes(), "application/pdf").run()

    assert not app.exception
    shown = app.text_area[0].value
    assert "ForkTheSource Sample Document" in shown
    assert "Journal of Tests, 12(3):45-67, 2021" in shown


def test_page_count_is_reported():
    app = start_app()
    app.file_uploader[0].upload("sample.pdf", SAMPLE.read_bytes(), "application/pdf").run()

    pages = [metric for metric in app.metric if metric.label == "Pages"]
    assert pages and pages[0].value == "1"
