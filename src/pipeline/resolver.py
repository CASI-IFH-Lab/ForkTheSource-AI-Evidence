"""Stage 3 - Resolver. Plain code, no model calls.

Looks each structured reference up in public catalogues and attaches whatever the
catalogue says. Responses are cached on disk so a re-run costs no network calls;
the cache directory and the request timeout both come from config.yaml.
"""

from __future__ import annotations

from typing import Any


def run(references: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Not implemented yet - lands in M2."""
    raise NotImplementedError("resolver.run: implemented in M2")
