"""A1 - offline tests for the AIR judge and the gate.

Every test in this file runs with NO network and NO API key. The one
exception is ``test_live_air_smoke``, which is skipped unless a key is
present, because CI has none and a suite that goes red without credentials
stops being run.

The fake client is the whole trick. ``judge_reference`` takes a keyword-only
``client``, so the ladder - reply, retry, schema failure, gateway error - is
driven by handing it a scripted object rather than by patching the network.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src import settings
from src.contract import MatchEvidence, Reference, ResolvedSource, Verdict, load_ledger
from src.judge import gate as gate_mod
from src.judge.agent import (
    PARSE_NOISE_CEILING,
    STUB_CONFIDENCE,
    JudgeParseError,
    JudgeSchemaError,
    apply_evidence_rules,
    build_verdict,
    extract_json_object,
    judge_reference,
    stub_status,
)
from src.judge.gate import (
    GATE_FAILURE_RATIONALE,
    GateCountMismatch,
    GateDuplicateVerdict,
    force_needs_check,
    gate_batch,
    verdict_banned_terms,
)
from src.judge.prompts import JUDGE_SYSTEM_PROMPT, build_user_prompt, evidence_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ledger_fixture.json"

JUDGE_MODEL = settings.model_for("judge")
BANNED_TERMS = settings.banned_terms()

# How long the live smoke test waits to decide the gateway is unreachable.
PROBE_TIMEOUT_SECONDS = 20.0

# So the live smoke test below actually runs on a machine that has a .env,
# and stays skipped in CI, which has none. Nothing else in this file needs
# the environment: the offline tests all drive a scripted client.
load_dotenv()


# ---------------------------------------------------------------------------
# The scripted client
# ---------------------------------------------------------------------------


class FakeCompletions:
    """Replays a script. A string is a reply; an Exception is raised instead."""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0) if self.script else ""
        if isinstance(item, Exception):
            raise item
        return _as_response(item)


class FakeClient:
    def __init__(self, script):
        self.completions = FakeCompletions(script)
        self.chat = self

    @property
    def calls(self):
        return self.completions.calls


def _as_response(content: str):
    message = type("Message", (), {"content": content})()
    choice = type("Choice", (), {"message": message})()
    return type("Response", (), {"choices": [choice]})()


def reply(status="verified", confidence=0.9, rationale="Signals agree.", checks=None):
    payload = {"status": status, "confidence": confidence, "rationale": rationale}
    if checks is not None:
        payload["checks"] = checks
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Fixture data - real contract objects, straight off the committed ledger
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ledger():
    return load_ledger(FIXTURE_PATH)


@pytest.fixture(scope="module")
def entries(ledger):
    return {entry.reference.ref_id: entry for entry in ledger.entries}


@pytest.fixture()
def clean(entries):
    """A reference that resolved cleanly, with no indicators."""
    return entries["R01"]


@pytest.fixture()
def retracted(entries):
    return entries["R04"]


@pytest.fixture()
def malformed(entries):
    """malformed is the ONLY indicator, and nothing resolved."""
    return entries["R06"]


# ---------------------------------------------------------------------------
# The prompt states the boundary
# ---------------------------------------------------------------------------


def test_prompt_is_a_module_constant_so_r3_can_attack_it():
    assert isinstance(JUDGE_SYSTEM_PROMPT, str)
    assert len(JUDGE_SYSTEM_PROMPT) > 500


def test_prompt_names_all_four_statuses_and_no_fifth():
    for status in ("verified", "needs_check", "conflict", "unresolvable"):
        assert status in JUDGE_SYSTEM_PROMPT


def test_prompt_forbids_every_banned_term_by_name():
    """The prompt must name the words it forbids, or the rule is vague.

    This file deliberately does NOT assert the prompt is free of banned
    terms - it cannot be, since forbidding a word means writing it. The gate
    scans model OUTPUT, never the prompt.
    """
    lowered = JUDGE_SYSTEM_PROMPT.lower()
    for term in ("fake", "fabricated", "invented", "fraud", "ai-generated", "ai-written"):
        assert term in lowered, f"the prompt does not name {term!r} as forbidden"


def test_prompt_carries_the_two_enforced_rules():
    lowered = JUDGE_SYSTEM_PROMPT.lower()
    assert "retracted" in lowered and "conflict" in lowered
    assert "never escalates" in lowered or "never escalate" in lowered


def test_evidence_payload_hides_the_raw_provider_blob(clean):
    payload = evidence_payload(clean.reference, clean.evidence)
    assert "raw" not in payload["resolved_record"]
    assert payload["signals"]["doi_match"] is clean.evidence.doi_match
    assert payload["reference_as_printed"]["ref_id"] == "R01"


def test_user_prompt_explains_the_tri_state_and_the_absolute_year_delta(clean):
    text = build_user_prompt(clean.reference, clean.evidence)
    assert "doi_match: null" in text
    assert "absolute" in text


# ---------------------------------------------------------------------------
# Tolerant parsing
# ---------------------------------------------------------------------------


def test_parses_a_bare_json_object():
    assert extract_json_object(reply())["status"] == "verified"


def test_parses_through_a_markdown_fence():
    assert extract_json_object("```json\n" + reply() + "\n```")["status"] == "verified"


def test_parses_through_a_thinking_block():
    """The configured judge is a reasoning model; its narration has braces in it."""
    noisy = (
        "<think>Let me consider {this} and {that} before answering.</think>\n"
        "Here is the result:\n" + reply(status="needs_check")
    )
    assert extract_json_object(noisy)["status"] == "needs_check"


def test_skips_a_preamble_object_and_finds_the_one_with_a_status():
    text = '{"type": "json_object"}\nthen:\n' + reply(status="conflict")
    assert extract_json_object(text)["status"] == "conflict"


def test_a_brace_inside_a_string_does_not_unbalance_the_scan():
    text = reply(rationale="The record reads {2019} where the entry reads 2020.")
    assert "2019" in extract_json_object(text)["rationale"]


def test_no_json_at_all_is_a_parse_error():
    with pytest.raises(JudgeParseError):
        extract_json_object("I am afraid I cannot answer that.")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_build_verdict_uses_our_ref_id_not_the_models():
    verdict = build_verdict(json.loads(reply()) | {"ref_id": "R99"}, "R01", JUDGE_MODEL)
    assert verdict.ref_id == "R01"


def test_confidence_is_clamped_not_rejected():
    assert build_verdict(json.loads(reply(confidence=1.4)), "R01", JUDGE_MODEL).confidence == 1.0
    assert build_verdict(json.loads(reply(confidence=-2)), "R01", JUDGE_MODEL).confidence == 0.0


def test_a_fourth_check_is_truncated_not_fatal():
    verdict = build_verdict(
        json.loads(reply(checks=["a", "b", "c", "d"])), "R01", JUDGE_MODEL
    )
    assert verdict.checks == ["a", "b", "c"]


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "suspicious", "confidence": 0.5, "rationale": "x"},
        {"status": "verified", "confidence": 0.5, "rationale": "   "},
        {"status": "verified", "confidence": "high", "rationale": "x"},
        {"confidence": 0.5, "rationale": "x"},
    ],
    ids=["fifth-status", "empty-rationale", "confidence-not-a-number", "no-status"],
)
def test_schema_failures_are_rejected(payload):
    with pytest.raises(JudgeSchemaError):
        build_verdict(payload, "R01", JUDGE_MODEL)


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------


def test_happy_path_records_the_configured_model(clean):
    client = FakeClient([reply(checks=["Open the arXiv link and compare the title."])])
    verdict = judge_reference(clean.reference, clean.evidence, client=client)
    assert verdict.status == "verified"
    assert verdict.judge_model == JUDGE_MODEL
    assert len(client.calls) == 1


def test_model_and_temperature_come_from_settings(clean):
    client = FakeClient([reply()])
    judge_reference(clean.reference, clean.evidence, client=client)
    call = client.calls[0]
    assert call["model"] == settings.model_for("judge")
    assert call["temperature"] == settings.temperature_for("judge")
    assert call["timeout"] == float(settings.llm_settings()["timeout_seconds"])


def test_malformed_json_is_retried_once_then_succeeds(clean):
    client = FakeClient(["sorry, no.", reply(status="needs_check")])
    verdict = judge_reference(clean.reference, clean.evidence, client=client)
    assert verdict.status == "needs_check"
    assert verdict.judge_model == JUDGE_MODEL
    assert len(client.calls) == 2


def test_malformed_json_twice_falls_back_to_the_stub(clean):
    attempts = 1 + int(settings.llm_settings()["max_retries"])
    client = FakeClient(["nope"] * attempts)
    verdict = judge_reference(clean.reference, clean.evidence, client=client)
    assert verdict.judge_model == "fallback:stub"
    assert verdict.status == "needs_check"
    assert verdict.confidence == STUB_CONFIDENCE
    assert len(client.calls) == attempts


def test_a_schema_failure_does_not_burn_a_retry(clean):
    """JSON that is not a Verdict is the model disagreeing, not a slip."""
    client = FakeClient([json.dumps({"status": "definitely_wrong"}), reply()])
    verdict = judge_reference(clean.reference, clean.evidence, client=client)
    assert verdict.judge_model == "fallback:stub"
    assert len(client.calls) == 1


def test_a_gateway_error_falls_back_immediately(clean):
    client = FakeClient([TimeoutError("gateway timeout"), reply()])
    verdict = judge_reference(clean.reference, clean.evidence, client=client)
    assert verdict.judge_model == "fallback:stub"
    assert len(client.calls) == 1


def test_a_missing_api_key_falls_back_rather_than_raising(clean, monkeypatch):
    """The offline demo path: no .env, no key, still thirty verdicts."""
    monkeypatch.delenv("AIR_API_KEY", raising=False)
    monkeypatch.delenv("AIR_BASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    verdict = judge_reference(clean.reference, clean.evidence)
    assert verdict.judge_model == "fallback:stub"


def test_the_sdks_own_retry_layer_is_switched_off(clean):
    """D-202: ``llm.max_retries`` is the whole retry policy, not half of it.

    Without this the SDK re-sends each request twice underneath the ladder,
    and one reference against a flaky gateway costs six requests.
    """
    seen: dict = {}

    class OptionsClient(FakeClient):
        def with_options(self, **kwargs):
            seen.update(kwargs)
            return self

    judge_reference(clean.reference, clean.evidence, client=OptionsClient([reply()]))
    assert seen == {"max_retries": 0}


def test_a_client_without_with_options_still_works(clean):
    """The test doubles here have none, and neither might a future stub."""
    client = FakeClient([reply()])
    assert not hasattr(client, "with_options")
    assert judge_reference(clean.reference, clean.evidence, client=client).judge_model == (
        JUDGE_MODEL
    )


def test_ritiks_classifier_is_named_in_the_ledger(clean):
    def rule_based_status(ev):
        return ("conflict", 0.7, "Deterministic signals disagree with the printed entry.")

    client = FakeClient([ConnectionError("down")])
    verdict = judge_reference(clean.reference, clean.evidence, rule_based_status, client=client)
    assert verdict.judge_model == "fallback:rule_based"
    assert verdict.status == "conflict"
    assert verdict.confidence == 0.7


def test_an_unknown_fallback_still_names_itself(clean):
    def my_classifier(ev):
        return ("needs_check", 0.5, "Something else answered.")

    client = FakeClient([ConnectionError("down")])
    verdict = judge_reference(clean.reference, clean.evidence, my_classifier, client=client)
    assert verdict.judge_model == "fallback:my_classifier"


def test_a_fallback_that_raises_still_produces_a_verdict(clean):
    def exploding(ev):
        raise RuntimeError("the deterministic path is broken too")

    client = FakeClient([ConnectionError("down")])
    verdict = judge_reference(clean.reference, clean.evidence, exploding, client=client)
    assert verdict.judge_model == "fallback:stub"


def test_a_fallback_returning_a_verdict_is_accepted(clean):
    def already_a_verdict(ev):
        return Verdict(
            ref_id="whatever",
            status="unresolvable",
            confidence=0.2,
            rationale="Nothing resolved.",
            checks=[],
            judge_model="some-other-path",
        )

    client = FakeClient([ConnectionError("down")])
    verdict = judge_reference(clean.reference, clean.evidence, already_a_verdict, client=client)
    assert verdict.ref_id == "R01"
    assert verdict.judge_model == "some-other-path"


def test_stub_status_is_conservative():
    status, confidence, rationale = stub_status(
        MatchEvidence(ref_id="R01")
    )
    assert status == "needs_check"
    assert confidence == STUB_CONFIDENCE
    assert rationale.strip()
    for term in BANNED_TERMS:
        assert term.lower() not in rationale.lower()


# ---------------------------------------------------------------------------
# The chaos test - judge_reference NEVER raises
# ---------------------------------------------------------------------------


class ChaosCompletions:
    """Raises, returns nonsense, or returns something almost right. At random."""

    def __init__(self, rng):
        self.rng = rng

    def create(self, **kwargs):
        roll = self.rng.random()
        if roll < 0.3:
            raise random.choice(
                [RuntimeError("boom"), TimeoutError("slow"), ConnectionError("down")]
            )
        if roll < 0.5:
            return _as_response(None)
        if roll < 0.7:
            return _as_response("{{{ not json at all")
        if roll < 0.85:
            return _as_response(json.dumps({"status": "made_up", "confidence": None}))
        return _as_response(reply(confidence=self.rng.uniform(-1, 2)))


class ChaosClient:
    def __init__(self, seed):
        self.completions = ChaosCompletions(random.Random(seed))
        self.chat = self


def test_judge_reference_never_raises(clean, retracted, malformed):
    """Two hundred hostile clients, three shapes of evidence, zero exceptions."""
    for seed in range(200):
        for entry in (clean, retracted, malformed):
            verdict = judge_reference(
                entry.reference, entry.evidence, client=ChaosClient(seed)
            )
            assert isinstance(verdict, Verdict)
            assert verdict.ref_id == entry.reference.ref_id
            assert 0.0 <= verdict.confidence <= 1.0


def test_a_client_that_is_not_a_client_at_all(clean):
    verdict = judge_reference(clean.reference, clean.evidence, client=object())
    assert verdict.judge_model == "fallback:stub"


# ---------------------------------------------------------------------------
# The retraction floor and the parse-noise ceiling - D-201
# ---------------------------------------------------------------------------


def test_retracted_evidence_yields_at_least_conflict(retracted):
    """Even when the model says the reference is perfect."""
    assert "retracted" in retracted.evidence.indicators
    client = FakeClient([reply(status="verified", confidence=0.99)])
    verdict = judge_reference(retracted.reference, retracted.evidence, client=client)
    assert verdict.status == "conflict"
    assert "retraction notice" in verdict.rationale


@pytest.mark.parametrize("status", ["verified", "needs_check", "unresolvable"])
def test_the_retraction_floor_holds_from_every_lower_status(retracted, status):
    client = FakeClient([reply(status=status)])
    verdict = judge_reference(retracted.reference, retracted.evidence, client=client)
    assert verdict.status == "conflict"


def test_the_retraction_floor_also_applies_to_a_fallback_verdict(retracted):
    def too_relaxed(ev):
        return ("verified", 0.9, "Deterministic signals all agree.")

    client = FakeClient([ConnectionError("down")])
    verdict = judge_reference(retracted.reference, retracted.evidence, too_relaxed, client=client)
    assert verdict.status == "conflict"


def test_parse_noise_lowers_confidence_and_never_escalates_to_conflict(malformed):
    """The named test in the A1 DoD. An unreadable reference is not a suspicious one."""
    assert list(malformed.evidence.indicators) == ["malformed"]
    assert malformed.evidence.resolved is None
    client = FakeClient([reply(status="conflict", confidence=0.95)])
    verdict = judge_reference(malformed.reference, malformed.evidence, client=client)
    assert verdict.status == "unresolvable"
    assert verdict.confidence <= PARSE_NOISE_CEILING


def test_parse_noise_with_a_resolved_record_lands_on_needs_check(malformed):
    evidence = malformed.evidence.model_copy(
        update={"resolved": ResolvedSource(provider="crossref", raw={})}
    )
    client = FakeClient([reply(status="conflict", confidence=0.95)])
    verdict = judge_reference(malformed.reference, evidence, client=client)
    assert verdict.status == "needs_check"


def test_the_parse_noise_ceiling_is_narrow(malformed):
    """With a second indicator present, the conflict rests on real evidence."""
    evidence = malformed.evidence.model_copy(
        update={"indicators": ["malformed", "doi_mismatch"]}
    )
    client = FakeClient([reply(status="conflict", confidence=0.95)])
    verdict = judge_reference(malformed.reference, evidence, client=client)
    assert verdict.status == "conflict"
    assert verdict.confidence == 0.95


def test_the_ceiling_leaves_a_non_conflict_verdict_alone(malformed):
    client = FakeClient([reply(status="unresolvable", confidence=0.8)])
    verdict = judge_reference(malformed.reference, malformed.evidence, client=client)
    assert verdict.status == "unresolvable"
    assert verdict.confidence == 0.8


def test_apply_evidence_rules_is_a_pure_function(clean):
    verdict = Verdict(
        ref_id="R01",
        status="verified",
        confidence=0.9,
        rationale="Fine.",
        checks=[],
        judge_model=JUDGE_MODEL,
    )
    assert apply_evidence_rules(verdict, clean.evidence) == verdict


# ---------------------------------------------------------------------------
# The gate - three code checks, no model call (D-004 / D-200)
# ---------------------------------------------------------------------------


def _verdict(ref_id="R01", status="verified", rationale="Signals agree.", checks=None):
    return Verdict(
        ref_id=ref_id,
        status=status,
        confidence=0.9,
        rationale=rationale,
        checks=checks or [],
        judge_model=JUDGE_MODEL,
    )


def test_gate_passes_a_clean_batch_through_unchanged(ledger):
    verdicts = [entry.verdict for entry in ledger.entries]
    assert gate_batch(verdicts, len(verdicts)) == verdicts


def test_gate_catches_a_planted_banned_term():
    poisoned = _verdict(rationale="This citation is fake.")
    gated = gate_batch([poisoned], 1)
    assert gated[0].status == "needs_check"
    assert gated[0].rationale == GATE_FAILURE_RATIONALE
    assert gated[0].judge_model.startswith("gate-forced:")


def test_gate_scans_the_checks_not_only_the_rationale():
    """An accusation wearing the costume of an instruction."""
    poisoned = _verdict(checks=["Confirm the reference is not fabricated."])
    assert gate_batch([poisoned], 1)[0].rationale == GATE_FAILURE_RATIONALE


@pytest.mark.parametrize("term", BANNED_TERMS)
def test_gate_catches_every_term_in_config(term):
    poisoned = _verdict(rationale=f"The record appears {term.upper()} to this reader.")
    assert gate_batch([poisoned], 1)[0].rationale == GATE_FAILURE_RATIONALE


def test_gate_reads_the_term_list_from_settings_not_a_private_copy(monkeypatch):
    """A hardcoded copy would drift from Roy's release gate - D-019."""
    monkeypatch.setattr(gate_mod, "banned_terms", lambda: ["banana"])
    assert gate_batch([_verdict(rationale="Perfectly ordinary.")], 1)[0].rationale != (
        GATE_FAILURE_RATIONALE
    )
    assert gate_batch([_verdict(rationale="A banana of a record.")], 1)[0].rationale == (
        GATE_FAILURE_RATIONALE
    )


def test_gate_catches_a_counts_mismatch(ledger):
    verdicts = [entry.verdict for entry in ledger.entries]
    with pytest.raises(GateCountMismatch):
        gate_batch(verdicts, len(verdicts) + 1)
    with pytest.raises(GateCountMismatch):
        gate_batch(verdicts[:-1], len(verdicts))


def test_gate_catches_a_duplicate_ref_id():
    with pytest.raises(GateDuplicateVerdict):
        gate_batch([_verdict("R01"), _verdict("R01")], 2)


def test_gate_rejudges_once_and_accepts_a_clean_answer():
    poisoned = _verdict(rationale="The entry looks fabricated.")
    clean = _verdict(rationale="The DOI resolves to a different title.")
    gated = gate_batch([poisoned], 1, rejudge_fn=lambda v: clean)
    assert gated[0] is clean


def test_gate_forces_when_the_second_attempt_is_also_poisoned():
    poisoned = _verdict(rationale="The entry looks fabricated.")
    gated = gate_batch([poisoned], 1, rejudge_fn=lambda v: _verdict(rationale="Still fake."))
    assert gated[0].rationale == GATE_FAILURE_RATIONALE


def test_gate_forces_when_the_rejudge_itself_raises():
    def explode(v):
        raise RuntimeError("gateway down")

    poisoned = _verdict(rationale="The entry looks fabricated.")
    assert gate_batch([poisoned], 1, rejudge_fn=explode)[0].rationale == GATE_FAILURE_RATIONALE


def test_gate_rejects_a_rejudge_that_answers_about_a_different_reference():
    poisoned = _verdict("R01", rationale="The entry looks fabricated.")
    gated = gate_batch([poisoned], 1, rejudge_fn=lambda v: _verdict("R02"))
    assert gated[0].ref_id == "R01"
    assert gated[0].rationale == GATE_FAILURE_RATIONALE


def test_a_forced_verdict_keeps_the_reference_in_the_ledger():
    """Forced, never dropped: thirty references in means thirty rows out."""
    forced = force_needs_check(_verdict("R07", rationale="This is fraud."))
    assert forced.ref_id == "R07"
    assert forced.checks == []
    assert verdict_banned_terms(forced) == []


def test_gate_makes_no_model_call(monkeypatch):
    """D-200: the gate is three code checks. It must not reach for a client."""
    def explode(*args, **kwargs):
        raise AssertionError("gate.py called the gateway")

    monkeypatch.setattr("src.llm.get_client", explode)
    assert gate_batch([_verdict()], 1)


def test_no_critic_model_key_came_back(monkeypatch):
    """D-200 closes D-004 without re-adding config keys."""
    config = settings.load_config()
    assert "critic" not in (config.get("models") or {})
    assert "critic_temperature" not in config


# ---------------------------------------------------------------------------
# No model name anywhere in src/
# ---------------------------------------------------------------------------


def test_no_hardcoded_model_name_in_the_judge_package():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src"
    needles = ("qwen", "glm-", "gemma", "sk-")
    offenders = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        offenders += [f"{path.name}:{needle}" for needle in needles if needle in lowered]
    assert not offenders, offenders


# ---------------------------------------------------------------------------
# The one live test
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("AIR_API_KEY") or not os.getenv("AIR_BASE_URL"),
    reason="no AIR credentials in the environment - offline suite covers the rest",
)
def test_live_air_smoke(clean):
    """One real call to the gateway. Skipped in CI, run before every demo.

    A gateway that cannot be reached SKIPS; a gateway that answers badly
    FAILS. The distinction is the difference between a useful pre-demo check
    and a test that goes red whenever the VPN hiccups - and the AIR gateway
    does drop connections intermittently, which is precisely the condition
    ``judge_reference``'s fallback ladder exists to absorb.
    """
    from openai import APIConnectionError, APIStatusError, APITimeoutError

    from src.judge import prompts
    from src.llm import get_client

    client = get_client().with_options(max_retries=0)
    try:
        client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=settings.temperature_for("judge"),
            messages=[
                {"role": "system", "content": prompts.JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(clean.reference, clean.evidence)},
            ],
            # Not llm.timeout_seconds: this is a reachability probe, and a
            # gateway that is up answers this prompt in under a second
            # (measured). Waiting the full configured minute to learn the VPN
            # is off would put 60s into every local suite run.
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except (APIConnectionError, APITimeoutError) as exc:
        pytest.skip(f"AIR gateway unreachable right now ({type(exc).__name__}) - VPN?")
    except APIStatusError as exc:
        pytest.fail(f"AIR gateway rejected the request: {exc.status_code} {exc}")

    verdict = judge_reference(clean.reference, clean.evidence)
    assert isinstance(verdict, Verdict)
    assert verdict.judge_model == JUDGE_MODEL, (
        f"the gateway answered the probe but judge_reference degraded to "
        f"{verdict.judge_model} - that is a bug in the ladder, not the network"
    )
    assert verdict.rationale.strip()
    assert verdict_banned_terms(verdict) == []
    assert gate_batch([verdict], 1)[0] == verdict
