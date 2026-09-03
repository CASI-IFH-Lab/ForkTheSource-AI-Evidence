"""Stage 2 - Extractor. Model call.

Takes one raw reference string and returns it as structured JSON: authors, year,
title, venue, volume, issue, pages, identifiers. The reply is validated against a
schema; on a bad reply we retry once, then mark the item "extraction_failed".
"""

from __future__ import annotations

from typing import Any


def run(references: list[str], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Not implemented yet - lands in M1."""
    raise NotImplementedError("extractor.run: implemented in M1")
