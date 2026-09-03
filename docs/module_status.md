# Module status — where the repo actually is

Last verified against commit `4328eb7` on `ritik/m0-skeleton`. `main` is at `ffd0180`
(the empty folder structure).

This file exists because the Module Implementation Plan says what *should* be built and
this repo says what *is* built, and those two are not the same thing yet. The "actual"
column is the one to trust: it was read off the working tree, not off the plan.

> **One thing to read before anything else:** the Module Implementation Plan is not
> checked into this repo. Every "plan status" and "owner" cell below is either taken
> from the B0 task brief or marked `confirm`. The **Actual** column is verified against
> the tree; the **Owner** and **Plan** columns need one pass from Ritik against the real
> plan document. Fix those cells, then delete this warning.

## The table

| ID | Module | Owner | Plan status | **Actual status in this repo** | Branch / commit |
|----|--------|-------|-------------|-------------------------------|-----------------|
| B0 | App skeleton (Streamlit app, pipeline package, tests) | Ritik | merge-queue #1 | **Done.** App starts, drop zone accepts a PDF, raw text renders. 29 tests pass. | `ritik/m0-skeleton` @ `4328eb7` |
| B1 | Contract — the four statuses and six indicators | **Arsha** | merge-queue #2 | **Not started, not on `main`.** `src/contract.py` does not exist and must not be created by anyone else. | none |
| B2 | Config loader + `config.yaml` + `.env.example` | Ritik | merge-queue #3 | **Done — landed inside B0.** See the proof below. No separate PR needed. | `ritik/m0-skeleton` @ `4328eb7` |
| B3 | *(not named in the B0 brief — confirm)* | confirm | confirm | **Not started.** Nothing in the tree corresponds to it. | none |
| P1 | PDF extraction | confirm | — | **HALF DONE.** See the P1 section below. | `ritik/m0-skeleton` @ `4328eb7` (the done half) |
| P2 | Reference extraction / normalization | confirm | — | **Not started. Blocked on B1.** `src/pipeline/extractor.py` is a stub that raises. | none |
| P3 | Resolver — catalogue lookups + disk cache | Ritik | — | **Not started.** `src/pipeline/resolver.py` is a stub that raises. Cache dir is configured but nothing reads it. | none |
| P4 | Judge | confirm | — | **Not started.** `src/pipeline/judge.py` is a stub that raises. **Missing the `fallback_fn` seam** — see Deviations. | none |
| P5 | Thresholds / status assignment | Ritik | — | **Not started.** No thresholds exist in `config.yaml`. | none |
| P6 | Orchestrator | confirm | — | **Not started, and it has no home.** There is no `src/orchestrator.py`. See Deviations. | none |
| A1 | Critic — banned-terms review of the write-up | confirm | — | **Not started.** `src/pipeline/critic.py` is a stub that raises. `banned_terms` is in `config.yaml` and readable, but nothing calls it. | none |
| A2 | *(not named in the B0 brief — confirm)* | confirm | — | **Not started.** | none |
| A3 | *(not named in the B0 brief — confirm)* | confirm | — | **Not started.** | none |
| R1 | *(not named in the B0 brief — confirm)* | confirm | — | **Not started.** | none |
| R2 | Eval harness | confirm | — | **Not started.** `eval/` exists as an empty directory, so git does not track it. `eval/outputs/` is already in `.gitignore`. | none |
| R3 | *(not named in the B0 brief — confirm)* | confirm | — | **Not started.** Drafting is unblocked. | none |
| R4 | README acceptance test — fresh clone to running app in under 10 minutes | confirm | — | **Seeded, not done.** [setup.md](setup.md) was written to that bar and is the thing R4 should test. | `ritik/m0-skeleton` (docs commit) |

## B2 landed inside B0 — do not open a second PR

This is the single most important line in this file, so it gets its own heading.

Merge-queue item **#3 (B2, config)** is already satisfied by the B0 branch. The B0 PR
closes **#1 and #3 together**. Nobody needs to branch B2, and a B2 PR opened against
this tree will conflict with files that already exist.

The files that prove it, all present at `4328eb7`:

| File | What it contributes to B2 |
|------|---------------------------|
| `config.yaml` | The settings themselves: five model names, `temperature`, `critic_temperature`, `resolvers.cache_dir`, `resolvers.timeout_seconds`, `banned_terms`. |
| `src/config.py` | The loader, and the only code in the repo that opens `config.yaml`. Exposes `load_config`, `model_for`, `temperature_for`, `banned_terms`, `resolver_settings`, `cache_dir`. |
| `.env.example` | The credential template — `AIR_API_KEY` and `AIR_BASE_URL` by name, values left as placeholders. Already on `main` since `ffd0180`; B0 does not modify it. |
| `tests/test_config.py` | Five tests guarding the config shape, including that an unknown stage raises instead of guessing. |

Full detail on every key lives in [config_reference.md](config_reference.md).

## P1 is half done — read this before branching it

Do not treat P1 as unstarted, and do not treat it as finished. The split is precise:

**The half that exists**, in [`src/pipeline/intake.py`](../src/pipeline/intake.py):

- `extract_pages(pdf) -> list[str]` — per-page pdfplumber text extraction. One string per
  page, in page order. A page with no extractable text comes back as `""` rather than
  being dropped, so a page's index in the list is always its page number minus one.
- `extract_text(pdf) -> str` — the same pages joined by a blank line.
- `run(pdf, config=None) -> dict` — the stage entry point, returning `{"pages", "text",
  "page_count"}`.

All three accept a path, raw `bytes`, or an open file object. All three are covered by
`tests/test_intake.py` against a committed fixture, `tests/data/sample.pdf`.

**The half that does not exist:**

- **The body / references split.** `locate_bibliography(pages)` exists as a stub in the
  same file and raises `NotImplementedError`. It is a signature and a docstring, nothing
  more. This is plain code when it lands — heading match plus a check that the following
  lines look like references. No model call.
- **The tables map.** Nothing calls `page.extract_tables()` anywhere in the repo. There
  is no table extraction of any kind.
- **The corrupt-page guards.** There are none. `extract_pages` will propagate whatever
  pdfplumber raises on a malformed page, and a whole-document failure takes the app down
  with it. The only guard that exists is in `app.py`, and it is a UX message for the
  different case of a PDF that parses fine but yields no text (a scan needing OCR).

So: whoever picks up P1 is finishing a file, not starting one, and the `malformed`
indicator from the contract is the one their guards will need to emit.

## What is safe to start right now

Statuses referenced below are the contract's four — `verified`, `needs_check`,
`conflict`, `unresolvable` — and the indicators are the six: `retracted`,
`version_mismatch`, `doi_mismatch`, `duplicate_entry`, `orphan`, `malformed`. Both sets
live in B1 and nowhere else yet, which is what makes B1 the gate.

**Arsha — start B1 today.** `src/contract.py` is yours and it is the critical path.
It must import nothing from `src/pipeline/` and nothing from `src/config.py`; the four
statuses and six indicators are data definitions and should not need a config read or a
model call. Everything downstream is waiting on the names you choose, so the shape
matters more than the polish.

**B1 blocks P2.** The extractor cannot normalize a reference into a status without the
status enum to normalize it into. Anyone tempted to start P2 by inlining their own copy
of the four statuses should not: that guarantees a rename conflict the day B1 lands.

**Nothing blocks A1, A2, R1, or R3's drafting.** These four can proceed in parallel with
B1, today:

- **A1 (critic)** can be drafted against `config.yaml` alone. `banned_terms` is already
  there and already readable via `src.config.banned_terms()`. A1 must not import
  `src/contract.py` — it reviews prose, not statuses — and must use
  `critic_temperature`, not `temperature`.
- **A2** — drafting is unblocked; confirm its definition against the plan before
  branching.
- **R1** — drafting is unblocked.
- **R3** — drafting is unblocked.

**Blocked, do not start:** P2 (needs B1), P6 (needs the stages it orchestrates, and
needs a decision on where it lives), R2 (needs at least one real stage to evaluate),
R4 (needs a merged B0 to fresh-clone).

**A rule for everyone regardless of module:** no module hardcodes a model name. Model
names come from `config.yaml` through `src.config.model_for(stage)`, and the CI check for
this is `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/`, which must find nothing.

## Deviations from the plan found in this tree

These are small and cheap to fix now. None of them are fixed in the B0 branch, because
B0 is a docs-and-skeleton branch and changing a stage signature is P-lane work.

1. **`judge.run` has no `fallback_fn` seam.** The plan requires the judge to take a
   `fallback_fn` defaulting to a stub, so the two lanes merge independently. Today the
   signature is `run(references, config)`. The seam has to be added by whoever lands P4,
   as `run(references, config, fallback_fn=None)`. It was deliberately not added in B0.
2. **The orchestrator has no home.** The plan has P6 taking a `judge_fn`, but there is no
   `src/orchestrator.py` and no orchestrator seam in `app.py` — `app.py` calls
   `intake.run` directly. P6 needs a decision: new module, or a function in `app.py`.
3. **Nothing outside tests reads any config key.** `src/config.py` and `src/llm.py` are
   both fully written and both entirely unexercised by the running app — `app.py` imports
   only `src.pipeline.intake`. This is correct for M0 (no model calls) but it means the
   config path has never run in anger. The first stage to land will be the first real
   test of it.
4. **`intake.run`'s `config` parameter is optional and ignored.** Every other stage takes
   `config` as a required positional. Intake is `config=None` and does not read it. Worth
   normalizing when P1 is finished, so the orchestrator can call all seven stages
   identically.
5. **Config keys the plan needs that do not exist yet.** Listed in full in
   [config_reference.md](config_reference.md) — the short version is P3's cache TTL, P4's
   per-request timeout, and P5's thresholds are all absent.
