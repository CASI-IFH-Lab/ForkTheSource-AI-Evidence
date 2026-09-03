"""Stage 7 - Critic. Model call, deliberately a different model family.

Last pass before a human reads anything: checks the write-up is supported by the
evidence and uses none of the banned_terms from config.yaml. Runs at its own
temperature (critic_temperature) so its judgement stays as steady as possible.
"""

from __future__ import annotations

from typing import Any


def run(report: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Not implemented yet - lands in M5."""
    raise NotImplementedError("critic.run: implemented in M5")
