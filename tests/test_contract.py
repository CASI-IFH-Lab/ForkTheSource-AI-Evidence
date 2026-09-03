"""Offline tests for the src.contract / src.priority data contract.

No network access, no API key: everything here runs against the local
pydantic models, the committed fixture, and in-memory data.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from src import settings

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
from src.priority import _SCALAR_KEYS, _SEVERITY_KEYS, compute_priority

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = FIXTURES_DIR / "ledger_fixture.json"

# Read from config.yaml rather than kept as a private copy: D-019 puts this
# exact scan in A1's gate.py and R2's release gate, and a second hardcoded
# list would drift from the one those two read. config.yaml currently
# carries 11 terms, including "not reproducible" and "AI-written", which an
# inlined list written against the B1 brief would have missed.
BANNED_TERMS = tuple(term.lower() for term in settings.banned_terms())

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
        "verified": 3,
        "needs_check": 1,
        "conflict": 2,
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


def test_orphan_is_verified_not_needs_check(fixture_ledger):
    """D-017: orphan is derived from the claim map, not from resolution.

    An uncited reference that resolves cleanly is verified. Pinned because
    needs_check is the intuitive-but-wrong answer, and it would put the
    lowest-value item in the file on the reviewer's worklist.
    """
    matches = [e for e in fixture_ledger.entries if "orphan" in e.evidence.indicators]
    assert matches, "no entry carries the orphan indicator"
    for entry in matches:
        assert entry.verdict.status == "verified", (
            f"{entry.reference.ref_id}: orphan must be verified per D-017, "
            f"got {entry.verdict.status!r}"
        )
        assert entry.evidence.resolved is not None


def test_duplicate_entry_is_needs_check_not_conflict(fixture_ledger):
    """D-016: divergent metadata means one copy is wrong and nothing says which.

    conflict would assert the bibliography is definitely wrong; it also
    carries severity 1.0 and would crowd the worklist.
    """
    matches = [
        e for e in fixture_ledger.entries if "duplicate_entry" in e.evidence.indicators
    ]
    assert matches, "no entry carries the duplicate_entry indicator"
    for entry in matches:
        assert entry.verdict.status == "needs_check", (
            f"{entry.reference.ref_id}: duplicate_entry must be needs_check per "
            f"D-016, got {entry.verdict.status!r}"
        )


def test_doi_mismatch_records_doi_match_false_not_none(fixture_ledger):
    """The tri-state must distinguish "DOIs disagree" from "no DOI to compare".

    docs/defect_catalog.md names doi_match coming back None instead of False
    as the likely swapped-DOI failure, so the fixture models False.
    """
    matches = [e for e in fixture_ledger.entries if "doi_mismatch" in e.evidence.indicators]
    assert matches, "no entry carries the doi_mismatch indicator"
    for entry in matches:
        assert entry.evidence.doi_match is False, (
            f"{entry.reference.ref_id}: doi_match must be False, not "
            f"{entry.evidence.doi_match!r}"
        )


def test_version_mismatch_row_has_exactly_one_preprint_side(fixture_ledger):
    """D-020 via D-036: the indicator keys on preprint-ness, not on venue.

    Pinned on the fixture so the "exactly one side" reading is demonstrated
    rather than only described, and so a future edit that drops is_preprint
    from the resolved side fails here.
    """
    matches = [
        e for e in fixture_ledger.entries if "version_mismatch" in e.evidence.indicators
    ]
    assert matches, "no entry carries the version_mismatch indicator"
    for entry in matches:
        citation_is_preprint = entry.reference.arxiv_id is not None
        resolved = entry.evidence.resolved
        assert resolved is not None
        assert resolved.is_preprint is False, (
            f"{entry.reference.ref_id}: the resolved side must SAY it is not a "
            f"preprint, got {resolved.is_preprint!r} (None would mean the "
            "provider did not say -- D-036)"
        )
        assert citation_is_preprint != bool(resolved.is_preprint), (
            "exactly one side must be a preprint"
        )


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


@pytest.mark.parametrize(
    "raw_doi",
    [
        "10.1/X",
        "https://doi.org/10.1/x",
        "doi:10.1/x",
        " 10.1/x ;",
    ],
)
def test_resolved_source_doi_normalizes_identically_to_reference(raw_doi):
    """Both sides of a DOI comparison must be normalized the same way.

    P5 compares Reference.doi against ResolvedSource.doi to set doi_match.
    If only one side were normalized, a citation printing
    "https://doi.org/10.1/X" against a resolver returning "10.1/x" would
    compare unequal and raise a spurious doi_mismatch -> conflict, which is
    a false accusation on a correctly-cited reference.
    """
    resolved = ResolvedSource(provider="crossref", doi=raw_doi, raw={})
    reference = Reference(ref_id="R01", raw_text="text", doi=raw_doi)
    assert resolved.doi == "10.1/x"
    assert resolved.doi == reference.doi


def test_resolved_source_doi_normalizes_on_assignment():
    resolved = ResolvedSource(provider="crossref", raw={})
    resolved.doi = " 10.1/X ;"
    assert resolved.doi == "10.1/x"


def test_resolved_source_doi_none_stays_none():
    assert ResolvedSource(provider="crossref", raw={}).doi is None


@pytest.mark.parametrize("value", [True, False, None])
def test_is_preprint_accepts_all_three_states(value):
    """D-036: tri-state, like doi_match. All three are legal values."""
    assert ResolvedSource(provider="openalex", is_preprint=value, raw={}).is_preprint is value


def test_is_preprint_defaults_to_none_not_false():
    """None means "the provider did not say", NOT "not a preprint".

    Mirrors test_doi_mismatch_records_doi_match_false_not_none, which pins
    the same None-vs-False distinction on the other tri-state field.
    Defaulting to False would let
    P5 conclude "definitely a published version" from a provider that said
    nothing, and D-020's indicator would then fire or not fire on absent
    evidence rather than on a real signal.
    """
    resolved = ResolvedSource(provider="crossref", raw={})
    assert resolved.is_preprint is None
    assert resolved.is_preprint is not False


def test_is_preprint_none_is_distinguishable_from_false():
    silent = ResolvedSource(provider="crossref", raw={})
    says_not_preprint = ResolvedSource(provider="crossref", is_preprint=False, raw={})
    assert silent.is_preprint is None
    assert says_not_preprint.is_preprint is False
    # The distinction must survive a JSON round trip, since it crosses a
    # lane boundary as serialised ledger data.
    assert silent.model_dump(mode="json")["is_preprint"] is None
    assert says_not_preprint.model_dump(mode="json")["is_preprint"] is False


def test_resolved_source_arxiv_id_round_trips():
    resolved = ResolvedSource(provider="arxiv", arxiv_id="2005.14165", is_preprint=True, raw={})
    dumped = resolved.model_dump(mode="json")
    assert dumped["arxiv_id"] == "2005.14165"
    assert ResolvedSource.model_validate(dumped).arxiv_id == "2005.14165"
    assert ResolvedSource(provider="crossref", raw={}).arxiv_id is None


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
# _load_priority_config reads the REAL config.yaml through src.settings.
#
# config.yaml's priority block currently carries `severity` and nothing else:
# usage_base, usage_step, retracted_bonus and cap are absent (D-009,
# docs/pr/B0.md flag 3). Naming them is B1's, but config.yaml is Ritik's
# file, so until they land the default path must fail closed rather than
# invent numbers. These tests pin that, and pin the success path against an
# injected complete block so the reader is proven to work the day it lands.
# --------------------------------------------------------------------------


def test_priority_config_is_either_complete_or_fails_closed():
    """Asserts the contract, not the current contents of config.yaml.

    config.yaml is Ritik's file, and D-032 part 2 asks him to add four keys
    to it. A test that pins the keys as *absent* would go red the moment he
    does that -- reading as "your config PR broke B1", inviting a revert of
    a correct change, and breaking the ground rule that the suite is green
    when a PR opens. So this asserts both legitimate states and rejects only
    the dangerous one:

      keys present -> the default path works, scoring from config
      keys absent  -> RuntimeError naming exactly the missing keys, and
                      naming none of the formula's numbers, which would mean
                      a hardcoded default had crept into src/priority.py

    The state this rejects is "keys absent but a score comes back anyway" --
    a silent default. Which branch runs is discovered from config.yaml
    through src.settings, never assumed.
    """
    block = settings.load_config().get("priority") or {}
    severity = block.get("severity") or {}

    missing = [f"severity.{k}" for k in _SEVERITY_KEYS if k not in severity]
    missing += [k for k in _SCALAR_KEYS if k not in block]

    ev = _minimal_evidence()
    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.9)

    if not missing:
        # Complete. severity.conflict 1.0 x usage saturated at 3 claims
        # (0.4 + 0.2*3 -> capped 1.0) x confidence 0.9 = 0.9, per D-032.
        assert compute_priority(ev, verdict, 3) == 0.9, (
            "the default path must score from config.yaml: with D-032's values "
            "(severity.conflict 1.0, usage_base 0.4, usage_step 0.2, cap 1.0) a "
            "conflict at confidence 0.9 cited by 3 claims scores 0.9"
        )
        return

    with pytest.raises(RuntimeError) as exc_info:
        compute_priority(ev, verdict, 3)
    message = str(exc_info.value)

    # Split on the sentence terminator, not on "." -- a missing severity key
    # is itself dotted ("severity.conflict") and would be truncated.
    clause = message.split("keys: ", 1)[1].split(". Priority scoring", 1)[0]
    named = [key.strip() for key in clause.split(",")]
    assert sorted(named) == sorted(missing), (
        f"the error must name exactly the missing keys.\n"
        f"  missing in config.yaml: {sorted(missing)}\n"
        f"  named in the error    : {sorted(named)}"
    )
    for number in ("0.4", "0.2", "0.3"):
        assert number not in message, (
            f"{number!r} appears in the fail-closed error -- a hardcoded default "
            "may have crept into src/priority.py. D-032: no defaults, ever."
        )


def test_load_priority_config_names_only_the_keys_that_are_missing(monkeypatch):
    partial = {"priority": {"severity": WEIGHTS["severity"], "usage_base": 0.4}}
    monkeypatch.setattr(settings, "load_config", lambda *a, **k: partial)

    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.5)
    with pytest.raises(RuntimeError) as exc_info:
        compute_priority(_minimal_evidence(), verdict, 1)
    message = str(exc_info.value)
    missing_clause = message.split("config.yaml is missing priority config keys: ")[1]
    assert "usage_step" in missing_clause
    assert "retracted_bonus" in missing_clause
    assert "cap" in missing_clause
    assert "usage_base" not in missing_clause  # present, so not reported


def test_load_priority_config_matches_explicit_weights_when_block_is_complete(monkeypatch):
    complete = {"priority": dict(WEIGHTS)}
    monkeypatch.setattr(settings, "load_config", lambda *a, **k: complete)

    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=0.5)
    ev = _minimal_evidence()
    assert compute_priority(ev, verdict, 1) == compute_priority(
        ev, verdict, 1, weights=WEIGHTS
    )


def test_load_priority_config_uses_severity_from_config_not_a_default(monkeypatch):
    """A retuned severity must actually change the score."""
    retuned = {"priority": {**WEIGHTS, "severity": {**WEIGHTS["severity"], "conflict": 0.5}}}
    monkeypatch.setattr(settings, "load_config", lambda *a, **k: retuned)

    verdict = _minimal_verdict(status=VerdictStatus.CONFLICT, confidence=1.0)
    ev = _minimal_evidence()
    assert compute_priority(ev, verdict, 3) == 0.5
