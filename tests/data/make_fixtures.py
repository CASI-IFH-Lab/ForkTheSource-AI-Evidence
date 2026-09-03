"""Builds the synthetic PDF fixtures that tests/test_intake.py reads.

    python tests/data/make_fixtures.py

Replaces the old make_sample_pdf.py. `sample.pdf` is no longer synthetic - it is a
real open-access paper now, because the heading regex and the reference split have to
be exercised against how real typesetting actually comes out of pdfplumber, not
against a fixture written to make them pass. Provenance and licence for the two real
papers are recorded at the top of tests/test_intake.py.

The four files built here each pin down one behaviour that a real paper cannot:

    synthetic.pdf     tiny, one page, known strings. tests/test_app.py uploads this
                      into the Streamlit shell - the app test should not pay 2 MB and
                      15 pages to assert that text reaches a text area.
    no_heading.pdf    real-looking references with NO heading line anywhere, so the
                      last-15%-of-pages fallback is the only way to find them.
    false_heading.pdf "References" alone on a line in a contents list on page 1, then
                      the real heading on page 3. The split must land on the LATER one.
    image_only.pdf    no text layer at all - a scan. Must come back empty with a note
                      rather than raising.

synthetic.pdf is written by hand (no dependency); the other three need reportlab,
which is NOT in requirements-dev.txt on purpose: the fixtures are committed, so only
someone regenerating them needs it.

    python -m pip install reportlab
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# synthetic.pdf - written by hand, so the fast app-shell fixture has no build
# dependency at all. Same content it has had since B0; tests/test_app.py asserts
# against these exact strings.
# ---------------------------------------------------------------------------
SYNTHETIC_LINES = [
    "ForkTheSource Sample Document",
    "",
    "This is a sample document for intake tests.",
    "",
    "References",
    "[1] A. Author and B. Writer. A study of things. Journal of Tests, 12(3):45-67, 2021.",
    "[2] C. Coder. Another paper about code. Proceedings of Nowhere, pages 1-9, 2019.",
    "[3] D. Doe. Yet another reference. Review of Examples, 5(1):10-20, 2023.",
]


def escape(line: str) -> str:
    """Backslashes and brackets are special inside a PDF text string."""
    for character in ("\\", "(", ")"):
        line = line.replace(character, "\\" + character)
    return line


def content_stream(lines: list[str]) -> bytes:
    body = ["BT", "/F1 12 Tf", "72 720 Td", "16 TL"]
    body += [f"({escape(line)}) Tj T*" for line in lines]
    body.append("ET")
    return "\n".join(body).encode("ascii")


def build_synthetic(lines: list[str]) -> bytes:
    stream = content_stream(lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode("ascii") + b" 0 obj\n" + body + b"\nendobj\n"

    xref_at = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode("ascii") + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode("ascii") + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_at).encode("ascii") + b"\n%%EOF\n"
    return bytes(out)


# ---------------------------------------------------------------------------
# The reportlab three
# ---------------------------------------------------------------------------
# Reference entries written in the [1] style the arXiv sample uses, so a fixture and
# a real paper exercise the same downstream shape. Deliberately wrapped across lines,
# because real reference lists wrap and P2's pre-splitter has to cope with it.
REFERENCE_LINES = [
    "[1] A. Author and B. Writer. A study of things that were studied.",
    "    Journal of Tests, 12(3):45-67, 2021.",
    "[2] C. Coder. Another paper about code, at some length.",
    "    Proceedings of Nowhere, pages 1-9, 2019.",
    "[3] D. Doe and E. Example. Yet another reference to something.",
    "    Review of Examples, 5(1):10-20, 2023.",
    "[4] F. Fisher. On the reproducibility of reproducibility studies.",
    "    Annals of Recursion, 3(2):100-115, 2024.",
]

# A body paragraph that mentions the word inline. It must NOT be treated as a heading:
# the regex requires the word ALONE on its line, and this is the case that proves it.
BODY_LINES = [
    "2 Method",
    "",
    "We describe the method here. Readers who want the full derivation",
    "should consult the references listed at the end of this paper, and",
    "in particular the bibliography of [2], which is more complete.",
    "",
    "The remainder of this section is filler so that the document has",
    "enough pages for the last-15% fallback to have something to bite on.",
]


def _page_of(canvas_obj, lines: list[str], *, size: int = 11) -> None:
    """One page of monospaced-ish text at a fixed leading, then a page break."""
    text = canvas_obj.beginText(72, 720)
    text.setFont("Helvetica", size)
    text.setLeading(16)
    for line in lines:
        text.textLine(line)
    canvas_obj.drawText(text)
    canvas_obj.showPage()


def build_no_heading(path: Path) -> None:
    """Eight pages. Real references on the last one, and no heading line anywhere.

    Eight pages because the fallback takes int(8 * 0.15) == 1 page, which is exactly
    the page the references are on - so a passing test means the fallback found them,
    not that it got lucky with a wide net.
    """
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    pdf.setTitle("No Heading Fixture")
    _page_of(pdf, ["A Paper With No References Heading", "", *BODY_LINES])
    for number in range(2, 8):
        _page_of(pdf, [f"Section {number}", "", f"Body text on page {number}.", "", *BODY_LINES[2:]])
    # The reference list, with nothing announcing it. No "References", no
    # "Bibliography" - the fallback is the only way in.
    _page_of(pdf, REFERENCE_LINES)
    pdf.save()


def build_false_heading(path: Path) -> None:
    """Contents list on page 1 says "References"; the real heading is on page 3."""
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    pdf.setTitle("False Heading Fixture")
    _page_of(
        pdf,
        [
            "A Paper With A Contents List",
            "",
            "Contents",
            "",
            "1 Introduction",
            "2 Method",
            "3 Results",
            "References",  # <- matches the heading regex, and is NOT the split point
            "",
            "1 Introduction",
            "",
            "This paper has a contents list, which is where papers most often",
            "mention their reference section before reaching it.",
        ],
    )
    _page_of(pdf, ["2 Method", "", *BODY_LINES[2:]])
    _page_of(pdf, ["References", "", *REFERENCE_LINES])
    pdf.save()


def build_image_only(path: Path) -> None:
    """A page with graphics and no text objects - what a scan looks like to pdfplumber."""
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    pdf.setTitle("Image Only Fixture")
    # Grey blocks roughly where lines of text would be. No drawString anywhere, so the
    # PDF has no text layer to extract - which is the entire point of the fixture.
    pdf.setFillGray(0.75)
    for row in range(24):
        pdf.rect(72, 700 - row * 24, 400 + (row % 5) * 20, 12, stroke=0, fill=1)
    pdf.showPage()
    pdf.setFillGray(0.75)
    for row in range(18):
        pdf.rect(72, 700 - row * 24, 380 + (row % 4) * 25, 12, stroke=0, fill=1)
    pdf.save()


def main() -> int:
    synthetic = HERE / "synthetic.pdf"
    synthetic.write_bytes(build_synthetic(SYNTHETIC_LINES))
    print(f"wrote {synthetic.name} ({synthetic.stat().st_size} bytes)")

    try:
        import reportlab  # noqa: F401
    except ImportError:
        print(
            "\nreportlab is not installed, so no_heading.pdf, false_heading.pdf and\n"
            "image_only.pdf were NOT rebuilt. The committed copies are still valid;\n"
            "install it only if you need to change them:\n\n"
            "    python -m pip install reportlab\n",
            file=sys.stderr,
        )
        return 1

    for name, build in (
        ("no_heading.pdf", build_no_heading),
        ("false_heading.pdf", build_false_heading),
        ("image_only.pdf", build_image_only),
    ):
        target = HERE / name
        build(target)
        print(f"wrote {target.name} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
