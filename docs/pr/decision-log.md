# docs: decision log + worklog

<!-- Paste from line 5 onward as the PR body. The H1 above is the title. -->

## Module

**ID:** none — project documentation
**Merge-queue item(s) closed:** none. This is not a plan module; it is the record-keeping
the plan's PR template now requires.
**Owner:** Ritik

## What this changes

Two new documents and four files wired to them. `docs/decisions.md` holds every decision
that constrains someone else's module, with stable D-numbers (**D-001** to **D-021**) that
PR bodies, cards and other docs can cite. `docs/worklog.md` records what actually happened
per session — including what went wrong and what it cost — as distinct from what was
decided.

The reason both exist is the same reason A3 is one line of wiring: on a three-lane build,
the expensive failure is not a wrong decision, it is a decision nobody can find, made by one
person, discovered by another as a broken assumption two modules later.

Docs only. **No change under `src/`, `tests/` or `config.yaml`** — verified below.

## The standing rule this establishes

> **Any decision that constrains another person's module, or that departs from the Module
> Implementation Plan, gets an entry in `docs/decisions.md` BEFORE the PR that implements it
> is opened.**

`.github/pull_request_template.md` gains a checkbox for it. **A PR that establishes a rule
and does not log it is incomplete**, and "N/A" is a fine answer for a PR that establishes
nothing.

## What the decision log contains

Twenty-one entries, newest first. Each carries date, decider, status, the modules and paths
it affects, the rule, the reasoning **in prose including the rejected alternative**, and the
obligation it creates and on whom.

**Four are open, and they are the entire Sync 1 agenda:**

| ID | One line | Whose call |
|----|----------|-----------|
| **D-004** | Does `gate.py` want a model of its own? `models.critic` / `critic_temperature` were removed. | Arsha |
| **D-008** | `tests/test_layout.py` must be amended before A1 lands. | Arsha + Ritik |
| **D-009** | The priority formula lives in `src/priority.py`, shared infra, shipping with B1. | Arsha |
| **D-020** | `version_mismatch` fires on preprint-ness, not venue divergence. Constrains P5 step 2. | Ritik |

**Three entries are reversals**, and they are deliberately the most detailed in the file,
because a reversal marks the difference between a preference and load-bearing reasoning:

- **D-020** — the venue-divergence ruling overturned. Venue strings are the least normalised
  field in a bibliography, so string inequality would fire the indicator on correctly-cited
  references including the clean control, whose false-accusation count must be zero; and a
  similarity test has no threshold in `config.yaml` to tune against.
- **D-006** — a test that would fail until `src/contract.py` existed was written, then
  removed. It would have made Arsha's first experience of the repo a red suite she did not
  cause, whose easiest resolution is deleting the assertion. **Do not use a failing test as
  a to-do list for another person.**
- **D-003** — `src/config.py` → `src/settings.py`, establishing that **the plan beats the
  brief**, because briefs are written from memory and the plan is a committed artifact.

## Two things the backfill surfaced that the tree contradicts

Both are recorded in the entries rather than quietly reconciled, and neither is fixed here
because both need files this PR is not permitted to touch.

1. **D-007 is decided but NOT implemented.** `resolvers.mailto` was to move to `.env` as
   `CROSSREF_MAILTO`, with P4 refusing to start when unset. `config.yaml:17` still carries
   `mailto: your-asurite@asu.edu`, `tests/test_config.py:68` still asserts
   `"@" in config["mailto"]`, and `docs/config_reference.md` still documents it as a config
   key. It needs one PR touching `config.yaml`, `.env.example`, `src/settings.py`,
   `tests/test_config.py` and two docs. Called out in the *Open at Sync 1* section as
   implementation debt so it is not lost.
2. **D-008's open item is worse than it was described.** The stated concern was that the
   lane rule would forbid A1 importing `src.llm.get_client()`. In fact `tests/test_layout.py`
   does not check `src.llm` at all — its forbidden list is `src.judge.*` and `dashboard.*` —
   so that import passes today; the conflict is with the plan's *prose*. The real bug is
   that the check walks **every** file under `src/`, so the moment `src/judge/agent.py`
   exists and imports `src/judge/prompts.py`, the test flags **Arsha's own intra-package
   import** as a lane violation. She hits it on her first A1 commit, not at review.

## What the worklog contains

Four sessions, chronological, every claim sourced to a commit or command output, with
**"not verified"** written where a claim cannot be sourced — which matters here because both
feature branches were squash-merged, so their intermediate commits no longer exist.

The failures are the point of the file:

- **Session 1** — `.env.example` disappeared and was blamed on `mv`. Wrong diagnosis; the
  cause was Dropbox restoring and removing files underneath git. Confirmed in session 2 when
  Dropbox restored `src/pipeline/` and all six files after `git rm` deleted them, with
  `drwx------` permissions.
- **Session 2** — five docs written against an inferred module mapping and rewritten the
  same session (**D-001**); 15 green tests removed because they were enforcing the wrong
  architecture; **and the near-miss**: the first 16 characters of the live AIR key were
  nearly committed into `docs/config_reference.md` as a worked example. Caught before the
  commit, nothing pushed, key not burned. `scripts/check_secrets.sh` and
  `tests/test_no_secrets.py` exist because of it. That entry is the most useful line in the
  file, because the mechanism was not carelessness with credentials — it was *writing
  documentation*, using a real value because a realistic example is more useful than a fake
  one. That impulse will recur. The control is mechanical or it is nothing.
- **Session 3** — the 21-vs-23 discovery, found by the validation checklist rather than by
  review; the checklist growing 9 → 13 items; and six of the nine defect types not mapping
  cleanly onto the closed vocabulary.
- **Session 4** — the Dropbox relocation, the venv rebuild, and the three merges with SHAs.

## Definition of done

- [x] **`docs/decisions.md` exists**, 21 entries D-001 to D-021, newest first, stable IDs.
      Evidence: `grep -c "^## D-0" docs/decisions.md` → `21`.
- [x] **Every entry has Date, Decided by, Status, Affects, Decision, Why, Consequence**, with
      Why in prose and naming the rejected alternative.
- [x] **An "Open at Sync 1" section at the top listing only the open entries** — D-004,
      D-008, D-009, D-020 — plus a separate one-line note that D-007 is implementation debt
      rather than an open question.
- [x] **The standing rule is stated in the header.**
- [x] **Reversals recorded as reversals** — D-020, D-006, D-003.
- [x] **`docs/worklog.md` exists**, four sessions, chronological, every claim sourced and
      "not verified" written where it cannot be.
- [x] **Both files in the README docs index.** Evidence: `README.md` § Docs, plus
      `docs/defect_catalog.md` and `eval/golden/FORMAT.md`, which were missing from it.
- [x] **`.github/pull_request_template.md` gains a Decisions-recorded section** with a
      D-number line and an N/A box.
- [x] **D-number pointers in `docs/module_status.md`, `docs/architecture_map.md` and
      `eval/golden/FORMAT.md`.** All nine rulings in FORMAT.md's table now cite D-011-D-019.
- [x] **`docs/module_status.md` reflects post-merge reality** — B0, B2 and B3 are **ON
      `main`**, not on a branch; header updated from `ffd0180` to `04b8ffe`; the "right now"
      row of the timing table rewritten; the file-ownership table restructured into D-008's
      three tiers.
- [x] **Docs only — no change under `src/`, `tests/` or `config.yaml`.** Evidence:
      `git diff --name-only` lists exactly five modified files, none of them under `src/` or
      `tests/`.
- [x] **`pytest` green: 39 passed.** Unchanged, correctly — this PR adds no behaviour.
- [x] **`./scripts/check_secrets.sh` → PASS.**
- [x] **No model name in `src/`** → exit 1, no output.

## Project ground rules

- [x] No model name anywhere in `src/`. `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/` finds nothing.
- [x] `./scripts/check_secrets.sh` passes (pytest runs it too).
- [x] `.env` is untracked and `git status` does not list it.
- [x] Model names read via `src.settings.model_for(stage)` — N/A, no code in this PR.
- [x] Every model reply validated against a schema — N/A, no model calls in this PR.
- [x] `pytest` passes. The count is unchanged at 39, which is correct: no behaviour added.

## Decisions recorded

- [x] Decisions recorded (`docs/decisions.md` D-0NN): **this PR creates D-001 through
      D-021.** It establishes one new rule of its own — the standing rule in the header — and
      that rule is the file's own subject.
- [ ] N/A

## How I tested

```
$ git diff --name-only
.github/pull_request_template.md
README.md
docs/architecture_map.md
docs/module_status.md
eval/golden/FORMAT.md

$ pytest
collected 39 items
============================== 39 passed in 0.86s ==============================

$ ./scripts/check_secrets.sh
check_secrets: PASS

$ grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/ ; echo $?
1

$ grep -c "^## D-0" docs/decisions.md
21
```

**One deliberate deviation from the brief for this PR.** The brief said "docs only, no
change under `src/`, `tests/`, `eval/` or `config.yaml`", and also required a one-line
pointer in `eval/golden/FORMAT.md`. Those conflict. The specific instruction was followed:
`eval/golden/FORMAT.md` is modified, and only to add the pointer blockquote and the
D-numbers in its rulings table — no label, field, rule or expected value is touched. Nothing
else under `eval/` is changed.

## Eval output

- [x] N/A — R2 is not merged yet.

## Statuses and indicators touched

None. No code in this PR classifies anything. `docs/decisions.md` quotes the four statuses
and six indicators inside entries D-011 to D-020 as specification text only.

## What this unblocks

Nothing mechanically — no module has a code dependency on a doc. What it does is make Sync 1
runnable: the agenda is the *Open at Sync 1* table, four items, readable in ten seconds,
each with the reasoning already written down so the meeting is a decision rather than a
re-derivation.

It also gives **Arsha** the three things she needs before B1 and A1: **D-009** (B1 also
carries `src/priority.py`), **D-008** (`tests/test_layout.py` breaks on her first A1 commit
unless amended), and **D-004** (`gate.py` is three code checks unless she decides otherwise).

## Reviewer's guide — 10 minutes

Docs only, so this is a read rather than a review.

1. **`docs/decisions.md` § Open at Sync 1** — four rows. If you disagree with any of them,
   that is the meeting.
2. **The three reversals: D-020, D-006, D-003.** These are the entries that mark which parts
   of the tree are load-bearing reasoning rather than preference. If any of them is wrong,
   something downstream is wrong.
3. **D-007 and D-008's *Consequence* paragraphs** — the two places the log contradicts the
   tree. Both are real and neither is fixed here.
4. **`docs/worklog.md` § Session 2, "The near-miss"** — one paragraph, and the reason
   `check_secrets.sh` exists.

**Skim or skip:** the D-011-D-019 entries if you already read the B3 PR (they are its nine
rulings with fuller reasoning), the index table, and the README/template diffs.

## Anything I was unsure about

- **The backfill was reconstructed from memory and I was asked to find what it missed.** Two
  candidate decisions in the tree have no entry and no explicit instruction to add one, so
  they are reported rather than assigned a D-number unilaterally — the `defect_id` schema
  extension (four fields beyond the plan's example, which R1 writes 23 rows against), and
  the choice to keep `app.py`'s `AppTest` coverage as B0's definition of done. Both are in
  the session report; either can become D-022 and D-023 on a one-line say-so.
- **Dates.** Every entry is dated from the reflog rather than from recollection, which puts
  D-001 through D-019 on 2026-09-03 even though session 1 ran on 09-02. The reflog is the
  only source in the tree and it is what it says.
- **`docs/decisions.md` is in nobody's lane.** `docs/` beyond the B0 docs is Roy's per the
  ownership table, but this file is project-wide rather than R-lane. Treated as shared, in
  the spirit of D-008's tier 1. Worth thirty seconds at Sync 1.
