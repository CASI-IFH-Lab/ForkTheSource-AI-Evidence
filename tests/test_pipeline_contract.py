"""Every stage keeps the same shape, so the app can walk them in order.

The six unimplemented stages have nothing to test behaviourally yet. This holds
their scaffolding in place: each milestone fills in the real test beside it.
"""

import importlib

import pytest

from src.pipeline import STAGES

EXPECTED = (
    "intake",
    "extractor",
    "resolver",
    "judge",
    "repro_extractor",
    "repro_judge",
    "critic",
)


def test_all_seven_stages_are_declared_in_order():
    assert STAGES == EXPECTED


@pytest.mark.parametrize("stage", STAGES)
def test_stage_module_exposes_run(stage):
    module = importlib.import_module(f"src.pipeline.{stage}")
    assert callable(getattr(module, "run", None)), f"{stage}.run() is missing"


@pytest.mark.parametrize("stage", STAGES)
def test_stage_module_says_what_it_does(stage):
    module = importlib.import_module(f"src.pipeline.{stage}")
    assert (module.__doc__ or "").strip(), f"{stage} needs a module docstring"
