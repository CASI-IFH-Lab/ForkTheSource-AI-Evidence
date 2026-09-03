# REPLAN — Phase 1 in 2 hours, Phase 2 in 4–5. Effective immediately.

**This overrides §6 (timeline) and each document's fallback section. Everything else in
`00_TEAM_PLAN_SHARED.md`, your individual document, and the ADDENDUM still stands —
interfaces frozen, ownership unchanged, ten rules unchanged.**

Clock starts when Ritik posts "T0" in chat. All times below are T+.

---

## 0. Status is known — branches collapsed, and two setup steps that were skipped

As of T0: **Arsha is merging A1** → she runs the top branch of §3: finish and merge A1,
then A2-minimal, then A3 wiring. **Roy is mid-R1** → decision rule: if your golden labels
are not yet written at T+0:15, cut to the FOUR-defect scope in §4 *now* — finishing six
and missing the window is the wrong trade. If the labels for six already exist, keep six.

**Arsha and Roy, before your next commit — two one-time steps that were skipped:**
1. `bash scripts/install_hooks.sh` (per-clone; STATUS.md says only one lane has ever
   appended a block, which means two clones skipped this).
2. Append a `STARTED` block to **your own** `progress/<you>.md` — the §10 format from the
   shared plan — and push it to main directly (progress files are append-only and yours
   alone; this is the one file that pushes without a PR). That push also proves your
   hooks and the Action work from your machine.

If your `progress/<you>.md` still has no block at T0, you are invisible to the other two
and to STATUS.md, and every "is X done yet?" question that follows is on you.

## 1. What the T+2:00 internal demo IS (redefined)

**Primary path — guaranteed, no dependency on anything unmerged:**
1. `python scripts/run_pipeline.py eval/corpus/paper1.pdf` runs live on the spiked paper
   — the AIR **extractor** call is real and visible in the CLI progress output.
2. The dashboard opens the produced ledger from the sidebar picker and renders counters,
   worklist, evidence detail.
3. `run_eval.py --fixtures` scores that ledger against Roy's golden labels — the metrics
   table, live.
4. The hallucinated-reference evidence click (ADDENDUM beat 1:20).

**Stretch, in order, only if merged by T+1:40:** wired LLM judge in the run (A1+A3) → the
live typed refusal → upload-zone flow. **The upload flow is now officially stretch.** A
dashboard reading a real ledger produced two minutes earlier on stage is a complete
internal demo; say it plainly, never apologize for it.

## 2. Ritik — T+0 to T+2:00

| T+ | Task |
|---|---|
| 0:00–0:45 | **P5** — run the prepared prompt UNCHANGED. Merge. Post `rule_based_status` availability the second it lands; Arsha's fallback and Roy's baseline both wait on the name. |
| 0:45–1:15 | **P6** — orchestrator per your card, one trim: the smoke test + the counts invariant + judge_fn injection test are the DoD; skip nothing else but gold-plate nothing. Merge, post, and **immediately run the pipeline on Roy's spiked paper** — commit the ledger to `data/output/` is gitignored, so hand the file path in chat. |
| 1:15–1:30 | `scripts/precache_demo.py` — two full runs on the spiked paper so the demo is warm and Wi-Fi-proof. |
| 1:30–2:00 | Drive a full dress run of §1's primary path. Fix only what breaks it. |

Cut from Phase 1 (already deferred, confirming): tables, D-037 arXiv-waterfall extras
beyond what's merged, any doc updates outside progress files.

## 3. Arsha — T+0 to T+2:00, branch on A1 status

**If A1 is merged or nearly:** 0:00–0:20 finish/merge A1 → 0:20–1:30 **A2-minimal** →
1:30–1:50 **A3 wiring only** (`wiring.py` one-liner + pass `judge_fn=wired_judge` into a
CLI flag or the sidebar — NOT the upload zone) → 1:50 merge.

**If A1 is in-progress:** cut A1 to **A1-minimal**: `prompts.py` + `agent.py` with the
stub fallback and the degradation ladder. **`gate.py` moves to Phase 2 hour one** — the
banned-terms discipline is still enforced tonight by Roy's eval scan, so the demo is
covered. Merge by 0:50, then A2-minimal.

**If A1 is not started:** skip A1 entirely until Phase 2. Go straight to **A2-minimal**
now — the dashboard is the demo; the judge is not, on this clock. The pipeline demos on
`rule_based_status` and we present the LLM judge as "wired in the enhancement phase."

**A2-minimal, the only version being built today (~70 min):** row 1 counters via the
`Ledger` methods + the counts-sum refusal guard; the top-3 worklist cards with rationale,
checks, lookup link; ONE expander template for the evidence click (as-printed vs resolved,
signal table, indicator chips) — this is demo beat 1:20, it is not optional; sidebar
ledger picker from a path. **Cut with no discussion:** the AIR progress strip (CLI shows
the models instead), full-ledger expanders beyond the template, theme polish, the
0-conflict/all-conflict layout tests.

## 4. Roy — T+0 to T+2:00, branch on R1 status

**If R1 merged:** 0:00–0:50 **R2-minimal** → 0:50–1:10 score Arsha's fixture + (at ~1:15)
Ritik's real ledger → 1:10–1:40 demo script per the ADDENDUM beats → 1:40–2:00 dress run,
you narrate.

**If R1 in-progress or not started:** **R1 collapses to FOUR defects** — swapped DOI,
hallucinated (the story's star), real retracted DOI (verify in OpenAlex FIRST), version-
pair trap — on ONE paper, no separate clean control (the paper's `injected:false` rows
are the clean baseline; the release gate still works). Labels + merge by 0:50. Then
R2-minimal 0:50–1:30, demo script 1:30–1:50.

**R2-minimal:** `--fixtures` mode only — ref_id hard-error join, exact-set indicators,
defect_id recall, the two release gates (conflict-on-clean, banned-terms), plain-text
metrics table. **Cut:** `--full`, worklist assertion, `report.py` markdown polish,
`test_harness.py` beyond the join/gates tests. **R3 is cut entirely from Phase 1** — the
refusal beat is you typing prompt #4 at the live judge *if* A1 landed, or quoting the
prompt rules if it didn't. The suite is Phase 2.

## 5. Phase 2 — the 4–5 hours after the internal demo, priority-ordered

Work the list top-down; where you stop is where you stop. Nothing lower may start while
something higher in your column is unfinished.

| # | Ritik | Arsha | Roy |
|---|---|---|---|
| 1 | Fix whatever the dress run exposed | **Land whatever Phase 1 cut:** gate.py, then A3 upload flow, then the AIR progress strip | **R2 `--full`** + worklist assertion |
| 2 | D-037 waterfall hardening + resolver fixtures | **The Reviewer Brief** (ADDENDUM §4 — the headline) | **R3: six prompts**, transcripts, pick the demo refusal |
| 3 | **Claim scanner** (ADDENDUM E-R) | Claim-evidence map + uncited-claim chips | Corpus to **two** papers / ~12 defects (21 only if time) |
| 4 | Per-stage latency in progress callback | Donut, CSV, theme polish | README + statuses.md per ADDENDUM, metrics slide from eval output |
| 5 | Batch mode | — | Two timed rehearsals + backup video + secrets/language sweep |

Row 5 for Roy is **not cuttable** — the final demo without a rehearsal and a backup
recording is how good builds die on stage.

## 6. Rules that tighten under compression

- **Merge windows, not merge perfection.** A module at 85% with green tests merges at its
  window; the remaining 15% is a Phase 2 row-1 item, logged in your progress file. An
  unmerged 100% is worth nothing at T+2:00.
- **A merge without a progress block is not a merge.** The block is the last step of the
  merge, every time — see §7.
- **REQUEST response time drops to zero-defer:** on this clock, an open REQUEST is
  answered at the requester's next message, not "next natural break."
- **No new decisions.** Anything that would need a D-number gets built the frozen way and
  the objection logged. Decision-making resumes in Phase 2.
- **T+1:40 is the integration freeze.** Nothing new merges between 1:40 and the demo
  except fixes to the primary path. Ritik calls it in chat.

## 7. Logging and docs are part of the merge, not after it

Right now `progress/ritik.md` has five blocks and the other two files have zero. That
means STATUS.md — the thing built so nobody has to ask "is X done?" — only works for one
lane out of three. Under a 2-hour clock this gets *more* important, not less, because
nobody has time to answer status questions in chat.

**The rule, effective now: a merge is these four things, in order, and the last two take
ninety seconds combined.**

1. Squash-merge your PR (with `docs/pr/<module>.md` as its body — that file IS your
   module's documentation; write it, don't skip it).
2. `git checkout main && git pull`.
3. Append a `MERGED` block to `progress/<you>.md` — sha, test count, the `publishes:`
   line with exact symbols and signatures, `next:` with an ETA — and push it.
4. Post two lines in chat.

A module missing step 3 is **not merged** for planning purposes: nobody downstream can
see what it exports, and STATUS.md's interface table is the only authority the other two
agents are told to trust. `BLOCKED`, `REQUEST`, and `SCOPE-CUT` blocks likewise go in the
progress file first, chat second — chat scrolls away, the file is the record.

**Docs under compression — exactly this much, no more:**
- `docs/pr/<module>.md` per merge (mandatory, it's the PR body anyway).
- Progress blocks (mandatory, above).
- Roy's stranger-facing docs — README, `docs/demo_script.md`, `docs/statuses.md` — in his
  scheduled slots per §4 and the ADDENDUM. Nobody else touches them.
- `docs/module_status.md` and `docs/architecture_map.md` stay **frozen** — do not
  "helpfully" update them; they are rewritten once, in Phase 2 row 4, by Roy. Live truth
  is STATUS.md, which maintains itself if your hooks are installed.
- Decision log: compression rule from §6 stands — build the frozen way, log objections in
  your progress file, D-numbers resume in Phase 2. Exception: Ritik still logs the
  ADDENDUM adoption as his next D-1NN inside the P5 branch, since it's already written.

## 7. Progress logs and docs — mandatory, and now enforced

**The current state:** `progress/ritik.md` has a block per merge. `progress/arsha.md` and
`progress/roy.md` have never had one — STATUS.md reads "Nothing to report" for both
lanes. That defeats the system: "Latest from each lane" is how we avoid interrupting each
other, and two of the three lanes are dark. Under a 2-hour clock, dark lanes mean the
integration freeze gets called on guesswork.

**The rule, effective now: a merge is complete when the progress block is pushed, not
when the PR closes.** Tell your agent, in these words, at the start of your session:
*"After every squash-merge: pull main, append a MERGED block to progress/<me>.md in the
shared plan §10 format, and push it. This is part of the merge step, not optional
follow-up."* Ritik's agent already does this; yours has not, and the fix is one sentence
of instruction.

**Minimum blocks per person today:**
- `STARTED` at T0 (§0 above)
- one `MERGED` block per module, at the merge — with the `publishes:` line filled in,
  because that line is what the other two build against
- `BLOCKED` / `REQUEST` the moment they occur, per shared plan §9
- one closing block at **T+2:00**: what shipped, what was cut (`SCOPE-CUT` word, naming
  the cut), and your first Phase 2 item — this is the input to the Phase 2 kickoff, so
  the demo debrief is reading, not interrogation
- the same closing block again at the end of Phase 2

**Docs under compression — exactly this much, no more:**
- **PR bodies:** still required, cut to the DoD boxes checked + a three-line
  "how I tested." No essays today.
- **`docs/decisions.md`:** one entry today — Ritik logs the ADDENDUM framing decision
  (his next D-1NN) inside the P5 branch. Everything else that smells like a decision gets
  built the frozen way and logged as an OBJECTION block instead; the log reopens in
  Phase 2.
- **`docs/worklog.md`:** one short session block per person at T+2:00–2:10 (three lines:
  built, cut, cost) and one at Phase 2 close. Append-only, your own section, no conflicts.
- **README / `docs/statuses.md` / `docs/demo_script.md`:** Roy's, already scheduled in
  his §4 column per the ADDENDUM — these are the stranger-facing docs and they are part
  of the demo, not overhead.
- **`docs/module_status.md` and `docs/architecture_map.md`: stay frozen.** STATUS.md is
  the live truth. Anyone who "helpfully" updates the frozen history docs today is
  creating Phase 2 merge conflicts for Roy.
