"""P1 - PDF intake and normalization. Owner: Ritik. Plain code, no LLM, no network.

HALF DONE. What is here works: per-page pdfplumber extraction, with a page that has no
extractable text coming back as "" rather than being dropped, so a page's index is always
its page number minus one.

What P1 still owes, per its plan card:
  - parse_pdf(path) -> ParsedDocument is the PUBLIC INTERFACE other modules may import.
    It does not exist yet. The functions below are its internals.
    ParsedDocument: {name, pages, tables, body_text, references_text, ref_start_page}
  - the body/references split (locate_bibliography below is a stub), plus the fallback of
    treating the last 15% of pages as the reference region when no heading is found
  - per-page tables as {page, rows}
  - a try/except around each page: one corrupt page must never kill a run

Do not build those here as a drive-by. They are P1 and they get their own branch.
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
