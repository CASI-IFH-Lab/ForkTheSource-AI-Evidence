"""The judge call, and the ladder it climbs down when the gateway will not answer.

``judge_reference`` NEVER raises. That is not politeness, it is the demo: a
run of thirty references must produce thirty verdicts whether the gateway is
up, slow, or unreachable, and the ledger must be honest about which. Every
verdict records its provenance in ``Verdict.judge_model``:

    "<the configured model name>"  the model answered and validated
    "fallback:rule_based"          Ritik's deterministic classifier answered
    "fallback:stub"                nothing answered; the conservative default
    "fallback:<name>"              some other injected classifier answered

so "it degrades honestly" is a property you can read off the ledger rather
than a claim made on stage.

THE LADDER
    no JSON in the reply            -> retry (llm.max_retries) -> fallback_fn
    JSON, but the schema is wrong   -> fallback_fn immediately
    gateway error / timeout         -> fallback_fn immediately
    no API key / no gateway URL     -> fallback_fn immediately

The split between the first two is deliberate. A reply with no JSON in it is
usually a formatting slip, and a second attempt is cheap and often works. A
reply that IS JSON but omits ``rationale``, or names a status outside the
closed vocabulary, is the model disagreeing with the schema - asking again
buys a second round-trip and the same answer, so we take the deterministic
result instead.

``fallback_fn`` is Ritik's frozen ``rule_based_status(ev) -> (status,
confidence, rationale)``, injected by A3 through ``src/judge/wiring.py``. It
is a parameter and never an import: ``src/judge/`` must not import
``src/matching/`` (D-008), and this is the seam that makes that possible.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterator

from pydantic import ValidationError

from src.contract import STATUSES, MatchEvidence, Reference, Verdict
from src.judge import prompts
from src.settings import llm_settings, model_for, temperature_for

# fallback_fn: (MatchEvidence) -> (status, confidence, rationale)
StatusFn = Callable[[MatchEvidence], "tuple[str, float, str]"]

STUB_STATUS = "needs_check"
STUB_CONFIDENCE = 0.3
STUB_RATIONALE = (
    "No model verdict was available for this reference, so it is left for a human to "
    "look at rather than given an automatic outcome."
)

# Judge-model labels for the non-model paths. Anything not listed becomes
# "fallback:<function name>" - an injected classifier we did not anticipate
# still names itself in the ledger rather than hiding behind "fallback".
_FALLBACK_LABELS = {
    "stub_status": "fallback:stub",
    "rule_based_status": "fallback:rule_based",
}

_THINK_BLOCK = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```[a-zA-Z0-9_-]*\s*|```")


class JudgeReplyError(Exception):
    """Base for "the model's reply is not a verdict"."""


class JudgeParseError(JudgeReplyError):
    """No JSON object could be found in the reply. Retryable."""


class JudgeSchemaError(JudgeReplyError):
    """JSON was found but it is not a Verdict. Not retryable - see the ladder."""


def stub_status(ev: MatchEvidence) -> tuple[str, float, str]:
    """The conservative default fallback: ``needs_check`` at 0.3.

    ``needs_check`` rather than ``unresolvable`` because the reference may
    well have resolved perfectly - what failed is the judging, not the
    lookup, and ``unresolvable`` would be a claim about the reference made
    on the strength of our own outage. 0.3 is low enough that
    ``compute_priority`` keeps these in the middle of the worklist: worth a
    human's eye, never ahead of a retraction.
    """
    return (STUB_STATUS, STUB_CONFIDENCE, STUB_RATIONALE)


# ---------------------------------------------------------------------------
# Parsing a reply that was written by a language model
# ---------------------------------------------------------------------------


def _balanced_objects(text: str) -> Iterator[str]:
    """Yield every brace-balanced ``{...}`` substring, outermost first.

    A reasoning model narrates before it answers, and the narration contains
    braces. Slicing from the first ``{`` to the last ``}`` swallows the
    narration; slicing to the FIRST ``}`` truncates the answer. Walking a
    depth counter is the only version that is right on both, and it costs
    one pass.

    String literals are tracked so a brace inside a rationale - the record
    reads {2019} - cannot unbalance the scan.
    """
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
                if depth == 0 and start >= 0:
                    yield text[start : index + 1]


def extract_json_object(reply: str) -> dict:
    """Find the verdict object in a model reply. Tolerant, but not credulous.

    Strips ``<think>`` blocks and markdown fences, then returns the first
    balanced object that parses AND carries a ``status`` key. The ``status``
    requirement is what stops a stray ``{"type": "json_object"}`` preamble
    from being mistaken for the answer. Falls back to the first object that
    merely parses, so a reply that omits ``status`` reaches the schema check
    and is reported as a schema failure rather than a parse failure - the
    two take different rungs of the ladder.
    """
    text = _FENCE.sub("", _THINK_BLOCK.sub("", reply or "")).strip()

    first_parsed: dict | None = None
    for candidate in _balanced_objects(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        if "status" in parsed:
            return parsed
        if first_parsed is None:
            first_parsed = parsed

    if first_parsed is not None:
        return first_parsed
    raise JudgeParseError("no JSON object found in the model reply")


def _coerce_checks(value: Any) -> list[str]:
    """Normalise ``checks`` to at most three non-empty strings.

    Truncating a fourth check rather than rejecting the reply is a
    deliberate small mercy: the contract caps at three, and discarding an
    otherwise good verdict over one extra suggestion would send a correct
    answer down the fallback ladder for a formatting nit.
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise JudgeSchemaError(f"'checks' must be a list, got {type(value).__name__}")
    checks = [str(item).strip() for item in value if str(item).strip()]
    return checks[:3]


def build_verdict(payload: dict, ref_id: str, judge_model: str) -> Verdict:
    """Validate one parsed reply into a ``Verdict``, or raise ``JudgeSchemaError``.

    ``ref_id`` comes from OUR record, never from the model. A model that
    misreads or invents a ref_id would otherwise attach its verdict to the
    wrong reference, and ``LedgerEntry`` would reject the whole entry at
    construction.
    """
    if not isinstance(payload, dict):
        raise JudgeSchemaError("the model reply is not a JSON object")

    status = payload.get("status")
    if not isinstance(status, str) or status.strip().lower() not in STATUSES:
        raise JudgeSchemaError(f"status {status!r} is not one of {STATUSES}")

    rationale = payload.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise JudgeSchemaError("'rationale' is missing or empty")

    raw_confidence = payload.get("confidence")
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        raise JudgeSchemaError(f"'confidence' is not a number: {raw_confidence!r}") from None
    # Clamped, not rejected: 1.2 is a model overshooting a scale, and the
    # meaning - as sure as it gets - survives clamping intact.
    confidence = max(0.0, min(1.0, confidence))

    try:
        return Verdict(
            ref_id=ref_id,
            status=status.strip().lower(),
            confidence=confidence,
            rationale=rationale.strip(),
            checks=_coerce_checks(payload.get("checks")),
            judge_model=judge_model,
        )
    except ValidationError as exc:
        raise JudgeSchemaError(f"reply failed contract validation: {exc}") from exc


# ---------------------------------------------------------------------------
# The fallback rung
# ---------------------------------------------------------------------------


def _fallback_label(fallback_fn: StatusFn) -> str:
    name = getattr(fallback_fn, "__name__", None) or type(fallback_fn).__name__
    return _FALLBACK_LABELS.get(name, f"fallback:{name}")


def _last_resort(ref_id: str) -> Verdict:
    """The verdict that exists so ``judge_reference`` can keep its promise."""
    return Verdict(
        ref_id=ref_id,
        status=STUB_STATUS,
        confidence=STUB_CONFIDENCE,
        rationale=STUB_RATIONALE,
        checks=[],
        judge_model="fallback:stub",
    )


def _fallback_verdict(ref_id: str, ev: MatchEvidence, fallback_fn: StatusFn) -> Verdict:
    """Run ``fallback_fn`` and shape its answer into a ``Verdict``.

    Accepts either the frozen tuple shape or a ready-made ``Verdict``, so an
    injected classifier that already speaks the contract is not forced to
    take itself apart. A fallback that raises, or answers in a shape the
    contract rejects, drops to ``_last_resort`` - the rung below which there
    is nothing left to fail.
    """
    try:
        result = fallback_fn(ev)
    except Exception:
        return _last_resort(ref_id)

    if isinstance(result, Verdict):
        return result.model_copy(update={"ref_id": ref_id})

    try:
        status, confidence, rationale = result
        return Verdict(
            ref_id=ref_id,
            status=str(status).strip().lower(),
            confidence=max(0.0, min(1.0, float(confidence))),
            rationale=str(rationale).strip() or STUB_RATIONALE,
            checks=[],
            judge_model=_fallback_label(fallback_fn),
        )
    except Exception:
        return _last_resort(ref_id)


# ---------------------------------------------------------------------------
# Two rules the prompt states and the code enforces
# ---------------------------------------------------------------------------

RETRACTION_NOTE = (
    " Raised to conflict because the resolved record carries a retraction notice."
)
PARSE_NOISE_NOTE = (
    " Lowered from conflict: the only signal here is reference text that did not parse "
    "cleanly, which is missing information rather than a disagreement."
)
PARSE_NOISE_CEILING = 0.5


def apply_evidence_rules(verdict: Verdict, ev: MatchEvidence) -> Verdict:
    """Enforce the retraction floor and the parse-noise ceiling. D-201.

    Both rules are in the system prompt, and a prompt is a request. These
    two are the ones we cannot afford to have politely ignored, so they are
    also post-conditions:

    RETRACTION FLOOR - ``retracted`` in the indicators means the provider
    published a retraction notice. That is a fact about the record, not an
    inference about the authors, so raising the status is never an
    accusation. Nothing may sit below ``conflict``.

    PARSE-NOISE CEILING - when ``malformed`` is the ONLY indicator, the sole
    thing we know is that our own parser could not read the entry. An
    unreadable reference is not a suspicious one, and ``conflict`` on that
    evidence is exactly the false alarm this project exists to avoid. It
    drops to ``unresolvable`` when nothing resolved, and to ``needs_check``
    when something did. The guard is deliberately narrow: with any second
    indicator present - a DOI mismatch, a retraction - the conflict rests on
    real evidence and stands untouched.

    Applied to fallback verdicts too, not only model ones. A deterministic
    classifier is not exempt from a rule that exists to keep the output
    honest.
    """
    indicators = {getattr(i, "value", i) for i in ev.indicators}

    if "retracted" in indicators and verdict.status != "conflict":
        return verdict.model_copy(
            update={
                "status": "conflict",
                "rationale": verdict.rationale.rstrip() + RETRACTION_NOTE,
            }
        )

    if indicators == {"malformed"} and verdict.status == "conflict":
        return verdict.model_copy(
            update={
                "status": "unresolvable" if ev.resolved is None else "needs_check",
                "confidence": min(verdict.confidence, PARSE_NOISE_CEILING),
                "rationale": verdict.rationale.rstrip() + PARSE_NOISE_NOTE,
            }
        )

    return verdict


# ---------------------------------------------------------------------------
# The public entry point
# ---------------------------------------------------------------------------


def _single_attempt_client(client: Any) -> Any:
    """The same client with the SDK's own retry layer switched off. D-202.

    The OpenAI SDK retries twice by default, underneath us and invisibly. On
    top of the ladder's ``llm.max_retries`` that is up to six requests for
    one reference, and against a flaky gateway six requests at
    ``llm.timeout_seconds`` each is six minutes on a single row - measured,
    not theorised: one reference took 182s wall-clock to reach our "gateway
    error" rung while the SDK quietly re-sent it three times.

    ``llm.max_retries`` is meant to be the whole retry policy. A second
    hidden one makes the configured number a lie and makes Ritik's per-stage
    progress callback unreadable.

    Degrades to the client as given when it has no ``with_options`` - the
    test doubles in ``tests/test_judge.py`` do not.
    """
    with_options = getattr(client, "with_options", None)
    if not callable(with_options):
        return client
    try:
        return with_options(max_retries=0)
    except Exception:
        return client


def _ask(client: Any, model: str, temperature: float, timeout: float, messages: list) -> str:
    response = _single_attempt_client(client).chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
        timeout=timeout,
    )
    return response.choices[0].message.content or ""


def judge_reference(
    ref: Reference,
    ev: MatchEvidence,
    fallback_fn: StatusFn | None = None,
    *,
    client: Any | None = None,
) -> Verdict:
    """Classify one reference. Returns a ``Verdict`` under every condition.

    ``client`` is keyword-only and exists for tests - the whole offline suite
    drives this function with a fake object. Production callers omit it and
    get the one shared gateway client from ``src.llm``; there is deliberately
    no second client inside this package (D-008).

    Every rung of the ladder passes through ``apply_evidence_rules`` on the
    way out, so the retraction floor and the parse-noise ceiling hold no
    matter which rung answered.
    """
    return apply_evidence_rules(_judge(ref, ev, fallback_fn, client), ev)


def _judge(
    ref: Reference,
    ev: MatchEvidence,
    fallback_fn: StatusFn | None,
    client: Any | None,
) -> Verdict:
    """The ladder itself. Split out only so the public entry point is one line."""
    fallback_fn = fallback_fn or stub_status

    try:
        model = model_for("judge")
        temperature = temperature_for("judge")
        settings = llm_settings()
        timeout = float(settings["timeout_seconds"])
        attempts = 1 + int(settings["max_retries"])
    except Exception:
        # config.yaml is unreadable or incomplete. That is loud everywhere
        # else in this repo; here it degrades, because a run that produces
        # no verdicts is worse than one that produces deterministic verdicts
        # and labels them as such.
        return _fallback_verdict(ref.ref_id, ev, fallback_fn)

    if client is None:
        try:
            from src.llm import get_client

            client = get_client()
        except Exception:
            return _fallback_verdict(ref.ref_id, ev, fallback_fn)

    messages = [
        {"role": "system", "content": prompts.JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": prompts.build_user_prompt(ref, ev)},
    ]

    for _ in range(max(1, attempts)):
        try:
            reply = _ask(client, model, temperature, timeout, messages)
        except Exception:
            return _fallback_verdict(ref.ref_id, ev, fallback_fn)

        try:
            payload = extract_json_object(reply)
        except JudgeParseError:
            continue  # retryable: no JSON at all
        except Exception:
            return _fallback_verdict(ref.ref_id, ev, fallback_fn)

        try:
            return build_verdict(payload, ref.ref_id, model)
        except Exception:
            return _fallback_verdict(ref.ref_id, ev, fallback_fn)

    return _fallback_verdict(ref.ref_id, ev, fallback_fn)
