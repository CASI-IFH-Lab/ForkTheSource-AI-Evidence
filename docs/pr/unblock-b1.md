# unblock B1: priority config keys (D-009), Windows test fixes, requirements

<!-- Paste from line 5 onward as the PR body. The H1 above is the title. -->

## Module

**ID:** none — unblocking work for **B1 (#2)** and **A1 (#6)**
**Merge-queue item(s) closed:** none directly. Removes the last four blockers on
`arsha/b1-contract`.
**Owner:** Ritik

## What this changes

Four things, every one in a file I own and every one blocking Arsha's B1 branch
(`b712165`, not yet PR'd). No features. `pytest` **48 → 68**.

1. **`config.yaml` gains the four `priority.*` keys** B1 named — closes **D-009** and
   D-032's part 2.
2. **`tests/test_layout.py`'s encoding bug** — which meant the D-008 lane checks were not
   running on Windows *at all*.
3. **`tests/test_no_secrets.py`'s 6 Windows failures** — fixed *and* the guard reimplemented
   in Python so it never silently skips.
4. **`requirements.txt`** loses the bare `pytest` line, at her flag.

**Her 8 pre-existing failures are all accounted for**: 2 in `test_layout.py` (both
import-scanning tests, via `imported_modules()`) and 6 in `test_no_secrets.py`. She verified
them against a pristine `origin/main` worktree; they were mine.

## 1. The four priority keys — B1 needs no edit

```yaml
priority:
  severity: { ... unchanged ... }
  usage_base: 0.4        # floor for a reference cited by zero claims
  usage_step: 0.2        # added per citing claim; usage saturates at 3 claims
  retracted_bonus: 0.3   # flat addition when the retracted indicator is present
  cap: 1.0               # upper clamp on the final score
```

**All four are the plan's own numbers, from P6 step 2** — not chosen, and pinned by a test
exactly the way the four `thresholds` are, so retuning one requires saying so in a PR.
`severity` is untouched.

### The reader

```python
settings.priority_weights(config: dict | None = None) -> dict[str, Any]
settings.PRIORITY_SCALARS  # ("usage_base", "usage_step", "retracted_bonus", "cap")
```

Returns the four scalars as floats plus `severity` under its own key. It is a **companion
to `priority_severity()`, not a replacement** — `severity` is delegated to that function so
the map keeps one definition of its validation and float coercion, and **no existing caller
changes**. No defaults; a missing key raises `KeyError` naming **every** missing key at
once, because someone fixing `config.yaml` wants the whole list.

**B1 does not call it, and does not need to.** I checked her call site before naming
anything: `src/priority.py::_load_priority_config()` calls `settings.load_config()`, takes
`severity` through `settings.priority_severity(config)`, and reads the four scalars
**straight off `config["priority"]`**. Adding the keys is sufficient on its own.
`tests/test_config.py::test_b1s_priority_call_path_sees_all_five_keys` now *is* that call
path, so a later refactor moving the scalars behind an accessor fails in my file rather than
in hers.

### Verified end-to-end against her actual branch

In a worktree of `origin/arsha/b1-contract`, not by reasoning about it:

| | Result |
|---|---|
| **Before** my keys — her `_load_priority_config()` | fails closed: *"missing priority config keys: usage_base, usage_step, retracted_bonus, cap"* |
| **After** — same function | `{'severity': {...}, 'usage_base': 0.4, 'usage_step': 0.2, 'retracted_bonus': 0.3, 'cap': 1.0}` |
| **After** — `compute_priority(ev, v, 3)`, retracted conflict, confidence 0.9, **no `weights=`** | `1.0` — severity 1.0 × usage min(1.0, 0.4+0.2×3) × 0.9 = 0.9, +0.3 retracted, capped |
| **After** — clean verified entry, 0 citing claims | `0.0` |
| **After** — her full suite | **108 passed** |

Her default-lookup path was dead code until now; it is live and correct.

## 2. The encoding bug — the lane checks were not running on Windows

`imported_modules()` called `path.read_text()` with no encoding, so it used the locale
encoding. **Root cause confirmed, not assumed:** `app.py` contains
`page_icon="🍴"` — UTF-8 `f0 9f 8d b4` — and decoding `app.py` as cp1252 raises
`'charmap' codec can't decode byte 0x8d in position 392`, exactly the byte and exactly the
failure reported.

The consequence is worse than two failing tests. `imported_modules()` is what the lane
checks call, so **the D-008 enforcement that keeps three people out of each other's files
was silently not running on Windows.**

**I found the rest mechanically rather than by grep**, with
`PYTHONWARNDEFAULTENCODING=1 pytest -W error::EncodingWarning`. That surfaced **two sites
the grep missed**:

| Site | Defect |
|---|---|
| `tests/test_layout.py:134` | `read_text()` — the reported bug |
| `tests/test_no_secrets.py:23` | `subprocess.run(..., text=True)` — decodes with the locale encoding too |
| `tests/test_no_secrets.py:52,71,83,95` | four `write_text()` calls |

All fixed. `src/settings.py` already passed `encoding="utf-8"`;
`src/ingest/pdf_parser.py:44` is `pdfplumber.open()`, which reads a PDF and takes **no**
`encoding` at all, so demanding one would be wrong — it is exempted by name with a comment
saying why.

**Added a guard so it cannot come back:** an AST check over `src/`, `tests/`, `scripts/`,
`dashboard/`, `eval/` and `app.py` for `read_text`/`write_text`/`open` without `encoding=`,
plus `subprocess` `text=True` without it. AST rather than grep so a docstring mention is not
a finding, binary modes exempted (matching on the *mode value* — `open("y", "rb")` would
otherwise read the filename as the mode), and **armed in both directions** by two probe
tests, the same standard the lane checks are held to. Equivalent to running the suite under
`PYTHONWARNDEFAULTENCODING=1` except it runs by default and covers files no test imports.

## 3. The 6 Windows secrets failures — fixed, and the guard no longer skips

`bash` received `C:\Users\...\check_secrets.sh` and exited 127, so all six assertions read
as guard failures rather than harness failures.

**Two changes, and the second is the one that matters.**

The script is now invoked through a **relative path with `cwd` set** —
`["bash", "scripts/check_secrets.sh"]` — which sidesteps drive letters and separators
entirely, and works because the script's own first act is `cd "$(dirname "$0")/.."`. The six
shell tests carry a `skipif` with a named reason when `bash` is absent.

**But skipping alone was not acceptable.** A secrets check that skips on someone's machine
is a secrets check that is not there, and the whole reason `check_secrets.sh` exists is that
hand-catching is not a control — twice now (the key in B0, the email in D-007). So **both
scans are reimplemented in Python** and exercised against the same planted secrets. Those
tests never skip.

The Python versions mirror the shell's semantics deliberately, including the parts that look
like details:

- **Tracked files only**, via `git ls-files -z`.
- **Binary files skipped the way `grep -I` skips them** (a NUL byte means binary), so the two
  committed PDFs cannot produce a `sk-`-shaped false positive nobody can act on. There is a
  test for this.
- **The gateway host is read out of `.env.example`**, never hardcoded — **D-031**;
  hardcoding it here would put the literal in a tracked file outside the template, the exact
  thing the guard forbids. A test asserts the host parse returns something, so scan 2 cannot
  degrade to a silent no-op.

**Verified on a synthetic PATH containing only `git` and `python` — no `bash`:**

```
.ssssss........
SKIPPED [6] bash is not on PATH, so scripts/check_secrets.sh cannot be driven
            directly. The Python reimplementation in this file runs the same two
            scans and does not skip - see this module's docstring.
9 passed, 6 skipped
```

Every planted-secret case still ran.

## 4. requirements.txt

The bare `pytest` line is removed. **This is my line being pulled at Arsha's flag** — she
added `requirements-dev.txt` (`-r requirements.txt` + `pytest>=8.0`) and the rebase union
kept `pytest` in both files; it is a dev dependency and belongs in one. Her
`pydantic>=2.6,<3` is untouched (it lives on her branch).

**One thing beyond the literal instruction, because the instruction alone breaks `main`:**
`requirements-dev.txt` does not exist on `main` — it is on her branch. Removing `pytest`
without it would leave `main` in a state where a fresh clone cannot run the suite, while
`docs/setup.md` step 5 says `pip install -r requirements.txt` and step 6 runs `pytest`. So
this PR **also adds `requirements-dev.txt`, byte-identical to hers** (verified with `diff`,
so it merges without conflict), and points `docs/setup.md` step 5 and the README install
line at it. If you would rather `main` carried the removal alone and waited for B1, that is
a one-line revert.

### The merge she will face — trialled, not guessed

I ran the merge in a throwaway worktree of her branch:

- **Exactly one conflict, in `requirements.txt`**, and it is trivial. Resolution: drop
  `pytest`, keep `pydantic>=2.6,<3`.
- `requirements-dev.txt` merged **clean** (identical content).
- Everything else merged clean.
- **Combined suite after resolving: 128 passed.**

## Decisions recorded

- [ ] Decisions recorded (`docs/decisions.md` D-0NN)
- [x] **N/A — with a note.** Items 2-4 are bug fixes and establish no rule. Item 1 is
      **D-009's implementation**, not a new decision, so it opens no number.

**`docs/decisions.md` is deliberately not touched by this PR, and D-009 is not marked
resolved here.** Arsha has *already written it* on `arsha/b1-contract`: D-009's status is
set to **RESOLVED by D-032**, D-032 is added with the full reasoning, and the *Open at Sync
1* table already carries the row *"D-032, part 2 only — the four `priority.*` key names are
chosen and implemented; adding them to `config.yaml` needs Ritik, whose file it is"*.

Editing the same entry and the same table here would conflict with a 260-line diff on the
critical path — the opposite of this PR's purpose. The log becomes correct when B1 merges.

**Arsha: one line for you when you rebase** — that *Open at Sync 1* row is now satisfied, so
flip it to closed in your own diff. It is your file in your own change, so no conflict.

**Sync 1 is now two items:** **D-004** (yours — does `gate.py` want a model?) and **D-020**
(mine — P5's preprint test).

## Project ground rules

- [x] No model name anywhere in `src/`. `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/` → exit 1, no output.
- [x] `./scripts/check_secrets.sh` passes (pytest runs it too — now via two independent implementations).
- [x] `.env` is untracked and `git status` does not list it.
- [x] Model names read via `src.settings.model_for(stage)` — unchanged.
- [x] Every model reply validated against a schema — N/A, no model calls in this PR.
- [x] `pytest` passes, **and the count went up**: 48 → 68.

## How I tested

```
$ pytest                                    # BEFORE
48 passed

$ pytest                                    # AFTER
collected 68 items

tests/test_app.py ...                                                    [  4%]
tests/test_config.py ........................                            [ 39%]
tests/test_intake.py ......                                              [ 48%]
tests/test_layout.py ....................                                [ 77%]
tests/test_no_secrets.py ...............                                 [100%]

============================== 68 passed in 1.52s ==============================

$ ./scripts/check_secrets.sh
check_secrets: PASS

$ grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/ ; echo $?
1

$ PYTHONWARNDEFAULTENCODING=1 pytest -W error::EncodingWarning -q
68 passed          # independent confirmation: no implicit text encodings remain
```

| File | Was | Now | Change |
|------|-----|-----|--------|
| `tests/test_config.py` | 15 | **24** | +9 — four values pinned, a missing-key raise per scalar, all-keys-at-once, whole-block-missing, B1's call path, `priority_severity` signature |
| `tests/test_layout.py` | 17 | **20** | +3 — the encoding guard and its two probes (the `read_text` fix itself adds none) |
| `tests/test_no_secrets.py` | 7 | **15** | +8 — the Python reimplementation of both scans, plus binary-skip and host-parse coverage |
| `tests/test_app.py` | 3 | 3 | — |
| `tests/test_intake.py` | 6 | 6 | — |
| **Total** | **48** | **68** | **+20** |

### Windows verification — read this line

**The encoding fix is NOT verified on Windows.** I have no Windows runner and no cp1252
locale on macOS. What *is* verified here:

- The **root cause**, precisely: decoding `app.py` as cp1252 raises at byte `0x8d`,
  offset 392 — the byte and offset Arsha reported.
- That **no implicit text encoding remains** anywhere the suite touches, by the
  `PYTHONWARNDEFAULTENCODING=1 -W error::EncodingWarning` sweep, which is the same
  mechanism a cp1252 machine would trip.
- That the **bash-absent path** behaves correctly, on a synthetic PATH with no bash.

**Arsha needs to confirm all 8 failures are gone on her machine.** The mechanism is
understood and mechanically swept, but "understood" is not "observed on the platform".

## Eval output

- [x] N/A — R2 is not merged yet.

## Statuses and indicators touched

None classified here. `config.yaml`'s `priority.severity` is keyed by the four contract
statuses, unchanged.

## What this unblocks

**B1 (#2, Arsha)** — the last blocker in my files is gone, and her default priority path is
live. **A1 (#6, Arsha)** follows B1.

## Reviewer's guide — 10 minutes

Merged without review: it exists purely to remove obstacles from someone else's path.

1. **`config.yaml`'s `priority:` block** — four numbers. If any is wrong, everything
   downstream of the worklist ordering is wrong.
2. **`src/settings.py: priority_weights()`** — ~30 lines. Confirm it is a companion to
   `priority_severity()` and that nothing about your call path changed.
3. **`tests/test_no_secrets.py`'s module docstring** — why there are two implementations of
   the same two scans.
4. **The Windows-verification note above.**

**Skim or skip:** the AST guard internals, `docs/config_reference.md`, the setup/README
install lines.

## Anything I was unsure about

- **Adding `requirements-dev.txt` here** goes beyond "remove the bare pytest line", and I
  did it because the removal alone leaves `main` unable to run its own documented test step.
  Byte-identical to hers, so it merges clean. Easy to revert if you would rather wait.
- **Not touching `docs/decisions.md`** is a judgment call against the letter of the brief,
  made because Arsha has already written that exact update and duplicating it would conflict
  on the critical path. The one-line follow-up is named above.
- **The encoding guard is a new test, in a PR that says "no features".** I judged a
  regression guard for the bug being fixed to be part of the fix, not a feature — this bug
  was invisible on my machine and cost someone else eight failures, which is the worst shape
  a defect can have. If you disagree, deleting the three tests leaves the fix intact.
- **`priority_weights()` has no caller yet.** P6 will be the first; B1 reads the block
  directly. It exists so P6 does not re-derive validation, and it is what pins the four
  values in a test.
