"""The folded-in critic: three code checks over a batch of verdicts, no model call.

D-004 asked whether ``gate.py`` wants a model of its own. It does not, and
D-200 closes it: all three checks are decidable by inspection, so a model
here would add a second thing that can fail, a second thing that costs a
round-trip, and a second thing whose own output would need gating.

    1. every ``ref_id`` carries exactly one verdict
    2. the status counts sum to ``total``
    3. no banned term appears in any rationale or any check

Checks 1 and 2 are STRUCTURAL - a verdict is missing, duplicated, or
invented - and there is no per-entry repair for them, so they raise. That
mirrors ``Ledger.assert_consistent()`` and the dashboard's refusal to render
inconsistent counts: a worklist that is confidently wrong about how many
references it covers is worse than one that stops.

Check 3 is a CONTENT failure in one entry, and that one entry can be
replaced. It is re-judged once if the caller supplied a way to, and
otherwise forced to ``needs_check`` with a rationale that says so. Forced,
not deleted: the reference stays in the ledger, keeps its place in the
worklist, and announces that its rationale was withheld. A silent drop would
be the one failure mode this project cannot have.

The banned-term list is read from ``settings.banned_terms()`` on every call
and never cached in this module. Roy's release gate reads the same list from
the same place; a private copy here would drift, and we would pass while he
fails on the same ledger (D-019).
"""

from __future__ import annotations

from collections import Counter
from typing import Callable, Iterable, Sequence

from src.contract import STATUSES, Verdict
from src.settings import banned_terms

GATE_FAILURE_RATIONALE = "judge output failed quality gate"
GATE_FAILURE_STATUS = "needs_check"
GATE_FAILURE_CONFIDENCE = 0.3


class GateError(ValueError):
    """A structural problem the gate cannot repair entry by entry."""


class GateCountMismatch(GateError):
    """The number of verdicts does not match the number of references."""


class GateDuplicateVerdict(GateError):
    """Some ``ref_id`` carries more than one verdict."""


def find_banned_terms(text: str, terms: Iterable[str] | None = None) -> list[str]:
    """Every banned term appearing in ``text``, case-insensitively.

    Substring rather than word-boundary matching on purpose: "fraud" has to
    catch "fraudulent", and "plagiarism" has to catch "plagiarism-adjacent".
    The cost is that a legitimate word containing a banned one would trip the
    gate - and tripping toward ``needs_check`` is the safe direction.
    """
    terms = banned_terms() if terms is None else terms
    lowered = (text or "").lower()
    return [term for term in terms if term.lower() in lowered]


def verdict_banned_terms(verdict: Verdict, terms: Iterable[str] | None = None) -> list[str]:
    """Banned terms across a verdict's rationale AND every one of its checks.

    Scanning the checks matters as much as the rationale: "Confirm this
    reference is not fabricated" is an accusation wearing the costume of an
    instruction, and it is the phrasing a model reaches for first.
    """
    terms = list(banned_terms() if terms is None else terms)
    found: list[str] = list(find_banned_terms(verdict.rationale, terms))
    for check in verdict.checks:
        for term in find_banned_terms(check, terms):
            if term not in found:
                found.append(term)
    return found


def force_needs_check(verdict: Verdict) -> Verdict:
    """Replace a verdict that failed the content check, visibly.

    ``judge_model`` becomes ``gate-forced:<original>`` so the ledger still
    records which path produced the answer that was rejected. The dashboard
    and Roy's eval can both count these; a run where the gate fires ten
    times is a run we want to know about, not one we want to look clean.
    """
    return Verdict(
        ref_id=verdict.ref_id,
        status=GATE_FAILURE_STATUS,
        confidence=GATE_FAILURE_CONFIDENCE,
        rationale=GATE_FAILURE_RATIONALE,
        checks=[],
        judge_model=f"gate-forced:{verdict.judge_model}",
    )


def _assert_structure(verdicts: Sequence[Verdict], total: int) -> None:
    counts = Counter(verdict.ref_id for verdict in verdicts)
    duplicates = sorted(ref_id for ref_id, n in counts.items() if n > 1)
    if duplicates:
        raise GateDuplicateVerdict(
            f"more than one verdict for ref_id(s): {duplicates}. Every reference "
            "carries exactly one verdict - see src/judge/gate.py."
        )

    status_total = sum(
        sum(1 for verdict in verdicts if verdict.status == status) for status in STATUSES
    )
    if status_total != total or len(verdicts) != total:
        raise GateCountMismatch(
            f"{len(verdicts)} verdicts ({status_total} carrying a contract status) "
            f"for {total} references. The counters on the dashboard are derived from "
            "this sum, so a mismatch is refused rather than rendered."
        )


def gate_batch(
    verdicts: Sequence[Verdict],
    total: int,
    *,
    rejudge_fn: Callable[[Verdict], Verdict] | None = None,
) -> list[Verdict]:
    """Run the three checks over a batch and return the batch, repaired.

    ``rejudge_fn`` is keyword-only and optional, so the frozen two-argument
    signature in the integration contract is exactly what a caller sees.
    When it is supplied, a verdict that trips the language rule gets one
    second attempt; if that attempt trips it too, or raises, the entry is
    forced. One retry, never a loop - a model that reached for an accusation
    twice will reach for it a third time, and the demo has a clock.
    """
    terms = banned_terms()
    _assert_structure(verdicts, total)

    gated: list[Verdict] = []
    for verdict in verdicts:
        if not verdict_banned_terms(verdict, terms):
            gated.append(verdict)
            continue

        if rejudge_fn is not None:
            try:
                second = rejudge_fn(verdict)
            except Exception:
                second = None
            if (
                isinstance(second, Verdict)
                and second.ref_id == verdict.ref_id
                and not verdict_banned_terms(second, terms)
            ):
                gated.append(second)
                continue

        gated.append(force_needs_check(verdict))

    return gated
