"""Guards the file layout the plan's parallel-work design depends on.

Replaces tests/test_pipeline_contract.py, which enforced a uniform seven-stage
run(payload, config) walk. The plan has no such thing: it has an orchestrator calling
named functions across three packages, each with its own narrow public interface. The old
test was 15 green tests enforcing the wrong architecture.

What matters instead is that the lanes stay disjoint. Section 3 of the plan puts Ritik,
Arsha and Roy in three vertical lanes that never point at each other until the integration
modules at the bottom, and that disjointness is the whole reason three people can work at
once. These tests fail the moment it erodes.

Two things this file deliberately does NOT do, both from docs/decisions.md:

- It does not assert that src/contract.py is absent. That assertion was removed in the
  B1-unblock pass: it was green until Arsha created the file she is supposed to create,
  and then red for the one action that was correct, with "delete the assertion" as its
  prescribed fix. See D-006 - do not use a test as a to-do list for another person.
- It does not forbid a lane from importing SHARED_INFRA, and it does not forbid a package
  from importing itself. See D-008.
"""

import ast
import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"

# Ritik's packages, created in B0 so the lane has somewhere to land.
RITIK_PACKAGES = ("src.ingest", "src.resolvers", "src.matching")

# ---------------------------------------------------------------------------
# The three tiers of file ownership - docs/decisions.md D-008.
#
# EDIT THESE LISTS, NOT THE LOGIC BELOW. Every rule in this file is derived from
# these three constants, so moving a file between tiers is a one-line data change.
# ---------------------------------------------------------------------------

# TIER 1 - SHARED INFRASTRUCTURE. Imported by anything, redefined by nobody.
#
# The plan's lane rule read literally would forbid A1 from calling src.llm.get_client(),
# and the only way to satisfy that would be a SECOND gateway client inside src/judge/
# with its own timeout handling and its own base-URL error message. Duplicated
# infrastructure diverges silently, which is the opposite of what lane isolation is for.
# A client, a settings loader, a contract and a priority formula are written once.
SHARED_INFRA = ("src.settings", "src.llm", "src.contract", "src.priority")

# TIER 2 - LANE-EXCLUSIVE. Cross-lane FEATURE imports are forbidden in BOTH directions:
# Ritik's lane may not import Arsha's, and Arsha's may not import Ritik's. The seams are
# dependency injection (judge_fn, fallback_fn), not imports.
LANES = {
    # app.py is the B0 shell and is deleted in the A3 PR - D-010.
    "Ritik": ("src.ingest", "src.resolvers", "src.matching", "src.pipeline", "app"),
    "Arsha": ("src.judge", "dashboard"),
    "Roy": ("eval",),
}

# TIER 3 - INTEGRATION is A3 only, and it is one line on Arsha's branch. It needs no
# constant here because it is a single PR rather than a standing exception.

# Where to look for Python files. Anything not under one of these is unowned.
SCAN_ROOTS = ("src", "dashboard", "eval", "app.py")


def _owns(prefix: str, module: str) -> bool:
    """Does `prefix` own the dotted module name `module`? Exact match or a sub-module."""
    return module == prefix or module.startswith(prefix + ".")


def lane_of(module: str) -> str | None:
    """Which lane owns this dotted module name, or None if nobody exclusively does.

    Shared infrastructure returns None on purpose: it belongs to no lane, which is
    precisely what makes it importable from every lane.
    """
    if any(_owns(prefix, module) for prefix in SHARED_INFRA):
        return None
    for lane, prefixes in LANES.items():
        if any(_owns(prefix, module) for prefix in prefixes):
            return lane
    return None


def lane_of_path(path: Path) -> str | None:
    """The lane that owns a file on disk, by converting its path to a module name."""
    relative = path.resolve().relative_to(REPO_ROOT).with_suffix("")
    return lane_of(".".join(relative.parts))


def cross_lane_offenders(owner: str | None, imported: object) -> list[str]:
    """Which of `imported` reach into a lane other than `owner`'s.

    The whole rule lives here:
      - SHARED_INFRA is never an offender (lane_of returns None).
      - A file's own lane is never an offender, so src/judge/agent.py importing
        src/judge/prompts.py is fine. That intra-package case is the bug this
        function was rewritten to fix - see D-008.
      - Anything owned by a different lane is an offender.
    """
    offenders = []
    for module in imported:
        target = lane_of(module)
        if target is None or target == owner:
            continue
        offenders.append(f"{module} ({target}'s lane)")
    return sorted(offenders)


def python_files_under(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def all_owned_python_files() -> list[Path]:
    files: list[Path] = []
    for name in SCAN_ROOTS:
        files.extend(python_files_under(REPO_ROOT / name))
    return files


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


# ---------------------------------------------------------------------------
# The packages exist and are importable
# ---------------------------------------------------------------------------


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


def test_pipeline_module_is_reserved_for_p6():
    """src/pipeline.py is P6's file. Creating it empty invites imports from nothing."""
    assert not (SRC / "pipeline.py").exists(), "src/pipeline.py is reserved for P6"
    assert not (SRC / "pipeline").is_dir(), (
        "src/pipeline/ as a package collides with src/pipeline.py, which the plan "
        "reserves for the P6 orchestrator"
    )


# ---------------------------------------------------------------------------
# Tier 1: shared infrastructure is importable from everywhere
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", SHARED_INFRA)
def test_shared_infra_is_importable_from_any_lane(module: str):
    """Asserted POSITIVELY so a future tightening cannot silently forbid it.

    D-008. If someone later adds src.llm to a lane's prefix list to "tighten" isolation,
    this test fails and points them at the entry explaining why a second gateway client
    is a bug rather than better hygiene.
    """
    assert lane_of(module) is None, (
        f"{module} is shared infrastructure and must belong to no lane - see D-008"
    )
    for lane in LANES:
        assert cross_lane_offenders(lane, [module]) == [], (
            f"{lane}'s lane must be allowed to import {module} - see D-008"
        )


def test_a_lane_may_import_its_own_package():
    """The intra-package false positive that would have broken Arsha's first A1 commit.

    The old check walked every file under src/ and forbade any import of src.judge.*,
    which meant src/judge/agent.py importing src/judge/prompts.py was flagged as a lane
    violation. D-008.
    """
    assert cross_lane_offenders("Arsha", ["src.judge.prompts", "dashboard.theme"]) == []
    assert cross_lane_offenders("Ritik", ["src.ingest.extractor", "src.matching.rules"]) == []
    assert cross_lane_offenders("Roy", ["eval.report"]) == []


# ---------------------------------------------------------------------------
# Tier 2: cross-lane feature imports, forbidden in both directions
# ---------------------------------------------------------------------------


def test_no_cross_lane_feature_imports():
    """No file in any lane imports another lane's feature code.

    The plan is explicit that P6 accepts judge_fn and does NOT import src/judge, and the
    same holds in reverse. If this fails, a lane boundary has been crossed and two
    branches that were designed to merge in any order now conflict.
    """
    offenders = []
    for path in all_owned_python_files():
        owner = lane_of_path(path)
        for offender in cross_lane_offenders(owner, imported_modules(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)} ({owner}) imports {offender}")
    assert not offenders, "lane boundary crossed:\n" + "\n".join(offenders)


def test_ritiks_lane_may_not_import_arshas():
    """The rule is armed, not merely vacuously true while src/judge/ is absent."""
    assert cross_lane_offenders("Ritik", ["src.judge"]) != []
    assert cross_lane_offenders("Ritik", ["src.judge.agent"]) != []
    assert cross_lane_offenders("Ritik", ["dashboard.app"]) != []


def test_arshas_lane_may_not_import_ritiks_pipeline():
    """A2's own DoD box: the dashboard renders ledger_fixture.json fully offline.

    The old check only ran in one direction, so nothing stopped dashboard/app.py from
    importing src/pipeline and quietly making A2 depend on P6. Armed the same way.
    """
    assert cross_lane_offenders("Arsha", ["src.pipeline"]) != []
    assert cross_lane_offenders("Arsha", ["src.ingest.pdf_parser"]) != []
    assert cross_lane_offenders("Arsha", ["src.resolvers.resolver"]) != []
    assert cross_lane_offenders("Arsha", ["src.matching.rules"]) != []


def test_app_shell_only_imports_ritiks_lane():
    """app.py is the B0 shell. It may use src/, never dashboard/ or src/judge/."""
    names = imported_modules(REPO_ROOT / "app.py")
    assert any(n.startswith("src.ingest") for n in names), (
        "app.py should read PDFs through src/ingest"
    )
    assert cross_lane_offenders("Ritik", names) == []
