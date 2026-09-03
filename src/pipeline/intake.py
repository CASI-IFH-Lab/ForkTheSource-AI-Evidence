"""Stage 1 - Intake. Plain code, no model calls.

Opens the PDF, pulls the text out page by page, and (from M1) works out which of
those pages hold the bibliography.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import IO, Any

import pdfplumber

# What we hand to pdfplumber: a path, the raw bytes, or an already-open file.
PdfSource = str | Path | bytes | IO[bytes]


def _as_openable(pdf: PdfSource) -> Any:
    """pdfplumber wants a path or a file-like object, so wrap raw bytes in one."""
    if isinstance(pdf, bytes):
        return io.BytesIO(pdf)
    return pdf


def extract_pages(pdf: PdfSource) -> list[str]:
    """Return one string per page, in page order.

    A page with no extractable text comes back as an empty string rather than
    being dropped, so a page's position in the list is always its page number - 1.
    """
    with pdfplumber.open(_as_openable(pdf)) as document:
        return [page.extract_text() or "" for page in document.pages]


def extract_text(pdf: PdfSource) -> str:
    """Return the whole document's text, pages joined by a blank line."""
    return "\n\n".join(extract_pages(pdf))


def locate_bibliography(pages: list[str]) -> list[str]:
    """Return only the pages holding the reference list.

    Not implemented yet - lands in M1, still as plain code (heading match plus a
    check that the following lines look like references).
    """
    raise NotImplementedError("intake.locate_bibliography: implemented in M1")


def run(pdf: PdfSource, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Stage entry point. Reads the PDF and reports what came out."""
    pages = extract_pages(pdf)
    return {
        "pages": pages,
        "text": "\n\n".join(pages),
        "page_count": len(pages),
    }
