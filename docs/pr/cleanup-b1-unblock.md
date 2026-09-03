# cleanup: unblock B1 and A1, implement D-007, log D-022..D-030

<!-- Paste from line 5 onward as the PR body. The H1 above is the title. -->

## Module

**ID:** none — cleanup ahead of B1 and A1
**Merge-queue item(s) closed:** none. This clears obstacles from **#2 (B1)** and **#6 (A1)**
before their owner branches.
**Owner:** Ritik

## What this changes

Two bugs on `main` would have turned Arsha's suite red on her first B1 and A1 commits, for
reasons she did not cause. Both are fixed. **D-007** is implemented after being logged but
not landed. Ten decisions that constrain unwritten modules are logged as **D-022 to D-031**.

No features. `pytest` 39 → **48**.

**Arsha and Roy: add `CROSSREF_MAILTO` to your own `.env` after pulling.** Nothing calls it
yet, so an absent value is currently silent — P4 will be the first code to notice.

## The D-006 investigation — and what was actually true

The brief for this PR reported `docs/decisions.md` D-006 and `docs/module_status.md` as
contradicting each other about whether the contract-absence test existed. **Reported
before changing anything, as asked: neither document was wrong.**

- `tests/test_layout.py::test_contract_does_not_exist_yet` **was live** on `main` at
  `278fccd`. Verified: `pytest tests/test_layout.py --collect-only -q` → **11 tests,
  including it**. `docs/module_status.md` was correct.
- **D-006 was describing a different test.** Its Decision paragraph says a test that would
  *fail* until `src/contract.py` existed was written and removed, "and what shipped instead
  is `test_contract_does_not_exist_yet`, which asserts the file's **absence**, passes today".
  That matches the tree exactly. The entry was easy to misread as saying the green
  assertion had been removed, and its title — *"The red contract test was written and then
  removed"* — did not help.

**The concern behind the brief was right anyway, and the test is removed.** The green
assertion was defended last session on the grounds that it was green, named for what it
waited on, and legitimately deleted by B1's diff. That argument does not survive the actual
sequence: Arsha's first B1 commit *is* `src/contract.py`, so the suite goes red for the one
correct action, and the prescribed fix is **deleting an assertion**. The docstring saying
"DELETE THIS TEST IN THE B1 PR" makes that discoverable, not harmless — it makes
delete-the-assertion the documented, correct, first-thing-you-learn response to a red suite.
That is precisely the habit D-006's first pass rejected, reached by a longer route.

**B1's diff now touches no test in `tests/test_layout.py`.** Creating `src/contract.py`
leaves the suite green.

D-006 is rewritten: retitled *"No test asserts the contract's absence, in either
direction"*, recording both removals, and carrying a paragraph correcting its own earlier
wording. Its generalisation is sharpened to: **do not use a test as a to-do list for another
person — including a green test whose resolution is deleting an assertion.**

`test_pipeline_module_is_reserved_for_p6` is **deliberately kept** and is not an exception:
nobody is scheduled to create `src/pipeline/` as a package, so it guards a mistake rather
than waiting on a task, and its resolution is "stop doing that", not "delete the assertion".

## The layout test's intra-package false positive — fixed and simulated

The old check walked every file under `src/` and forbade any import of `src.judge.*` or
`dashboard.*`. Correct in intent, wrong in scope: **`src/judge/agent.py` importing
`src/judge/prompts.py` was a lane violation.** Arsha hits that on her first A1 commit.

`tests/test_layout.py` is rewritten around **D-008's three tiers, as module-level constants
with a comment citing the entry**, so the next person edits data rather than logic:

```python
SHARED_INFRA = ("src.settings", "src.llm", "src.contract", "src.priority")
LANES = {
    "Ritik": ("src.ingest", "src.resolvers", "src.matching", "src.pipeline", "app"),
    "Arsha": ("src.judge", "dashboard"),
    "Roy":   ("eval",),
}
```

The whole rule is two small functions. `lane_of(module)` returns `None` for shared infra —
belonging to no lane is exactly what makes it importable from every lane — and
`cross_lane_offenders(owner, names)` skips a file's own lane, which is the fix.

**What is new beyond the fix:**

- **Shared infra is asserted POSITIVELY**, parametrised over all four modules, so a future
  "tightening" that adds `src.llm` to a lane's prefix list fails with a pointer back to
  D-008 rather than silently forcing a second gateway client.
- **Both directions are enforced.** `test_arshas_lane_may_not_import_ritiks_pipeline` is
  new — **A2's own DoD box** (the dashboard renders `ledger_fixture.json` fully offline).
  Nothing previously stopped `dashboard/app.py` importing `src/pipeline`.
- **The rules are armed, not vacuously true** while `src/judge/` and `dashboard/` do not
  exist. Three tests assert the classifier *does* reject the forbidden imports, so the
  guard cannot rot into a check that passes because there is nothing to check.

**Verified by simulation, not by reading the logic.** Files created, suite run, files removed:

| Simulation | Expected | Result |
|---|---|---|
| `src/judge/{__init__,prompts,agent}.py` + `dashboard/{app,theme}.py`, importing intra-package **and** `src.llm`, `src.settings`, `src.contract` | pass | **17 passed** |
| `dashboard/app.py` importing `src.pipeline` | fail | **caught** |
| `src/matching/rules.py` importing `src.judge.agent` | fail | **caught** |

`git status` clean afterwards.

## D-007 implemented

| Change | Where |
|--------|-------|
| `resolvers.mailto` removed, replaced by a comment pointing at D-007 | `config.yaml` |
| `CROSSREF_MAILTO` added as a **name with a placeholder value** | `.env.example` |
| `crossref_mailto() -> str` — reads the env, raises on unset **or whitespace** | `src/settings.py` |
| `mailto` asserted **absent**; reader asserted to raise unset and to strip when set | `tests/test_config.py` (+3) |
| `mailto` row removed; API section added; *why it is a credential* section added | `docs/config_reference.md` |
| Step 4 lists all three env names with the failure mode for each; troubleshooting extended | `docs/setup.md` |
| P4 row records the obligation and marks D-007 implemented | `docs/module_status.md` |

It lives in `src/settings.py` rather than `src/llm.py` because `llm.py` is the gateway
client and a Crossref contact address is not a gateway concern — but it follows `llm.py`'s
pattern exactly: `load_dotenv()`, `os.getenv`, raise naming the variable and pointing at
`.env.example`.

**It raises rather than returning `""`** so a caller cannot pass emptiness through to a
`User-Agent` header and get the demotion anyway. The failure D-007 exists to make loud is
silent by nature: without a contact address Crossref does not error, it drops you out of
the polite pool and answers more slowly with tighter rate limits, so P4 looks like it has a
performance problem rather than a configuration problem.

### A second near-miss, of exactly the shape this section warns about

While writing the `config_reference.md` paragraph explaining that *a real mailbox in a
tracked file is the same category of mistake as a pasted key*, the worked example for
`crossref_mailto()` was written as `# -> "ragarw68@asu.edu"` — **a real address, in a
tracked file, inside the paragraph warning against it.**

Caught and replaced with `# -> your own address` before the commit.
`grep -rn "ragarw68"` over the tree returns nothing.

Recorded in `docs/worklog.md` because it is the **second** near-miss with the same
mechanism: *writing documentation*, reaching for a real value because a realistic example is
more useful than a fake one. Two for two. And note that **`check_secrets.sh` would not have
caught this one** — an email address is neither key-shaped nor the gateway host. The guard
covers the case it was built for, not the class.

## Decisions recorded

- [x] Decisions recorded (`docs/decisions.md` D-0NN): **logs D-022 to D-031**; **closes
      D-006, D-007 and D-008**; rewrites D-006; updates the *Open at Sync 1* table.
- [ ] N/A

**D-022 to D-031** were established in B3 and the B2 config pass and never logged. Each
constrains a module nobody has written yet:

| ID | Constrains | One line |
|----|-----------|----------|
| D-022 | R1, R2 | The schema's `control`, `source`, `verified_by`/`verified_on`. `control` is read, **never inferred** from "every label is `injected: false`" — that inference breaks the moment a spiked paper is committed before its labels. `source.license` restricts paper selection to five strings. (`defect_id` is D-016 — cross-referenced, not duplicated.) |
| D-023 | R1's corpus | One defect, one expected status — an ambiguous defect gets the **injection split**, never the label adjusted. |
| D-024 | R2, P5, A1 | Indicator matching is **exact-set**. Under subset matching `[]` matches anything and **D-011 and D-020 would have no teeth at all**. |
| D-025 | P6, R2 | `document` joins to `Ledger.document_name`, not the PDF filename. |
| D-026 | P2, R2 | `ref_id` is opaque (`"R03"` ≠ `"R3"`) and an unmatched id is a **hard error**, not a miss — the two failures need opposite responses and look identical in a score. |
| D-027 | R2, P6 | R2 asserts worklist correctness from existing labels: top-3 all `injected: true`, no trap in it. Per-status metrics are **order-blind**, and the top-3 is a demo beat. |
| D-028 | **P1** | Document-level defects are out of the golden labels and reassigned to P1 as a fixture PDF. B3 assigning work into Ritik's lane. |
| D-029 | P5, R2 | The confidence-band `thresholds` shape was **rejected** — it would have quietly built a different classifier than the one R2 measures. A reversal. |
| D-030 | P2, P4, A1 | `llm.timeout_seconds` (60) is separate from `resolvers.timeout_seconds` (10). One number breaks whichever caller you did not pick. |
| D-031 | every PR | `check_secrets.sh` reads the gateway host **out of `.env.example`** — hardcoding it would violate the rule the script enforces. |

**Four documented choices were deliberately NOT logged** — the 7-7-7 split, the `defect_id`
numbering, the clean-control similarity constraint, and the `sample.pdf` path. They belong
to Roy and to me, and logging them as decisions would convert every revision their owner
makes into a documented reversal. A note at the foot of `docs/decisions.md` says they exist
as documented choices, and states the test: **not "was this a choice" but "does someone
else's unwritten code depend on it".**

### Open at Sync 1 is now three items, no debt

| ID | Whose call |
|----|-----------|
| **D-004** — does `gate.py` want a model of its own? | Arsha |
| **D-009** — the priority formula in `src/priority.py`, shipping with B1 | Arsha |
| **D-020** — `version_mismatch` fires on preprint-ness | Ritik |

## Project ground rules

- [x] No model name anywhere in `src/`. `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/` → exit 1, no output.
- [x] `./scripts/check_secrets.sh` passes (pytest runs it too).
- [x] `.env` is untracked and `git status` does not list it.
- [x] Model names read via `src.settings.model_for(stage)` — unchanged.
- [x] Every model reply validated against a schema — N/A, no model calls in this PR.
- [x] `pytest` passes, **and the count went up**: 39 → 48.

## Definition of done

- [x] **The contract-absence assertion is gone**, and every doc describing the old behaviour
      is fixed. `grep -rn "test_contract_does_not_exist_yet"` leaves only: the rewritten
      module_status prose, the rewritten D-006 entry, and `docs/pr/B0.md` — a merged PR's
      body, **annotated with a SUPERSEDED note rather than rewritten**, because it is the
      record of what PR #1 said, not a live spec.
- [x] **`grep -rn "asserts its absence"`** leaves only correct hits: the two now reading
      *"no test asserts its absence"*, and `docs/pr/B0.md:54`, which is about
      **`src/pipeline.py`** and is still true.
- [x] **A file under `src/judge/` may import `src/judge/*`.** Simulated: 17 passed.
- [x] **A file in one lane may not import another lane's features, in either direction.**
      Simulated both ways: both caught.
- [x] **Shared infra importable from any lane, asserted positively.** 4 parametrised tests.
- [x] **Tier lists are module-level constants with a comment citing D-008.**
- [x] **D-007 implemented** across seven files, with the reader raising on unset.
- [x] **D-022 to D-031 logged**, same entry format, each with the rejected alternative.
- [x] **`architecture_map.md`'s reader count fixed** — see the note below.
- [x] **No doc claims B3 has four rulings** — see the note below.
- [x] **`pytest` 48 passed**, `check_secrets.sh` PASS.

## How I tested

```
$ pytest tests/test_layout.py --collect-only -q     # BEFORE, to settle the D-006 question
11 tests collected

$ pytest
collected 48 items

tests/test_app.py ...                                                    [  6%]
tests/test_config.py ...............                                     [ 37%]
tests/test_intake.py ......                                              [ 50%]
tests/test_layout.py .................                                   [ 85%]
tests/test_no_secrets.py .......                                         [100%]

============================== 48 passed in 0.78s ==============================

$ ./scripts/check_secrets.sh
check_secrets: PASS

$ grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/ ; echo $?
1

$ grep -rn "ragarw68" .        # the near-miss above
(no output)
```

Test count, file by file:

| File | Was | Now | Change |
|------|-----|-----|--------|
| `tests/test_layout.py` | 11 | **17** | −1 contract absence (D-006); −1 one-directional lane check, +8 tier-aware checks (D-008) |
| `tests/test_config.py` | 12 | **15** | +3 for D-007 |
| `tests/test_app.py` | 3 | 3 | — |
| `tests/test_intake.py` | 6 | 6 | — |
| `tests/test_no_secrets.py` | 7 | 7 | — |
| **Total** | **39** | **48** | **+9** |

## Eval output

- [x] N/A — R2 is not merged yet.

## Statuses and indicators touched

None. No code in this PR classifies anything. D-022 to D-027 quote the four statuses and six
indicators as specification text only.

## What this unblocks

**B1 (#2, Arsha) and A1 (#6, Arsha).** Both were startable before; both had a red suite
waiting at the first commit. Neither does now.

Also removes the last piece of implementation debt in the log, so *Open at Sync 1* is three
real decisions rather than four plus a to-do.

## Reviewer's guide — 10 minutes

Merged without review because it exists to remove obstacles from Arsha's path rather than to
make decisions for her, and B1 is the critical path. Read it after the fact.

1. **`tests/test_layout.py`, the constants and the two functions** (`SHARED_INFRA`, `LANES`,
   `lane_of`, `cross_lane_offenders`) — about 40 lines carrying the whole rule. If the tier
   lists are wrong, say so; that is a one-line data change.
2. **`src/settings.py: crossref_mailto()`** — confirm the raise-on-unset is what you want
   and that it belongs in `settings.py` rather than `llm.py`.
3. **D-006 in `docs/decisions.md`** — the reasoning for removing the assertion, and the
   paragraph correcting the entry's own earlier wording.
4. **The *Open at Sync 1* table** — three items now. D-004 and D-009 are yours.

**Skim or skip:** D-022 to D-031 if you already read the B3 PR (they are its rulings' fuller
reasoning), the doc-wiring diffs, and `docs/worklog.md` § Session 5.

## Anything I was unsure about

- **The brief's premise on D-006 was slightly off and I proceeded anyway.** There was no
  contradiction between the two documents — reported above, and the action was the same
  under either reading, so nothing was blocked on it.
- **The reader-count fix inverted while I was implementing D-007.** The brief said
  `architecture_map.md`'s "11 readers" was wrong and ten was right. That was true of
  `main` — but `crossref_mailto()` makes it 12 `def`s and 11 public functions. Resolved by
  making both docs *precise* instead of picking a number: **ten `config.yaml` readers, plus
  one env-backed reader**. `module_status.md`'s "Ten readers" was right about config readers
  and is now explicit that it means config readers.
- **Nothing in the tree claimed B3 has four rulings.** Every doc already said nine. The only
  "four" is the note in `docs/pr/B3.md` that flags the earlier brief's discrepancy, which is
  a correction rather than a claim. Left as is.
- **`docs/pr/B0.md` is annotated, not corrected.** It is a merged PR's body. Rewriting the
  claim would falsify the record of what PR #1 said, so it carries a SUPERSEDED blockquote
  instead. If you would rather it were edited outright, that is a one-line change.
- **`app` is in Ritik's lane list in `tests/test_layout.py`.** Slightly odd next to package
  names, and it disappears at A3 when `app.py` is deleted (**D-010**). It is there so the
  generic check covers `app.py` too rather than relying only on its dedicated test.
