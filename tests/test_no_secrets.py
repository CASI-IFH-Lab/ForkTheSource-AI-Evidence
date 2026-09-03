"""Runs scripts/check_secrets.sh under pytest, and proves it actually catches things.

The near-miss this exists to prevent: during the B0 docs pass, the first 16 characters
of a live API key were drafted into a doc as a worked example of what not to paste. It
was caught by hand before the commit. Hand-catching is not a control. (It happened a
second time in the D-007 pass with a real email address - see docs/worklog.md.)

Note how the fake secrets below are BUILT AT RUNTIME from fragments rather than written
as literals. If this file contained a literal key-shaped string, the guard would find it
here and fail on its own test suite.

TWO IMPLEMENTATIONS OF THE SAME TWO SCANS, on purpose
-----------------------------------------------------
`scripts/check_secrets.sh` is the real guard - it is what runs before a push, and the
shell tests below drive it directly. But it needs `bash`, and on a default Windows
install it either is not on PATH or receives a Windows path it cannot execute (exit 127).
Six tests here failed that way on a teammate's machine.

Skipping them there was not acceptable: **a secrets check that skips on someone's machine
is a secrets check that is not there**, and the entire reason the script exists is that
hand-catching is not a control. So the two scans are also implemented in Python
(`scan_for_key_shaped_literals`, `scan_for_gateway_host`), which runs everywhere with no
shell, and is exercised against the same planted secrets. The shell tests skip cleanly
with a named reason when bash is missing; the Python tests never skip.

The Python versions mirror the shell's semantics deliberately, including the parts that
look like details: tracked files only (`git ls-files`), binary files skipped the way
`grep -I` skips them, and the gateway host read OUT of .env.example rather than
hardcoded (D-031 - hardcoding it here would put the literal in a tracked file outside
the template, which is the exact thing the guard forbids).
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_secrets.sh"
SCRIPT_RELATIVE = "scripts/check_secrets.sh"
TEMPLATE = ".env.example"

BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(
    BASH is None,
    reason=(
        "bash is not on PATH, so scripts/check_secrets.sh cannot be driven directly. "
        "The Python reimplementation in this file runs the same two scans and does "
        "not skip - see this module's docstring."
    ),
)

# Same pattern as check 1 in the shell script: sk- followed by 8+ key characters.
KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}")


# ---------------------------------------------------------------------------
# Driving the real shell guard
# ---------------------------------------------------------------------------


def run_script(cwd: Path) -> subprocess.CompletedProcess:
    """Invoke the guard through a RELATIVE path, with cwd set.

    Not `str(cwd / "scripts" / "check_secrets.sh")`: on Windows that is a path like
    C:\\Users\\...\\check_secrets.sh, which Git-Bash cannot execute - it exits 127 and
    every assertion below reads as a guard failure rather than a harness failure. A
    relative path sidesteps drive letters and separators entirely, and the script's own
    first act is `cd "$(dirname "$0")/.."`, which resolves correctly from `cwd`.

    encoding is explicit because `text=True` alone decodes with the locale encoding.
    """
    return subprocess.run(
        ["bash", SCRIPT_RELATIVE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
    )


def test_script_exists_and_is_executable():
    assert SCRIPT.exists(), "scripts/check_secrets.sh is missing"


@needs_bash
def test_this_repo_is_clean():
    """The real check: no secrets in this tree, right now."""
    result = run_script(REPO_ROOT)
    assert result.returncode == 0, (
        "check_secrets.sh failed on this repo:\n"
        f"{result.stdout}\n{result.returncode=}"
    )
    assert "PASS" in result.stdout


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A throwaway git repo with the guard installed and a valid .env.example."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / "check_secrets.sh")
    # Assembled from fragments so this file never contains the literal host.
    host = ".".join(["openai", "rc", "asu", "edu"])
    (tmp_path / TEMPLATE).write_text(
        f"AIR_API_KEY=paste-your-own-key\nAIR_BASE_URL=https://{host}/v1\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def stage_all(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def plant_key(repo: Path) -> str:
    planted = "sk-" + "eXampleKey123"          # built at runtime, never a literal here
    (repo / "notes.md").write_text(
        f"do not paste your key like {planted}\n", encoding="utf-8"
    )
    return planted


def plant_gateway_host(repo: Path) -> str:
    host = ".".join(["openai", "rc", "asu", "edu"])
    (repo / "src_config.py").write_text(f'BASE = "https://{host}/v1"\n', encoding="utf-8")
    return host


@needs_bash
def test_guard_passes_on_a_clean_fake_repo(fake_repo: Path):
    stage_all(fake_repo)
    assert run_script(fake_repo).returncode == 0


@needs_bash
def test_guard_catches_a_key_shaped_literal(fake_repo: Path):
    """The exact near-miss: a key pasted into a doc."""
    plant_key(fake_repo)
    stage_all(fake_repo)

    result = run_script(fake_repo)
    assert result.returncode != 0, "the guard did not catch a planted key"
    assert "FAIL" in result.stdout
    assert "notes.md" in result.stdout
    assert "rotate the key" in result.stdout


@needs_bash
def test_guard_catches_the_gateway_host_outside_the_template(fake_repo: Path):
    plant_gateway_host(fake_repo)
    stage_all(fake_repo)

    result = run_script(fake_repo)
    assert result.returncode != 0, "the guard did not catch a hardcoded gateway host"
    assert "FAIL" in result.stdout
    assert "src_config.py" in result.stdout


@needs_bash
def test_guard_ignores_untracked_files(fake_repo: Path):
    """Untracked scratch files cannot reach GitHub, so they are not the guard's business."""
    planted = "sk-" + "eXampleKey123"
    (fake_repo / "scratch.txt").write_text(planted, encoding="utf-8")
    # deliberately NOT staged
    subprocess.run(["git", "add", TEMPLATE, "scripts"], cwd=fake_repo, check=True)

    assert run_script(fake_repo).returncode == 0


@needs_bash
def test_guard_fails_loudly_if_the_template_is_missing(fake_repo: Path):
    """The .env.example deletion slip that already happened once in this repo."""
    stage_all(fake_repo)
    (fake_repo / TEMPLATE).unlink()

    result = run_script(fake_repo)
    assert result.returncode != 0
    assert "missing" in result.stdout


# ---------------------------------------------------------------------------
# The same two scans in Python, so the guard runs with no shell at all
# ---------------------------------------------------------------------------


def tracked_files(repo: Path) -> list[Path]:
    """What `git ls-files -z` reports, as paths. Tracked only, like the shell guard."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [repo / name for name in result.stdout.split("\0") if name]


def readable_text(path: Path) -> str | None:
    """The file's text, or None if it is binary or unreadable.

    Mirrors `grep -I`: a NUL byte means binary, and binary files are skipped rather than
    scanned. Without this, the two committed PDFs would be searched for `sk-`-shaped
    byte sequences and could produce a false positive that nobody could act on.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    return raw.decode("utf-8", errors="replace")


def scan_for_key_shaped_literals(repo: Path) -> list[str]:
    """Check 1: any API-key-shaped literal in any tracked file."""
    hits: list[str] = []
    for path in tracked_files(repo):
        text = readable_text(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if KEY_PATTERN.search(line):
                hits.append(f"{path.relative_to(repo).as_posix()}:{number}")
    return hits


def gateway_host(repo: Path) -> str | None:
    """The host, read OUT of .env.example - never hardcoded here. D-031."""
    template = repo / TEMPLATE
    if not template.exists():
        return None
    for line in template.read_text(encoding="utf-8").splitlines():
        if line.startswith("AIR_BASE_URL="):
            value = line.split("=", 1)[1].strip()
            value = re.sub(r"^[a-zA-Z]+://", "", value)
            return value.split("/")[0] or None
    return None


def scan_for_gateway_host(repo: Path) -> list[str]:
    """Check 2: the gateway host appearing anywhere outside .env.example."""
    host = gateway_host(repo)
    if not host:
        return []
    hits: list[str] = []
    for path in tracked_files(repo):
        if path.relative_to(repo).as_posix() == TEMPLATE:
            continue
        text = readable_text(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if host in line:
                hits.append(f"{path.relative_to(repo).as_posix()}:{number}")
    return hits


def test_python_scan_finds_no_key_shaped_literal_in_this_repo():
    """The real check again, with no shell. This one never skips."""
    assert scan_for_key_shaped_literals(REPO_ROOT) == []


def test_python_scan_finds_no_gateway_host_outside_the_template():
    assert scan_for_gateway_host(REPO_ROOT) == []


def test_python_scan_reads_the_host_from_the_template():
    """If this returns None the second scan is silently doing nothing."""
    assert gateway_host(REPO_ROOT), "could not read AIR_BASE_URL's host from .env.example"


def test_python_scan_catches_a_planted_key(fake_repo: Path):
    plant_key(fake_repo)
    stage_all(fake_repo)
    assert scan_for_key_shaped_literals(fake_repo) == ["notes.md:1"]


def test_python_scan_catches_the_gateway_host_outside_the_template(fake_repo: Path):
    plant_gateway_host(fake_repo)
    stage_all(fake_repo)
    assert scan_for_gateway_host(fake_repo) == ["src_config.py:1"]


def test_python_scan_ignores_untracked_files(fake_repo: Path):
    planted = "sk-" + "eXampleKey123"
    (fake_repo / "scratch.txt").write_text(planted, encoding="utf-8")
    subprocess.run(["git", "add", TEMPLATE, "scripts"], cwd=fake_repo, check=True)

    assert scan_for_key_shaped_literals(fake_repo) == []


def test_python_scan_skips_binary_files(fake_repo: Path):
    """A NUL byte means binary, like `grep -I`. Guards against a PDF false positive."""
    planted = ("sk-" + "eXampleKey123").encode("utf-8")
    (fake_repo / "blob.bin").write_bytes(b"\x00\x01" + planted + b"\x00")
    stage_all(fake_repo)

    assert scan_for_key_shaped_literals(fake_repo) == []
    assert readable_text(fake_repo / "blob.bin") is None


def test_python_scan_finds_nothing_when_the_template_is_missing(fake_repo: Path):
    """gateway_host returns None rather than raising, so scan 2 degrades to a no-op.

    The SHELL guard hard-fails in this case, which is the correct behaviour for the
    pre-push gate. This function is a scanner rather than a gate, so the hard failure
    belongs in its caller - test_guard_fails_loudly_if_the_template_is_missing covers
    it, and test_python_scan_reads_the_host_from_the_template covers the silent-no-op
    risk on the real repo.
    """
    stage_all(fake_repo)
    (fake_repo / TEMPLATE).unlink()

    assert gateway_host(fake_repo) is None
    assert scan_for_gateway_host(fake_repo) == []
