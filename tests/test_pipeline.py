"""P6 - the orchestrator. Every test here runs OFFLINE.

The extractor takes an injected stub client and `src.pipeline.resolve` is monkeypatched,
so nothing in this file needs `AIR_API_KEY`, `CROSSREF_MAILTO` or a network. That is not
only hygiene: the DoD is that the rule-based path runs end to end with no AIR key, and a
test that quietly needed one would not be testing it.
"""

from __future__ import annotations

import json

import pytest

from src import pipeline
from src.contract import (
    Ledger,
    MatchEvidence,
    Reference,
    ResolvedSource,
    Verdict,
    VerdictStatus,
    load_ledger,
)
from src.ingest import extractor

# ---------------------------------------------------------------------------
# D-204's seven stage keys, copied by hand.
#
# NOT imported from dashboard.theme. That import would cross a lane boundary in exactly
# the direction tests/test_layout.py forbids, and it would also make this test vacuous:
# comparing P6's tuple against the tuple P6 was written from proves nothing. This is a
# transcription of the decision entry, and if the two ever disagree, one of the two
# authors changed a frozen vocabulary and this is where it surfaces.
# ---------------------------------------------------------------------------
D204_STAGE_KEYS = ("intake", "extract", "resolve", "evidence", "verdict", "priority", "ledger")

#: The two stages that call a model, and therefore the only two that may report one.
D204_AIR_STAGES = ("extract", "verdict")


class _Reply:
    def __init__(self, content: str) -> None:
        self.choices = [type("Choice", (), {"message": type("M", (), {"content": content})()})()]


class StubClient:
    """The extractor's one method, replaying a canned reply per entry."""

    def __init__(self, replies: dict[str, str] | None = None) -> None:
        self.replies = replies or {}
        self.calls: list[str] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, *, model, temperature, messages, timeout):  # noqa: ANN001
        entry = messages[-1]["content"]
        self.calls.append(entry)
        for needle, reply in self.replies.items():
            if needle in entry:
                return _Reply(reply)
        return _Reply(
            json.dumps(
                {
                    "title": "Layer Normalization",
                    "authors": ["Jimmy Lei Ba", "Jamie Ryan Kiros", "Geoffrey E Hinton"],
                    "year": 2016,
                    "doi": None,
                    "arxiv_id": "1607.06450",
                    "venue": "arXiv",
                }
            )
        )


TWO_ENTRIES = (
    "[1] Jimmy Lei Ba, Jamie Ryan Kiros, and Geoffrey E Hinton. Layer normalization. 2016.\n"
    "[2] B. Writer. A second title. Review, 2020."
)

BODY = "We build on layer normalization [1]. A second sentence cites something else [2]."


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """A per-test extractor cache, so nothing here reads or writes the real one."""
    monkeypatch.setattr(extractor, "cache_path", lambda: tmp_path / "extractor_cache.json")


@pytest.fixture
def tiny_pdf(tmp_path):
    """A real two-page PDF on disk: body on page 1, two references on page 2.

    A real PDF rather than a stubbed `ParsedDocument`, because `intake` is one of the
    seven stages and mocking it out would leave the end-to-end DoD box untested.
    """
    from reportlab.pdfgen import canvas

    path = tmp_path / "tiny.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    for page in ([BODY], ["References", *TWO_ENTRIES.splitlines()]):
        text = pdf.beginText(72, 720)
        text.setFont("Helvetica", 11)
        text.setLeading(16)
        for line in page:
            text.textLine(line)
        pdf.drawText(text)
        pdf.showPage()
    pdf.save()
    return path


def _resolved(title="Layer Normalization", **kwargs) -> ResolvedSource:
    base = dict(
        provider="arxiv",
        title=title,
        authors=["Jimmy Lei Ba", "Jamie Ryan Kiros", "Geoffrey E Hinton"],
        year=2016,
        arxiv_id="1607.06450",
        raw={"_lookup_branch": "arxiv_id"},
    )
    base.update(kwargs)
    return ResolvedSource(**base)


@pytest.fixture
def offline_resolve(monkeypatch):
    """Every reference resolves to the same good record. No network, ever.

    Patched on `src.pipeline`, not on `src.resolvers.resolver`: P6 imports the name, so
    rebinding the source module would leave P6 holding the original function.
    """

    def fake(ref: Reference):
        return _resolved()

    monkeypatch.setattr(pipeline, "resolve", fake)
    return fake


def _run(tiny_pdf, tmp_path, **kwargs) -> Ledger:
    kwargs.setdefault("client", StubClient())
    kwargs.setdefault("output_dir", tmp_path / "out")
    return pipeline.run(tiny_pdf, **kwargs)


# ---------------------------------------------------------------------------
# End to end on the rule-based path, with no AIR key
# ---------------------------------------------------------------------------
def test_a_pdf_becomes_a_ledger_on_disk(tiny_pdf, tmp_path, offline_resolve):
    ledger = _run(tiny_pdf, tmp_path)

    assert isinstance(ledger, Ledger)
    assert len(ledger.entries) == 2
    assert [e.reference.ref_id for e in ledger.entries] == ["R01", "R02"]

    path = pipeline.ledger_path_for(ledger.document_name, tmp_path / "out")
    assert path.exists(), "run() writes the ledger before it returns"
    assert path.name == "tiny_ledger.json"
    assert load_ledger(path).model_dump() == ledger.model_dump(), "what was written round-trips"


def test_every_verdict_on_the_default_path_is_the_rule_baseline(tiny_pdf, tmp_path, offline_resolve):
    """No judge_fn, no AIR judge call, no import of src.judge - see test_layout."""
    ledger = _run(tiny_pdf, tmp_path)
    assert {e.verdict.judge_model for e in ledger.entries} == {"rule_based"}


def test_claims_are_extracted_and_reach_the_priority_score(tiny_pdf, tmp_path, offline_resolve):
    ledger = _run(tiny_pdf, tmp_path)
    assert ledger.claims, "extract_claims ran and its output is on the ledger"
    cited = {e.reference.ref_id for e in ledger.entries if e.reference.cited_by_claims}
    assert cited, "cited_by_claims was filled in place, which is priority's usage input"


# ---------------------------------------------------------------------------
# D-204 - the seven stage keys, in order, with model names on exactly two
# ---------------------------------------------------------------------------
def test_the_seven_d204_stage_keys_are_emitted_in_order(tiny_pdf, tmp_path, offline_resolve):
    seen: list[tuple[str, str | None]] = []
    _run(tiny_pdf, tmp_path, progress=lambda stage, model: seen.append((stage, model)))

    assert [stage for stage, _ in seen] == list(D204_STAGE_KEYS)


def test_only_the_two_air_stages_report_a_model_name(tiny_pdf, tmp_path, offline_resolve):
    """A model name on a deterministic stage would put a model on the strip that was
    never called - the opposite of what the AIR beat is for."""
    seen: dict[str, str | None] = {}
    _run(tiny_pdf, tmp_path, progress=lambda stage, model: seen.__setitem__(stage, model))

    named = {stage for stage, model in seen.items() if model is not None}
    assert named == set(D204_AIR_STAGES)
    for stage in D204_STAGE_KEYS:
        if stage not in D204_AIR_STAGES:
            assert seen[stage] is None, f"{stage} must pass None"


def test_the_extract_stage_reports_the_configured_extractor_model(
    tiny_pdf, tmp_path, offline_resolve
):
    from src import settings

    seen: dict[str, str | None] = {}
    _run(tiny_pdf, tmp_path, progress=lambda stage, model: seen.__setitem__(stage, model))
    assert seen["extract"] == settings.model_for("extractor")


def test_the_verdict_stage_reports_the_model_that_actually_ran(tiny_pdf, tmp_path, offline_resolve):
    """Default path: `rule_based`, matching the judge_model on every Verdict."""
    seen: dict[str, str | None] = {}
    ledger = _run(tiny_pdf, tmp_path, progress=lambda s, m: seen.__setitem__(s, m))
    assert seen["verdict"] == "rule_based"
    assert {e.verdict.judge_model for e in ledger.entries} == {seen["verdict"]}


def test_an_injected_judge_puts_the_configured_judge_model_on_the_strip(
    tiny_pdf, tmp_path, offline_resolve
):
    from src import settings

    def fake_judge(ref: Reference, ev: MatchEvidence) -> Verdict:
        return Verdict(
            ref_id=ev.ref_id,
            status=VerdictStatus.NEEDS_CHECK.value,
            confidence=0.5,
            rationale="a fake judge",
            judge_model="fake",
        )

    seen: dict[str, str | None] = {}
    _run(
        tiny_pdf,
        tmp_path,
        judge_fn=fake_judge,
        progress=lambda s, m: seen.__setitem__(s, m),
    )
    assert seen["verdict"] == settings.model_for("judge")


def test_the_key_is_verdict_and_not_judge(tiny_pdf, tmp_path, offline_resolve):
    """The chip is LABELLED "judge"; the key is `verdict`. D-204 is explicit, and getting
    it wrong lights nothing and raises nothing."""
    seen = []
    _run(tiny_pdf, tmp_path, progress=lambda stage, _model: seen.append(stage))
    assert "verdict" in seen
    assert "judge" not in seen


def test_an_unknown_stage_name_is_a_hard_error_here(tiny_pdf, tmp_path):
    """Downstream a misspelling is silent, so it is caught at the emit instead."""
    with pytest.raises(pipeline.PipelineIntegrityError, match="stage keys"):
        pipeline._emit(lambda s, m: None, "extraction", "some-model")


def test_a_callback_that_raises_does_not_take_the_run_down(tiny_pdf, tmp_path, offline_resolve):
    """A chip that fails to light must not cost a correct ledger."""

    def exploding(stage, model):
        raise RuntimeError("the strip blew up")

    ledger = _run(tiny_pdf, tmp_path, progress=exploding)
    assert len(ledger.entries) == 2


# ---------------------------------------------------------------------------
# judge_fn injection - the seam that lets P6 merge while A1 is unbuilt
# ---------------------------------------------------------------------------
def test_an_injected_judge_fn_decides_every_verdict(tiny_pdf, tmp_path, offline_resolve):
    calls: list[tuple[Reference, MatchEvidence]] = []

    def fake_judge(ref: Reference, ev: MatchEvidence) -> Verdict:
        calls.append((ref, ev))
        return Verdict(
            ref_id=ev.ref_id,
            status=VerdictStatus.CONFLICT.value,
            confidence=0.77,
            rationale="the fake judge says so",
            checks=["one check"],
            judge_model="fake-judge-v1",
        )

    ledger = _run(tiny_pdf, tmp_path, judge_fn=fake_judge)

    assert len(calls) == 2, "the judge is called once per reference"
    assert all(isinstance(ref, Reference) and isinstance(ev, MatchEvidence) for ref, ev in calls)
    assert {e.verdict.judge_model for e in ledger.entries} == {"fake-judge-v1"}
    assert ledger.summary_counts()["conflict"] == 2
    assert all(e.priority > 0 for e in ledger.entries), "the injected status drives priority"


def test_the_judge_receives_the_evidence_for_its_own_reference(tiny_pdf, tmp_path, offline_resolve):
    """A ref/evidence mismatch would be caught by LedgerEntry, but late and confusingly."""

    def checking_judge(ref: Reference, ev: MatchEvidence) -> Verdict:
        assert ref.ref_id == ev.ref_id
        return pipeline.default_judge(ref, ev)

    assert len(_run(tiny_pdf, tmp_path, judge_fn=checking_judge).entries) == 2


# ---------------------------------------------------------------------------
# The counts invariant - the app-level refusal
# ---------------------------------------------------------------------------
def test_the_counts_invariant_holds_on_a_real_run(tiny_pdf, tmp_path, offline_resolve):
    ledger = _run(tiny_pdf, tmp_path)
    assert sum(ledger.summary_counts().values()) == len(ledger.entries)
    assert ledger.counts_are_consistent()


def test_the_counts_invariant_raises_pipeline_integrity_error():
    """Armed against a stub, because through `Ledger` alone this cannot be made to fail -
    pydantic will not let a status outside the vocabulary onto a Verdict. An invariant
    nobody can see failing is an invariant nobody can trust."""

    class LyingLedger:
        entries = [1, 2, 3]

        def summary_counts(self):
            return {"verified": 1, "needs_check": 0, "conflict": 0, "unresolvable": 0}

    with pytest.raises(pipeline.PipelineIntegrityError, match="counters disagree"):
        pipeline._check_counts(LyingLedger())


def test_nothing_is_written_when_the_invariant_fails(tiny_pdf, tmp_path, monkeypatch, offline_resolve):
    """"Before writing" is the whole point - a refused run leaves no file behind."""

    def boom(ledger):
        raise pipeline.PipelineIntegrityError("counters disagree with its own rows")

    monkeypatch.setattr(pipeline, "_check_counts", boom)
    out = tmp_path / "out"
    with pytest.raises(pipeline.PipelineIntegrityError):
        _run(tiny_pdf, tmp_path)
    assert not (out / "tiny_ledger.json").exists()


# ---------------------------------------------------------------------------
# malformed_ref_ids reaches build_evidence - end to end, not by inspection
# ---------------------------------------------------------------------------
def test_the_malformed_set_reaches_build_evidence(tiny_pdf, tmp_path, offline_resolve):
    """P5's kwarg is optional, so a P6 that forgot it would lose every `malformed`
    indicator with nothing raising. This is the test that makes the gap loud."""
    client = StubClient(replies={"Layer normalization": "not json at all"})
    ledger = _run(tiny_pdf, tmp_path, client=client)

    by_id = {e.reference.ref_id: e for e in ledger.entries}
    assert "malformed" in by_id["R01"].evidence.indicators, "extraction failed and it shows"
    assert "malformed" not in by_id["R02"].evidence.indicators, "R02 extracted fine"
    assert by_id["R01"].reference.raw_text, "a malformed entry keeps its printed text"
    assert len(ledger.entries) == 2, "extraction never drops an entry"


def test_a_titleless_reference_is_not_malformed(tiny_pdf, tmp_path, offline_resolve):
    """D-102: malformed comes from the extraction ATTEMPT, never from `title is None`."""
    titleless = json.dumps(
        {"title": None, "authors": ["A. Author"], "year": 2020,
         "doi": None, "arxiv_id": None, "venue": None}
    )
    ledger = _run(tiny_pdf, tmp_path, client=StubClient(replies={"Layer normalization": titleless}))
    by_id = {e.reference.ref_id: e for e in ledger.entries}
    assert by_id["R01"].reference.title is None
    assert "malformed" not in by_id["R01"].evidence.indicators


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_two_consecutive_runs_produce_identical_summary_counts(tiny_pdf, tmp_path, offline_resolve):
    first = _run(tiny_pdf, tmp_path)
    second = _run(tiny_pdf, tmp_path)
    assert first.summary_counts() == second.summary_counts()
    assert first.indicator_counts() == second.indicator_counts()
    assert [e.priority for e in first.entries] == [e.priority for e in second.entries]
    assert first.model_dump() == second.model_dump(), "byte-for-byte, not just the counters"


def test_the_worklist_order_is_stable_across_runs(tiny_pdf, tmp_path, offline_resolve):
    first = [e.reference.ref_id for e in _run(tiny_pdf, tmp_path).worklist()]
    second = [e.reference.ref_id for e in _run(tiny_pdf, tmp_path).worklist()]
    assert first == second


# ---------------------------------------------------------------------------
# A registry outage degrades to unresolvable with the run still completing
# ---------------------------------------------------------------------------
def test_a_dead_registry_degrades_to_unresolvable(tiny_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "resolve", lambda ref: None)
    ledger = _run(tiny_pdf, tmp_path)
    assert ledger.summary_counts()["unresolvable"] == 2
    assert ledger.evidence_coverage() == 0.0
    assert sum(ledger.summary_counts().values()) == len(ledger.entries)


# ---------------------------------------------------------------------------
# The lane boundary, asserted from this side too
# ---------------------------------------------------------------------------
def test_pipeline_does_not_import_the_judge_lane():
    """test_layout.py owns this rule; this is the one-line version at P6's own door,
    because it is P6's merge-while-A1-is-unbuilt guarantee that depends on it."""
    import ast
    from pathlib import Path

    source = Path(pipeline.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not [n for n in imported if n.startswith("src.judge") or n.startswith("dashboard")]
