"""P5 - the evidence builder. Owner: Ritik. Pure functions, no LLM, no network.

    build_evidence(ref, resolved, ledger_refs, malformed_ref_ids=frozenset()) -> MatchEvidence

Turns one (reference, resolved-source) pair into the four signals and up to six
indicators that P5's classifier and A1's judge both read. Deterministic: same inputs,
same MatchEvidence, on every machine.

## Four things in here are load-bearing and easy to get wrong

**`year_delta` is `ge=0` in the contract.** The natural implementation,
`resolved.year - reference.year`, raises at construction for every reference cited
*earlier* than the resolved record's year - which is the wrong-year defect's primary
direction, so the natural implementation fails on precisely the rows the eval is built
to catch. We store `abs(...)`. The sign is not lost information we needed: nothing
downstream asks which direction the year moved, and D-105 records the reasoning.

**`doi_match` is tri-state, and `None` is the COMMON case.** `sample.pdf` has 0 DOIs in
40 references, so two thirds of the corpus reaches here with nothing to compare. `None`
means "one side had no DOI" (D-034) and must never be read as a mismatch.

**`version_mismatch` fires only on KNOWN values.** `resolved.is_preprint is None` means
the provider did not say, so we do not know, so we do not fire. Collapsing `None` to
`False` would assert "definitely the published version" on missing data - which is
exactly what D-020 forbids. This closes D-020's P5 half; see D-106.

**Similarity uses `difflib` only, never an optional accelerator.** See the note on
`title_similarity` below.

## malformed, and a signature question that is NOT mine to settle

The frozen §7 signature is `build_evidence(ref, resolved, ledger_refs)`. P2's malformed
set (D-102) is a fourth fact, and there is nowhere in those three arguments to put it.
It is passed as an **optional trailing keyword** with an empty default, so every existing
three-positional-argument call site keeps working unchanged and nothing in Arsha's or
Roy's lane breaks. **A caller that does not pass it gets no `malformed` indicator at
all** - which is a silent gap if P6 forgets. Flagged in the P5 report as the reviewer's
call, not settled here.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Iterable

from src.contract import Indicator, MatchEvidence, Reference, ResolvedSource

#: An arXiv DOI prefix on the REFERENCE side is a preprint signal we can read without
#: asking a provider - the whole 10.48550 prefix is arXiv's (D-037).
_ARXIV_DOI_PREFIX = "10.48550/"

_WORD_RE = re.compile(r"[a-z0-9]+")
_THE_LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+")


def _normalise_text(value: str | None) -> str:
    """Casefold, strip accents, collapse punctuation and whitespace to single spaces.

    Deliberately NOT stemming or dropping stopwords: a title comparison that
    aggressively normalises starts matching different papers with similar words, and a
    false match here becomes a `verified` verdict on the wrong record.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    return " ".join(_WORD_RE.findall(text))


def _last_name(name: str) -> str:
    """The surname out of "Jimmy Lei Ba", "Ba, Jimmy Lei" or "Collins FS".

    Both orders appear in the real corpus - arXiv prints "Given Family", PLOS prints
    "Family Initials" - so this has to cope with both without a heuristic that silently
    picks the wrong token.
    """
    if not _normalise_text(name):
        return ""
    if "," in name:
        # "Family, Given" - everything before the comma is the surname.
        return _normalise_text(name.split(",", 1)[0]).split(" ")[-1]

    raw_parts = [part for part in name.split() if part.strip()]
    if len(raw_parts) == 1:
        return _normalise_text(raw_parts[0])

    # "Collins FS" - a trailing ALL-CAPS short token is initials, not a surname.
    # Length alone is not enough and getting this wrong is silent: "Jimmy Lei Ba" has a
    # two-letter SURNAME, and a length test returned "lei" for it, which drops the
    # author overlap between an arXiv-style and a PLOS-style rendering of the same
    # person from 1.0 to 0.33.
    tail = raw_parts[-1].rstrip(".")
    if len(tail) <= 3 and tail.isalpha() and tail.isupper():
        return _normalise_text(raw_parts[-2])
    return _normalise_text(tail).split(" ")[-1]


def _last_names(names: Iterable[str]) -> set[str]:
    return {last for last in (_last_name(name) for name in names) if last}


def title_similarity(left: str | None, right: str | None) -> float:
    """Token-sort similarity in [0, 1]. Zero when either side is missing.

    **`difflib` only, on purpose.** The card offered "rapidfuzz if available, difflib
    fallback", and an optional accelerator is the wrong shape for this particular
    number: rapidfuzz and difflib do not agree to two decimal places, the thresholds
    that consume this are 0.92 and 0.70, and R2 scores a baseline against it. "Whether
    rapidfuzz happens to be installed" would become an input to the confusion matrix,
    and two teammates would get different metrics from the same ledger. Stdlib, one
    implementation, identical everywhere. If we want rapidfuzz it should be a pinned
    requirement rather than an optional import - the reviewer's call, not this file's.
    """
    left_normalised, right_normalised = _normalise_text(left), _normalise_text(right)
    if not left_normalised or not right_normalised:
        return 0.0
    # Token SORT: word order differences between a printed citation and a registry
    # record are not evidence of a different paper.
    left_sorted = " ".join(sorted(left_normalised.split(" ")))
    right_sorted = " ".join(sorted(right_normalised.split(" ")))
    ratio = difflib.SequenceMatcher(None, left_sorted, right_sorted).ratio()
    return round(min(max(ratio, 0.0), 1.0), 4)


def author_overlap(left: Iterable[str], right: Iterable[str]) -> float:
    """Jaccard overlap of normalised surnames. Zero when either side is empty."""
    left_names, right_names = _last_names(left), _last_names(right)
    if not left_names or not right_names:
        return 0.0
    union = left_names | right_names
    if not union:
        return 0.0
    return round(len(left_names & right_names) / len(union), 4)


def year_delta(reference_year: int | None, resolved_year: int | None) -> int | None:
    """``abs`` difference, or None when either side has no year.

    ABS, and the contract forces the question: ``MatchEvidence.year_delta`` is ``ge=0``,
    so a signed delta raises at construction the moment a reference is cited with a year
    EARLIER than the record's - which is the direction the wrong-year defect usually
    takes. See D-105.
    """
    if reference_year is None or resolved_year is None:
        return None
    return abs(int(resolved_year) - int(reference_year))


def doi_match(reference_doi: str | None, resolved_doi: str | None) -> bool | None:
    """Tri-state. ``None`` when either side has no DOI - never ``False``. D-034.

    ``None`` is the common case, not the edge case: `sample.pdf` prints no DOIs at all.
    """
    if not reference_doi or not resolved_doi:
        return None
    return _normalise_text(reference_doi) == _normalise_text(resolved_doi)


def reference_looks_like_a_preprint(ref: Reference) -> bool:
    """Preprint evidence available on the REFERENCE side alone, without a provider."""
    if ref.arxiv_id:
        return True
    return bool(ref.doi and ref.doi.lower().startswith(_ARXIV_DOI_PREFIX))


def _duplicate_of(ref: Reference, ledger_refs: list[Reference]) -> Reference | None:
    """Another entry with the same normalised title+year but divergent metadata.

    Same title and year is the identity test; a DIFFERENT DOI, arXiv id or author set is
    what makes it worth flagging rather than a harmless repeat. A bibliography that
    genuinely lists one work twice with identical metadata is a formatting quirk, not a
    provenance problem.
    """
    if not ref.title:
        return None
    key = (_normalise_text(ref.title), ref.year)
    for other in ledger_refs:
        if other.ref_id == ref.ref_id or not other.title:
            continue
        if (_normalise_text(other.title), other.year) != key:
            continue
        divergent = (
            (ref.doi or None) != (other.doi or None)
            or (ref.arxiv_id or None) != (other.arxiv_id or None)
            or _last_names(ref.authors) != _last_names(other.authors)
        )
        if divergent:
            return other
    return None


def build_evidence(
    ref: Reference,
    resolved: ResolvedSource | None,
    ledger_refs: list[Reference],
    malformed_ref_ids: Iterable[str] = frozenset(),
) -> MatchEvidence:
    """Four signals and up to six indicators for one reference. Never raises.

    ``malformed_ref_ids`` is P2's side-channel (D-102) and is optional so that the
    frozen three-argument signature keeps working - see the module docstring.
    """
    malformed = set(malformed_ref_ids)
    indicators: list[Indicator] = []
    notes: list[str] = []

    if ref.ref_id in malformed:
        # From the extraction attempt, NEVER from title being None. A titleless work is
        # a successful extraction of a titleless work (D-102).
        indicators.append(Indicator.MALFORMED)
        notes.append("extraction could not read this entry; raw_text is preserved")

    if not ref.cited_by_claims:
        indicators.append(Indicator.ORPHAN)
        notes.append("no in-text citation marker maps to this entry")

    duplicate = _duplicate_of(ref, ledger_refs)
    if duplicate is not None:
        indicators.append(Indicator.DUPLICATE_ENTRY)
        notes.append(f"same title and year as {duplicate.ref_id}, with divergent metadata")

    if resolved is None:
        notes.append("no registry record was found for this reference")
        return MatchEvidence(
            ref_id=ref.ref_id,
            resolved=None,
            title_similarity=0.0,
            author_overlap=0.0,
            year_delta=None,
            doi_match=None,
            indicators=indicators,
            notes=notes,
        )

    similarity = title_similarity(ref.title, resolved.title)
    overlap = author_overlap(ref.authors, resolved.authors)
    delta = year_delta(ref.year, resolved.year)
    doi_agreement = doi_match(ref.doi, resolved.doi)

    if resolved.is_retracted:
        indicators.append(Indicator.RETRACTED)
        notes.append(f"{resolved.provider} reports this work as retracted")

    if doi_agreement is False:
        # BOTH sides had a DOI and they differ. doi_match None means we cannot make
        # this claim at all.
        indicators.append(Indicator.DOI_MISMATCH)
        notes.append(f"printed DOI {ref.doi} does not match the resolved {resolved.doi}")

    if _version_mismatch(ref, resolved, similarity):
        indicators.append(Indicator.VERSION_MISMATCH)
        notes.append(
            "exactly one side is a preprint: reference preprint="
            f"{reference_looks_like_a_preprint(ref)}, resolved is_preprint="
            f"{resolved.is_preprint}"
        )

    if resolved.is_preprint is None:
        notes.append(
            f"{resolved.provider} did not say whether this is a preprint - "
            "version_mismatch is not asserted either way"
        )

    return MatchEvidence(
        ref_id=ref.ref_id,
        resolved=resolved,
        title_similarity=similarity,
        author_overlap=overlap,
        year_delta=delta,
        doi_match=doi_agreement,
        indicators=indicators,
        notes=notes,
    )


def _version_mismatch(ref: Reference, resolved: ResolvedSource, similarity: float) -> bool:
    """EXACTLY ONE side a preprint, asserted only on values we actually know. D-020.

    Requires strong title similarity, because on a weak match we do not know the two
    records describe the same work, and "preprint versus published" is a claim about one
    work. Not venue divergence, not year alone - both of those fire on ordinary
    differences between a printed citation and a registry record.
    """
    from src import settings

    if resolved.is_preprint is None:
        return False  # provider did not say; we do not know; we do not fire
    if similarity < float(settings.thresholds()["title_strong"]):
        return False
    return reference_looks_like_a_preprint(ref) != bool(resolved.is_preprint)
