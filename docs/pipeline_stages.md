# The seven-stage scaffold

`src/pipeline/` holds one module per stage. Every module exposes the same entry point:

```python
run(payload, config) -> result
```

That uniformity is the whole point of the package. It means the orchestrator can walk
`src.pipeline.STAGES` in order without a branch per stage, and it means a stage can be
swapped for a stub in a test without the caller knowing.

Only stage 1 does anything today. The other six raise `NotImplementedError` with a
message naming the milestone they land in, so a mis-wired call fails with a sentence you
can act on rather than an `AttributeError`.

> **Confidence note.** The `run()` signatures, the real-or-stub column, and the flow
> diagram below are read directly off commit `4328eb7` and are exact. The **plan module**
> column (which of P1-P6 / A1 fills each stage) is *inferred* from the B0 task brief,
> because the Module Implementation Plan is not checked into this repo. Cells marked
> `inferred` need one confirmation pass; cells marked `unknown` were not derivable at all.

## The flow

Reproduced verbatim from the docstring at the top of
[`src/pipeline/__init__.py`](../src/pipeline/__init__.py):

```
    PDF
     |
     1. intake           plain code   pull text out of the PDF, find the bibliography
     2. extractor        model        turn each raw reference string into JSON fields
     3. resolver         plain code   look each reference up in public catalogues
     4. judge            model        does the paper's citation match what we found?
     5. repro_extractor  model        pull the paper's reproducibility claims out
     6. repro_judge      model        are those claims actually backed by evidence?
     7. critic           model        review the write-up before a human sees it
     |
    Table of results
```

Two of the seven make no model call at all. `intake` is pdfplumber and plain Python;
`resolver` is HTTP requests against public catalogues plus a disk cache. Neither should
ever import `src/llm.py`, and neither has an entry under `models:` in `config.yaml` — so
`model_for("intake")` raises by design.

## Stage by stage

### 1. `intake` — real

```python
run(pdf: PdfSource, config: dict[str, Any] | None = None) -> dict[str, Any]
```
where `PdfSource = str | Path | bytes | IO[bytes]`.

| | |
|---|---|
| **Plan module** | P1, *partially landed* — see [module_status.md](module_status.md) |
| **Today** | **Real.** The only implemented stage. |
| **Consumes** | A PDF, as a path, raw bytes, or an open file object. `app.py` passes bytes from the uploader. |
| **Produces** | `{"pages": list[str], "text": str, "page_count": int}`. One list entry per page in page order; a page with no extractable text is `""` rather than dropped, so index equals page number minus one. |

Also exports `extract_pages(pdf)`, `extract_text(pdf)`, and `locate_bibliography(pages)`
— the last of which is a stub that raises and is the body/references split P1 still owes.

Note the signature irregularity: `config` is optional here and **ignored**, where every
other stage takes it as a required positional. Worth normalizing when P1 finishes.

### 2. `extractor` — stub

```python
run(references: list[str], config: dict[str, Any]) -> list[dict[str, Any]]
```

| | |
|---|---|
| **Plan module** | P2 — `inferred`. **Blocked on B1.** |
| **Today** | Raises `NotImplementedError("extractor.run: implemented in M1")` |
| **Consumes** | Raw reference strings, one per bibliography entry, from `intake.locate_bibliography`. |
| **Produces** | One dict per reference: authors, year, title, venue, volume, issue, pages, identifiers. Validated against a schema; on a bad reply, retry once, then mark the item `extraction_failed`. |

`extraction_failed` is a processing outcome, not one of the four contract statuses. A
reference that fails extraction cannot be assigned `verified` / `needs_check` /
`conflict` / `unresolvable`, because there is nothing to assign a status to — it should
surface with the `malformed` indicator instead. Confirm that boundary with Arsha when B1
lands rather than guessing at it here.

### 3. `resolver` — stub

```python
run(references: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]
```

| | |
|---|---|
| **Plan module** | P3 — `inferred` (it owns the cache TTL noted as P3 pre-work) |
| **Today** | Raises `NotImplementedError("resolver.run: implemented in M2")` |
| **Consumes** | Structured references from the extractor. |
| **Produces** | The same references with whatever the catalogue says attached. Responses cached on disk under `resolvers.cache_dir`, with `resolvers.timeout_seconds` as the HTTP timeout. |

This is where `retracted`, `doi_mismatch` and `orphan` get their evidence: the resolver
finds out what the catalogue actually holds, and the judge decides what the discrepancy
means. The resolver should attach facts, not verdicts.

### 4. `judge` — stub

```python
run(references: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]
```

| | |
|---|---|
| **Plan module** | P4 — `inferred` (it owns the LLM timeout noted as P4 pre-work) |
| **Today** | Raises `NotImplementedError("judge.run: implemented in M3")` |
| **Consumes** | Resolved references — what the paper cited alongside what the catalogue holds. |
| **Produces** | One verdict per reference: one of the four statuses, any of the six indicators that apply, and the reasoning. Validated JSON. |

**This signature is incomplete.** It is missing the `fallback_fn` seam the plan requires
— see the seams section below. Adding it is P4's job, not B0's.

### 5. `repro_extractor` — stub

```python
run(document_text: str, config: dict[str, Any]) -> list[dict[str, Any]]
```

| | |
|---|---|
| **Plan module** | `unknown` — not derivable from the B0 brief |
| **Today** | Raises `NotImplementedError("repro_extractor.run: implemented in M4")` |
| **Consumes** | The paper's full text (`intake.run(...)["text"]`), not the bibliography. This is the one stage that reads the body rather than the references. |
| **Produces** | The paper's own reproducibility claims as structured JSON — shared code, data, environment, hardware. |

### 6. `repro_judge` — stub

```python
run(claims: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]
```

| | |
|---|---|
| **Plan module** | `unknown` — not derivable from the B0 brief |
| **Today** | Raises `NotImplementedError("repro_judge.run: implemented in M4")` |
| **Consumes** | Extracted claims from stage 5. |
| **Produces** | One verdict per claim — how well the evidence backs it. Validated JSON. |

The banned terms matter most here. A claim with no supporting artifact is
`unresolvable`, and the write-up must not call it `irreproducible` — that word is in
`banned_terms` precisely because this stage is where the temptation arises.

### 7. `critic` — stub

```python
run(report: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]
```

| | |
|---|---|
| **Plan module** | A1 — `inferred` (A1 is named as the `banned_terms` consumer) |
| **Today** | Raises `NotImplementedError("critic.run: implemented in M5")` |
| **Consumes** | The assembled write-up, after both judges. |
| **Produces** | The write-up plus a pass/fail and what to change. |

Two hard constraints, both already expressed in `config.yaml` and both easy to break
without any test failing:

1. **A different model family from the judge.** `models.critic` is a Google model where
   the judges are Qwen. Point it at a Qwen model and the stage still runs, still passes,
   and stops catching the judges' blind spots.
2. **`critic_temperature`, not `temperature`.** Call
   `config.temperature_for("critic")` and you get the right key automatically — `0.0`.
   Reading `settings["temperature"]` directly gets you `0.1` and a non-deterministic gate.

## Dependency-injection seams

The plan requires two seams so the P-lane and A-lane can merge independently. Neither
exists in the tree yet; both are recorded here so they get built the same way by whoever
gets there first.

**1. The orchestrator takes `judge_fn`.**

```python
def run_pipeline(pdf, config, judge_fn=judge.run):
    ...
```

So the P-lane can develop the orchestrator against a stub judge while the A-lane is
still writing the real one, and neither branch blocks the other.

**2. The judge takes `fallback_fn`.**

```python
def run(references, config, fallback_fn=None):
    ...
```

For when the primary judge model is unavailable or its reply fails schema validation
twice. Defaulting to `None` (or to a stub that returns `needs_check` for everything) means
the judge is callable before any fallback exists.

**The rule that makes both work: each defaults to a stub.** A seam with a required
argument is not a seam — it forces every caller, including tests, to know about a
collaborator that may not be written yet. Default it, and both lanes merge in either
order.

**Current state of both seams, stated plainly:** neither is implemented.
`judge.run(references, config)` has no third parameter, and there is no orchestrator
module at all — `app.py` calls `intake.run` directly. P4 owns adding `fallback_fn`; P6
owns creating the orchestrator and deciding whether it is a new `src/orchestrator.py` or
a function in `app.py`. Doing this in B0 would have been feature code on a docs branch.

## The contract test

[`tests/test_pipeline_contract.py`](../tests/test_pipeline_contract.py) enforces the
uniformity this file describes: all seven stages are declared in `STAGES` in order, each
module exposes a callable `run`, and each has a module docstring. It is 15 of the 29
tests. If you add a stage, add it to `STAGES` or the suite tells you.
