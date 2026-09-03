# Module status — where the repo actually is

Ground truth: [module_implementation_plan.pdf](module_implementation_plan.pdf), now in the
repo. Verified against commit `04b8ffe` on `main`, with **B0, B2 and B3 merged**.

The plan says what should be built; this file says what *is* built. Where they differ, the
**Actual** column is the one read off the working tree.

> **Any constraint in this file that you might want to argue with cites a D-number.** The
> reasoning is in [decisions.md](decisions.md), and the four still-open decisions are listed
> in its *Open at Sync 1* section. What actually happened, and what it cost, is in
> [worklog.md](worklog.md).

## The table

Owners and plan status are from the plan. Actual status is from the tree.

| ID | Module | Owner | Queue # | **Actual status in this repo** | Where |
|----|--------|-------|---------|-------------------------------|-------|
| B0 | App skeleton | Ritik | 1 | **DONE — ON `main`.** Merged in PR #1 at `a579dab`. App starts, drop zone accepts a PDF, raw text renders. Self-merged without review — **D-021**. | `main` |
| B1 | `src/contract.py` + fixtures | **Arsha** | 2 | **Not started. Critical path.** Does not exist and must not be created by anyone else. `tests/test_layout.py` asserts its absence as a live reminder — **D-006**. Also carries `src/priority.py` — **D-009**. | — |
| B2 | `config.yaml` + `src/settings.py` | Ritik | 3 | **DONE — ON `main`**, landed inside B0 and extended. See below. Critic keys dropped — **D-004**. | `main` |
| B3 | Golden-label format + defect catalog | **Roy** | 4 | **DONE — ON `main`.** Merged in PR #2 at `04b8ffe`. Written by Ritik in Roy's absence; **Roy owns it from here.** Nine rulings — **D-011**-**D-019**; one open constraint on P5 — **D-020**. | `main` |
| P1 | PDF intake & normalization | Ritik | 5 | **HALF DONE.** See the P1 section. | `src/ingest/pdf_parser.py` |
| P2 | Reference extractor (LLM) | Ritik | 8 | **Not started. Blocked on B1.** | → `src/ingest/extractor.py`, `claims.py`, `prompts.py` |
| P3 | Resolver cache layer (SQLite) | Ritik | 10 | **Not started.** Config keys now exist (`cache_ttl_hours`, `schema_version`). | → `src/resolvers/cache.py` |
| P4 | Scholarly resolvers | Ritik | 12 | **Not started.** Config keys now exist (`providers`, `mailto`, `timeout_seconds`). **`mailto` must move to `.env` as `CROSSREF_MAILTO` and P4 must refuse to start without it — D-007, decided and NOT yet implemented.** **Sync 1 gate.** | → `src/resolvers/{crossref,openalex,arxiv,resolver}.py` |
| P5 | Evidence builder + rule classifier | Ritik | 13 | **Not started.** All four thresholds now in config. | → `src/matching/{evidence,rules}.py` |
| P6 | Pipeline orchestrator | Ritik | 14 | **Not started.** `src/pipeline.py` deliberately does not exist — reserved, and asserted absent by a test. | → `src/pipeline.py`, `scripts/run_pipeline.py` |
| A1 | LLM judge agent (incl. the folded-in critic as `gate.py`) | **Arsha** | 6 | **Not started.** Unblocked by B1 + fixtures — no pipeline imports needed. `gate.py` is three code checks, not a model call — **D-004**. `tests/test_layout.py` needs amending first — **D-008**. | → `src/judge/{prompts,agent,gate,priority}.py` |
| A2 | Interactive dashboard | **Arsha** | 9 | **Not started.** Runs on `ledger_fixture.json` alone, fully offline. | → `dashboard/{app,theme}.py` |
| A3 | Integration (`judge_fn` wiring) | **Arsha** (Ritik reviews) | 15 | **Not started.** Needs P6 + A1 + A2 all on main. **Deletes `app.py`** — **D-010**. | → `src/judge/wiring.py`, `dashboard/app.py` |
| R1 | Spiked corpus + golden labels | **Roy** | 7 | **UNBLOCKED NOW** — B3 is on `main` and R1's only dependency is its format. Data-only. `eval/corpus/originals/` stays **tracked**. | → `eval/corpus/`, `eval/golden/`, `docs/defect_catalog.md` |
| R2 | Eval harness | **Roy** | 11 (fixtures) / 16 (full) | **Not started.** `eval/` is now tracked (B3 put `eval/golden/` in it). Recall is over `defect_id`s — **D-014**, **D-016**; the release gate is **D-019**. | → `eval/run_eval.py`, `eval/report.py` |
| R3 | Adversarial + honesty suite | **Roy** | 16 | **Not started.** Needs A1 on main to attack the real judge. | → `eval/adversarial.txt`, `eval/run_adversarial.py` |
| R4 | Docs, metrics slide, demo | **Roy** (Arsha reviews) | 17 | **Seeded.** [setup.md](setup.md) is written to R4's own acceptance bar: fresh clone + README → running app in under 10 minutes. | `README.md`, → `docs/architecture.md`, `deck/` |

## B2 landed inside B0 — do not open a second PR

Merge-queue item **#3 (B2, config)** was satisfied by the B0 branch. PR #1 closed
**#1 and #3 together** and is merged. Nobody needs to branch B2, and a B2 PR opened against this
tree will conflict with files that already exist.

The files that prove it:

| File | What it contributes to B2 |
|------|---------------------------|
| `config.yaml` | Models per role, temperature, thresholds, banned terms, cache settings, resolver settings, priority severities — every tunable the plan's B2 card lists. |
| `src/settings.py` | The loader, and the only code that opens `config.yaml`. Ten readers, no defaults anywhere. |
| `.env.example` | The credential template: `AIR_API_KEY`, `AIR_BASE_URL`, placeholder values. On `main` since `ffd0180`. |
| `tests/test_config.py` | 12 tests pinning the shape, including that plan-sourced thresholds are not casually retuned. |

B0 also went **beyond** the B2 card, closing the gaps found during the first docs pass:
`llm.timeout_seconds`, `llm.max_retries`, `resolvers.cache_ttl_hours`,
`resolvers.providers`, `resolvers.mailto`, `cache.schema_version`, the four
`thresholds`, and `priority.severity`. Full detail in
[config_reference.md](config_reference.md).

## P1 is half done — read this before branching it

Do not treat P1 as unstarted, and do not treat it as finished.

**The half that exists**, in [`src/ingest/pdf_parser.py`](../src/ingest/pdf_parser.py):

- `extract_pages(pdf) -> list[str]` — per-page pdfplumber extraction. One string per page
  in page order; a page with no extractable text is `""` rather than dropped, so index
  equals page number minus one.
- `extract_text(pdf) -> str` — those pages joined by a blank line.
- `run(pdf, config=None) -> dict` — returns `{"pages", "text", "page_count"}`.

All three accept a path, raw `bytes`, or an open file object, and all three are covered by
`tests/test_intake.py` against `tests/data/sample.pdf`.

**The half that does not exist.** Note especially the first item — the plan's *public
interface* for P1 is not what is currently there:

- **`parse_pdf(path) -> ParsedDocument` does not exist.** That is the only thing other
  modules are permitted to import from P1, and it is unwritten. `ParsedDocument` is
  `{name, pages, tables, body_text, references_text, ref_start_page}`. The three functions
  above are its future internals, not its interface — so P1 is not "add a function", it is
  "wrap what is there in the shape the plan promised P2 and A3".
- **The body/references split.** `locate_bibliography(pages)` is a stub that raises. Plain
  code when it lands: a case-insensitive regex for a `References`/`Bibliography` heading
  alone on its line.
- **The no-heading fallback.** Treat the last 15% of pages as the reference region and
  record that as a note. Nothing like it exists.
- **The tables map.** Nothing calls `extract_tables()` anywhere in the repo.
- **The per-page corrupt-page guard.** There is none. One corrupt page currently takes the
  whole run down, which is exactly what the P1 card forbids. The only guard that exists is
  in `app.py`, and it handles the different case of a PDF that parses but yields no text.

Whoever picks up P1 is finishing a file, not starting one.

## When each person can start what

| When | Ritik | Arsha | Roy |
|------|-------|-------|-----|
| **Right now** — B0, B2 and B3 are **on `main`** | **P1** — finish `src/ingest/pdf_parser.py`. Environment works. | **B1** (`src/contract.py` + fixtures + `src/priority.py`, **D-009**). Zero dependency on anything merged. This is the critical path and the whole team is waiting on the names you pick. | **R1** (spiked corpus + golden labels). B3's format is on `main`, so this is unblocked. Read `docs/defect_catalog.md` § *Handoff notes for Roy* first. |
| **On B1 merge** (#2) | **P2** unblocks — the extractor needs `Reference` to emit. | **A1** unblocks (judge agent, on fixtures + stub fallback). Then **A2** on `ledger_fixture.json`. | **R1** unblocks once B3 is in — golden labels need the contract's enum values. |
| **Then, in lane order** | P3 → P4 (Sync 1 gate) → P5 → P6 | A1 → A2 → wait for P6 | R1 → R2 fixture mode → R3 |
| **A3, queue #15** | Review only. | **A3 — the first and only time two lanes share a file.** | R2 full mode + R3 against the live judge. |

Two things worth stating plainly:

**A3 is the single integration moment, by design.** Until queue #15, the three lanes touch
no shared file. A3 is one line of wiring — `wired_judge = partial(judge_reference,
fallback_fn=rules.rule_based_status)` — plus the dashboard upload flow. That the
integration is one line rather than a big-bang merge is the payoff of the layout
realignment in this PR.

**B1 blocks P2, A1 and R1 — three modules across all three lanes.** It is the highest-
leverage hour anyone can spend right now. Nobody should work around it by inlining their
own copy of the four statuses; that guarantees a rename conflict the day B1 lands.
`tests/test_layout.py::test_contract_does_not_exist_yet` is there as the reminder, and
deleting it is part of B1's diff.

## File ownership — the disjointness *is* the parallel-work guarantee

> **This table has THREE tiers, not two — see D-008.** Shared infrastructure
> (`src/settings.py`, `src/llm.py`, `src/contract.py`, `src/priority.py`) is imported by
> anyone and redefined by nobody: the lane rule read literally would force a second gateway
> client inside `src/judge/`, which is the opposite of what it is for. **D-008 is open** —
> `tests/test_layout.py` must be amended before A1 lands, because as written it will flag
> Arsha's own intra-package imports as lane violations.

| Tier | Owner | Files |
|------|-------|-------|
| **Shared infra** | nobody exclusively | `src/settings.py`, `src/llm.py`, `src/contract.py`, `src/priority.py` |
| **Lane-exclusive** | **Ritik** | `src/ingest/`, `src/resolvers/`, `src/matching/`, `src/pipeline.py`, `config.yaml`, `app.py`, `scripts/` |
| **Lane-exclusive** | **Arsha** | `src/judge/`, `dashboard/` |
| **Lane-exclusive** | **Roy** | `eval/`, `docs/defect_catalog.md`, and `docs/` beyond the B0 docs |
| **Integration** | **Arsha** (Ritik reviews) | A3 only — the one moment two lanes share a file |

This table is not bureaucracy. Section 1 of the plan defines a module as *"one branch, one
owner, one PR, one public interface, and zero imports from another person's unmerged
work"*, and Section 3's three lanes never point at each other until P6/A3. Conflicts are
near-zero **because** the file sets do not intersect — so the moment two people edit one
file outside A3, the design has stopped protecting them.

Two mechanical consequences, both now enforced by tests:

- Nothing under `src/` may import `src/judge` or `dashboard` — the orchestrator takes
  `judge_fn` instead. `tests/test_layout.py` parses the AST of every file under `src/` to
  check this.
- `src/judge/` and `dashboard/` were deliberately **not** created in B0, even as empty
  packages. Arsha creates them on her branch, so the directories arrive with an owner
  attached.

## Deviations and gaps in this tree

**Not deviations, though the first docs pass called them that.** The `judge_fn` and
`fallback_fn` seams are not "missing": they live in `src/pipeline.py` (P6) and
`src/judge/agent.py` (A1), and neither file exists yet. A seam cannot be absent from a file
nobody has written. Their target signatures are recorded in
[architecture_map.md](architecture_map.md#the-two-seams) so both are built the same way by
whoever gets there first.

**Real, still open:**

1. **Nothing outside tests reads any config key.** `app.py` imports only
   `src.ingest.pdf_parser`, and `run()` ignores its `config` argument. `src/settings.py`
   and `src/llm.py` are fully written and entirely unexercised by the running app. Correct
   for B0 — there are no LLM calls — but the config path has never run in anger, and P1
   will be the first to exercise it.
2. **`settings.cache_dir()` has no caller**, not even a test that calls it for its return
   value. Its `mkdir` side effect is only incidentally covered. P3 will be its first real
   user.
3. **`tests/data/sample.pdf` vs the plan's `tests/sample.pdf`.** The P1 card names
   `tests/sample.pdf`; the fixture is at `tests/data/sample.pdf`. Left alone on purpose:
   the current fixture is a 970-byte synthetic PDF, and P1's card calls for a real
   open-access paper, so P1 replaces the file anyway and should settle the path then.
4. **`app.py` and `dashboard/app.py` will both exist.** B0's `app.py` is the skeleton
   shell; A2 builds the real dashboard. From A2 onward there are two Streamlit
   entrypoints, and R4's README needs to say which one a stranger should run.
5. **The README tagline overstates scope.** It says "Provenance + reproducibility
   verification"; reproducibility-claim extraction is not in the plan. Softened in this PR
   and flagged for R4 — see [descoped.md](descoped.md).
