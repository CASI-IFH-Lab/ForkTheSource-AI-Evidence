"""Priority scoring for ledger entries.

``compute_priority`` turns a (evidence, verdict, citation-usage) triple into
a single ``[0, 1]`` float used to sort the reviewer worklist (see
``Ledger.worklist()`` in ``src.contract``). All five weights are
configuration, not code: they live in ``config.yaml`` under ``priority.*``
and are read through ``src.settings`` so a lane can retune scoring without
touching this module. Callers that already have the block in hand (tests,
the fixture generator) pass it directly via ``weights=`` instead of relying
on the default lookup.

As of this module's introduction, neither ``src/settings.py`` nor
``config.yaml``'s ``priority`` block exist yet - both are out of scope here.
``_load_priority_config`` is written to fail closed rather than guess: a
missing module or a missing key raises ``RuntimeError`` naming exactly what
is absent, never a silent fallback to hardcoded numbers. Every caller in
this codebase currently passes ``weights=`` explicitly; the default lookup
becomes live the day something adds the config block and the settings
loader.

This module imports only from ``src.contract`` - never ``src.judge`` or
``src.pipeline`` - to stay a leaf in the dependency graph.
"""

from __future__ import annotations

from typing import Mapping

from src.contract import Indicator, MatchEvidence, Verdict

_SEVERITY_KEYS = ("conflict", "needs_check", "unresolvable", "verified")
_SCALAR_KEYS = ("usage_base", "usage_step", "retracted_bonus", "cap")
_REQUIRED_KEYS = tuple(f"severity.{key}" for key in _SEVERITY_KEYS) + _SCALAR_KEYS


def _load_priority_config() -> Mapping:
    try:
        from src import settings  # lazy: may not exist yet
    except ImportError as exc:
        raise RuntimeError(
            "src.settings is not available; cannot load priority config "
            "keys: " + ", ".join(_REQUIRED_KEYS)
        ) from exc

    config = getattr(settings, "CONFIG", None)
    if config is None:
        get_config = getattr(settings, "get_config", None)
        if get_config is not None:
            config = get_config()

    if not isinstance(config, Mapping):
        raise RuntimeError(
            "src.settings has no usable CONFIG/get_config() to load "
            "priority config keys: " + ", ".join(_REQUIRED_KEYS)
        )

    block = config.get("priority", {})
    severity = block.get("severity", {}) if isinstance(block, Mapping) else {}

    missing = []
    for key in _SEVERITY_KEYS:
        if not isinstance(severity, Mapping) or key not in severity:
            missing.append(f"severity.{key}")
    for key in _SCALAR_KEYS:
        if not isinstance(block, Mapping) or key not in block:
            missing.append(key)

    if missing:
        raise RuntimeError(
            "config.yaml is missing priority config keys: " + ", ".join(missing)
        )

    return block


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
