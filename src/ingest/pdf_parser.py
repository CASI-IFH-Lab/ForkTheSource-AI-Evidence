"""P1 - PDF intake and normalization. Owner: Ritik. Plain code, no LLM, no network.

``parse_pdf(path) -> ParsedDocument`` is the PUBLIC INTERFACE. P2 and A3 import that and
nothing else from this module. ``extract_pages``, ``extract_text`` and
``locate_bibliography`` are its internals, still exported because the B0 tests read them
directly, but they are not part of the contract - if you are writing new code against
this module, call ``parse_pdf``.

``ParsedDocument`` lives here rather than in ``src/contract.py``: contract.py is Tier 1
shared infrastructure and frozen, and an intake-shaped intermediate that only P2 and A3
ever see does not belong in it.

Three things in here are worth knowing before you change them.

**Word spacing.** pdfplumber's default ``x_tolerance`` of 3 points is too wide for the
font metrics most real papers use, and it silently glues whole lines into one token:
the arXiv sample comes out as ``JimmyLeiBa,JamieRyanKiros,andGeoffreyEHinton`` and the
PLOS sample as ``1. CollinsFS,TabakLA(2014)NIHplanstoenhancereproducibility``. Two out
of two real papers, so this is the common case, not an edge case. Every extraction here
passes ``x_tolerance_ratio=0.15``, which scales the tolerance with the font size instead
of fixing it in absolute points - a 6pt footnote and 10pt body text need different
absolute tolerances, which is why an absolute default cannot be right for both. 0.15 was
picked by measurement, not taste: at 0.25 the body text glues back together, and at 0.10
words start splitting apart mid-word. Both real fixtures come out clean at 0.15 and the
synthetic fixtures are unaffected.

**The split point is the LAST heading match, not the first.** Papers name their
reference section before they reach it - in a contents list, in a running header, in a
sentence like "see the references". ``tests/data/false_heading.pdf`` is that case.

**A page that fails is a note, never an exception.** One unreadable page in a
fifteen-page paper must not cost the other fourteen. What is NOT swallowed is a file
pdfplumber cannot open at all: that raises, on purpose, because handing back an empty
document would tell the user their paper has no text when the truth is that they
uploaded something that is not a PDF.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, NamedTuple

import pdfplumber

# What we hand to pdfplumber: a path, the raw bytes, or an already-open file.
PdfSource = str | Path | bytes | IO[bytes]

# See the module docstring. Measured, not guessed: 0.25 re-glues, 0.10 over-splits.
_TEXT_KWARGS: dict[str, Any] = {"x_tolerance_ratio": 0.15}

# A references heading ALONE on its line, optionally numbered ("6 References",
# "VI. Bibliography"). Anchored at both ends, so the word inside a sentence -
# "see the references listed at the end" - is not a heading. Case-insensitive.
_HEADING_RE = re.compile(
    r"^\s*(?:\d+\.?\s*|[IVXLC]+\.?\s*)?"
    r"(references|bibliography|works cited|literature cited)\.?\s*$",
    re.IGNORECASE,
)

#: When no heading is found, treat this trailing fraction of the pages as the
#: reference region, minimum one page.
_FALLBACK_FRACTION = 0.15


@dataclass
class ParsedDocument:
    """Everything intake knows about one PDF. Built only by ``parse_pdf``.

    Not frozen, and not by accident: freezing the dataclass would advertise an
    immutability it cannot deliver, because ``pages``, ``tables`` and ``notes`` are
    lists and stay mutable either way. Treat it as read-only by convention. Equality
    is field-by-field, which is what makes the determinism test meaningful.

    Fields:
        name:            display name for the source. The file's basename for a path,
                         the ``.name`` attribute of a file-like object if it has one,
                         otherwise ``"<bytes>"``. Pass ``name=`` to override.
        pages:           one string per page, in page order. A page with no extractable
                         text is ``""`` rather than dropped, so a page's index is always
                         its page number minus one. This is the authoritative view.
        tables:          ``[]`` in Phase 1. Phase 2 fills it with ``{page, rows}`` dicts.
                         Nothing here calls ``extract_tables()`` yet - it is the slowest
                         thing pdfplumber does and no consumer reads the result.
        body_text:       the document text BEFORE the references heading.
        references_text: the document text AFTER it. The heading line itself belongs to
                         neither - it is a separator, and P2 wants entries, not a title.
        ref_start_page:  1-BASED page number of the page the split happened on, so
                         ``pages[ref_start_page - 1]`` is that page. ``None`` only when
                         the document has no extractable text anywhere.
        notes:           human-readable record of everything that did not go cleanly:
                         a page that failed, the fallback firing, an empty reference
                         block. Empty list means a clean read.
    """

    name: str
    pages: list[str]
    tables: list[Any] = field(default_factory=list)
    body_text: str = ""
    references_text: str = ""
    ref_start_page: int | None = None
    notes: list[str] = field(default_factory=list)


def _as_openable(pdf: PdfSource) -> Any:
    """pdfplumber wants a path or a file-like object, so wrap raw bytes in one."""
    if isinstance(pdf, bytes):
        return io.BytesIO(pdf)
    return pdf


def _name_of(pdf: PdfSource, name: str | None) -> str:
    """Best available display name for the source."""
    if name is not None:
        return name
    if isinstance(pdf, (str, Path)):
        return Path(pdf).name
    # Streamlit's UploadedFile and any open file object carry the original filename.
    attached = getattr(pdf, "name", None)
    if isinstance(attached, str) and attached:
        return Path(attached).name
    return "<bytes>"


def _extract_pages_with_notes(pdf: PdfSource) -> tuple[list[str], list[str]]:
    """Per-page text plus a note for every page that failed.

    The try/except is per page and deliberately broad: pdfplumber surfaces a font,
    encoding or geometry problem on one page as almost any exception type, and there is
    no useful taxonomy to switch on. ``Exception`` and not ``BaseException`` so a
    Ctrl-C still stops the run.
    """
    pages: list[str] = []
    notes: list[str] = []
    with pdfplumber.open(_as_openable(pdf)) as document:
        for number, page in enumerate(document.pages, start=1):
            try:
                pages.append(page.extract_text(**_TEXT_KWARGS) or "")
            except Exception as exc:  # noqa: BLE001 - see docstring
                pages.append("")
                notes.append(
                    f"page {number}: text extraction failed "
                    f"({type(exc).__name__}: {exc}) - page kept as empty text"
                )
    return pages, notes


def extract_pages(pdf: PdfSource) -> list[str]:
    """Return one string per page, in page order.

    A page with no extractable text - or one that fails outright - comes back as an
    empty string rather than being dropped, so a page's position in the list is always
    its page number - 1. Internal to ``parse_pdf``; kept exported for the B0 tests.
    """
    return _extract_pages_with_notes(pdf)[0]


def extract_text(pdf: PdfSource) -> str:
    """Return the whole document's text, pages joined by a blank line."""
    return "\n\n".join(extract_pages(pdf))


class _Line(NamedTuple):
    """One line of text, remembering which 1-based page it came from."""

    page: int
    text: str


def _lines_of(pages: list[str]) -> list[_Line]:
    return [
        _Line(number, line)
        for number, page in enumerate(pages, start=1)
        for line in page.splitlines()
    ]


def _join(lines: list[_Line]) -> str:
    """Rejoin lines, blank line between pages - the same convention as ``extract_text``.

    Pages that contributed no lines contribute no blank separator either, so this is a
    text view rather than a byte-exact reconstruction. ``pages`` is the field to use
    when page positions matter.
    """
    chunks: list[str] = []
    current: list[str] = []
    page: int | None = None
    for line in lines:
        if page is not None and line.page != page and current:
            chunks.append("\n".join(current))
            current = []
        page = line.page
        current.append(line.text)
    if current:
        chunks.append("\n".join(current))
    return "\n\n".join(chunks)


class _Split(NamedTuple):
    body_text: str
    references_text: str
    ref_start_page: int | None
    notes: list[str]


def _split_references(pages: list[str]) -> _Split:
    """Split already-extracted pages into body and references.

    Heading match first, last-match-wins; the last-15%-of-pages fallback second. The
    one guarantee callers can rely on: if the document has any text at all,
    ``references_text`` is not empty and, if anything unusual happened on the way to
    it, ``notes`` says what.
    """
    notes: list[str] = []
    lines = _lines_of(pages)

    if not any(page.strip() for page in pages):
        notes.append(
            "no extractable text on any of "
            f"{len(pages)} page(s) - this is almost certainly a scan and needs OCR, "
            "which is out of scope"
        )
        return _Split("", "", None, notes)

    matches = [index for index, line in enumerate(lines) if _HEADING_RE.match(line.text)]

    if matches:
        # LAST match, not first: a contents list or a running header names the section
        # before the paper reaches it. tests/data/false_heading.pdf is that case.
        at = matches[-1]
        ref_start_page = lines[at].page
        if len(matches) > 1:
            earlier = ", ".join(f"page {lines[i].page}" for i in matches[:-1])
            notes.append(
                f"{len(matches)} references headings found ({earlier}, and page "
                f"{ref_start_page}); split at the last one"
            )
        body_text = _join(lines[:at])
        references_text = _join(lines[at + 1 :])
        if not references_text.strip():
            notes.append(
                f"the references heading on page {ref_start_page} is the last line with "
                "text, so references_text is empty - the reference list is probably an "
                "image, or in a part of the page pdfplumber did not reach"
            )
        return _Split(body_text, references_text, ref_start_page, notes)

    # No heading anywhere. Take the trailing slice of pages instead.
    total = len(pages)
    count = max(1, int(total * _FALLBACK_FRACTION))
    start = total - count + 1
    notes.append(
        f"no references heading found; fell back to the last {count} of {total} page(s) "
        f"(the last {_FALLBACK_FRACTION:.0%}), starting at page {start}"
    )

    # references_text must never be SILENTLY empty when the document has text. If the
    # trailing slice landed on blank pages, widen it backwards until it has something.
    while start > 1 and not "".join(pages[start - 1 :]).strip():
        start -= 1
    if start != total - count + 1:
        notes.append(
            f"the last {count} page(s) had no text, so the reference region was widened "
            f"back to page {start}"
        )

    body_text = _join([line for line in lines if line.page < start])
    references_text = _join([line for line in lines if line.page >= start])
    if total == 1:
        notes.append(
            "the document is a single page, so the fallback treated the whole page as "
            "the reference region and body_text is empty"
        )
    return _Split(body_text, references_text, start, notes)


def locate_bibliography(pages: list[str]) -> list[str]:
    """Return only the pages holding the reference list, in page order.

    A thin view over ``_split_references``, kept because the module has exported this
    name since B0. New code should call ``parse_pdf`` and read ``references_text``,
    which does not lose the split's position within a page.
    """
    start = _split_references(pages).ref_start_page
    if start is None:
        return []
    return pages[start - 1 :]


def parse_pdf(path: PdfSource, name: str | None = None) -> ParsedDocument:
    """Read a PDF into a ``ParsedDocument``. The public interface of P1.

    ``path`` is a filesystem path, raw bytes, or an open binary file - A3's upload flow
    has bytes, Roy's corpus runner has paths. Pass ``name`` when the source carries no
    usable filename of its own.

    Raises only if pdfplumber cannot open the source at all. Everything softer than
    that - a page that fails, no text layer, no heading, an empty reference list - comes
    back as a valid ``ParsedDocument`` with an explanation in ``notes``.
    """
    pages, notes = _extract_pages_with_notes(path)
    split = _split_references(pages)
    return ParsedDocument(
        name=_name_of(path, name),
        pages=pages,
        tables=[],  # Phase 2. Nothing calls extract_tables() yet - see the docstring.
        body_text=split.body_text,
        references_text=split.references_text,
        ref_start_page=split.ref_start_page,
        notes=notes + split.notes,
    )


def run(pdf: PdfSource, config: dict[str, Any] | None) -> dict[str, Any]:
    """Stage entry point, called by P6 the same way every other stage is.

    ``config`` is required positional for that uniformity and is not read yet - P1 has
    nothing to configure. Pass ``None`` to say so explicitly rather than leaving it to a
    default, so a future setting cannot start applying silently to old call sites.

    The returned dict keeps its B0 shape on purpose, because app.py and the B0 tests
    read it. New code should call ``parse_pdf`` and get the split as well.
    """
    document = parse_pdf(pdf)
    return {
        "pages": document.pages,
        "text": "\n\n".join(document.pages),
        "page_count": len(document.pages),
    }
