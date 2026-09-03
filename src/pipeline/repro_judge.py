"""Stage 6 - Reproducibility judge. Model call.

Checks each extracted claim against the evidence that backs it, and rates how well
supported it is. Output is validated JSON, one verdict per claim.
"""

from __future__ import annotations

from typing import Any


def run(claims: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Not implemented yet - lands in M4."""
    raise NotImplementedError("repro_judge.run: implemented in M4")
