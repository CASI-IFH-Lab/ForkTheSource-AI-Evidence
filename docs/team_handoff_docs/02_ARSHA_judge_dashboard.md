# ARSHA — AI Verification Engine + Dashboard Lane

**Read `00_TEAM_PLAN_SHARED.md` first. This document assumes it.**

> ## CURRENT STATE
>
> **A1 and A2 are both MERGED** (`ab06a80`, `9dbcd55`) — ahead of the plan this banner
> was drafted against, and `gate.py` did NOT slip: `src.judge.gate.gate_batch` is live on
> `main`. A2 shipped fuller than A2-MINIMAL (counters, seven-chip AIR strip, top-3
> worklist, per-entry expanders), so REPLAN §3's minimal scope is already satisfied.
>
> **Your next module is A3 wiring, WITHOUT the upload zone** — and you have it correctly
> marked blocked on P6. P5 is Ritik's next module, P6 the one after.
>
> `rule_based_status` — your `fallback_fn` — lands with Ritik's **P5**: watch for the
> MERGED block and import it by name from `src.matching.rules`. `wired_judge` is still
> yours to publish.
>
> **Nothing you consume changed.** The extractor's D-102 return-shape change does not
> touch your lane.
>
> Hooks and progress blocks: already done — you are posting blocks in `progress/arsha.md`.
> If `bash scripts/install_hooks.sh` has not been run in this clone, run it once.

Paste both documents into your agent at session start. For each task say:
*"Generate the prompt for A1 from my document, then execute it."*

---

## Your vertical

You own the part of this project that the judges will actually look at, and the part that
demonstrates the AIR platform. The LLM judge is the reasoning core; the dashboard is the
whole visible product. **Your lane has zero code dependency on Ritik's until 4:30** — you
build A1 and A2 entirely against `tests/fixtures/ledger_fixture.json`, which is already on
`main` and which you wrote. A3 is the single deliberate integration moment and it is
roughly one line plus UI wiring.

**You own:**

```
src/judge/           prompts.py, agent.py, gate.py, wiring.py
dashboard/           app.py, theme.py
tests/test_judge.py
tests/test_dashboard_data.py
tests/test_contract.py   (yours — you wrote it in B1)
tests/fixtures/      ledger_fixture.json and anything else you need to fake
progress/arsha.md
docs/decisions.md    D-200 – D-299 only
docs/pr/A1.md, A2.md, A3.md
```

**You never touch:** `src/ingest/`, `src/resolvers/`, `src/matching/`, `src/pipeline.py`,
`app.py` (the root one), `config.yaml`, `src/contract.py`, `src/priority.py`,
`src/settings.py`, `src/llm.py`, `scripts/`, `tests/test_layout.py`,
`tests/test_config.py`, `tests/test_intake.py`, `eval/`, `README.md`.

### Three things your agent will want to do, and must not

This is the part of your document that matters most, so it is near the top.

**1. It will want to fix Ritik's files.** During the baseline sprint your agent correctly
found real bugs in `tests/test_layout.py` and `tests/test_no_secrets.py` — and the right
move was exactly what happened: diagnose precisely, report it, do not touch the file. Keep
doing that. A diagnosis is worth more than a patch, because a patch in someone else's file
costs a conflict on the critical path.

**2. It will want to improve a frozen interface.** `src/contract.py` and `src/priority.py`
are yours by authorship but they are Tier 1 and frozen for all of Phase 1. Ritik's P2, P4,
P5 and P6 are all being written against them right now. If your agent finds a real
modelling flaw, it **implements against the flawed model and logs a D-2NN objection.** A
better contract that lands at 3:00 breaks four modules in flight.

**3. It will want to raise its own exception types and conventions.** Inside `src/judge/`
and `dashboard/`, do whatever you think is right — that is your lane and rule R6 gives you
full authority there. Outside them, match what exists.

Every time you disagree with something outside your files, the move is the same: write it
under `OBJECTIONS` or `REQUEST` in `progress/arsha.md`, post once in chat, keep building.

---

## A1 — LLM judge agent on AIR (0:20–2:20, ~90 min)

Branch `arsha/a1-judge`. **This is the centrepiece of the project.** The honesty boundary
is enforced here in code, not just in the prompt.

```python
judge_reference(ref, ev, fallback_fn=None) -> Verdict     # NEVER raises
gate_batch(verdicts, total: int) -> list[Verdict]
```

Files: `src/judge/prompts.py`, `agent.py`, `gate.py`, `tests/test_judge.py`.
Client from `src.llm.get_client()` — **do not build a second client.** Model from
`settings.model_for("judge")`, temperature from `settings.temperature_for("judge")`.
Never hardcode a model name; `grep -rn "qwen\|glm\|gemma\|sk-" src/` must stay at exit 1.

### The prompt (`prompts.py`) — hard rules, and they are the project's principle

The system prompt must state, and the code must enforce:

- Never say a citation is fake, fabricated, invented, nonexistent, fraudulent,
  plagiarised, sloppy, AI-generated or AI-written. **Use the four status names.**
- Never score AI authorship. Never allege misconduct. Never invent an identifier.
- Ground **only** in the supplied evidence signals. If a signal is absent, say what is
  missing, not what it implies.
- `retracted` in the indicators → at least `conflict`.
- Parse noise **lowers confidence toward `needs_check`, never toward `conflict`.** An
  unreadable reference is not a suspicious one.
- Output strict JSON: `{status, confidence, rationale, checks[]}`. `checks` is 1–3
  concrete things a human can do in under a minute — "open the DOI and compare the title",
  not "verify the reference".

Keep the prompt in `prompts.py` as a module constant so Roy's R3 can attack the real
thing and so R4 can quote it in the docs.

### `agent.py` — the degradation ladder

Tolerant parse: strip code fences, grab the first `{...}`, pydantic-validate into
`Verdict`. Then:

```
malformed JSON        -> one retry (llm.max_retries) -> fallback_fn
missing key / gateway error / timeout  -> fallback_fn immediately
```

Record which path produced each verdict in `judge_model`: the real model name, or
`"fallback:stub"`, or `"fallback:rule_based"`. **A run is always honest about how it got
its answers** — this is what lets us say "it degrades honestly" on stage instead of
hiding it.

`fallback_fn` defaults to a conservative stub returning `needs_check` at confidence 0.3.
A3 swaps in Ritik's `rule_based_status`. **`judge_reference` never raises** — prove it with
a chaos test using a fake client that raises randomly.

`Verdict.checks` enforces `max_length=3` with **no minimum** — that was your own
deliberate divergence so the fallback stub stays representable with empty checks. The
prompt still asks the live model for 1–3; the contract just doesn't make degradation
impossible. Have the dashboard render "no checks — fallback verdict" rather than an empty
gap.

### `gate.py` — the folded-in critic, three code checks, no model call

1. Every `ref_id` has exactly one verdict.
2. Status counts sum to `total`.
3. Case-insensitive scan of `rationale` + every `check` against
   `settings.banned_terms()`. **Read it from settings — never keep a private copy.** The
   same list is used by Roy's release gate and a second copy would drift.

Any failure → re-judge that entry once → else force `needs_check` with rationale
`"judge output failed quality gate"`. A visible, honest failure, not a silent one.

**On D-004, which is yours:** you decide whether `gate.py` wants a model of its own. My
recommendation is no — three code checks are deterministic, instant, and free, and a
model-based gate is a second thing that can fail. If you agree, log D-2NN closing D-004
and move on. If you disagree, log it and keep the gate code-only for Phase 1 anyway;
`models.critic` no longer exists in `config.yaml` and adding it is a Tier 1 change.

### Tests — 100% offline, no key, no network

Fixture evidence in, fallback out. A fake client object exercises the malformed-JSON retry.
A poisoned verdict (`"this citation is fake"`) must be caught by the gate test. Plus one
**live** smoke test against AIR, marked `@pytest.mark.skipif` on missing key so CI stays
green.

**DoD:**
```
[ ] full suite green with NO network and NO key
[ ] one live AIR smoke test returns valid JSON (skipped without a key)
[ ] gate catches a planted banned term AND a counts mismatch
[ ] judge_reference never raises — chaos test with a randomly-raising client
[ ] judge_model records which path produced each verdict
[ ] retracted evidence yields at least conflict
[ ] parse noise lowers confidence, never escalates to conflict — named test
[ ] no model name in src/; model and temperature from settings
[ ] D-004 closed in your range
```

**Merge by 2:20 — this is CHECKPOINT 1.** Then post: *"A1 merged. AIR judge live on
`models.judge`. `judge_reference(ref, ev, fallback_fn=None) -> Verdict`, never raises.
@roy R3 can attack the real judge now."*

---

## A2 — the dashboard (2:20–4:10, ~110 min)

Branch `arsha/a2-dashboard`. `dashboard/app.py`, `dashboard/theme.py`,
`tests/test_dashboard_data.py`.

**Depends on `src/contract.py` + `tests/fixtures/ledger_fixture.json` ONLY. Works fully
offline. Zero imports from `src/ingest`, `src/resolvers`, `src/matching`, `src/pipeline`
— and `tests/test_layout.py` will enforce that, so do not try.**

```python
streamlit run dashboard/app.py
render_ledger(ledger: Ledger) -> None      # import-safe, testable
```

### Phase 1 layout — build in this order and stop when the clock says so

**Row 1 — the summary. Build first, it is the demo's opening image.**
Four counters with proportional bars: `verified` green, `needs_check` amber, `conflict`
red, `unresolvable` grey. **Use the `Ledger` methods you already wrote** — do not
reimplement in the UI: `summary_counts()`, `evidence_coverage()`, `indicator_counts()`,
`worklist()` (already sorted by `-priority` with the `ref_id` tie-break), and
`counts_are_consistent()` for the guard. **REFUSE to render**, with a visible error
banner, when `counts_are_consistent()` is false — a mirror of Ritik's
`PipelineIntegrityError`. A dashboard that renders wrong numbers confidently is worse
than one that says it cannot.

**Row 2 — the AIR progress strip.** Seven stage chips: `intake`, `extract`, `resolve`,
`evidence`, `verdict`, `priority`, `ledger`. Each shows the model name when there is one.
In A2 this renders statically from a fixture; A3 wires it to the live callback. **This is
the beat at 0:20 in the demo where the AIR platform becomes visible — it is not
decoration, it is the thing we are being judged on.** Give it real visual weight.

**Row 3 — the worklist.** Top 3 by `priority` desc: status badge, confidence %, the
one-line rationale, the suggested checks, and a one-click lookup URL. Then the full ledger
as expanders sorted by priority: side-by-side "as printed" versus "resolved record", the
signal table (`title_similarity`, `author_overlap`, `year_delta`, `doi_match`), indicator
chips, suggested checks.

**Sidebar.** Ledger picker from `data/output/*.json`. Judge model name from config. Upload
zone present but stubbed with "pipeline wiring lands in A3".

**`theme.py`.** Status colours, labels and icons defined **once**. All wording neutral —
process states, never verdicts. Label them "needs checking", not "suspicious". Keep every
`st.*` call thin so `render_ledger`'s logic is testable on a parsed fixture.

**`doi_match` renders as three states**, not a checkbox: match, mismatch, and "no DOI on
one side". Collapsing `None` into "mismatch" is the single most likely way this UI
manufactures a false accusation.

### Not in Phase 1 — deferred, do not build

Claim-evidence map row. Donut chart. CSV export. Those are Phase 2 and they are the first
things to cut if the clock slips.

**DoD:**
```
[ ] fixture renders in one screen at 1920x1080, no scroll for the summary
[ ] counts-sum guard demonstrably trips on a corrupted copy of the fixture
[ ] a ledger with 0 conflicts and one with all-conflicts both render without layout break
[ ] doi_match shows three distinct states
[ ] every label neutral — no banned term anywhere in the UI, tested
[ ] zero imports from src/ingest, src/resolvers, src/matching, src/pipeline
[ ] render_ledger testable without Streamlit running
```

**Merge by 4:10 — CHECKPOINT 2.** Post: *"A2 merged. `streamlit run dashboard/app.py`
renders any Ledger JSON. Upload zone stubbed for A3."*

---

## A3 — integration (4:30–5:00, ~30 min)

Branch `arsha/a3-integration`. **Do not start before P6 is on main.** Check
`cat STATUS.md`; Ritik posts in chat the moment it merges.

`src/judge/wiring.py`:
```python
from functools import partial
from src.judge.agent import judge_reference
from src.matching.rules import rule_based_status

wired_judge = partial(judge_reference, fallback_fn=rule_based_status)
```

That is the whole integration. One import crossing the lane boundary, in one file, at the
one moment the design allows it.

Then in `dashboard/app.py`:
1. Upload zone saves the PDF to `data/uploads/`.
2. Calls `run(pdf_path, judge_fn=wired_judge, progress=cb)` where `cb(stage, model)`
   lights the corresponding chip in the progress strip **with the model name**.
3. Renders the returned ledger. Cache the result so re-render is instant.
4. Error surface: a pipeline exception shows a visible error state **naming the stage** —
   never a blank screen. Gateway down mid-run shows the banner "judge in rule-based mode
   this session". Honest degradation, visibly.

**DoD:**
```
[ ] fresh clone -> one command -> upload the spiked PDF -> dashboard renders
[ ] progress strip lights each stage with the correct AIR model name
[ ] two runs -> identical dashboard counts
[ ] full flow works with Wi-Fi disabled (Ritik's cache is warm)
[ ] a raised pipeline exception shows the stage name, not a blank page
[ ] Ritik reviews — this is the one PR in Phase 1 that gets a review
```

Post: *"A3 merged. Upload → live pipeline → dashboard, AIR models named per stage. Demo
path is green."*

---

## Your fallback, if you are behind

At **CHECKPOINT 1 (2:20)** — if A1 is not merged:
1. Merge A1 with the stub fallback and **without** the live smoke test. The offline path
   is what the demo runs on anyway.
2. If `gate.py` is not done, merge `agent.py` alone and add the gate in a second PR. The
   gate is a quality guarantee, not a demo dependency.

At **CHECKPOINT 2 (4:10)** — if A2 is not merged:
1. Cut the full-ledger expanders. Keep row 1 (counters), the progress strip, and the top-3
   worklist. **That is a complete demo.**
2. Cut the sidebar ledger picker; hardcode the path.
3. Cut the signal table inside the expanders; keep the as-printed-vs-resolved pair.

**Never cut:** the four counters, the top-3 worklist, the AIR progress strip, and the
counts-sum guard. Those four are the product.

If A3 cannot land by 5:00, the demo runs the dashboard on Roy's ledger file. Say so
plainly, do not apologise — a dashboard reading a real spiked-paper ledger is a real demo.

---

## Phase 2 — yours (5:00 onward)

**The AIR Reviewer Brief. This is the headline enhancement and it is yours.** One more
`models.judge` call that takes the finished `Ledger` and emits a ~150-word neutral brief:
how many references, how many need attention, which three matter most and why, what to
check first. It renders at the top of the dashboard. It is the most quotable thing in the
pitch and the clearest possible answer to "how are you using the ASU AIR platform".

Same rules apply: no banned terms, `gate_batch`-style scan over its output, and it falls
back to a deterministic template if the gateway is down.

Then: claim-evidence map, donut, CSV export, live per-stage latency in the progress strip.

---

## The four things that will bite you

1. **`doi_match` is tri-state.** `None` means one side had no DOI. It is not `False`.
   Render three states.
2. **`version_mismatch` is not a conflict.** A preprint cited where the journal version
   exists is a correct citation with a note. If your UI colours it red, we have made the
   exact false alarm the project exists to avoid. Roy has planted one in the corpus.
3. **`banned_terms` has 11 entries and lives in `config.yaml`.** Read it through
   `settings.banned_terms()` every time. A hardcoded copy will drift from Roy's release
   gate and you will pass while he fails.
4. **`git merge main`, never rebase, never force-push.** If a conflict lands in
   `src/ingest/`, `src/matching/`, `src/pipeline.py` or `eval/`, take `main`'s version
   without reading it and file a REQUEST if something breaks.
