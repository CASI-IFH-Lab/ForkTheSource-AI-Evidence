"""Builds tests/data/sample.pdf, the fixture the intake test reads.

Committed so the fixture is reproducible: if the file is ever lost or you want to
change what it says, run this and commit the result.

    python tests/data/make_sample_pdf.py

It writes the PDF by hand rather than pulling in a PDF-authoring library, because
the test only needs a page with known text on it.
"""

from pathlib import Path

LINES = [
    "ForkTheSource Sample Document",
    "",
    "This is a sample document for intake tests.",
    "",
    "References",
    "[1] A. Author and B. Writer. A study of things. Journal of Tests, 12(3):45-67, 2021.",
    "[2] C. Coder. Another paper about code. Proceedings of Nowhere, pages 1-9, 2019.",
    "[3] D. Doe. Yet another reference. Review of Examples, 5(1):10-20, 2023.",
]

OUTPUT = Path(__file__).parent / "sample.pdf"


def escape(line: str) -> str:
    """Backslashes and brackets are special inside a PDF text string."""
    for character in ("\\", "(", ")"):
        line = line.replace(character, "\\" + character)
    return line


def content_stream() -> bytes:
    body = ["BT", "/F1 12 Tf", "72 720 Td", "16 TL"]
    body += [f"({escape(line)}) Tj T*" for line in LINES]
    body.append("ET")
    return "\n".join(body).encode("ascii")


def build_pdf() -> bytes:
    stream = content_stream()
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


if __name__ == "__main__":
    OUTPUT.write_bytes(build_pdf())
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
