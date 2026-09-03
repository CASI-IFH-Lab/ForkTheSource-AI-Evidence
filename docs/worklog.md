# Worklog

What **happened**, session by session, chronological. Not what was decided — decisions live
in [decisions.md](decisions.md) with stable D-numbers, and this file cites them rather than
restating them.

The point of this file is the failures. What was built is visible in the tree; what went
wrong, and what it cost, is not, and it is the part that stops the same hour being lost
twice.

**Sourcing rule.** Every claim here is traceable to a commit, a command output, or a
document in the tree, and the source is named. Where something cannot be sourced it says
**not verified** rather than being reconstructed from memory. Two branches were
squash-merged and deleted, so their intermediate commits no longer exist — several session 1
and 2 details are sourced to `docs/pr/B0.md` (written while they were live) rather than to a
diff, and that is called out where it applies.

All timestamps are from `git reflog --date=format:"%Y-%m-%d %H:%M"` on the local clone.

---

## Session 1 — M0 skeleton

**2026-09-02, 21:51 → 22:53. Branch `ritik/m0-skeleton`, off `main` at `ffd0180`.**

### What was built

| Commit | Time | What |
|--------|------|------|
| `ffd0180` | 21:51 | `initial fodler structure` — `main`'s first and, until session 4, only commit. Seven files: `.env.example`, `.gitignore`, `README.md`, `config.yaml`, `requirements.txt`, `src/__init__.py`, `tests/__init__.py`. Verified: `git ls-tree -r --name-only ffd0180`. |
| `4328eb7` | 22:53 | `M0: Streamlit skeleton with the seven-stage pipeline scaffolded` — the Streamlit shell, `pdfplumber` intake, and `src/pipeline/` as a package containing seven stage modules. |

A working app at the end of it: `streamlit run app.py`, drop a PDF, see the raw text
pdfplumber reads out of it.

**Test count: 29.** Not verified from the tree — `4328eb7` is no longer reachable as a
distinct commit after the squash merge. Sourced to the test-count table in
`docs/pr/B0.md`, whose arithmetic is self-consistent with the 39 that `main` carries today
(29 − 15 + 11 + 7 + 7 = 39).

### What went wrong: `.env.example` disappeared

`.env.example` vanished from the working tree mid-session. It was **originally blamed on
`mv`** — the file was believed to have been moved or overwritten during a restructure, and
the session spent time reconstructing it on that assumption.

That diagnosis was wrong. The actual cause was **Dropbox**: the clone lived inside a
Dropbox-synced folder, and Dropbox was restoring and removing files underneath git. The
confirmation came in session 2, when the same mechanism did something unmistakable — see
below. `.env.example` is present in `ffd0180` (verified above), which is consistent with
the file never having been deleted in git's view at all.

**Cost:** debugging time spent on a `mv` that had not happened, and a wrong root cause
carried into the next session.

**Resolution, session 4:** the clone was moved out of Dropbox entirely, to
`/Users/ritik/Documents/Projects/CASI Hackathon/ForkTheSource-AI-Evidence`.

---

## Session 2 — the five B0 docs, then the correction pass

**2026-09-03, 00:04 → 00:34. Branch `ritik/m0-skeleton`.**

Two halves, and the second reversed a good deal of the first.

### First half: five docs written against an inferred mapping

| Commit | Time | What |
|--------|------|------|
| `4eb1b58` | 00:04 | `docs(B0): module status, setup, config reference, stage map, PR template` |
| `76e8c36` | 00:06 | `docs(B0): correct the minimum Python version in setup.md` |

The Module Implementation Plan **was not in the repo**. The five docs were therefore
written against a module mapping inferred from the working title and the skeleton's file
names, and the inference was wrong in four ways: P3 and P4 merged into one resolver stage,
P4 mistaken for the judge, the judge placed in Ritik's lane rather than Arsha's, and A1
described as a critic — a stage the plan does not contain.

**Cost:** all five docs were rewritten later in the same session. See **D-001**; the fix was
to commit the plan at `docs/module_implementation_plan.pdf` and make it ground truth.

### Second half: the layout realignment and the config pass

| Commit | Time | What |
|--------|------|------|
| `1c0de13` | 00:25 | `refactor(B0): align file layout to the plan, add a secrets guard` |
| `c83f17f` | 00:27 | `config(B2): close the gaps the B0 pass found, drop the critic keys` |
| `5f7cf6f` | 00:34 | `docs(B0): rewrite against the real plan; land the plan PDF in the repo` |

`src/pipeline/` was dismantled as a package and its contents redistributed into
`src/ingest/`, `src/resolvers/` and `src/matching/`, with `src/pipeline.py` left reserved as
a file for P6 (**D-002**). `src/config.py` became `src/settings.py` (**D-003**). The two
repro stages were deleted and recorded in `docs/descoped.md` (**D-005**). `models.critic`
and `critic_temperature` were dropped from `config.yaml` (**D-004**).

### What went wrong: Dropbox restored git-deleted files mid-operation

During the layout work, `git rm` removed `src/pipeline/` and all six of its stage files.
**Dropbox restored the directory and every one of those files**, with `drwx------`
permissions.

This is the same mechanism as session 1's `.env.example` disappearance, running in the other
direction, and it is what identified the real cause retrospectively. Git's index was correct
throughout and the resulting commit is clean — the damage was to the working tree and to the
session's confidence in it.

**Cost:** the deletion had to be verified against the index rather than the filesystem, and
session 1's root-cause analysis had to be thrown out. Recorded at the time in
`docs/pr/B0.md` flag 2, which recommended either pausing sync while working or moving the
clone out of Dropbox.

**Resolution, session 4:** the clone was moved. `docs/pr/B0.md` flag 2 is now marked
resolved.

### Test count: 29 → 39, and fifteen tests were deliberately removed

Sourced to the test-count table in `docs/pr/B0.md`. The 39 is verified directly on `main`
(below); the four deltas are not independently verifiable post-squash.

| Change | Count | What the tests were enforcing |
|--------|-------|-------------------------------|
| **removed** `tests/test_pipeline_contract.py` | **−15** | A uniform seven-stage `run(payload, config)` walk over a `STAGES` tuple. **This is not the project's architecture** — the plan has an orchestrator calling named functions across three packages, each with its own narrow interface. Fifteen *green* tests were holding the wrong contract in place, which is worse than fifteen red ones: they were actively defending the inferred design against correction. |
| **added** `tests/test_layout.py` | **+11** | That the three packages exist and import; that `src/contract.py` does not exist yet; that `src/pipeline.py` stays reserved; and that nothing under `src/` imports `src/judge` or `dashboard`. Import checks parse the AST, so a docstring mentioning `dashboard/app.py` is not mistaken for a dependency. |
| **added** `tests/test_no_secrets.py` | **+7** | The secrets guard — including proof it catches a *planted* key and a hardcoded gateway host, not merely that it passes on a clean tree. |
| **added** to `tests/test_config.py` | **+7** | The new config keys, plus assertions that the dropped critic keys stay dropped (**D-004**). |

Net coverage loss, stated honestly in the PR body: nothing now checks that every future
stage module exposes a uniform entry point — because they are not supposed to.

### The AIR key was verified live

The read-only model listing against the gateway returned the model catalogue, with no
`AuthenticationError`. This was the plan's hour 0-1 item *"keys verified (AIR is alive)"*.

Sourced to the definition-of-done section of `docs/pr/B0.md`. **Not re-verified in session
3 or 4** — no gateway call has been made since, and none of the code on `main` calls a model.

### The near-miss: sixteen characters of a live key, nearly committed

`scripts/check_secrets.sh` was not planned. It was written in reaction.

While drafting `docs/config_reference.md`, a worked example of what an `AIR_API_KEY` value
looks like was written using **the first 16 characters of the real, live key** — into a
tracked markdown file, in a repo with a remote, on a branch that was about to be pushed.

It was caught before the commit. Nothing was pushed, and the key was not rotated because it
was never committed. But the margin was one `git add` and the reason it was caught was
attention, which is not a control.

Two things came out of it, both on `main` now:

1. **`scripts/check_secrets.sh`** — scans tracked files for key-shaped literals (`sk-`
   followed by 8+ key characters) and for the gateway host appearing anywhere outside
   `.env.example`. It reads the expected host **out of `.env.example`** rather than
   hardcoding it, because hardcoding the host would put that literal into a tracked file
   outside `.env.example` — the exact thing the script exists to forbid.
2. **`tests/test_no_secrets.py`** — wires the script into `pytest`, and asserts it *catches*
   a planted key, so the guard cannot rot into a script that always passes.

The script's own header carries the operational rule: if it ever fires on a real key,
**rotate in Voyager immediately**. Deleting the commit is not the fix — assume the key is
burned.

**This is the most useful line in this file.** The mechanism that nearly leaked the key was
not carelessness with credentials; it was *writing documentation*, using a real value
because a realistic example is more useful than a fake one. That impulse is correct and it
will recur, in this repo and every other. The control is mechanical or it is nothing.

**Traceability:** the guard and its tests are verifiable on `main` (`scripts/check_secrets.sh`,
`tests/test_no_secrets.py`, 7 tests). The near-miss itself left **no artifact in the tree**,
by definition — it is recorded here because it happened, and **not verified** from any commit.

---

## Session 3 — B3, in Roy's absence

**2026-09-03, 00:43 → 01:10. Branch `ritik/b3-label-format`, off `main` at `ffd0180`.**

| Commit | Time | What |
|--------|------|------|
| `f5602a3` | 00:51 | `docs(B3): golden-label format and defect catalog` — the format as specified, with nine open ambiguities. |
| `1d744e0` | 01:10 | `docs(B3): apply the eight rulings, extend the schema` |

Four files, all new: `eval/golden/FORMAT.md` (400 lines), `eval/golden/EXAMPLE.json`
(91 lines), `docs/defect_catalog.md`, `docs/pr/B3.md`. This put `eval/` into git for the
first time — it had been an empty directory, which git cannot track.

Written as a handoff document to someone else. Every injection method is instructions to a
third party, paper and `ref_id` cells are `TBD`, and no paper titles are invented, because
paper selection is R1's first step and belongs to whoever performs it.

### The 21-vs-23 discovery

The plan says "~21 defects across three papers". Writing the distribution table made it
clear that **21 and 23 are different numbers and the format could not express both**: a
duplicate-entry defect is by definition **two** bibliography rows, so label rows exceed
injections by two.

Left alone, this breaks recall silently. The denominator is 21 but the file has 23
`injected: true` rows, so any row-based count is wrong, and — worse — a pipeline that caught
one row of a duplicate pair and missed the other would be credited with half a detection for
an answer that is entirely wrong.

Fixed by adding a **`defect_id`** field: 21 ids, 23 rows, rows of a multi-row defect share
one id, recall measured over ids, and **an id matches only when all of its rows match**.
Ids assigned in the catalog immediately, before paper selection, so they never shift. See
**D-016**.

This was found by the validation checklist, not by review.

### The hand-validation checklist grew 9 → 13 items

Written as nine items; ended at **13** (verified: `eval/golden/FORMAT.md`, items 1-13 under
*Validation checklist for a hand-written label file*). It earned its keep immediately by
catching two real spec bugs on its first run against `EXAMPLE.json`:

1. **The specimen's filename stem did not match its `document` field** — which would have
   made R2 fail on a human-written label file. Item 1 now checks it, with `EXAMPLE.json`
   explicitly exempted as a documented specimen.
2. **The 21-vs-23 count**, above — no validation step could then satisfy it, which is how
   the gap surfaced. Item 9 now checks `defect_id` uniqueness with the documented exception
   for shared ids.

The last four items came from the rulings rather than from the schema: item 11 (the control
has zero injections), item 12 (every clean `unresolvable` has a recorded reason), and item 13
(each spiked paper retains a genuine `unresolvable`, from **D-018**).

### Six of the nine defect types did not map cleanly onto the closed vocabulary

This was the session's main finding, and it is a property of the contract rather than a
mistake in the catalog. The status vocabulary has four values and the indicator vocabulary
has six, and it is **closed and frozen at Sync 1**.

- **Three defect types have no indicator at all** and take `[]`: hallucinated reference
  (**D-018**), wrong year (**D-011**), and mangled author list (**D-015**). There is no
  indicator for a year mismatch and none for an author mismatch. Both gaps are documented as
  limitations rather than patched with an invention, because a vocabulary that grows whenever
  a defect does not fit is not closed — and the freeze is what lets R2 compare indicator
  arrays as exact sets.
- **Three more mapped to an indicator but not to an obvious status**: orphan (**D-017**),
  malformed (**D-012**), and the preprint/journal pair (**D-013**). Each needed a ruling on
  which of the four statuses is true, and in the malformed case the plan appeared to
  contradict itself until the two rules were separated — P5's line governs status from
  evidence, A1's governs confidence direction, and they never meet.
- **Three mapped cleanly and needed no ruling**: swapped DOI, duplicate entry, and citation
  to a retracted paper. The catalog marks the first and last "unchanged and unambiguous".

Nine rulings in total (the eight above plus the false-accusation definition, **D-019**), all
recorded as D-011 through D-019.

### What was left open

One item, and it constrains unwritten code: what makes `version_mismatch` fire. Session 3
ruled that it must require **venue divergence**. Session 4 reversed that — see below and
**D-020**.

---

## Session 4 — the Dropbox relocation, B0 and B3 to `main`, the decision log

**2026-09-03, from ~01:36. This session.**

### The relocation

Pre-move gates, all checked before anything moved:

| Gate | Result |
|------|--------|
| `git status` clean on both branches | Clean. Only untracked file: `ForkTheSource-AI-Evidence.code-workspace`, added by the editor. |
| Both branches fully pushed | `ritik/m0-skeleton` `5f7cf6f` == `origin/…`; `ritik/b3-label-format` `1d744e0` == `origin/…`. Verified against `git ls-remote --heads origin`. |
| `git stash list` empty | Empty. |
| No Streamlit server holding a file handle | No process; port 8501 clear. A stale `st.pid` remained in the old session's scratchpad — the pid file outlived the process. |

**Old path:** `/Users/ritik/Library/CloudStorage/Dropbox-ASU/Ritik Agarwal/Hackathon_CASI/ForkTheSource-AI-Evidence`
**New path:** `/Users/ritik/Documents/Projects/CASI Hackathon/ForkTheSource-AI-Evidence`

The move itself was performed outside this session and confirmed on arrival. The old parent
directory now contains **only a `.DS_Store`** — no `.git`, no `.env`, no `cache/`. Verified
by `ls -la` and by a `find` for `*ForkTheSource*` under the whole Dropbox tree, which
returned no remnant.

### The venv had to be rebuilt, and pip fought back

`.venv` stores absolute paths and was dead on arrival. `pyvenv.cfg` still read:

```
command = /opt/homebrew/opt/python@3.13/bin/python3.13 -m venv /Users/ritik/Library/CloudStorage/Dropbox-ASU/Ritik Agarwal/Hackathon_CASI/ForkTheSource-AI-Evidence/.venv
```

Deleted and recreated: Python 3.13.7, all seven requirements installed
(streamlit 1.63.0, pdfplumber 0.11.10, openai 3.7.0, python-dotenv 1.2.3, PyYAML 6.0.3,
requests 2.34.2, pytest 9.1.1).

**What went wrong:** the install took over seven minutes and looked hung. Cause was not the
move. `~/.pip/pip.conf` and `~/.config/pip/pip.conf` — both written by NVIDIA PyIndex —
carry `extra-index-url = https://pypi.ngc.nvidia.com`, which no longer resolves
(`NameResolutionError`). Every package was retried five times against the dead host before
falling through to PyPI. The install **did** succeed, exit code 0.

**Cost:** roughly seven minutes, and a false suspicion that the relocation had broken the
environment. **Not fixed** — the pip config is global to the machine and outside this repo,
so it was left alone rather than edited as a side effect of a repo task. It will slow every
`pip install` on this machine until someone removes the extra index. Worth five minutes of
Ritik's time, separately.

### Post-move verification

Everything below was run from the new path.

```
$ git status                     -> clean, on ritik/m0-skeleton
$ git log --oneline -3           -> 5f7cf6f, c83f17f, 1c0de13 (unchanged)
$ git remote -v                  -> origin https://github.com/CASI-IFH-Lab/ForkTheSource-AI-Evidence.git
$ git check-ignore -v .env       -> .gitignore:1:.env
$ ls -la .env .env.example       -> both present
$ pytest                         -> 39 passed in 2.02s
$ ./scripts/check_secrets.sh     -> check_secrets: PASS
```

### `gh` was already installed

The brief for this session recorded `gh` as not installed. It is: **gh 2.99.0**, authenticated
as `ritwiz06`, token scopes `gist, read:org, repo, workflow`, `viewerPermission: WRITE` on
`CASI-IFH-Lab/ForkTheSource-AI-Evidence`. No `brew install` and no interactive `gh auth
login` were needed. The browser fallback route was not used, though both PR bodies exist as
files in `docs/pr/` either way.

### The three merges

| # | PR | Title | `main` after |
|---|----|-------|--------------|
| 1 | [#1](https://github.com/CASI-IFH-Lab/ForkTheSource-AI-Evidence/pull/1) | `B0: app skeleton + B2 config (merge-queue #1 and #3)` | `ffd0180` → **`a579dab`** |
| 2 | [#2](https://github.com/CASI-IFH-Lab/ForkTheSource-AI-Evidence/pull/2) | `B3: golden-label format + defect catalog (merge-queue #4)` | `a579dab` → **`04b8ffe`** |
| 3 | #3 | `docs: decision log + worklog` | `04b8ffe` → *(this PR)* |

All three squash-merged, remote branch deleted, `main` pulled and re-verified after each.

**B0** gained one commit before the PR opened (`e4c24a7`): the deliberate-self-merge note in
`docs/pr/B0.md`, and flag 2 marked resolved now that the clone is out of Dropbox. It was
merged **without Arsha's review** — she had not started, and B1, B3, P1 and R1 all unblock on
it. Logged as a deliberate deviation, **D-021**, not an oversight.

**B3** branched off `ffd0180`, so `main` was merged into it first (`0767d6a`). **Zero
conflicts**, as predicted but verified rather than assumed: `comm -12` on the two changed-file
lists returned empty — B3's four files and B0's twenty-seven are disjoint sets.
`git diff --name-only --diff-filter=U` after the merge returned nothing.

Two further commits landed on B3 before the PR:

- `d48ae8e` — **the version_mismatch reversal (D-020)** and the originals note. Session 3's
  venue-divergence ruling was overturned: venue strings are the least normalised field in a
  bibliography, so string inequality would fire the indicator on correctly-cited references
  including the clean control, and a similarity test has no threshold in `config.yaml` to tune
  against. The indicator now fires when **exactly one record is a preprint**. Every label is
  identical under either formulation. Also recorded that `eval/corpus/originals/` stays
  **tracked** — R1 diffs against the originals and R2 may check `origin_file` exists, so
  gitignoring them makes that check pass on the labeller's machine and fail on every clone —
  with a ~10 MB escape hatch (store an arXiv ID plus a fetch script instead of the PDF).
- `52acf41` — `docs/pr/B3.md` rewritten. The old body led with `version_mismatch` as an
  unresolved action item and framed the categorical test as a recommendation *against* the
  ruling; D-020 settled it the other way.

### One discrepancy found against the brief

The session brief described B3 as having **four** ambiguities. The tree has **nine**, and all
nine are ruled on — `eval/golden/FORMAT.md` § Rulings lists them 1-9, and
`docs/defect_catalog.md` says "all nine ambiguities from the first pass have been ruled on"
in two places. Written as nine, with the discrepancy noted in the PR body rather than
silently reconciled.

### The decision log

`docs/decisions.md` — 21 entries, D-001 to D-021, newest first, with an "Open at Sync 1"
section listing the four unresolved ones (D-004, D-008, D-009, D-020) and a note that D-007
is decided but unimplemented.

Two things the backfill surfaced that the tree contradicts, both recorded in the entries
rather than papered over:

1. **D-007 is not implemented.** `resolvers.mailto` was to move to `.env` as
   `CROSSREF_MAILTO`. `config.yaml:17` still carries `mailto: your-asurite@asu.edu`,
   `tests/test_config.py:68` still asserts `"@" in config["mailto"]`, and
   `docs/config_reference.md` still documents it as a config key. Not fixed in this PR —
   this PR is docs-only by instruction and that change touches `config.yaml`, `src/` and
   `tests/`.
2. **D-008's open item is worse than described.** The concern was that the plan's lane rule
   would forbid A1 importing `src.llm.get_client()`. In fact `tests/test_layout.py` does not
   check `src.llm` at all — its forbidden list is `src.judge.*` and `dashboard.*` — so that
   import passes today. The real bug is that the check walks **every** file under `src/`, so
   the moment `src/judge/agent.py` exists and imports `src/judge/prompts.py`, the test will
   flag **Arsha's own intra-package import** as a lane violation. She hits it on her first A1
   commit, not at review.

### `docs/module_status.md` updated to post-merge reality

Its header said `main` is at `ffd0180` and its status column put B0, B2 and B3 "on a branch".
All three are now **on `main`**. Corrected in this PR.

---

## Standing facts, as of the end of session 4

| | |
|---|---|
| Repo path | `/Users/ritik/Documents/Projects/CASI Hackathon/ForkTheSource-AI-Evidence` |
| Old Dropbox path | Empty but for a `.DS_Store`. Verified. |
| `main` | `04b8ffe` before PR #3 |
| Tests on `main` | 39 passed |
| `check_secrets.sh` on `main` | PASS |
| On `main` | B0, B2, B3 |
| Not started | B1 (critical path, Arsha), P1-P6, A1-A3, R1-R4 |
| Open decisions | D-004, D-008, D-009, D-020 |
| Implementation debt | D-007 |
