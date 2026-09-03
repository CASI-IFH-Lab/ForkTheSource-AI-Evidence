"""R2-MINIMAL: the join and the two release gates.

Three tests, deliberately. REPLAN §4 cuts `test_harness.py` to the join and gate tests, so
exact-set indicators, defect_id recall and the worklist assertion are exercised by scoring
the real fixture ledger rather than by a test each -- those go in with `--full` in Phase 2.

The three here are the ones whose silent failure is expensive: a join that misses instead
of erroring reads as catastrophic recall (D-026), and a release gate that never fires is
worse than no gate at all because it is believed.

Offline: no network, no key. Every ledger under test is a mutated copy written into
tmp_path -- `tests/fixtures/ledger_fixture.json` is read and never written.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_LEDGER = ROOT / "tests" / "fixtures" / "ledger_fixture.json"
FIXTURE_LABELS = ROOT / "eval" / "golden_fixtures"


@pytest.fixture(scope="module")
def run_eval():
    spec = importlib.util.spec_from_file_location(
        "_run_eval_under_test", ROOT / "eval" / "run_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def planted(tmp_path: Path, mutate) -> Path:
    """A copy of the fixture ledger with `mutate` applied, written under tmp_path."""
    data = json.loads(FIXTURE_LEDGER.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "planted_ledger.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def score(run_eval, ledger: Path) -> int:
    return run_eval.main(["--fixtures", str(ledger), "--labels-dir", str(FIXTURE_LABELS)])


def entry(data: dict, ref_id: str) -> dict:
    return next(e for e in data["entries"] if e["reference"]["ref_id"] == ref_id)


def test_ref_id_mismatch_is_a_hard_error_naming_the_ids(run_eval, tmp_path, capsys):
    """A label with no ledger entry is a hard error with the id lists side by side."""
    ledger = planted(tmp_path, lambda d: d["entries"].pop(  # drop R08, keep its label
        next(i for i, e in enumerate(d["entries"]) if e["reference"]["ref_id"] == "R08")
    ))

    code = score(run_eval, ledger)
    err = capsys.readouterr().err

    assert code == 2, "a join gap must exit non-zero, never score as a miss (D-026)"
    assert "HARD ERROR" in err
    assert "ref_id join mismatch" in err
    assert "7 ledger entries vs 8 labels" in err
    assert "R08" in err, "the failure must name the unpaired id"
    assert "labelled, not in the ledger: R08" in err
    assert "LEDGER" in err and "LABELS" in err, "both id lists print side by side"


def test_conflict_on_clean_reference_fails_the_release_gate(run_eval, tmp_path, capsys):
    """conflict on an injected:false row is a false accusation -- hard FAIL (D-019)."""
    ledger = planted(tmp_path, lambda d: entry(d, "R01")["verdict"].update(status="conflict"))

    code = score(run_eval, ledger)
    out = capsys.readouterr().out

    assert code == 1, "a false accusation must block the release"
    assert "FAIL  conflict on an injected:false reference: 1" in out
    assert "RELEASE GATE FAIL" in out
    assert "R01" in out


def test_banned_term_in_a_rationale_fails_the_release_gate(run_eval, tmp_path, capsys):
    """Any banned term anywhere in a rationale, check or note is a hard FAIL (D-019).

    The hyphenated assertion is the point of the second half: `AI-generated` is the term
    the ADDENDUM's whole position rests on, and a matcher that cannot find it mid-sentence
    would leave the gate passing forever while reporting PASS.
    """
    from src.settings import banned_terms

    terms = banned_terms()
    sentence = "The bibliography for this section appears to be AI-generated in places."
    assert "AI-generated" in terms, "the term must come from settings.banned_terms(), not a copy"
    assert run_eval.scan_banned(sentence, terms) == ["AI-generated"], \
        "a hyphenated term must match inside a sentence"

    ledger = planted(tmp_path, lambda d: entry(d, "R01")["verdict"].update(rationale=sentence))

    code = score(run_eval, ledger)
    out = capsys.readouterr().out

    assert code == 1, "a banned term must block the release"
    assert "FAIL  banned terms in a rationale, check or note: 1" in out
    assert "R01: AI-generated" in out
    assert "RELEASE GATE FAIL" in out
