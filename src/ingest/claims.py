"""P2 - in-text citation mapping. Owner: Ritik. Plain regex, NO model, no network.

``extract_claims(doc, refs)`` finds the sentences that cite something and links them to
the references they cite, in both directions: the returned ``Claim`` objects carry
``ref_ids``, and ``Reference.cited_by_claims`` is filled in place on the references
passed in.

Both real fixtures cite the same way, which is what the marker grammar is built for:

    sample.pdf       63 markers, forms "[9]", "[17, 18]", "[4, 27, 28, 22]"
    plos_sample.pdf  41 markers, forms "[7]", "[1,2]", "[32,33]"

Ranges ("[1-3]") do not appear in either paper but are in the grammar because they are
common elsewhere, and a range silently read as the list [1, 3] would attribute a claim
to the wrong reference rather than fail visibly.

**A marker's number is a position, not an id.** ``split_entries`` only accepts a
numbered style when the markers run monotonically from 1, so printed number *n* is the
*n*-th extracted reference. A marker pointing past the end of the list is dropped: it
is a footnote, a table label, or a typo, and inventing a reference for it would be
worse than ignoring it.

Entries that end up cited by nothing are NOT flagged here - ``orphan`` is P5's to
stamp. This module only records the map.

Two known limits of doing this with a regex, both deliberate:

* Sentence splitting is `[.!?]` followed by whitespace and a capital. "et al. (2014)"
  and "Fig. 3 shows" can still split early. The consequence is a shorter claim
  sentence, never a wrong ``ref_id``.
* Claims are found per page, so a sentence spanning a page break becomes two claims.
  That is the trade for ``page`` being exact rather than guessed - and a page number a
  reviewer can turn to is worth more than a whole sentence.
"""

from __future__ import annotations

import re

from src.contract import Claim, Reference
from src.ingest.pdf_parser import ParsedDocument

# A bracketed group that STARTS with a digit and contains only digits, separators and
# spaces. "[9]", "[1,2]", "[17, 18]", "[1-3]" match; "[Fig. 1]" and "[]" do not.
_MARKER_RE = re.compile(r"\[(\d[\d\s,;–—-]*)\]")

# A range inside one marker part: "1-3", "1–3".
_RANGE_RE = re.compile(r"^(\d{1,3})\s*[-–—]\s*(\d{1,3})$")

# End of sentence: terminal punctuation, whitespace, then something that looks like a
# new sentence. Keeps "12(3):45-67, 2021." from splitting on every period.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'])")

_WHITESPACE_RE = re.compile(r"\s+")

#: A range wider than this is a typesetting artifact, not a citation list.
_MAX_RANGE_SPAN = 100


def _expand_marker(body: str) -> list[int]:
    """"17, 18" -> [17, 18]; "1-3" -> [1, 2, 3]. Order preserved, no dedupe here."""
    numbers: list[int] = []
    for part in re.split(r"[,;]", body):
        part = part.strip()
        if not part:
            continue
        ranged = _RANGE_RE.match(part)
        if ranged:
            low, high = int(ranged.group(1)), int(ranged.group(2))
            if 0 < low <= high and high - low < _MAX_RANGE_SPAN:
                numbers.extend(range(low, high + 1))
            continue
        if part.isdigit():
            numbers.append(int(part))
    return numbers


def _sentences(page_text: str) -> list[str]:
    flat = _WHITESPACE_RE.sub(" ", page_text).strip()
    if not flat:
        return []
    return [piece.strip() for piece in _SENTENCE_SPLIT_RE.split(flat) if piece.strip()]


def claim_id_for(position: int, total: int) -> str:
    """``C`` + 1-based position, two digits, three at 100 or more.

    Same width rule as ``ref_id`` (eval/golden/FORMAT.md) so the two id spaces read the
    same way, and matching the ``C01`` ids in B1's ledger fixture.
    """
    width = 2 if total < 100 else 3
    return f"C{position:0{width}d}"


def extract_claims(doc: ParsedDocument, refs: list[Reference]) -> list[Claim]:
    """Sentences that cite a reference, linked both ways. Plain regex, no model.

    Mutates ``refs``: each reference's ``cited_by_claims`` is replaced with the claim
    ids that cite it, in claim order. Call it once per document.
    """
    for reference in refs:
        reference.cited_by_claims = []
    if not refs:
        return []

    by_position = {index + 1: reference for index, reference in enumerate(refs)}

    # Body pages only. The reference list cites nothing; scanning it would turn every
    # entry's own marker into a claim about itself.
    last_body_page = (doc.ref_start_page - 1) if doc.ref_start_page else len(doc.pages)
    found: list[tuple[int, str, list[str]]] = []

    for page_number, page_text in enumerate(doc.pages[:last_body_page], start=1):
        for sentence in _sentences(page_text):
            ref_ids: list[str] = []
            for marker in _MARKER_RE.finditer(sentence):
                for number in _expand_marker(marker.group(1)):
                    reference = by_position.get(number)
                    if reference is None:
                        continue  # points past the list: not a citation into it
                    if reference.ref_id not in ref_ids:
                        ref_ids.append(reference.ref_id)
            if ref_ids:
                found.append((page_number, sentence, ref_ids))

    total = len(found)
    claims: list[Claim] = []
    for position, (page_number, sentence, ref_ids) in enumerate(found, start=1):
        claims.append(
            Claim(
                claim_id=claim_id_for(position, total),
                text=sentence,
                page=page_number,
                ref_ids=ref_ids,
            )
        )

    # The other direction.
    by_ref_id = {reference.ref_id: reference for reference in refs}
    for claim in claims:
        for ref_id in claim.ref_ids:
            reference = by_ref_id[ref_id]
            reference.cited_by_claims = [*reference.cited_by_claims, claim.claim_id]

    return claims
