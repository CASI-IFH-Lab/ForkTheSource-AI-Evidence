# ForkTheSource — Team Plan (SHARED)

**Everyone reads this document. All three of us. It is the constitution for the next
9–10 hours.**

Read it once, end to end, before you write a line of code. Then read your own
individual document. Then start.

- Team CASI — Ritik (pipeline), Arsha (judge + dashboard), Roy (corpus, eval, demo)
- Event: ASU AIR Spark Challenge 2026, built on the AIR LLM gateway via Voyager
- Repo: `github.com/CASI-IFH-Lab/ForkTheSource-AI-Evidence` — `main` is demo-sacred, PR-only
- Ground truth for module specs: `docs/module_implementation_plan.pdf` in the repo

**Starting state (verified against the tree):** `main` @ `a4d57dd`, **131 tests green**,
`check_secrets` PASS. Merged: B0 (app shell + intake half), B2 (config + settings), B3
(golden-label format), B1 (contract + priority + 8-entry fixture). Open decisions: exactly
two — D-004 (Arsha) and D-020's P5 half (Ritik) — both closed by tasks in the individual
documents, so **there is no Sync 1 meeting**; the agenda became work items.

---

## 0. How to use this document with your coding agent

Paste **this whole document plus your individual document** into your agent at the start
of your session. Then, for each task, say:

> "Generate the prompt for Task R2 from my document, then execute it."

Your agent produces the task brief from the spec and runs it. You review the diff. You
merge. You update your progress file. You move to the next task.

**Do not paste someone else's individual document into your agent.** It will helpfully
start "fixing" their files.

---

## 1. What we are building, in one paragraph

A reviewer drops a PDF. We extract its bibliography, resolve every reference against
Crossref / OpenAlex / arXiv, compute deterministic match signals, and have an AIR-hosted
LLM judge classify each reference into one of four process states — `verified`,
`needs_check`, `conflict`, `unresolvable` — with a neutral rationale and 1–3 concrete
human-verification steps. The output is a prioritised worklist: thirty references in,
eight worth checking, zero accusations. Two AIR models do the reasoning; everything else
is deterministic so the results are reproducible and measurable.

**The AIR gateway is the point of the project, not an implementation detail.** Two
stages call it in Phase 1 (extraction and judging), the UI names the model running at
each stage, and Phase 2 adds two more AIR-powered features. Any change that reduces
visible AIR usage is a change in the wrong direction.

---

## 2. Two phases, and what "done" means for each

| Phase | Hours | Definition of done |
|---|---|---|
| **Phase 1 — internal demo** | 0:00 – 5:00 | A stranger clones the repo, runs one command, drops a spiked PDF, and sees a prioritised worklist with per-reference evidence, with the AIR model names visible per stage. `eval/run_eval.py --full` prints a metrics table. |
| **Phase 2 — enhancement** | 5:00 – 10:00 | More AIR surface, the full 21-defect corpus, the 20-prompt refusal suite, the metrics slide, and a rehearsed 3-minute demo. |

**Phase 1 is not a prototype we throw away.** Every module in Phase 1 is the real
module. Phase 2 adds; it does not rebuild.

---

## 3. Scope: what is IN Phase 1, and what is deliberately deferred

**IN — Phase 1 (all of this must exist by 5:00):**

| Module | Owner | What |
|---|---|---|
| P1 | Ritik | `parse_pdf` → `ParsedDocument`; body/references split |
| P2 | Ritik | **AIR** reference extractor (`models.extractor`) |
| P3 | Ritik | SQLite resolver cache |
| P4 | Ritik | Crossref + OpenAlex + arXiv resolvers |
| P5 | Ritik | Evidence signals, six indicators, rule-based classifier |
| P6 | Ritik | Orchestrator → `Ledger` JSON, with `judge_fn` injected |
| A1 | Arsha | **AIR** LLM judge (`models.judge`) + gate + priority |
| A2 | Arsha | Streamlit dashboard: counters, worklist, evidence detail |
| A3 | Arsha | Integration: wire judge into pipeline, upload → dashboard, AIR progress strip |
| R1 | Roy | **ONE** spiked paper, 6 defects, golden labels, + 1 clean control |
| R2 | Roy | Eval harness, `--fixtures` and `--full` |
| R3 | Roy | **6** adversarial refusal prompts (the demo's refusal beat) |
| R4 | Roy | README, demo script, metrics output |

**DEFERRED to Phase 2 — do not build these before 5:00, even if you have time.
Help someone else instead:**

- The full 21-defect corpus across three papers (Phase 1 = one paper, six defects)
- The 20-prompt adversarial suite (Phase 1 = six prompts)
- Table extraction from PDFs (`ParsedDocument.tables` ships as `[]` in Phase 1)
- Claim-evidence map row in the dashboard
- Status donut chart
- CSV export
- Biomed resolvers, batch mode
- The AIR Reviewer Brief (Phase 2 headline feature — see §11)

If you finish early in Phase 1, the answer is never "start a Phase 2 item". It is:
post `AHEAD` in your progress file and ask in chat who needs help.

---

## 4. Ownership — the file lists are the parallel-work guarantee

Three tiers. This is decision **D-008** in `docs/decisions.md` and it is frozen.

### Tier 1 — Shared infrastructure. Import freely. **Modify: nobody, without all three agreeing.**

```
src/contract.py      the four statuses, six indicators, all cross-module models
src/priority.py      compute_priority
src/settings.py      config reader
src/llm.py           AIR gateway client
config.yaml          every tunable
```

These are **FROZEN AT HANDOFF**. See §5.

### Tier 2 — Lane-exclusive. Only the owner writes here. Ever.

| Owner | Files |
|---|---|
| **Ritik** | `src/ingest/`, `src/resolvers/`, `src/matching/`, `src/pipeline.py`, `scripts/`, `app.py`, `tests/test_intake.py`, `tests/test_extractor.py`, `tests/test_cache.py`, `tests/test_resolvers.py`, `tests/test_evidence.py`, `tests/test_pipeline_smoke.py`, `tests/test_layout.py`, `tests/test_config.py`, `tests/test_no_secrets.py`, `tests/data/` |
| **Arsha** | `src/judge/`, `dashboard/`, `tests/test_judge.py`, `tests/test_dashboard_data.py`, `tests/test_contract.py`, `tests/fixtures/` |
| **Roy** | `eval/`, `tests/test_harness.py`, `docs/defect_catalog.md`, `docs/demo_script.md`, `docs/statuses.md`, `README.md`, `deck/` |

### Tier 3 — Append-only shared files. Everyone writes, nobody edits anyone else's lines.

```
progress/ritik.md    progress/arsha.md    progress/roy.md
docs/decisions.md    (reserved number ranges — see §8)
docs/worklog.md      (append your own session section only)
```

`STATUS.md` is **generated**. Never hand-edit it.

### Documentation stays current, without becoming a conflict source

- **Live status lives in `STATUS.md` only.** `docs/module_status.md` and
  `docs/architecture_map.md` are **frozen history** for this sprint — nobody updates them
  until Phase 2 wrap-up, so nobody conflicts in them.
- **Every merge updates the docs you own.** Ritik: docstrings + `docs/pr/<module>.md`.
  Arsha: same, plus `docs/contract.md` if her lane's behaviour needs explaining.
  Roy: `README.md` quickstart, `docs/statuses.md`, `docs/demo_script.md` — the
  stranger-facing docs are his product.
- A module PR without an updated PR body and progress-file entry is not done.

---

## 5. The ten rules

These exist because our baseline sprint lost hours to agents overriding each other's
work, opening cleanup PRs, and renegotiating settled decisions. Every rule below maps to
a specific thing that actually went wrong.

**R1 — Never write to a file you do not own.** Not to fix a bug. Not to add a missing
key. Not to correct a typo. Not to "align" it with your module. If a file outside your
list needs to change, you file a REQUEST (§9) and keep working.

**R2 — Tier 1 is frozen.** `config.yaml`, `src/contract.py`, `src/priority.py`,
`src/settings.py`, `src/llm.py` do not change during Phase 1. Every key you could need is
already in `config.yaml`; every model you could need is already in `src/contract.py`. If
something genuinely is missing, file a REQUEST — do not add it yourself, and do not
work around it by inlining a copy.

**R3 — Implement the spec, then object.** If your agent believes a frozen interface is
wrong, it implements the interface as written and records the objection in your progress
file under `OBJECTIONS`. It does not implement its own better version. A better design
that breaks two other people's code is worse than a mediocre design that works.

**R4 — No cleanup PRs, no refactors, no renames.** Not in Phase 1. If you see something
ugly outside your files, note it in `progress/<you>.md` under `PHASE2` and move on. Every
cleanup PR in our baseline sprint cost more time than it saved.

**R5 — Fixtures over waiting.** You are never blocked. If your input does not exist yet,
you build a fixture that fakes it and keep going. `tests/fixtures/ledger_fixture.json` is
already on `main` for exactly this reason.

**R6 — Merge small, merge yourself.** One module = one branch = one PR. When your DoD
boxes are green and `pytest` passes, **squash-merge your own PR.** No cross-review in
Phase 1 — review is a blocker and our files are disjoint. Phase 2 restores review.

**R7 — Merge `main` into your branch, never rebase, never force-push.** `git merge main`.
If a conflict appears in a file you do not own, take `main`'s version unconditionally and
file a REQUEST.

**R8 — No decision that constrains someone else, without a log entry.** Append to
`docs/decisions.md` in your reserved range (§8) before you open the PR. "N/A" is a fine
answer for most PRs.

**R9 — Never commit a secret, and never paste a real value into a doc.** `.env` is
gitignored. `./scripts/check_secrets.sh` runs inside `pytest`. Run it before every push.
If a key ever lands in a commit: rotate it in Voyager immediately. Rotation is the fix;
deleting the commit is not.

**R10 — Update your progress file at every merge, and post in chat.** Two lines. This is
how the other two know what they can pull. A merge nobody knows about is worse than no
merge.

---

## 6. Master timeline — Phase 1

All three lanes run simultaneously. **Nobody waits for anybody** until 4:00.

| Clock | Ritik | Arsha | Roy |
|---|---|---|---|
| **0:00–0:20** | ALL THREE, TOGETHER: pull `main`, verify env, `pytest` green (131), AIR key live, read both your documents, post `READY`. **No code** — except Ritik's S0 status tooling. | ← same | ← same |
| **0:20–1:20** | **P1** finish `parse_pdf` | **A1** judge on fixture + stub | **R1** pick paper, inject 6 defects |
| **1:20–2:20** | **P2** AIR extractor → *merge P1, P2* | **A1** gate + priority → *merge A1* | **R1** golden labels → *merge R1* |
| **2:20–3:20** | **P3** cache + **P4** resolvers → *merge* | **A2** dashboard on fixture | **R2** `--fixtures` mode → *merge* |
| **3:20–4:10** | **P5** evidence + rules → *merge* | **A2** finish → *merge A2* | **R3** 6 refusal prompts → *merge* |
| **4:10–4:30** | **P6** orchestrator → *merge* | wait for P6, then start A3 | run `--fixtures` on every ledger on main |
| **4:30–5:00** | precache demo paper; support A3 | **A3** integration → *merge* | `run_eval.py --full`; demo script |
| **5:00** | **DEMO.** Ritik drives, Roy narrates, Arsha on backup laptop. |

**Two hard checkpoints. Post in chat at both.**

- **CHECKPOINT 1 — 2:20.** P1+P2 on main. A1 on main. R1 on main. If a lane has not
  merged anything by 2:20, that lane cuts scope immediately per its own document's
  fallback section.
- **CHECKPOINT 2 — 4:10.** P5 on main, A2 on main, R3 on main. P6 merges by 4:30 or we
  demo the dashboard on Roy's fixture ledger instead of a live run. **That fallback is
  acceptable and it is not a failure** — the dashboard reading a real spiked-paper ledger
  is a complete demo.

---

## 7. The integration contract — FROZEN

These signatures are the only things the three lanes agree on. They are frozen for all of
Phase 1 and Phase 2. **Nobody changes a name, an argument, or a return type.** If yours
is wrong, you wrap it — you do not change it.

```python
# ---- Ritik publishes ----------------------------------------------------
parse_pdf(path) -> ParsedDocument
    # ParsedDocument: {name, pages: list[str], tables: list, body_text,
    #                  references_text, ref_start_page, notes: list[str]}
    # Phase 1: tables is always []

extract_references(doc: ParsedDocument) -> list[Reference]
extract_claims(doc, refs) -> list[Claim]

make_key(url, params) -> str
cache_get(key) -> dict | None
cache_set(key, payload: dict) -> None

resolve(ref: Reference) -> ResolvedSource | None

build_evidence(ref, resolved, ledger_refs: list[Reference]) -> MatchEvidence
rule_based_status(ev: MatchEvidence) -> tuple[str, float, str]

run(pdf_path, judge_fn=None, progress=None) -> Ledger
    # judge_fn: Callable[[Reference, MatchEvidence], Verdict]
    #   default: wraps rule_based_status into a Verdict
    # progress: Callable[[stage_name: str, model_name: str | None], None]
    # src/pipeline.py MUST NOT import src/judge

# ---- Arsha publishes ---------------------------------------------------
judge_reference(ref, ev, fallback_fn=None) -> Verdict   # NEVER raises
gate_batch(verdicts, total: int) -> list[Verdict]
render_ledger(ledger: Ledger) -> None
wired_judge                        # partial(judge_reference, fallback_fn=rule_based_status)
    # src/judge/ MUST NOT import src/ingest, src/resolvers, src/matching, src/pipeline

# ---- Roy publishes -----------------------------------------------------
python eval/run_eval.py --fixtures <ledger.json>
python eval/run_eval.py --full
    # writes eval/outputs/metrics_<timestamp>.md
python eval/run_adversarial.py

# ---- Already on main @ a4d57dd (131 tests green), frozen -----------------
src.contract:  VerdictStatus, INDICATORS, Reference, Claim, ResolvedSource,
               MatchEvidence, Verdict, LedgerEntry, Ledger, load_ledger, save_ledger
    # ResolvedSource.is_preprint is TRI-STATE: True / False / None(provider didn't
    #   say). None is NOT False. Set from provider-native signals only, never by
    #   venue string matching (D-036). ResolvedSource.arxiv_id exists.
    # MatchEvidence.year_delta is NON-NEGATIVE (ge=0): P5 stores
    #   abs(resolved.year - reference.year). A signed value raises at construction.
    # MatchEvidence.doi_match is tri-state: None = one side had no DOI (D-034).
    # Verdict.checks: max 3, no minimum — a fallback verdict may carry none.
    # Ledger helpers you should USE, not reimplement: worklist() (sorted by
    #   -priority with ref_id tie-break), summary_counts(), indicator_counts(),
    #   evidence_coverage(), counts_are_consistent(), assert_consistent().
src.priority:  compute_priority(ev, verdict, n_citing_claims) -> float
src.settings:  load_config, model_for, temperature_for, banned_terms,
               resolver_settings, crossref_mailto, cache_dir, llm_settings,
               thresholds, priority_severity, priority_weights, cache_settings
src.llm:       get_client()
```

**The vocabulary is closed.** Four statuses: `verified`, `needs_check`, `conflict`,
`unresolvable`. Six indicators: `retracted`, `version_mismatch`, `doi_mismatch`,
`duplicate_entry`, `orphan`, `malformed`. Nobody adds a seventh of either. A reference
whose extraction fails keeps its `raw_text` and gets `malformed` — extraction never drops
an entry.

**The language rule is absolute.** No output of this system — rationale, check, note, UI
label, log line, README sentence — ever says a citation is fake, fabricated, invented,
nonexistent, fraudulent, plagiarised, sloppy, AI-generated or AI-written. We report
process states and name what a human should verify. `config.yaml:banned_terms` is the
list; `gate.py` scans for it; `run_eval.py` fails the release on a single hit.

---

## 8. The decision log — reserved ranges

Our baseline sprint had two people editing the same table in the same file with a
260-line diff on the critical path. Fixed by partition:

| Owner | Range |
|---|---|
| Ritik | **D-100 – D-199** |
| Arsha | **D-200 – D-299** |
| Roy | **D-300 – D-399** |

`D-001` – `D-037` are existing history. **Nobody edits an existing entry.** Nobody
renumbers. If you supersede an old decision, write a new entry in your own range that
says "supersedes D-0NN" and leave the old one alone.

Append at the end of the file, in your own range, in this format:

```markdown
## D-1NN — one-line title
**Time** · **Decided by** · **Status**: active | open
**Affects**: modules and paths
**Decision**: the rule, one or two sentences.
**Why**: the reasoning, including what you rejected.
**Consequence**: what this obliges someone to do, and who.
```

Log a decision when, and only when, your choice constrains someone else's module or
departs from the frozen spec. Naming a private helper is not a decision.

---

## 9. When something blocks you — the REQUEST protocol

You are never blocked for more than five minutes. Ever.

1. **Build a fixture and keep going.** Need P4's output? Hand-write one `ResolvedSource`
   JSON and code against it. Need the real judge? Use the stub. This is R5 and it is the
   single most important habit in this sprint.
2. **File a REQUEST** in your own progress file:

```markdown
### REQUEST → @ritik  (0:47)
NEED: src/matching/rules.py to export rule_based_status with the exact signature
      in §7 — I need it for wired_judge in A3.
WHY:  A3 is one line and that line imports it.
UNBLOCKED MEANWHILE BY: a local stub returning needs_check/0.3.
BLOCKS ME AT: 4:30 (A3).
```

3. **Post the same thing in chat, once.** Tag the person. Then go back to work.
4. The owner picks it up at their next natural break, not immediately.

**Never fix it yourself.** A REQUEST costs the other person two minutes. Editing their
file costs both of you thirty and a conflict.

---

## 10. The progress system

Two moving parts. Ritik lands both in hour 0.

### `progress/<you>.md` — you edit only your own

Append-only. One block per event. Format:

```markdown
## 1:24 — P2 MERGED
branch: ritik/p2-extractor → main @ <sha>
tests: 84 passed
publishes: extract_references(doc) -> list[Reference], extract_claims(doc, refs)
notes: entries pre-split in plain code, one AIR call per entry, retry-once then malformed.
next: P3 cache, ETA 2:00
```

Status words, used exactly: `READY`, `STARTED`, `MERGED`, `BLOCKED`, `AHEAD`,
`REQUEST`, `OBJECTION`, `SCOPE-CUT`.

### `STATUS.md` — generated, never edited

`scripts/update_status.py` regenerates it from git history, the three progress files, and
the test count. A `post-commit` and `post-merge` git hook runs it automatically, and it
also runs on every push to `main` via GitHub Actions.

**Before you branch anything: `git pull && cat STATUS.md`.** It tells you what is on
main, who published what interface, what is in flight, and what is blocked. It is the
answer to "what is the status" so nobody has to ask.

---

## 11. Phase 2 — the enhancement half (5:00 – 10:00)

Do not start these before 5:00. Listed now so nobody invents their own.

**The headline: the AIR Reviewer Brief (Arsha).** One more `models.judge` call that takes
the finished `Ledger` and produces a 150-word neutral brief for the reviewer: how many
references, how many need attention, which three matter most and why, what to check
first. It appears at the top of the dashboard and it is the most quotable thing in the
demo. It is also the clearest possible answer to "how are you using the AIR platform".

| Owner | Phase 2 |
|---|---|
| **Ritik** | D-037 arXiv waterfall fix (Crossref 404s every `10.48550/*`); tables extraction; per-stage AIR latency in the progress callback; batch mode |
| **Arsha** | The Reviewer Brief; claim-evidence map; donut; CSV export; the AIR model strip with live latency per stage |
| **Roy** | Corpus to 3 papers / 21 defects; adversarial to 20 prompts; metrics slide exported from `run_eval.py`; 3-minute script; backup video; pre-submission secrets and language sweep |

**Never cut, in either phase:** the one-screen dashboard, the worklist with evidence
links, the live refusal moment, the metrics table generated by `run_eval.py`, and visible
AIR model attribution per stage.

---

## 12. Git mechanics — the exact commands

```bash
# start a module
git checkout main && git pull
cat STATUS.md                          # know what you are building on
git checkout -b <you>/<module>         # e.g. arsha/a1-judge

# ... work ...
pytest                                 # must be green
./scripts/check_secrets.sh             # must PASS
git add -A && git commit -m "A1: judge agent + gate + priority"

# take main's latest, no rebase
git merge main                         # conflict outside your files -> take main's side

git push -u origin <you>/<module>
gh pr create --base main --head <you>/<module> \
  --title "A1: LLM judge agent on AIR" --body-file docs/pr/A1.md

# DoD green? squash-merge your own PR.
gh pr merge --squash --delete-branch

git checkout main && git pull
python scripts/update_status.py         # or let the hook do it
# append to progress/<you>.md, post two lines in chat
```

**Every PR body contains:** module ID, the DoD boxes checked with evidence, "how I
tested" with real command output, and `Decisions recorded: D-1NN` or `N/A`.

---

## 13. The demo, so everyone builds toward the same thing

Three minutes, at 5:00, and again at 10:00.

1. **0:00 The pain.** A reviewer gets a paper with thirty references. Checking them is
   an hour of tab-switching.
2. **0:20 Drop the PDF.** The AIR progress strip lights up stage by stage, naming the
   model: `extracting references — qwen3-30b-a3b-instruct`, `judging — qwen3-235b-a22b-thinking`.
   This beat is where the AIR platform becomes visible. Do not skip it.
3. **0:50 The dashboard.** Four counters. Thirty references in, eight worth checking.
4. **1:20 One evidence click.** As-printed versus resolved record, the signal table, the
   indicator chips, the suggested checks, the one-click lookup link.
5. **2:05 The refusal.** Ask it "is reference 7 fake?" It declines and redirects to the
   status and the verification steps. This is our principle, demonstrated live.
6. **2:30 The metrics.** The table straight out of `run_eval.py`: defect recall, zero
   false accusations on the clean control, determinism across three runs, zero banned
   terms.
7. **2:50 Close.** "Verifiability, never accusations. Thirty references in, eight worth
   checking, zero accusations."

---

## 14. If it goes wrong

| Situation | Do this |
|---|---|
| Behind at CHECKPOINT 1 (2:20) | Cut to your document's fallback scope. Tell the other two. |
| P6 not merged by 4:30 | Demo the dashboard on Roy's ledger. Announced, not apologised for. |
| AIR gateway down | The pipeline runs end-to-end on `rule_based_status` with no key. Say "it degrades honestly" on stage — it is a feature. |
| A registry is down | P3's cache plus `scripts/precache_demo.py`. Rehearse once with Wi-Fi off. |
| Your agent wants to change a frozen file | It does not. R2 and R3. Log the objection, implement the spec. |
| Conflict in someone else's file | Take `main`'s version. File a REQUEST. |
| You are stuck > 5 minutes | Fixture it, REQUEST it, keep moving. §9. |

---

## 15. Before you start — the ten-minute hour-zero checklist

Everyone, together, at 0:00. Nobody writes code until all five lines are true for all
three of us.

```bash
git checkout main && git pull            # 1. same main
python --version                         # 2. 3.10+ (3.13.7 verified)
pytest                                   # 3. green
./scripts/check_secrets.sh               # 4. PASS
python -c "from src.llm import get_client; print(len(get_client().models.list().data))"
                                         # 5. AIR is alive (VPN on)
```

Then each of us appends `## 0:15 — READY` to our own progress file, and Ritik pushes the
status tooling. Then we go, and we do not talk again until CHECKPOINT 1 unless someone
files a REQUEST.
