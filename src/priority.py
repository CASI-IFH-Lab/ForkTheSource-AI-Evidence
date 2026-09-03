"""Priority scoring for ledger entries.

``compute_priority`` turns a (evidence, verdict, citation-usage) triple into
a single ``[0, 1]`` float used to sort the reviewer worklist (see
``Ledger.worklist()`` in ``src.contract``). All five weights are
configuration, not code: they live in ``config.yaml`` under ``priority.*``
and are read through ``src.settings`` so a lane can retune scoring without
touching this module. Callers that already have the block in hand (tests,
the fixture generator) pass it directly via ``weights=`` instead of relying
on the default lookup.

``config.yaml``'s ``priority`` block currently defines ``severity`` and
nothing else: ``usage_base``, ``usage_step``, ``retracted_bonus`` and ``cap``
are absent, exactly as D-009 and ``docs/pr/B0.md`` flag 3 record. Naming
those four is B1's to do (D-009), but ``config.yaml`` is Ritik's file, so
they are proposed in ``docs/decisions.md`` D-032 and land in a follow-up.

Until they do, ``_load_priority_config`` fails closed rather than guessing:
it names the missing keys in a ``RuntimeError`` and never falls back to a
hardcoded number. A wrong-but-plausible priority score is worse than no
score, because it silently reorders the reviewer worklist. Every caller in
this codebase passes ``weights=`` explicitly, so nothing is blocked by the
gap; the default lookup goes live the day the four keys land.

This module imports only from ``src.contract`` - never ``src.judge`` or
``src.pipeline`` - to stay a leaf in the dependency graph.
"""

from __future__ import annotations

from typing import Mapping

from src.contract import Indicator, MatchEvidence, Verdict

_SEVERITY_KEYS = ("conflict", "needs_check", "unresolvable", "verified")
_SCALAR_KEYS = ("usage_base", "usage_step", "retracted_bonus", "cap")


def _load_priority_config() -> Mapping:
    """Read the whole ``priority.*`` block through ``src.settings``.

    One accessor, not a shape probe: ``settings.load_config()`` is the only
    thing in this repo that opens ``config.yaml`` (B2), and
    ``settings.priority_severity()`` is the typed reader for the severity
    map, so severity inherits that function's validation and float coercion
    rather than being re-parsed here. Both take the already-loaded config, so
    the file is read once.

    Fails closed: any absent key raises ``RuntimeError`` naming exactly the
    keys that are missing. There is deliberately no default for any of the
    five numbers - see this module's docstring and D-009.
    """
    from src import settings

    config = settings.load_config()

    try:
        severity = settings.priority_severity(config)
    except KeyError:
        severity = {}

    block = config.get("priority")
    if not isinstance(block, Mapping):
        block = {}

    missing = [f"severity.{key}" for key in _SEVERITY_KEYS if key not in severity]
    missing += [key for key in _SCALAR_KEYS if key not in block]

    if missing:
        raise RuntimeError(
            "config.yaml is missing priority config keys: "
            + ", ".join(missing)
            + ". Priority scoring has no defaults by design (D-009): a plausible "
            "wrong score silently reorders the reviewer worklist. Pass weights= "
            "explicitly, or add the keys to config.yaml."
        )

    return {**block, "severity": severity}


def compute_priority(
    ev: MatchEvidence,
    verdict: Verdict,
    n_citing_claims: int,
    weights: Mapping | None = None,
) -> float:
    block = weights if weights is not None else _load_priority_config()

    severity_map = block["severity"]
    # verdict.status is already a plain str (use_enum_values=True on
    # Verdict), but tolerate a raw enum too. Unknown status must raise
    # KeyError, never default to 0.
    status = getattr(verdict.status, "value", verdict.status)
    severity = severity_map[status]

    usage_base = block["usage_base"]
    usage_step = block["usage_step"]
    retracted_bonus = block["retracted_bonus"]
    cap = block["cap"]

    usage = min(1.0, usage_base + usage_step * max(0, n_citing_claims))
    score = severity * usage * verdict.confidence

    indicators = [
        indicator.value if isinstance(indicator, Indicator) else indicator
        for indicator in ev.indicators
    ]
    if Indicator.RETRACTED.value in indicators:
        score += retracted_bonus

    score = max(0.0, min(cap, score))
    return round(score, 3)
