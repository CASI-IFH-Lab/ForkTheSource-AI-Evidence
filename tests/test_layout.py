"""Guards the file layout the plan's parallel-work design depends on.

Replaces tests/test_pipeline_contract.py, which enforced a uniform seven-stage
run(payload, config) walk. The plan has no such thing: it has an orchestrator calling
named functions across three packages, each with its own narrow public interface. The old
test was 15 green tests enforcing the wrong architecture.

What matters instead is that the lanes stay disjoint. Section 3 of the plan puts Ritik,
Arsha and Roy in three vertical lanes that never point at each other until the integration
modules at the bottom, and that disjointness is the whole reason three people can work at
once. These tests fail the moment it erodes.
"""

import ast
import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"

# Ritik's packages, created in B0 so the lane has somewhere to land.
RITIK_PACKAGES = ("src.ingest", "src.resolvers", "src.matching")


@pytest.mark.parametrize("package", RITIK_PACKAGES)
def test_package_is_importable(package: str):
    module = importlib.import_module(package)
    assert module.__doc__, f"{package} needs a docstring naming its owner and module ID"


@pytest.mark.parametrize("package", RITIK_PACKAGES)
def test_package_has_an_init(package: str):
    path = SRC / package.split(".", 1)[1] / "__init__.py"
    assert path.exists(), f"{path} is missing"


def test_p1_lives_where_the_plan_says():
    from src.ingest import pdf_parser

    assert callable(pdf_parser.extract_pages)
    assert callable(pdf_parser.extract_text)


def test_contract_does_not_exist_yet():
    """B1 is the gate. DELETE THIS TEST IN THE B1 PR.

    src/contract.py is Arsha's and it is merge-queue #2. Until it lands, nobody should be
    inlining their own copy of the four statuses or the six indicators - that guarantees a
    rename conflict the day B1 merges. This test is a live reminder, and removing it is
    part of B1's diff.
    """
    contract = SRC / "contract.py"
    assert not contract.exists(), (
        "src/contract.py now exists - if this is the B1 PR, delete this test. "
        "If it is not, you are building Arsha's module."
    )


def test_pipeline_module_is_reserved_for_p6():
    """src/pipeline.py is P6's file. Creating it empty invites imports from nothing."""
    assert not (SRC / "pipeline.py").exists(), "src/pipeline.py is reserved for P6"
    assert not (SRC / "pipeline").is_dir(), (
        "src/pipeline/ as a package collides with src/pipeline.py, which the plan "
        "reserves for the P6 orchestrator"
    )


def python_files_under(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def imported_modules(path: Path) -> set[str]:
    """Every module name this file imports, from the AST.

    Parsed rather than grepped on purpose: a docstring that mentions dashboard/app.py is
    prose, not a dependency, and a substring check cannot tell the difference. This
    function only sees real import statements.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def crosses_lane_boundary(names: set[str]) -> list[str]:
    """Which of these imports reach into Arsha's lane."""
    return sorted(
        name
        for name in names
        if name == "dashboard"
        or name.startswith("dashboard.")
        or name == "src.judge"
        or name.startswith("src.judge.")
    )


def test_no_src_module_imports_arshas_lane():
    """Ritik's lane must not import src/judge/ or dashboard/.

    The plan is explicit that P6 accepts judge_fn and does NOT import src/judge. The real
    wiring is one line in A3, on Arsha's branch. If this fails, a lane boundary has been
    crossed and the two branches will now conflict.
    """
    offenders = []
    for path in python_files_under(SRC):
        for name in crosses_lane_boundary(imported_modules(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert not offenders, "lane boundary crossed:\n" + "\n".join(offenders)


def test_app_shell_only_imports_ritiks_lane():
    """app.py is the B0 shell. It may use src/, never dashboard/ or src/judge/."""
    names = imported_modules(REPO_ROOT / "app.py")
    assert any(n.startswith("src.ingest") for n in names), (
        "app.py should read PDFs through src/ingest"
    )
    assert not crosses_lane_boundary(names), (
        f"app.py crosses into Arsha's lane: {crosses_lane_boundary(names)}"
    )
