# Architecture map

Replaces `docs/pipeline_stages.md`, which described a uniform seven-stage
`run(payload, config)` walk. That was never this project's architecture — it was invented
before the plan was in the repo. The real design is an orchestrator calling **named
functions across three packages**, each with a narrow published interface, arranged so
three people can build at once.

Ground truth: [module_implementation_plan.pdf](module_implementation_plan.pdf), Sections 3-6.

> **Any constraint here that you might want to argue with cites a D-number** —
> see [decisions.md](decisions.md), whose *Open at Sync 1* section is the short list of what
> is still unresolved. The realignment this file describes is **D-002**; the three-tier
> ownership rule that governs the import arrows is **D-008** (open).

## The flow

Seven steps, but not seven interchangeable stages — each has its own signature, its own
owner, and its own contract types.

```
   PDF
    |
    1. intake    ──▶  2. extract  ──▶  3. resolve  ──▶  4. evidence
                                                            |
   ledger  ◀──  6. priority  ◀──  5. verdict  ◀─────────────┘
    |
   Ledger JSON  ──▶  dashboard
```

| # | Step | Module | Owner | File | Kind | Consumes | Produces |
|---|------|--------|-------|------|------|----------|----------|
| 1 | **intake** | P1 | Ritik | `src/ingest/pdf_parser.py` | plain code | a PDF path | `ParsedDocument` |
| 2 | **extract** | P2 | Ritik | `src/ingest/extractor.py`, `claims.py` | **LLM** (`extractor`) | `ParsedDocument` | `list[Reference]`, `list[Claim]` |
| 3 | **resolve** | P4 (on P3's cache) | Ritik | `src/resolvers/resolver.py` | plain code + HTTP | `Reference` | `ResolvedSource \| None` |
| 4 | **evidence** | P5 | Ritik | `src/matching/evidence.py` | plain code | `Reference` + `ResolvedSource` + all refs | `MatchEvidence` |
| 5 | **verdict** | A1, or P5's rules as the default | Arsha / Ritik | `src/judge/agent.py` / `src/matching/rules.py` | **LLM** (`judge`), or pure code | `Reference` + `MatchEvidence` | `Verdict` |
| 6 | **priority** | P6 / A1 | Ritik / Arsha | `src/pipeline.py` / `src/judge/priority.py` | plain code | `MatchEvidence` + `Verdict` + citing-claim count | `float` 0-1 |
| 7 | **ledger** | P6 | Ritik | `src/pipeline.py` | plain code | all of the above | `Ledger` → JSON |

Two observations that matter more than the table:

**Only two steps call a model.** Step 2 (extraction) and step 5 (the judge). Everything
else is deterministic — which is what makes Roy's evaluation meaningful and what lets the
whole pipeline run end-to-end with **no AIR key at all** on the rule-based path. The plan
banks on this: P6 ships working at hour ~12 on rules alone, so A3 upgrades a working demo
rather than racing to create one.

**Step 5 has two implementations on purpose.** `rules.rule_based_status` (P5) is the
deterministic baseline; `judge_reference` (A1) is the LLM. R2's metrics table shows them
side by side, and the plan's risk register is explicit: if the LLM row is not clearly
better by Sync 2, demo the rule-based path and present the judge as assist mode. The
architecture survives either outcome — that is why step 5 is injected rather than
hardcoded.

## The three lanes

From Section 3. Arrows mean "must be on main before". The lanes never point at each other
until P6/A3 at the bottom — that is the whole design.

```
   B0 skeleton   B1 contract   B2 config   B3 label format
        \            |    \        |            |
   ═══════════════════════════════════════════════════════════
     RITIK (pipeline)   │   ARSHA (judge + UI)  │  ROY (proof)
   ═══════════════════════════════════════════════════════════
     P1 PDF intake      │   A1 judge agent      │  R1 corpus +
          │             │      (stub fallback)  │     golden labels
     P2 extractor (LLM) │   A2 dashboard        │       │
          │             │      (fixture-driven) │  R2 eval harness
     P3 cache layer     │                       │     (fixture mode)
          │             │                       │       │
     P4 resolvers       │                       │  R3 adversarial +
          │             │                       │     honesty suite
     P5 evidence + decision logic               │
          │                                     │
     P6 orchestrator (judge_fn injected) ───────┤
          │                                     │
     A3 integration: dashboard ↔ pipeline ↔ judge  (Arsha, Ritik reviews)
          │
     R2 full mode ──▶ R4 docs, metrics slide, demo
```

## The merge queue

Section 3, reproduced in full. Order is about conflicts and gates, not about who waits: at
any moment each person is building the next module in their own lane.

| # | Module | Owner | Gate / note |
|---|--------|-------|-------------|
| 1 | B0 skeleton | Ritik | already built — this PR |
| 2 | B1 contract + fixtures | Arsha | Ritik reviews schema; merging = contract v0 agreed |
| 3 | B2 config + settings | Ritik | tiny; parallel with #2 — **already inside #1** |
| 4 | B3 golden format + defect catalog | Roy | docs-only; parallel with #2-3 |
| 5 | P1 PDF intake | Ritik | plain code, no LLM |
| 6 | A1 judge agent | Arsha | fixtures + stub fallback; no pipeline imports |
| 7 | R1 corpus + golden labels | Roy | data-only; any time after #4 |
| 8 | P2 extractor (LLM) | Ritik | gated on determinism: 2 identical runs |
| 9 | A2 dashboard | Arsha | renders `ledger_fixture.json` fully offline |
| 10 | P3 cache layer | Ritik | pure code; P4 depends on it |
| 11 | R2 eval harness (fixture mode) | Roy | scores any Ledger JSON vs golden |
| 12 | P4 resolvers | Ritik | **SYNC 1 gate: contract freezes before this merges** |
| 13 | P5 evidence + decision logic | Ritik | signals + indicators + rule classifier |
| 14 | P6 orchestrator | Ritik | end-to-end on rule-based verdicts |
| 15 | A3 integration | Arsha | one-line `judge_fn` wiring + upload + progress strip |
| 16 | R2 full mode + R3 adversarial | Roy | **release gate** |
| 17 | R4 docs + metrics slide + demo | Roy | Arsha reviews docs |

## The two seams

Dependency injection at the lane boundary is what lets both sides merge and run
independently. Neither seam exists yet, because neither file exists yet — this is the
target, recorded so both are built the same way.

**1. The orchestrator takes `judge_fn`** — P6, `src/pipeline.py`:
<!-- The priority formula does NOT live here: it is src/priority.py, shared infra, shipping with B1 - D-009 (open). -->

```python
run(pdf_path, judge_fn=None, progress=None) -> Ledger
# judge_fn: Callable[[Reference, MatchEvidence], Verdict]
#   default: wrap rule_based_status into a Verdict
# progress: callback(stage_name, model_name) for the UI strip
```

P6 **does not import `src/judge`.** That is not a style preference — it is what allows P6
to merge at queue #14 while A1 is still being built, and it is asserted by
`tests/test_layout.py`.

**2. The judge takes `fallback_fn`** — A1, `src/judge/agent.py`:

```python
judge_reference(ref, ev, fallback_fn=None) -> Verdict   # NEVER raises
```

Default is a conservative stub: `needs_check` at confidence 0.3. The degradation ladder is
malformed JSON → one retry → `fallback_fn`; missing key or gateway error → `fallback_fn`
immediately. Which path produced a verdict is recorded in `judge_model`, so a run is
always honest about how it got its answers.

**The rule that makes both work: each defaults to a stub.** A seam with a required argument
is not a seam — it forces every caller, tests included, to know about a collaborator that
may not exist. Default it, and the two branches merge in either order.

**The joining point is one line**, in A3's `src/judge/wiring.py`:

```python
wired_judge = partial(judge_reference, fallback_fn=rules.rule_based_status)
# then: run(pdf_path, judge_fn=wired_judge)
```

That single line is the entire integration. The LLM judge gets the deterministic
classifier as its fallback, and the orchestrator gets the LLM judge — each lane having
been built and merged without ever importing the other.

## The contract

Every cross-module value is a type from `src/contract.py` (B1, Arsha's, merge-queue #2).
Quoted here because every step above refers to it, and frozen at Sync 1:

```
VerdictStatus  = verified | needs_check | conflict | unresolvable
INDICATORS     = retracted, version_mismatch, doi_mismatch,
                 duplicate_entry, orphan, malformed        (closed list)

Reference      {ref_id, raw_text, title?, authors[], year?, doi?, arxiv_id?,
                venue?, cited_by_claims[]}
Claim          {claim_id, text, page?, ref_ids[]}
ResolvedSource {provider, title?, authors[], year?, doi?, venue?,
                is_retracted, url?, raw}
MatchEvidence  {ref_id, resolved, title_similarity, author_overlap,
                year_delta?, doi_match, indicators[], notes[]}
Verdict        {ref_id, status, confidence, rationale, checks[], judge_model}
LedgerEntry    {reference, evidence, verdict, priority}
Ledger         {document_name, claims[], entries[], summary_counts()}
```

**`extraction_failed` is not a status.** A reference whose LLM extraction fails keeps its
`raw_text`, gets the `malformed` indicator, and stays in the ledger — extraction never
drops an entry. The plan states this outright in P2 step 3, so it needs nobody's
confirmation.

## Where the critic went

There is no critic stage. The plan folds it into **A1's `gate.py`**, and it is three code
checks, not a model call:

1. Every `ref_id` has exactly one verdict.
2. Status counts sum to the entry total.
3. Case-insensitive scan of every rationale and check against `banned_terms`.

Any failure re-judges that entry once, then forces `needs_check` with the rationale
`"judge output failed quality gate"` — a visible, honest failure rather than a silent one.
Because it is pure code, `models.critic` and `critic_temperature` were removed from
`config.yaml`: they were keys nothing could ever read. **That removal is D-004, and its
status is open** — if Arsha concludes `gate.py` wants a model of its own, the keys come back
and a test changes with them.

The same accusation guard appears at three layers, which is deliberate: A1's prompt hard
rules, `gate.py`'s scan, and R3's adversarial suite plus R2's release-blocking
zero-accusation check on the clean control.

## What exists today

| Path | State |
|------|-------|
| `src/ingest/pdf_parser.py` | **Real, half of P1.** `extract_pages`, `extract_text`, `run`. `parse_pdf` and `locate_bibliography` unwritten. |
| `src/ingest/__init__.py` | Package marker, P1-P2. |
| `src/resolvers/__init__.py` | Package marker, P3-P4. Empty otherwise. |
| `src/matching/__init__.py` | Package marker, P5. Empty otherwise. |
| `src/settings.py` | **Real.** The B2 loader, 11 readers, no defaults. |
| `src/llm.py` | **Real.** Gateway client from env. No caller yet. |
| `app.py` | **Real.** B0 shell: drop zone → raw text. Superseded by `dashboard/app.py` at A2, and **deleted in the A3 PR — D-010**. |
| `src/pipeline.py` | **Deliberately absent.** Reserved for P6; a test asserts it. |
| `src/contract.py` | **Deliberately absent.** B1, Arsha's; a test asserts it. |
| `src/judge/`, `dashboard/` | **Deliberately absent.** Arsha creates them on her branch. |
