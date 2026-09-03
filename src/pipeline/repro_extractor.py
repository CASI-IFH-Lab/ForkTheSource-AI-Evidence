"""Stage 5 - Reproducibility extractor. Model call.

Pulls the paper's own reproducibility claims out of its text - shared code, data,
environment details, hardware - as structured JSON.
"""

from __future__ import annotations

from typing import Any


def run(document_text: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Not implemented yet - lands in M4."""
    raise NotImplementedError("repro_extractor.run: implemented in M4")
