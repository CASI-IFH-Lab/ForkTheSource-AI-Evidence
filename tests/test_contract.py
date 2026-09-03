"""Offline tests for the src.contract / src.priority data contract.

No network access, no API key: everything here runs against the local
pydantic models, the committed fixture, and in-memory data.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.contract import (
    INDICATORS,
    STATUSES,
    Claim,
    Indicator,
    Ledger,
    LedgerEntry,
    MatchEvidence,
    Reference,
    ResolvedSource,
    Verdict,
    VerdictStatus,
    load_ledger,
    save_ledger,
)
from src.priority import compute_priority

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = FIXTURES_DIR / "ledger_fixture.json"

BANNED_TERMS = (
    "fake",
    "fabricated",
    "invented",
    "nonexistent",
    "fraud",
    "plagiarism",
    "irreproducible",
    "sloppy",
    "ai-generated",
)

WEIGHTS = {
    "severity": {
        "conflict": 1.0,
        "needs_check": 0.6,
        "unresolvable": 0.5,
        "verified": 0.0,
    },
    "usage_base": 0.4,
    "usage_step": 0.2,
    "retracted_bonus": 0.3,
    "cap": 1.0,
}


def _load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "build_ledger_fixture", FIXTURES_DIR / "build_ledger_fixture.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _minimal_verdict(status: VerdictStatus = VerdictStatus.CONFLICT, **overrides) -> Verdict:
    kwargs = dict(
        ref_id="X",
        status=status,
        confidence=0.5,
        rationale="rationale",
        checks=["check"],
        judge_model="stub-judge-v0",
    )
    kwargs.update(overrides)
    return Verdict(**kwargs)


def _minimal_evidence(**overrides) -> MatchEvidence:
    kwargs = dict(ref_id="X")
    kwargs.update(overrides)
    return MatchEvidence(**kwargs)


@pytest.fixture(scope="session")
def fixture_ledger() -> Ledger:
    return load_ledger(FIXTURE_PATH)


# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------


def test_statuses_are_exactly_the_four_expected():
    assert set(STATUSES) == {"verified", "needs_check", "conflict", "unresolvable"}
    assert "extraction_failed" not in STATUSES
    with pytest.raises(ValueError):
        VerdictStatus("extraction_failed")


def test_indicator_vocabulary_is_closed():
    assert set(INDICATORS) == {
        "retracted",
        "version_mismatch",
        "doi_mismatch",
        "duplicate_entry",
        "orphan",
        "malformed",
    }
    with pytest.raises(ValidationError):
        _minimal_evidence(indicators=["not_a_real_indicator"])


# --------------------------------------------------------------------------
# Fixture structural checks
# --------------------------------------------------------------------------


def test_fixture_loads_and_validates(fixture_ledger):
    assert fixture_ledger.contract_version == "v0"
    assert len(fixture_ledger.entries) == 8


def test_fixture_status_counts_match_definition_of_done(fixture_ledger):
    assert fixture_ledger.summary_counts() == {
        "verified": 2,
        "needs_check": 1,
        "conflict": 3,
        "unresolvable": 2,
    }
    assert fixture_ledger.counts_are_consistent()


def test_fixture_coverage_is_075(fixture_ledger):
    assert fixture_ledger.evidence_coverage() == 0.75


def test_fixture_every_status_present(fixture_ledger):
    counts = fixture_ledger.summary_counts()
    for status in STATUSES:
        assert counts[status] > 0, f"status {status!r} has no entries in the fixture"


def test_fixture_every_indicator_present_exactly_once(fixture_ledger):
    counts = fixture_ledger.indicator_counts()
    for indicator in INDICATORS:
        assert counts[indicator] == 1, f"indicator {indicator!r} count was {counts[indicator]}"


def test_version_mismatch_is_never_conflict(fixture_ledger):
    matches = [
        entry
        for entry in fixture_ledger.entries
        if "version_mismatch" in entry.evidence.indicators
    ]
    assert matches, "no entry carries the version_mismatch indicator"
    for entry in matches:
        assert entry.verdict.status != "conflict"
        assert entry.verdict.status == "verified"


def test_malformed_entry_keeps_raw_text(fixture_ledger):
    matches = [
        entry for entry in fixture_ledger.entries if "malformed" in entry.evidence.indicators
    ]
    assert matches, "no entry carries the malformed indicator"
    for entry in matches:
        assert entry.reference.raw_text.strip() != ""


def test_resolved_none_iff_unresolvable(fixture_ledger):
    for entry in fixture_ledger.entries:
        is_unresolved_status = entry.verdict.status == "unresolvable"
        is_resolved_none = entry.evidence.resolved is None
        assert is_resolved_none == is_unresolved_status, (
            f"{entry.reference.ref_id}: resolved is None ({is_resolved_none}) "
            f"but status is {entry.verdict.status!r}"
        )


def test_non_verified_entries_have_at_least_one_check(fixture_ledger):
    for entry in fixture_ledger.entries:
        if entry.verdict.status != "verified":
            assert len(entry.verdict.checks) >= 1, f"{entry.reference.ref_id} has no checks"


def test_cited_by_claims_is_inverse_of_claim_ref_ids(fixture_ledger):
    expected: dict[str, list[str]] = {entry.reference.ref_id: [] for entry in fixture_ledger.entries}
    for claim in fixture_ledger.claims:
        for ref_id in claim.ref_ids:
            expected[ref_id].append(claim.claim_id)

    for entry in fixture_ledger.entries:
        assert entry.reference.cited_by_claims == expected[entry.reference.ref_id]


def test_fixture_contains_no_banned_terms():
    text = FIXTURE_PATH.read_text(encoding="utf-8").lower()
    for term in BANNED_TERMS:
        assert term not in text, f"banned term {term!r} found in fixture"


# --------------------------------------------------------------------------
# Validators
# --------------------------------------------------------------------------


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Reference(ref_id="R01", raw_text="text", unexpected_field="x")


def test_confidence_above_one_rejected():
    with pytest.raises(ValidationError):
        _minimal_verdict(confidence=1.4)


def test_more_than_three_checks_rejected():
    with pytest.raises(ValidationError):
        _minimal_verdict(checks=["a", "b", "c", "d"])


@pytest.mark.parametrize(
    "raw_doi",
    [
        "10.1/X",
        "https://doi.org/10.1/x",
        "doi:10.1/x",
        " 10.1/x ;",
    ],
)
def test_doi_normalization_on_init(raw_doi):
    ref = Reference(ref_id="R01", raw_text="text", doi=raw_doi)
    assert ref.doi == "10.1/x"


def test_doi_normalization_on_assignment():
    ref = Reference(ref_id="R01", raw_text="text")
    ref.doi = " 10.1/X ;"
    assert ref.doi == "10.1/x"


def test_doi_none_stays_none():
    ref = Reference(ref_id="R01", raw_text="text")
    assert ref.doi is None


def test_retracted_source_without_indicator_raises():
    with pytest.raises(ValidationError):
        _minimal_evidence(
            resolved=ResolvedSource(provider="crossref", is_retracted=True, raw={}),
            indicators=[],
        )


def test_retracted_source_with_indicator_passes():
    ev = _minimal_evidence(
        resolved=ResolvedSource(provider="crossref", is_retracted=True, raw={}),
        indicators=[Indicator.RETRACTED],
    )
    assert "retracted" in ev.indicators


def test_duplicate_indicators_collapsed_preserving_order():
    ev = _minimal_evidence(
        resolved=ResolvedSource(provider="crossref", is_retracted=True, raw={}),
        indicators=[Indicator.RETRACTED, Indicator.RETRACTED, Indicator.DOI_MISMATCH],
    )
    assert ev.indicators == ["retracted", "doi_mismatch"]


def test_ledger_entry_ref_id_misalignment_raises():
    reference = Reference(ref_id="A", raw_text="text")
    evidence = _minimal_evidence(ref_id="B")
    verdict = _minimal_verdict(ref_id="A")
    with pytest.raises(ValidationError):
        LedgerEntry(reference=reference, evidence=evidence, verdict=verdict)


def test_ledger_duplicate_ref_ids_raises():
    def make_entry(ref_id: str) -> LedgerEntry:
        return LedgerEntry(
            reference=Reference(ref_id=ref_id, raw_text="text"),
            evidence=_minimal_evidence(ref_id=ref_id),
            verdict=_minimal_verdict(ref_id=ref_id),
        )

    with pytest.raises(ValidationError):
        Ledger(document_name="doc", entries=[make_entry("R01"), make_entry("R01")])


def test_empty_ledger_has_zero_counts_and_zero_coverage():
    ledger = Ledger(document_name="empty")
    assert ledger.summary_counts() == {
        "verified": 0,
        "needs_check": 0,
        "conflict": 0,
        "unresolvable": 0,
    }
    assert ledger.evidence_coverage() == 0.0


# --------------------------------------------------------------------------
# save/load round trip
# --------------------------------------------------------------------------


def test_save_load_save_is_byte_identical(fixture_ledger, tmp_path):
    first = save_ledger(fixture_ledger, tmp_path / "first.json")
    reloaded = load_ledger(first)
    second = save_ledger(reloaded, tmp_path / "second.json")
    assert first.read_bytes() == second.read_bytes()


def test_committed_fixture_equals_a_fresh_save(tmp_path):
    generator = _load_generator_module()
    ledger = generator.build_ledger()
    fresh_path = save_ledger(ledger, tmp_path / "fresh.json")
    assert fresh_path.read_bytes() == FIXTURE_PATH.read_bytes()


# --------------------------------------------------------------------------
# worklist
# --------------------------------------------------------------------------


def test_worklist_is_deterministic(fixture_ledger):
    assert fixture_ledger.worklist() == fixture_ledger.worklist()


def test_worklist_is_descending_by_priority(fixture_ledger):
    priorities = [entry.priority for entry in fixture_ledger.worklist()]
    assert priorities == sorted(priorities, reverse=True)


def test_worklist_top_three_never_verified(fixture_ledger):
    top_three = fixture_ledger.worklist(limit=3)
    assert len(top_three) == 3
    for entry in top_three:
        assert entry.verdict.status != "verified"


# --------------------------------------------------------------------------
# priority formula
# --------------------------------------------------------------------------


def test_priority_verified_is_always_zero():
    verdict = _minimal_verdict(status=VerdictStatus.VERIFIED, confidence=0.99)
    ev = _minimal_evidence()
    for n in (0, 1, 3, 10):
        assert compute_priority(ev, verdict, n, weights=WEIGHTS) == 0.0


def test_priority_conflict_with_more_usage_beats_needs_check_with_less():
    ev = _minimal_evidence()
    conflict_verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.8)
    needs_check_verdict = _minimal_verdict(status=VerdictStatus.NEEDS_CHECK, confidence=0.8)
    conflict_score = compute_priority(ev, conflict_verdict, 3, weights=WEIGHTS)
    needs_check_score = compute_priority(ev, needs_check_verdict, 1, weights=WEIGHTS)
    assert conflict_score > needs_check_score


def test_priority_usage_saturates_at_three_claims():
    ev = _minimal_evidence()
    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.7)
    at_three = compute_priority(ev, verdict, 3, weights=WEIGHTS)
    at_four = compute_priority(ev, verdict, 4, weights=WEIGHTS)
    at_ten = compute_priority(ev, verdict, 10, weights=WEIGHTS)
    assert at_three == at_four == at_ten


def test_priority_retraction_adds_exactly_bonus():
    verdict = _minimal_verdict(status=VerdictStatus.NEEDS_CHECK, confidence=0.5)
    without = compute_priority(ev=_minimal_evidence(indicators=[]), verdict=verdict, n_citing_claims=0, weights=WEIGHTS)
    with_retraction = compute_priority(
        ev=_minimal_evidence(
            resolved=ResolvedSource(provider="crossref", is_retracted=True, raw={}),
            indicators=[Indicator.RETRACTED],
        ),
        verdict=verdict,
        n_citing_claims=0,
        weights=WEIGHTS,
    )
    assert round(with_retraction - without, 3) == 0.3


def test_priority_caps_at_one():
    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=1.0)
    ev = _minimal_evidence(
        resolved=ResolvedSource(provider="crossref", is_retracted=True, raw={}),
        indicators=[Indicator.RETRACTED],
    )
    assert compute_priority(ev, verdict, 10, weights=WEIGHTS) == 1.0


def test_priority_is_always_within_zero_one():
    for status in VerdictStatus:
        for confidence in (0.0, 0.3, 0.5, 0.7, 1.0):
            for n in (0, 1, 2, 3, 5):
                for retracted in (False, True):
                    verdict = _minimal_verdict(status=status, confidence=confidence)
                    if retracted:
                        ev = _minimal_evidence(
                            resolved=ResolvedSource(provider="crossref", is_retracted=True, raw={}),
                            indicators=[Indicator.RETRACTED],
                        )
                    else:
                        ev = _minimal_evidence()
                    score = compute_priority(ev, verdict, n, weights=WEIGHTS)
                    assert 0.0 <= score <= 1.0


def test_priority_unknown_status_raises_key_error():
    incomplete_weights = {
        "severity": {"conflict": 1.0, "needs_check": 0.6, "verified": 0.0},
        "usage_base": 0.4,
        "usage_step": 0.2,
        "retracted_bonus": 0.3,
        "cap": 1.0,
    }
    verdict = _minimal_verdict(status=VerdictStatus.UNRESOLVABLE, confidence=0.5)
    ev = _minimal_evidence()
    with pytest.raises(KeyError):
        compute_priority(ev, verdict, 1, weights=incomplete_weights)


# --------------------------------------------------------------------------
# _load_priority_config fail-closed behavior (no config.yaml/src.settings
# exist yet -- see src/priority.py's docstring)
# --------------------------------------------------------------------------


def test_load_priority_config_missing_module_raises_runtime_error(monkeypatch):
    monkeypatch.delitem(sys.modules, "src.settings", raising=False)
    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.5)
    ev = _minimal_evidence()
    with pytest.raises(RuntimeError) as exc_info:
        compute_priority(ev, verdict, 1)
    message = str(exc_info.value)
    assert "severity.conflict" in message
    assert "usage_base" in message


def test_load_priority_config_partial_block_names_missing_keys(monkeypatch):
    fake_settings = types.ModuleType("src.settings")
    fake_settings.CONFIG = {
        "priority": {
            "severity": {"conflict": 1.0, "needs_check": 0.6, "unresolvable": 0.5, "verified": 0.0},
            "usage_base": 0.4,
        }
    }
    monkeypatch.setitem(sys.modules, "src.settings", fake_settings)

    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.5)
    ev = _minimal_evidence()
    with pytest.raises(RuntimeError) as exc_info:
        compute_priority(ev, verdict, 1)
    message = str(exc_info.value)
    assert "usage_step" in message
    assert "retracted_bonus" in message
    assert "cap" in message
    assert "usage_base" not in message  # already present in the fake config


def test_load_priority_config_success_matches_explicit_weights(monkeypatch):
    fake_settings = types.ModuleType("src.settings")
    fake_settings.CONFIG = {"priority": WEIGHTS}
    monkeypatch.setitem(sys.modules, "src.settings", fake_settings)

    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.5)
    ev = _minimal_evidence()
    via_settings = compute_priority(ev, verdict, 1)
    via_explicit_weights = compute_priority(ev, verdict, 1, weights=WEIGHTS)
    assert via_settings == via_explicit_weights
