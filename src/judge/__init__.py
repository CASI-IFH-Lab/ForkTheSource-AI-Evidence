"""A1 - the AIR-hosted LLM judge. Owner: Arsha.

Three modules, one public surface:

- ``prompts.py``  the system prompt, as a module constant, so Roy's R3
  adversarial suite attacks the real string and R4 can quote it.
- ``agent.py``    ``judge_reference(ref, ev, fallback_fn=None) -> Verdict``,
  which never raises: every failure path degrades to a deterministic
  verdict and says so in ``Verdict.judge_model``.
- ``gate.py``     ``gate_batch(verdicts, total) -> list[Verdict]``, the
  folded-in critic: three code checks, no model call (D-004 / D-200).

This package depends on ``src.contract``, ``src.settings`` and ``src.llm``
- tier-1 shared infrastructure - and on nothing in Ritik's or Roy's lane.
The seam to the pipeline is dependency injection in both directions:
``src/pipeline.py`` receives ``judge_fn``, and ``judge_reference`` receives
``fallback_fn``. Neither imports the other. See D-008.
"""

from src.judge.agent import judge_reference, stub_status
from src.judge.gate import (
    GateCountMismatch,
    GateDuplicateVerdict,
    GateError,
    gate_batch,
)

__all__ = [
    "judge_reference",
    "stub_status",
    "gate_batch",
    "GateError",
    "GateCountMismatch",
    "GateDuplicateVerdict",
]
