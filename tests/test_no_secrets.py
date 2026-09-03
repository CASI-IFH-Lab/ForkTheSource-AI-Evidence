"""Runs scripts/check_secrets.sh under pytest, and proves it actually catches things.

The near-miss this exists to prevent: during the B0 docs pass, the first 16 characters
of a live API key were drafted into docs/setup.md as a worked example of what not to
paste. It was caught by hand before the commit. Hand-catching is not a control.

Note how the fake secrets below are BUILT AT RUNTIME from fragments rather than written
as literals. If this file contained a literal key-shaped string, the guard would find it
here and fail on its own test suite.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_secrets.sh"


def run_script(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(cwd / "scripts" / "check_secrets.sh")],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_script_exists_and_is_executable():
    assert SCRIPT.exists(), "scripts/check_secrets.sh is missing"


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
    (tmp_path / ".env.example").write_text(
        f"AIR_API_KEY=paste-your-own-key\nAIR_BASE_URL=https://{host}/v1\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def stage_all(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def test_guard_passes_on_a_clean_fake_repo(fake_repo: Path):
    stage_all(fake_repo)
    assert run_script(fake_repo).returncode == 0


def test_guard_catches_a_key_shaped_literal(fake_repo: Path):
    """The exact near-miss: a key pasted into a doc."""
    planted = "sk-" + "eXampleKey123"          # built at runtime, never a literal here
    (fake_repo / "notes.md").write_text(f"do not paste your key like {planted}\n")
    stage_all(fake_repo)

    result = run_script(fake_repo)
    assert result.returncode != 0, "the guard did not catch a planted key"
    assert "FAIL" in result.stdout
    assert "notes.md" in result.stdout
    assert "rotate the key" in result.stdout


def test_guard_catches_the_gateway_host_outside_the_template(fake_repo: Path):
    host = ".".join(["openai", "rc", "asu", "edu"])
    (fake_repo / "src_config.py").write_text(f'BASE = "https://{host}/v1"\n')
    stage_all(fake_repo)

    result = run_script(fake_repo)
    assert result.returncode != 0, "the guard did not catch a hardcoded gateway host"
    assert "FAIL" in result.stdout
    assert "src_config.py" in result.stdout


def test_guard_ignores_untracked_files(fake_repo: Path):
    """Untracked scratch files cannot reach GitHub, so they are not the guard's business."""
    planted = "sk-" + "eXampleKey123"
    (fake_repo / "scratch.txt").write_text(planted)
    # deliberately NOT staged
    stage_all_but_scratch = ["git", "add", ".env.example", "scripts"]
    subprocess.run(stage_all_but_scratch, cwd=fake_repo, check=True)

    assert run_script(fake_repo).returncode == 0


def test_guard_fails_loudly_if_the_template_is_missing(fake_repo: Path):
    """The .env.example deletion slip that already happened once in this repo."""
    stage_all(fake_repo)
    (fake_repo / ".env.example").unlink()

    result = run_script(fake_repo)
    assert result.returncode != 0
    assert "missing" in result.stdout
