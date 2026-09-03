"""P5 - the evidence builder and the rule-based classifier.

Pure functions, so every test here is offline and instant. This is the deterministic
baseline Roy's eval scores and Arsha's judge falls back to, so the tests are about the
rulings rather than about coverage: each of the six indicators, each tri-state that must
not collapse, and the two rules that exist because a real lookup got something wrong.
"""

from __future__ import annotations

import itertools

import pytest

from src import settings
from src.contract import Indicator, MatchEvidence, Reference, ResolvedSource, VerdictStatus
from src.matching.evidence import (
    author_overlap,
    build_evidence,
    doi_match,
    reference_looks_like_a_preprint,
    title_similarity,
    year_delta,
)
from src.matching.rules import rule_based_status

TITLE = "Layer Normalization"


def make_ref(**kwargs) -> Reference:
    base = dict(
        ref_id="R01",
        raw_text="[1] Jimmy Lei Ba, Jamie Ryan Kiros, and Geoffrey E Hinton. Layer normalization.",
        title=TITLE,
        authors=["Jimmy Lei Ba", "Jamie Ryan Kiros", "Geoffrey E Hinton"],
        year=2016,
        cited_by_claims=["C01"],
    )
    base.update(kwargs)
    return Reference(**base)


def make_resolved(**kwargs) -> ResolvedSource:
    base = dict(
        provider="crossref",
        title=TITLE,
        authors=["Jimmy Lei Ba", "Jamie Ryan Kiros", "Geoffrey E Hinton"],
        year=2016,
        raw={"_lookup_branch": "doi"},
    )
    base.update(kwargs)
    return ResolvedSource(**base)


def make_evidence(**kwargs) -> MatchEvidence:
    base = dict(
        ref_id="R01",
        resolved=make_resolved(),
        title_similarity=0.99,
        author_overlap=0.9,
        year_delta=0,
        doi_match=None,
    )
    base.update(kwargs)
    return MatchEvidence(**base)


# ---------------------------------------------------------------------------
# The four signals
# ---------------------------------------------------------------------------
def test_title_similarity_is_order_insensitive_and_bounded():
    assert title_similarity(TITLE, TITLE) == 1.0
    assert title_similarity("Attention Is All You Need", "All You Need Is Attention") == 1.0
    assert title_similarity(TITLE, "Deep Residual Learning") < 0.5
    assert title_similarity(None, TITLE) == 0.0
    assert title_similarity(TITLE, None) == 0.0
    assert title_similarity("", "") == 0.0
    assert 0.0 <= title_similarity("a", "b") <= 1.0


def test_title_similarity_ignores_case_accents_and_punctuation():
    # Accents are stripped, not transliterated: "Präprints" -> "praprints".
    assert title_similarity("Über Präprints!", "uber praprints") == 1.0
    assert title_similarity("Layer Normalization.", "layer  normalization") == 1.0
    assert title_similarity("Besançon, L.", "besancon l") == 1.0


def test_author_overlap_matches_across_the_two_real_naming_styles():
    """arXiv prints "Given Family"; PLOS prints "Family Initials". Same people."""
    assert author_overlap(["Jimmy Lei Ba", "Geoffrey E Hinton"], ["Ba, Jimmy Lei", "Hinton, Geoffrey E"]) == 1.0
    assert author_overlap(["Collins FS", "Tabak LA"], ["Francis S. Collins", "Lawrence A. Tabak"]) == 1.0
    assert author_overlap(["Smith J"], ["Jones A"]) == 0.0
    assert author_overlap([], ["Smith J"]) == 0.0
    assert author_overlap(["Smith J"], []) == 0.0


def test_a_two_letter_surname_is_not_mistaken_for_initials():
    """"Jimmy Lei Ba" has a two-letter SURNAME. A length test returned "lei" for it and
    silently dropped the overlap between two renderings of the same author to 0.33."""
    assert author_overlap(["Jimmy Lei Ba"], ["Ba, Jimmy"]) == 1.0
    # ...while a genuine all-caps initial block is still read as initials.
    assert author_overlap(["Collins FS"], ["Collins, Francis"]) == 1.0


def test_year_delta_is_absolute_so_a_late_citation_does_not_raise():
    """MatchEvidence.year_delta is ge=0, and the wrong-year defect usually cites LATE.

    A signed delta raises at construction on exactly the rows the eval exists to catch.
    D-105.
    """
    assert year_delta(2016, 2016) == 0
    assert year_delta(2020, 2015) == 5, "cited later than the record: must be positive"
    assert year_delta(2015, 2020) == 5, "cited earlier than the record: also positive"
    assert year_delta(None, 2016) is None
    assert year_delta(2016, None) is None
    # And the field really does reject a negative, which is why abs() is mandatory.
    with pytest.raises(Exception):
        MatchEvidence(ref_id="R01", year_delta=-5)


def test_a_reference_cited_too_late_builds_without_raising():
    evidence = build_evidence(make_ref(year=2020), make_resolved(year=2015), [])
    assert evidence.year_delta == 5


def test_doi_match_is_tri_state_and_none_is_not_false():
    assert doi_match("10.1/ABC", "10.1/abc") is True
    assert doi_match("10.1/abc", "10.2/xyz") is False
    assert doi_match(None, "10.1/abc") is None
    assert doi_match("10.1/abc", None) is None
    assert doi_match(None, None) is None
    assert doi_match(None, "10.1/abc") is not False, "D-034: absence is not disagreement"


def test_doi_match_none_is_the_common_case_on_real_input():
    """sample.pdf prints no DOIs in 40 references, so None is the norm, not the edge."""
    evidence = build_evidence(make_ref(doi=None), make_resolved(doi=None), [])
    assert evidence.doi_match is None


# ---------------------------------------------------------------------------
# The six indicators
# ---------------------------------------------------------------------------
def test_retracted_indicator():
    evidence = build_evidence(make_ref(), make_resolved(is_retracted=True), [])
    assert Indicator.RETRACTED.value in evidence.indicators


def test_doi_mismatch_requires_both_sides_to_have_a_doi():
    both = build_evidence(make_ref(doi="10.1/aaa"), make_resolved(doi="10.2/bbb"), [])
    assert Indicator.DOI_MISMATCH.value in both.indicators

    for ref_doi, resolved_doi in (("10.1/aaa", None), (None, "10.2/bbb"), (None, None)):
        evidence = build_evidence(make_ref(doi=ref_doi), make_resolved(doi=resolved_doi), [])
        assert Indicator.DOI_MISMATCH.value not in evidence.indicators, (
            "doi_match None means the claim cannot be made"
        )


def test_orphan_indicator_is_set_when_no_claim_cites_it():
    orphan = build_evidence(make_ref(cited_by_claims=[]), make_resolved(), [])
    assert Indicator.ORPHAN.value in orphan.indicators
    cited = build_evidence(make_ref(cited_by_claims=["C01"]), make_resolved(), [])
    assert Indicator.ORPHAN.value not in cited.indicators


def test_duplicate_entry_needs_divergent_metadata():
    first = make_ref(ref_id="R01", doi="10.1/aaa")
    same_but_different_doi = make_ref(ref_id="R02", doi="10.2/bbb")
    evidence = build_evidence(first, make_resolved(), [first, same_but_different_doi])
    assert Indicator.DUPLICATE_ENTRY.value in evidence.indicators

    identical = make_ref(ref_id="R02", doi="10.1/aaa")
    evidence = build_evidence(first, make_resolved(), [first, identical])
    assert Indicator.DUPLICATE_ENTRY.value not in evidence.indicators, (
        "an identical repeat is a formatting quirk, not a provenance problem"
    )


def test_malformed_comes_from_the_side_channel_not_from_a_missing_title():
    """D-102. A titleless work is a successful extraction of a titleless work."""
    titleless = make_ref(title=None)
    from_channel = build_evidence(titleless, None, [], malformed_ref_ids={"R01"})
    assert Indicator.MALFORMED.value in from_channel.indicators

    not_in_channel = build_evidence(titleless, None, [], malformed_ref_ids=frozenset())
    assert Indicator.MALFORMED.value not in not_in_channel.indicators, (
        "title is None must NOT imply malformed - that was the D-102 bug"
    )


def test_malformed_defaults_to_absent_when_the_caller_passes_nothing():
    """The frozen three-argument signature still works; see the module docstring."""
    evidence = build_evidence(make_ref(), make_resolved(), [])
    assert Indicator.MALFORMED.value not in evidence.indicators


# ---------------------------------------------------------------------------
# version_mismatch - D-020's P5 half
# ---------------------------------------------------------------------------
def test_version_mismatch_fires_when_exactly_one_side_is_a_preprint():
    preprint_ref = make_ref(arxiv_id="1607.06450")
    published = make_resolved(is_preprint=False)
    evidence = build_evidence(preprint_ref, published, [])
    assert Indicator.VERSION_MISMATCH.value in evidence.indicators

    # And the other direction.
    evidence = build_evidence(make_ref(), make_resolved(is_preprint=True), [])
    assert Indicator.VERSION_MISMATCH.value in evidence.indicators


def test_version_mismatch_does_not_fire_when_both_sides_agree():
    both_preprint = build_evidence(make_ref(arxiv_id="1607.06450"), make_resolved(is_preprint=True), [])
    assert Indicator.VERSION_MISMATCH.value not in both_preprint.indicators
    both_published = build_evidence(make_ref(), make_resolved(is_preprint=False), [])
    assert Indicator.VERSION_MISMATCH.value not in both_published.indicators


def test_version_mismatch_is_NOT_fired_when_is_preprint_is_None():
    """None means the provider did not say. Collapsing it to False would assert
    "definitely the published version" on missing data - D-020 forbids it."""
    evidence = build_evidence(make_ref(arxiv_id="1607.06450"), make_resolved(is_preprint=None), [])
    assert Indicator.VERSION_MISMATCH.value not in evidence.indicators
    assert any("did not say" in note for note in evidence.notes), (
        "the unknown has to be recorded, not silently dropped"
    )


def test_version_mismatch_needs_a_strong_title():
    """On a weak match we do not know it is the same work, and preprint-versus-published
    is a claim about ONE work."""
    weak = build_evidence(
        make_ref(arxiv_id="1607.06450", title="Something Else Entirely"),
        make_resolved(is_preprint=False),
        [],
    )
    assert Indicator.VERSION_MISMATCH.value not in weak.indicators


def test_an_arxiv_doi_counts_as_a_preprint_on_the_reference_side():
    assert reference_looks_like_a_preprint(make_ref(doi="10.48550/arXiv.1706.03762")) is True
    assert reference_looks_like_a_preprint(make_ref(arxiv_id="1607.06450")) is True
    assert reference_looks_like_a_preprint(make_ref()) is False


def test_version_mismatch_is_not_venue_divergence_and_not_year_alone():
    """Both fire on ordinary differences between a citation and a registry record."""
    venue_differs = build_evidence(make_ref(), make_resolved(venue="arXiv", is_preprint=False), [])
    assert Indicator.VERSION_MISMATCH.value not in venue_differs.indicators
    year_differs = build_evidence(make_ref(year=2016), make_resolved(year=2018, is_preprint=False), [])
    assert Indicator.VERSION_MISMATCH.value not in year_differs.indicators


# ---------------------------------------------------------------------------
# The classifier
# ---------------------------------------------------------------------------
def test_no_resolved_record_is_unresolvable():
    status, confidence, rationale = rule_based_status(make_evidence(resolved=None))
    assert status == VerdictStatus.UNRESOLVABLE.value
    assert 0.0 <= confidence <= 1.0
    assert rationale


def test_retraction_is_conflict():
    evidence = make_evidence(resolved=make_resolved(is_retracted=True), indicators=[Indicator.RETRACTED])
    assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value


def test_doi_mismatch_is_conflict():
    evidence = make_evidence(doi_match=False, indicators=[Indicator.DOI_MISMATCH])
    assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value


def test_a_matching_doi_is_verified():
    status, confidence, _ = rule_based_status(make_evidence(doi_match=True))
    assert status == VerdictStatus.VERIFIED.value
    assert confidence >= 0.9


def test_strong_title_plus_authors_is_verified_without_a_doi():
    status, _, rationale = rule_based_status(make_evidence(doi_match=None, author_overlap=0.9))
    assert status == VerdictStatus.VERIFIED.value
    assert "no DOI was printed" in rationale


def test_a_weak_match_with_no_author_overlap_is_conflict():
    evidence = make_evidence(title_similarity=0.2, author_overlap=0.0)
    assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value


def test_partial_agreement_is_needs_check():
    evidence = make_evidence(title_similarity=0.80, author_overlap=0.2)
    assert rule_based_status(evidence)[0] == VerdictStatus.NEEDS_CHECK.value


def test_version_mismatch_ALONE_is_not_a_conflict():
    """Citing the preprint of a later-published work is ordinary. Roy planted a corpus
    row for exactly this trap."""
    evidence = make_evidence(
        title_similarity=0.99,
        author_overlap=0.1,
        indicators=[Indicator.VERSION_MISMATCH],
    )
    status, _, rationale = rule_based_status(evidence)
    assert status == VerdictStatus.NEEDS_CHECK.value, "version_mismatch alone must not be conflict"
    assert status != VerdictStatus.CONFLICT.value
    assert "preprint" in rationale


def test_version_mismatch_with_a_retraction_is_still_a_conflict():
    """The indicators are orthogonal; the retraction is what makes it a conflict."""
    evidence = make_evidence(
        indicators=[Indicator.VERSION_MISMATCH, Indicator.RETRACTED],
        resolved=make_resolved(is_retracted=True),
    )
    assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value


# ---------------------------------------------------------------------------
# The title-search gate - D-104
# ---------------------------------------------------------------------------
def test_a_title_search_hit_cannot_reach_verified_without_author_agreement():
    """P4 measured this: a title search returned a DIFFERENT PLOS Biology article, on
    the branch carrying 14 of 34 PLOS references. Without the gate it scores verified -
    a false negative nobody re-reads."""
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(resolved=searched, title_similarity=0.99, author_overlap=0.1)
    status, _, rationale = rule_based_status(evidence)
    assert status == VerdictStatus.NEEDS_CHECK.value
    assert "searching the title" in rationale


def test_a_title_search_hit_WITH_author_agreement_may_be_verified():
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(resolved=searched, title_similarity=0.99, author_overlap=0.9)
    assert rule_based_status(evidence)[0] == VerdictStatus.VERIFIED.value


def test_the_gate_applies_only_to_the_title_search_branch():
    for branch in ("doi", "arxiv_id"):
        resolved = make_resolved(raw={"_lookup_branch": branch})
        evidence = make_evidence(resolved=resolved, title_similarity=0.99, author_overlap=0.9)
        assert rule_based_status(evidence)[0] == VerdictStatus.VERIFIED.value, branch


# ---------------------------------------------------------------------------
# A weak title-search hit is unresolvable, not conflict - D-108
# ---------------------------------------------------------------------------

#: The three measured cases from the P5 report, with their real signal values. Each is a
#: CORRECTLY cited reference that scored `conflict` because our own title search returned
#: a different paper.
D108_CASES = (
    ("R11", 0.66, 0.00, "Deep residual learning for image recognition"),
    ("R13", 0.35, 0.00, "Long short-term memory"),
    ("R33", 0.07, 0.00, "Governing the Commons"),
)


@pytest.mark.parametrize(("ref_id", "similarity", "overlap", "title"), D108_CASES)
def test_a_weak_title_search_hit_is_unresolvable_not_conflict(ref_id, similarity, overlap, title):
    """D-108. The three references from FINDING 1, at their measured signal values.

    `conflict` asserts the citation disagrees with the record. On this branch there is
    no record - the search returned its best hit, which is not the right hit - so the
    only thing we have evidence of is a bad search.
    """
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(
        ref_id=ref_id,
        resolved=searched,
        title_similarity=similarity,
        author_overlap=overlap,
        doi_match=None,
    )
    status, confidence, rationale = rule_based_status(evidence)
    assert status == VerdictStatus.UNRESOLVABLE.value, f"{ref_id} ({title}) -> {status}"
    assert status != VerdictStatus.CONFLICT.value
    assert "no sufficiently-matching record" in rationale
    assert 0.0 <= confidence <= 1.0


def test_the_same_weak_match_on_an_identifier_branch_is_still_a_conflict():
    """D-108 narrows `conflict`; it does not remove it.

    On the doi and arxiv_id branches an identifier tied the record to the reference, so
    a title sharing nothing with it IS a disagreement and stays one.
    """
    for branch in ("doi", "arxiv_id"):
        resolved = make_resolved(raw={"_lookup_branch": branch})
        evidence = make_evidence(
            resolved=resolved, title_similarity=0.07, author_overlap=0.0, doi_match=None
        )
        assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value, branch


def test_a_title_search_hit_with_no_author_overlap_is_unresolvable_even_on_a_fair_title():
    """"weak" is below title_weak OR no author overlap - either one, not both."""
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(
        resolved=searched, title_similarity=0.80, author_overlap=0.0, doi_match=None
    )
    assert rule_based_status(evidence)[0] == VerdictStatus.UNRESOLVABLE.value


def test_d108_does_not_swallow_the_d104_gate():
    """A STRONG title-search hit with no author agreement stays `needs_check`.

    D-104's demotion is a different statement - we found a plausible record and want it
    confirmed - and D-108 must not quietly replace it with "we found nothing".
    """
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(resolved=searched, title_similarity=0.99, author_overlap=0.0)
    status, _, rationale = rule_based_status(evidence)
    assert status == VerdictStatus.NEEDS_CHECK.value
    assert "searching the title" in rationale


def test_a_doi_mismatch_on_a_weak_title_search_hit_is_not_a_conflict():
    """plos_sample.pdf R24: a weak title search returned an unrelated book chapter, and
    its differing DOI then read as a conflict. The DOI is computed against a record we
    did not find - the same bad search wearing a stronger word."""
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(
        resolved=searched,
        title_similarity=0.44,
        author_overlap=0.0,
        doi_match=False,
        indicators=[Indicator.DOI_MISMATCH],
    )
    assert rule_based_status(evidence)[0] == VerdictStatus.UNRESOLVABLE.value


def test_a_doi_mismatch_on_an_identifier_branch_is_still_a_conflict():
    """The doi and arxiv_id branches are untouched: there the record was fetched BY the
    identifier, so a differing DOI on it is a real disagreement."""
    resolved = make_resolved(raw={"_lookup_branch": "doi"})
    evidence = make_evidence(
        resolved=resolved,
        title_similarity=0.40,
        author_overlap=0.0,
        doi_match=False,
        indicators=[Indicator.DOI_MISMATCH],
    )
    assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value


def test_a_retraction_outranks_d108_even_on_a_weak_title_search_hit():
    """D-108 sits BELOW the retraction check. Suppressing the highest-severity thing a
    provider tells us is not a call this branch makes."""
    retracted = make_resolved(raw={"_lookup_branch": "title_search"}, is_retracted=True)
    evidence = make_evidence(
        resolved=retracted,
        title_similarity=0.20,
        author_overlap=0.0,
        indicators=[Indicator.RETRACTED],
    )
    assert rule_based_status(evidence)[0] == VerdictStatus.CONFLICT.value


def test_a_partial_title_search_agreement_is_still_needs_check():
    """Some author overlap and a title above title_weak is partial agreement, not a
    failed search - D-108 must not eat the middle of the range."""
    searched = make_resolved(raw={"_lookup_branch": "title_search"})
    evidence = make_evidence(
        resolved=searched, title_similarity=0.80, author_overlap=0.5, doi_match=None
    )
    assert rule_based_status(evidence)[0] == VerdictStatus.NEEDS_CHECK.value


def test_a_missing_branch_stamp_does_not_crash_the_classifier():
    """An older cached ResolvedSource may have no _lookup_branch."""
    resolved = make_resolved(raw={})
    status, _, _ = rule_based_status(make_evidence(resolved=resolved, doi_match=True))
    assert status == VerdictStatus.VERIFIED.value


# ---------------------------------------------------------------------------
# Thresholds come from config, and nothing else
# ---------------------------------------------------------------------------
def test_the_classifier_reads_every_threshold_from_settings(monkeypatch):
    """Retuning is a config.yaml edit. Proven by making the edit change the outcome."""
    evidence = make_evidence(title_similarity=0.80, author_overlap=0.9, doi_match=None)
    assert rule_based_status(evidence)[0] == VerdictStatus.NEEDS_CHECK.value

    relaxed = dict(settings.thresholds())
    relaxed["title_strong"] = 0.75
    monkeypatch.setattr(settings, "thresholds", lambda config=None: relaxed)
    import src.matching.rules as rules_mod

    monkeypatch.setattr(rules_mod.settings, "thresholds", lambda config=None: relaxed)
    assert rule_based_status(evidence)[0] == VerdictStatus.VERIFIED.value, (
        "lowering title_strong in config must change the verdict"
    )


def test_year_tolerance_comes_from_config():
    tolerance = int(settings.thresholds()["year_tolerance"])
    within = make_evidence(year_delta=tolerance, doi_match=True)
    assert rule_based_status(within)[0] == VerdictStatus.VERIFIED.value
    beyond = make_evidence(year_delta=tolerance + 1, doi_match=True)
    assert rule_based_status(beyond)[0] != VerdictStatus.VERIFIED.value


def test_no_numeric_threshold_literal_sits_in_the_decision_path():
    """A literal here is a threshold that is in effect but not written down in config."""
    from pathlib import Path

    import src.matching.rules as rules_mod

    source = Path(rules_mod.__file__).read_text(encoding="utf-8")
    decision_path = source.split("def rule_based_status")[1].split("def _year_phrase")[0]
    for forbidden in ("0.92", "0.70", "0.60", "0.9,", "0.7,"):
        assert forbidden not in decision_path, f"{forbidden} should come from settings"


# ---------------------------------------------------------------------------
# The language rule is absolute
# ---------------------------------------------------------------------------
def test_no_rationale_contains_a_banned_term():
    """Every shape this module can produce, against config.yaml:banned_terms."""
    banned = [term.lower() for term in settings.banned_terms()]
    assert banned, "banned_terms must not be empty or this test is vacuous"

    shapes = []
    for resolved in (None, make_resolved(), make_resolved(raw={"_lookup_branch": "title_search"})):
        for similarity, overlap in itertools.product((0.0, 0.5, 0.8, 0.99), (0.0, 0.3, 0.9)):
            for delta in (None, 0, 1, 5):
                for doi_state in (None, True, False):
                    for indicators in (
                        [],
                        [Indicator.RETRACTED],
                        [Indicator.DOI_MISMATCH],
                        [Indicator.VERSION_MISMATCH],
                        [Indicator.MALFORMED],
                        [Indicator.ORPHAN, Indicator.DUPLICATE_ENTRY],
                    ):
                        if resolved is not None and Indicator.RETRACTED in indicators:
                            resolved_for_shape = make_resolved(is_retracted=True)
                        else:
                            resolved_for_shape = resolved
                        shapes.append(
                            MatchEvidence(
                                ref_id="R01",
                                resolved=resolved_for_shape,
                                title_similarity=similarity,
                                author_overlap=overlap,
                                year_delta=delta,
                                doi_match=doi_state,
                                indicators=indicators,
                            )
                        )

    assert len(shapes) > 500, "the cross-product should be broad"
    for evidence in shapes:
        status, confidence, rationale = rule_based_status(evidence)
        assert status in {s.value for s in VerdictStatus}
        assert 0.0 <= confidence <= 1.0
        assert rationale.strip()
        lowered = rationale.lower()
        for term in banned:
            assert term not in lowered, f"banned term {term!r} in: {rationale}"


def test_the_classifier_is_total_and_never_raises():
    """A1 calls this as a fallback precisely when something else already failed."""
    weird = MatchEvidence(ref_id="R01", resolved=None)
    assert rule_based_status(weird)[0] == VerdictStatus.UNRESOLVABLE.value
    empty_resolved = MatchEvidence(ref_id="R01", resolved=ResolvedSource(provider="x", raw={}))
    status, _, _ = rule_based_status(empty_resolved)
    assert status in {s.value for s in VerdictStatus}


def test_build_evidence_never_raises_on_empty_inputs():
    bare = Reference(ref_id="R01", raw_text="x")
    evidence = build_evidence(bare, None, [])
    assert evidence.ref_id == "R01"
    assert evidence.title_similarity == 0.0
    assert evidence.doi_match is None
    assert Indicator.ORPHAN.value in evidence.indicators


def test_evidence_is_deterministic():
    ref, resolved = make_ref(), make_resolved()
    first = build_evidence(ref, resolved, [ref], malformed_ref_ids={"R99"})
    second = build_evidence(ref, resolved, [ref], malformed_ref_ids={"R99"})
    assert first.model_dump() == second.model_dump()
    assert rule_based_status(first) == rule_based_status(second)
