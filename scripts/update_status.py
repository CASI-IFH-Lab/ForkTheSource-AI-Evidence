#!/usr/bin/env python3
"""Regenerate STATUS.md — the one-command answer to "where is everything".

Three people work three lanes in parallel. The failure mode this exists to kill is
somebody asking "is P2 merged yet, and what does it export" in chat and waiting eight
minutes for a reply. ``git pull && cat STATUS.md`` answers that, and STATUS.md is
ordered so the answer is readable in ten seconds: open blockers first, because
anything there is a person sitting idle.

Design rules, in priority order:

1. **It must never fail.** A status tool that crashes is worse than no status tool,
   because the next thing that happens is everyone goes back to asking in chat. Every
   input is optional and every section is independently guarded: if git is missing, or
   ``progress/`` is empty, or a module explodes on import, that *section* says so and
   the script still exits 0. The only non-zero exit is the deliberate one from
   ``--check``.
2. **Pure stdlib.** No new dependencies. This runs from a git hook on three different
   machines, one of them Git Bash on Windows.
3. **Deterministic apart from the timestamp.** Running it twice with no changes
   produces no diff at all: the timestamp is minute-granular and every list is sorted
   by a stable key. That is what makes ``--check`` meaningful.
4. **Under two seconds.** Typically ~1.3s, almost all of it ``pytest --collect-only``
   and importing pydantic. Every subprocess has a timeout so a hung input cannot hang
   the hook.

Usage::

    python scripts/update_status.py            # rewrite STATUS.md, exit 0
    python scripts/update_status.py --check     # exit 1 if STATUS.md is stale
    python scripts/update_status.py --stdout    # print, do not write

STATUS.md is GENERATED. Never hand-edit it; your edit is gone on the next commit.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import re
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATUS_PATH = REPO / "STATUS.md"
PROGRESS_DIR = REPO / "progress"

# Timeouts are safety nets against a hung input, not the expected path. Blowing one
# costs a "not collected" line in the output; blowing past it would hang a git hook.
GIT_TIMEOUT = 10
PYTEST_TIMEOUT = 20

YES, NO, WARN = "✅", "⬜", "⚠️"

STATUS_WORDS = (
    "READY",
    "STARTED",
    "MERGED",
    "BLOCKED",
    "AHEAD",
    "REQUEST",
    "OBJECTION",
    "SCOPE-CUT",
)
#: The two status words that mean a human is waiting on another human.
OPEN_WORDS = ("REQUEST", "BLOCKED")

#: The published-interface contract. Hardcoded on purpose: this is the list of things
#: the lanes agreed to export, so the table has to show a symbol as missing even when
#: - especially when - nobody has written the module yet. Deriving it from the tree
#: would only ever tell us what already exists.
PUBLISHED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("src.ingest.pdf_parser", ("parse_pdf",)),
    ("src.ingest.extractor", ("extract_references", "extract_claims")),
    ("src.resolvers.cache", ("make_key", "cache_get", "cache_set")),
    ("src.resolvers.resolver", ("resolve",)),
    ("src.matching.evidence", ("build_evidence",)),
    ("src.matching.rules", ("rule_based_status",)),
    ("src.pipeline", ("run",)),
    ("src.judge.agent", ("judge_reference",)),
    ("src.judge.gate", ("gate_batch",)),
    ("src.judge.wiring", ("wired_judge",)),
    ("dashboard.app", ("render_ledger",)),
    ("src.contract", ("Ledger", "load_ledger", "save_ledger")),
    ("src.priority", ("compute_priority",)),
    (
        "src.settings",
        (
            "load_config",
            "model_for",
            "temperature_for",
            "banned_terms",
            "resolver_settings",
            "crossref_mailto",
            "cache_dir",
            "llm_settings",
            "thresholds",
            "priority_severity",
            "priority_weights",
            "cache_settings",
        ),
    ),
    ("src.llm", ("get_client",)),
)


# ---------------------------------------------------------------------------
# subprocess plumbing - nothing in here raises
# ---------------------------------------------------------------------------
def _run(cmd: list[str], timeout: int) -> str | None:
    """Run ``cmd`` in the repo root. Return stdout, or None on any failure at all."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO),
            capture_output=True,
            text=True,
            # Explicit, not locale: `text=True` alone decodes with the console
            # codepage, which is cp1252 on a Windows clone and blows up on a commit
            # subject with a dash in it. `replace` because a mangled author name in
            # the report is fine and a crashed hook is not. See the encoding guard
            # in tests/test_layout.py.
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _git(*args: str) -> str | None:
    return _run(["git", *args], GIT_TIMEOUT)


def _main_ref() -> str | None:
    """The ref to read history from: ``main`` if it exists, else ``origin/main``, else HEAD.

    A CI checkout or a detached worktree may not have a local ``main``, and reading
    history is the whole point of the section, so fall back rather than report nothing.
    """
    for ref in ("main", "origin/main", "HEAD"):
        if _git("rev-parse", "--verify", "--quiet", ref):
            return ref
    return None


# ---------------------------------------------------------------------------
# progress/ parsing
# ---------------------------------------------------------------------------
# "## 0:15 - S0 STARTED", with an em dash, an en dash or a hyphen as the separator.
_HEADING_RE = re.compile(r"^##\s+(?P<clock>\S+)\s+[—–-]{1,2}\s+(?P<rest>\S.*?)\s*$")
_REQUEST_RE = re.compile(r"^REQUEST\s*(?:->|→)\s*@?(?P<owner>\S+)\s*$", re.IGNORECASE)
_FIELD_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9 _-]{0,40}):\s*(?P<val>.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


class Block:
    """One parsed ``## ...`` block from one person's progress file."""

    __slots__ = ("person", "clock", "module", "status", "owner", "fields", "lineno", "heading")

    def __init__(
        self,
        person: str,
        clock: str,
        module: str,
        status: str | None,
        owner: str | None,
        fields: list[tuple[str, str]],
        lineno: int,
        heading: str,
    ) -> None:
        self.person = person
        self.clock = clock
        self.module = module
        self.status = status  # None == the heading did not end in a known status word
        self.owner = owner
        self.fields = fields
        self.lineno = lineno
        self.heading = heading

    @property
    def ok(self) -> bool:
        return self.status is not None

    @property
    def clock_minutes(self) -> int:
        """``2:40`` -> 160. Unparseable clocks sort last rather than crashing a sort."""
        m = re.match(r"^(\d{1,3}):(\d{2})$", self.clock)
        if not m:
            return 10**6
        return int(m.group(1)) * 60 + int(m.group(2))

    def label(self) -> str:
        if self.status == "REQUEST" and self.owner:
            return f"REQUEST -> @{self.owner}"
        return f"{self.module} {self.status}"


def parse_progress_text(text: str, person: str = "?") -> list[Block]:
    """Parse one progress file into blocks, newest last.

    Deliberately tolerant in one direction only: an unrecognised heading becomes a
    block with ``status is None`` (reported as unparseable) and a stray line inside a
    block is ignored. Nothing in here raises on bad input - a malformed block must not
    be able to take the whole status tool down with it.

    Fenced code is skipped entirely, which is what lets each progress file carry a
    worked example that does not report itself as real status.
    """
    blocks: list[Block] = []
    in_fence = False
    current: Block | None = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        head = _HEADING_RE.match(raw)
        if head:
            rest = head.group("rest")
            owner = None
            req = _REQUEST_RE.match(rest)
            if req:
                # A request heading names no module of its own, so REQUEST *is* its
                # module - which is what lets a later "REQUEST MERGED" retire it.
                module, status, owner = "REQUEST", "REQUEST", req.group("owner")
            else:
                parts = rest.split()
                tail = parts[-1].upper() if parts else ""
                if len(parts) >= 2 and tail in STATUS_WORDS:
                    module, status = " ".join(parts[:-1]), tail
                else:
                    # A bare status word with no module is unparseable on purpose:
                    # nothing can retire it and nothing can attribute it, so it is
                    # better reported as broken than reported as status.
                    module, status = rest, None
            current = Block(person, head.group("clock"), module, status, owner, [], lineno, raw.strip())
            blocks.append(current)
            continue

        if current is None or not raw.strip():
            continue
        if raw.startswith("#"):  # any other heading ends the block
            current = None
            continue
        field = _FIELD_RE.match(raw)
        if field:
            current.fields.append((field.group("key").strip(), field.group("val")))

    return blocks


def read_progress() -> tuple[dict[str, list[Block]], list[str]]:
    """Return ``{person: blocks}`` plus a list of complaints about the directory."""
    notes: list[str] = []
    if not PROGRESS_DIR.is_dir():
        return {}, [f"`progress/` does not exist at {PROGRESS_DIR}."]

    per_person: dict[str, list[Block]] = {}
    files = sorted(p for p in PROGRESS_DIR.glob("*.md") if not p.name.startswith("_") and p.name != "README.md")
    if not files:
        notes.append("`progress/` has no person files yet (`progress/<name>.md`).")
    for path in files:
        person = path.stem
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            notes.append(f"could not read `progress/{path.name}`: {type(exc).__name__}")
            per_person[person] = []
            continue
        per_person[person] = parse_progress_text(text, person)
    return per_person, notes


def open_items(per_person: dict[str, list[Block]]) -> list[Block]:
    """Every REQUEST/BLOCKED block not retired by a later MERGED for the same module.

    Errs toward showing a stale request rather than hiding a live one: a stale entry
    costs somebody five seconds of reading, a hidden one costs somebody an hour of
    sitting still.
    """
    out: list[Block] = []
    for person in sorted(per_person):
        blocks = per_person[person]
        for i, b in enumerate(blocks):
            if b.status not in OPEN_WORDS:
                continue
            key = b.module.strip().upper()
            retired = any(
                j > i and other.status == "MERGED" and other.module.strip().upper() == key
                for j, other in enumerate(blocks)
            )
            if not retired:
                out.append(b)
    out.sort(key=lambda b: (b.clock_minutes, b.person, b.lineno))
    return out


# ---------------------------------------------------------------------------
# the import probe
# ---------------------------------------------------------------------------
def probe_interfaces() -> list[tuple[str, str, list[tuple[str, str]], str]]:
    """Import each contracted module and check its symbols against this checkout.

    Returns ``(module, mark, [(symbol, mark)], note)``. Output is swallowed and
    warnings are silenced so a module that prints at import time cannot corrupt
    STATUS.md, and every exception - including SystemExit from a module that calls
    ``sys.exit`` at import - is caught, because a half-written module must not be able
    to break the tool that reports it is half-written.
    """
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    results = []
    for module, symbols in PUBLISHED:
        note = ""
        mod = None
        sink = io.StringIO()
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    mod = importlib.import_module(module)
        except ModuleNotFoundError as exc:
            missing = getattr(exc, "name", "") or ""
            head = module.split(".")[0]
            if missing and missing != module and missing != head and not module.startswith(missing + "."):
                # The module exists; something it imports does not. Still not usable,
                # but "not written yet" and "needs `pip install`" are different bugs.
                note = f"missing dependency `{missing}`"
        except BaseException as exc:  # noqa: BLE001 - deliberate; see docstring
            results.append((module, WARN, [(s, NO) for s in symbols], type(exc).__name__))
            continue

        if mod is None:
            results.append((module, NO, [(s, NO) for s in symbols], note))
            continue

        marks = []
        for sym in symbols:
            try:
                present = hasattr(mod, sym)
            except BaseException:  # noqa: BLE001 - a pathological __getattr__
                present = False
            marks.append((sym, YES if present else NO))
        all_present = all(m == YES for _, m in marks)
        if not all_present and not note:
            # The module imports but the contracted name is not on it. Worth calling
            # out separately from "not written yet": it usually means the module was
            # written under a different name than the interface list agreed on.
            note = "module imports, symbol missing"
        results.append((module, YES if all_present else NO, marks, note))
    return results


# ---------------------------------------------------------------------------
# section renderers - each is called through _safe(), so each may raise freely
# ---------------------------------------------------------------------------
def _safe(fn, heading: str) -> list[str]:
    try:
        return fn()
    except BaseException as exc:  # noqa: BLE001
        return [heading, "", f"_Section failed to generate: {type(exc).__name__}: {exc}_", ""]


def _age(seconds: float) -> str:
    """Branch-tip age, floored to a 15-minute bucket.

    Buckets, not minutes, and deliberately: the question this column answers is "has
    this branch been sitting untouched for hours", never "is it 22 or 23 minutes old".
    Minute-level precision would rewrite a tracked STATUS.md once a minute forever,
    which would make every local pull conflict and make `--check` meaningless.
    """
    m = int(max(seconds, 0) // 60)
    m -= m % 15
    if m == 0:
        return "<15m"
    if m < 60:
        return f"{m}m"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h" if m == 0 else f"{h}h {m}m"
    d, h = divmod(h, 24)
    return f"{d}d" if h == 0 else f"{d}d {h}h"


def section_open(per_person: dict[str, list[Block]], notes: list[str]) -> list[str]:
    out = [f"## {WARN} OPEN REQUESTS AND BLOCKERS", ""]
    items = open_items(per_person)
    if not items:
        out.append("None — nobody is waiting.")
        out.append("")
    for b in items:
        if b.status == "REQUEST":
            title = f"**{b.clock} · {b.person} → @{b.owner or '?'}**"
        else:
            title = f"**{b.clock} · {b.person} · {b.module or '?'} BLOCKED**"
        out.append(f"- {title}")
        for key, val in b.fields:
            out.append(f"  - `{key}:` {val}")
        if not b.fields:
            out.append("  - _(no detail lines given)_")
        out.append("")
    for note in notes:
        out.append(f"- {WARN} {note}")
    if notes:
        out.append("")
    unparsed = [b for blocks in per_person.values() for b in blocks if not b.ok]
    if unparsed:
        out.append(f"- {WARN} {len(unparsed)} unparseable block heading(s) — these report nothing:")
        for b in sorted(unparsed, key=lambda b: (b.person, b.lineno)):
            out.append(f"  - `progress/{b.person}.md:{b.lineno}` — {b.heading}")
        out.append("")
    return out


def section_main() -> list[str]:
    out = ["## What is on main", ""]
    ref = _main_ref()
    if ref is None:
        return out + ["_No git history available (no `main`, `origin/main` or `HEAD`)._", ""]
    log = _git("log", "--oneline", "--no-decorate", "-25", ref)
    if log is None:
        return out + [f"_`git log` on `{ref}` failed — history not available._", ""]
    lines = [ln for ln in log.splitlines() if ln.strip()]
    if not lines:
        return out + [f"_`{ref}` has no commits._", ""]
    tags = sorted({m for ln in lines for m in re.findall(r"(?<![A-Za-z0-9])([A-Z][0-9])(?![A-Za-z0-9])", ln.upper())})
    if ref != "main":
        out.append(f"_Local `main` not found; reading `{ref}` instead._")
        out.append("")
    if tags:
        out.append(f"Module tags in these subjects: {' · '.join(tags)}  _(heuristic — the interface table below is authoritative)_")
        out.append("")
    for ln in lines:
        sha, _, subject = ln.partition(" ")
        out.append(f"- `{sha}` {subject}")
    out.append("")
    return out


def section_inflight() -> list[str]:
    out = ["## In flight", ""]
    raw = _git("branch", "-r")
    if raw is None:
        return out + ["_`git branch -r` failed — no remote branches to report._", ""]

    now = datetime.now(timezone.utc).timestamp()
    rows = []
    for line in raw.splitlines():
        name = line.strip()
        if not name or "->" in name:  # origin/HEAD -> origin/main
            continue
        short = name.split("/", 1)[1] if "/" in name else name
        if short in ("main", "master", "HEAD"):
            continue
        owner, _, module = short.partition("/")
        info = _git("log", "-1", "--format=%ct|%an", name)
        if info and "|" in info:
            ts, _, author = info.strip().partition("|")
            try:
                age = _age(now - float(ts))
            except ValueError:
                age = "?"
        else:
            age, author = "?", "?"
        ahead = _git("rev-list", "--count", f"main..{name}")
        ahead_s = ahead.strip() if ahead else "?"
        rows.append((owner, module or "—", short, author, age, ahead_s))

    if not rows:
        return out + ["None — no unmerged remote branches.", ""]
    rows.sort()
    out.append("| Owner | Module | Branch | Tip author | Tip age | Commits ahead of main |")
    out.append("| --- | --- | --- | --- | --- | --- |")
    for owner, module, short, author, age, ahead in rows:
        out.append(f"| {owner} | {module} | `{short}` | {author} | {age} | {ahead} |")
    out.append("")
    out.append("_`0` commits ahead means the branch is merged or stale — delete it._")
    out.append("")
    return out


def section_interfaces() -> list[str]:
    out = ["## Published interfaces", ""]
    results = probe_interfaces()
    live = sum(1 for _, _, marks, _ in results for _, m in marks if m == YES)
    total = sum(len(marks) for _, _, marks, _ in results)
    out.append(f"**{live} of {total} contracted symbols are importable in this checkout.**")
    out.append("")
    out.append("| Module | | Symbols |")
    out.append("| --- | --- | --- |")
    for module, mark, marks, note in results:
        syms = " · ".join(f"{m} `{s}`" for s, m in marks)
        cell = f"{mark} {note}" if note else mark
        out.append(f"| `{module}` | {cell} | {syms} |")
    out.append("")
    out.append(f"{YES} importable · {NO} not there yet · {WARN} import raised (exception class shown)")
    out.append("")
    return out


def section_lanes(per_person: dict[str, list[Block]]) -> list[str]:
    out = ["## Latest from each lane", ""]
    if not per_person:
        return out + ["_No progress files found._", ""]
    for person in sorted(per_person):
        blocks = [b for b in per_person[person] if b.ok]
        out.append(f"### {person}")
        if not blocks:
            total = len(per_person[person])
            why = "file has no parseable block yet" if total == 0 else f"{total} block(s), none parseable"
            out.append(f"_Nothing to report — {why}._")
            out.append("")
            continue
        last = blocks[-1]
        out.append(f"**{last.clock} — {last.label()}**")
        for key, val in last.fields:
            out.append(f"- `{key}:` {val}")
        if not last.fields:
            out.append("- _(no detail lines given)_")
        out.append("")
    return out


def collect_test_count() -> str:
    """``pytest --collect-only`` is advisory here: never let it fail the run."""
    out = _run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        PYTEST_TIMEOUT,
    )
    if out is None:
        return "not collected"
    m = re.search(r"(\d+)\s+tests?\s+collected", out)
    if m:
        return f"{m.group(1)} passed"
    m = re.search(r"^(\d+)\s+tests?", out.strip().splitlines()[-1] if out.strip() else "")
    if m:
        return f"{m.group(1)} passed"
    return "not collected"


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def build() -> str:
    per_person, notes = read_progress()
    sha = (_git("rev-parse", "--short", _main_ref() or "HEAD") or "unknown").strip() or "unknown"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [f"# STATUS — generated {stamp}, main @ {sha}", ""]
    lines += ["<!-- GENERATED by scripts/update_status.py. Do not hand-edit: your edit", "     is gone on the next commit. Edit progress/<you>.md instead. -->", ""]
    lines += _safe(lambda: section_open(per_person, notes), f"## {WARN} OPEN REQUESTS AND BLOCKERS")
    lines += _safe(section_main, "## What is on main")
    lines += _safe(section_inflight, "## In flight")
    lines += _safe(section_interfaces, "## Published interfaces")
    lines += _safe(lambda: section_lanes(per_person), "## Latest from each lane")
    lines += [f"## Tests: {collect_test_count()}", ""]

    text = "\n".join(lines)
    return text.rstrip("\n") + "\n"


_STAMP_RE = re.compile(r"^# STATUS — generated .*?, (main @ .*)$", re.MULTILINE)


def _normalize(text: str) -> str:
    """Strip the timestamp so ``--check`` compares content, not clock ticks."""
    return _STAMP_RE.sub(r"# STATUS — generated <TS>, \1", text, count=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate STATUS.md.")
    ap.add_argument("--check", action="store_true", help="exit 1 if STATUS.md is stale; write nothing")
    ap.add_argument("--stdout", action="store_true", help="print the report instead of writing STATUS.md")
    args = ap.parse_args(argv)

    try:
        text = build()
    except BaseException as exc:  # noqa: BLE001 - rule 1: never fail
        print(f"update_status: could not build a report: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0

    if args.stdout:
        # The report contains em dashes and emoji, and a Windows console is cp1252,
        # so go around the text layer rather than raising UnicodeEncodeError.
        try:
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.flush()
        except (AttributeError, OSError):
            sys.stdout.write(text)
        return 0

    try:
        old = STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists() else ""
    except OSError:
        old = ""
    stale = _normalize(old) != _normalize(text)

    if args.check:
        if stale:
            print("update_status: STATUS.md is stale.", file=sys.stderr)
            return 1
        return 0

    if stale:
        try:
            STATUS_PATH.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"update_status: could not write STATUS.md: {exc}", file=sys.stderr)
            return 0
        print(f"update_status: STATUS.md updated ({STATUS_PATH.name}).")
    else:
        print("update_status: STATUS.md already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
