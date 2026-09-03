"""P5 - the rule-based classifier. Owner: Ritik. Pure function, no LLM, no network.

    rule_based_status(ev: MatchEvidence) -> tuple[str, float, str]

This is the deterministic baseline the whole project is measured against. Arsha's A1
imports it BY NAME as `fallback_fn`, so it runs whenever the judge is unavailable or
declines; Roy's eval scores it as the baseline row. It must therefore be **total** -
every MatchEvidence gets a status - and it must never raise.

## The mapping

    no resolved record                                  -> unresolvable
    retracted or doi_mismatch                           -> conflict
    strong title + year within tolerance + (DOI agrees
      or authors agree)                                 -> verified
    weak title + no author overlap                      -> conflict
    otherwise                                           -> needs_check

Every threshold comes from `settings.thresholds()`. There is not a single numeric
literal in the decision path, so retuning is a `config.yaml` edit and a test proves the
edit changes behaviour.

## Two rules that exist because of measured failures

**A title-search hit may not reach `verified` on title similarity alone.** It needs a
strong title AND author agreement above `author_strong`. P4 measured why: resolving a
real PLOS reference by title returned a *different* PLOS Biology article, and that
branch carries 14 of `plos_sample.pdf`'s 34 references. Without this gate the
mis-resolution scores `verified` - a false negative a reviewer never sees, because
`verified` is the one status nobody re-reads. D-104.

**`version_mismatch` alone is NOT a conflict.** A paper citing the preprint of a work
that was later published is *ordinary* and extremely common; it is worth surfacing and
it is not a provenance failure. It maps to `needs_check`. Roy planted a corpus row for
exactly this trap.

## Rationales

Neutral evidence language: what was compared, what agreed, what did not. No rationale
this module produces may contain any `settings.banned_terms()` entry - there is a test
over the full cross-product of shapes asserting it, because this text reaches a human in
the dashboard and the language rule is absolute.
"""

from __future__ import annotations

from src import settings
from src.contract import Indicator, MatchEvidence, VerdictStatus

#: Confidence for each outcome. Deliberately modest: this is a rule baseline, not a
#: judge, and a rule that claims 0.99 invites a reviewer to skip the row.
_CONFIDENCE = {
    "unresolvable_no_record": 0.60,
    "conflict_retracted": 0.95,
    "conflict_doi_mismatch": 0.90,
    "conflict_weak_match": 0.70,
    "verified_doi": 0.95,
    "verified_authors": 0.85,
    "needs_check_default": 0.50,
    "needs_check_version": 0.60,
    "needs_check_title_search": 0.55,
}

_TITLE_SEARCH = "title_search"


def _branch(ev: MatchEvidence) -> str | None:
    """Which waterfall branch resolved this, from P4's raw stamp. None if absent."""
    if ev.resolved is None:
        return None
    branch = ev.resolved.raw.get("_lookup_branch")
    return branch if isinstance(branch, str) else None


def _year_ok(ev: MatchEvidence, tolerance: int) -> bool:
    """A missing year is not a year disagreement - it is a missing signal."""
    return ev.year_delta is None or ev.year_delta <= tolerance


def rule_based_status(ev: MatchEvidence) -> tuple[str, float, str]:
    """Classify one MatchEvidence. Returns (status, confidence, rationale).

    Total and never raises: A1 calls this as its fallback precisely when something else
    has already gone wrong, so it cannot be the thing that also fails.
    """
    limits = settings.thresholds()
    title_strong = float(limits["title_strong"])
    title_weak = float(limits["title_weak"])
    author_strong = float(limits["author_strong"])
    year_tolerance = int(limits["year_tolerance"])

    indicators = set(ev.indicators)

    # ---- no record at all ------------------------------------------------
    if ev.resolved is None:
        reason = "no registry record was found for the printed reference"
        if Indicator.MALFORMED.value in indicators:
            reason = (
                "extraction could not read this entry, and no registry record was found "
                "for it; the printed text is preserved for a human to read"
            )
        return (
            VerdictStatus.UNRESOLVABLE.value,
            _CONFIDENCE["unresolvable_no_record"],
            f"{reason}. A reviewer should confirm the reference against the source.",
        )

    provider = ev.resolved.provider
    branch = _branch(ev)

    # ---- conflict: retraction and DOI disagreement -----------------------
    if Indicator.RETRACTED.value in indicators:
        return (
            VerdictStatus.CONFLICT.value,
            _CONFIDENCE["conflict_retracted"],
            f"{provider} records this work as retracted. Title similarity "
            f"{ev.title_similarity:.2f}, author overlap {ev.author_overlap:.2f}. "
            "A reviewer should check whether a retraction notice applies to the citation.",
        )

    if Indicator.DOI_MISMATCH.value in indicators:
        return (
            VerdictStatus.CONFLICT.value,
            _CONFIDENCE["conflict_doi_mismatch"],
            "the printed DOI and the DOI on the resolved record differ, while title "
            f"similarity is {ev.title_similarity:.2f}. A reviewer should confirm which "
            "identifier belongs to the cited work.",
        )

    strong_title = ev.title_similarity >= title_strong
    authors_agree = ev.author_overlap >= author_strong
    year_ok = _year_ok(ev, year_tolerance)

    # ---- the title-search gate (D-104) -----------------------------------
    # A title search returns the best hit, not the right hit. On this branch a strong
    # title is what got the record back in the first place, so it is not independent
    # evidence - author agreement is.
    if branch == _TITLE_SEARCH and strong_title and year_ok and not authors_agree:
        return (
            VerdictStatus.NEEDS_CHECK.value,
            _CONFIDENCE["needs_check_title_search"],
            "this record was found by searching the title, not by an identifier, and "
            f"the author lists overlap {ev.author_overlap:.2f}. Title similarity "
            f"{ev.title_similarity:.2f} alone does not establish that the search "
            "returned the cited work. A reviewer should confirm the match.",
        )

    # ---- verified --------------------------------------------------------
    if strong_title and year_ok and ev.doi_match is True:
        return (
            VerdictStatus.VERIFIED.value,
            _CONFIDENCE["verified_doi"],
            f"the printed DOI matches the record {provider} returned, with title "
            f"similarity {ev.title_similarity:.2f} and "
            f"{_year_phrase(ev)}. Identifier and metadata agree.",
        )

    if strong_title and year_ok and authors_agree:
        return (
            VerdictStatus.VERIFIED.value,
            _CONFIDENCE["verified_authors"],
            f"title similarity {ev.title_similarity:.2f} and author overlap "
            f"{ev.author_overlap:.2f} against the record {provider} returned, with "
            f"{_year_phrase(ev)}. Metadata agrees; no DOI was printed to compare.",
        )

    # ---- conflict: the match itself is weak ------------------------------
    if ev.title_similarity < title_weak and ev.author_overlap <= 0.0:
        return (
            VerdictStatus.CONFLICT.value,
            _CONFIDENCE["conflict_weak_match"],
            f"the record {provider} returned shares neither the title (similarity "
            f"{ev.title_similarity:.2f}) nor any author surname with the printed "
            "reference. A reviewer should establish which work is cited.",
        )

    # ---- version_mismatch alone is NOT a conflict ------------------------
    if Indicator.VERSION_MISMATCH.value in indicators:
        return (
            VerdictStatus.NEEDS_CHECK.value,
            _CONFIDENCE["needs_check_version"],
            f"the printed reference and the {provider} record disagree about whether "
            "this is a preprint or a published version, while title similarity is "
            f"{ev.title_similarity:.2f}. A reviewer should decide which version the "
            "citation intends.",
        )

    # ---- everything else -------------------------------------------------
    return (
        VerdictStatus.NEEDS_CHECK.value,
        _CONFIDENCE["needs_check_default"],
        f"partial agreement with the record {provider} returned: title similarity "
        f"{ev.title_similarity:.2f}, author overlap {ev.author_overlap:.2f}, "
        f"{_year_phrase(ev)}. A reviewer should confirm the remaining fields.",
    )


def _year_phrase(ev: MatchEvidence) -> str:
    if ev.year_delta is None:
        return "no year available on both sides to compare"
    if ev.year_delta == 0:
        return "the same publication year"
    return f"a {ev.year_delta}-year difference in publication year"
