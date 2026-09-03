"""Stage 4 - Judge. Model call.

Compares what the paper cited against what the resolver actually found, and says
how well they agree and why. Output is validated JSON, one verdict per reference.
"""

from __future__ import annotations

from typing import Any


def run(references: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Not implemented yet - lands in M3."""
    raise NotImplementedError("judge.run: implemented in M3")
