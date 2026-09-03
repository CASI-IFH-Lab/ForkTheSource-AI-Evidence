# Arsha — progress

Append-only. One block per event. Status words: READY, STARTED, MERGED, BLOCKED, AHEAD,
REQUEST, OBJECTION, SCOPE-CUT. Newest at the bottom.

---

## 0:15 — READY

hour-zero checklist, all five lines:

```
git checkout main && git pull        -> main @ 663db6a
python --version                     -> 3.11 / 3.14.6 (repo .venv is the interpreter)
pytest                               -> 131 passed in 4.08s
./scripts/check_secrets.sh           -> PASS
python -c "...get_client().models.list()..."  -> AIR models: 48
```

note: on this machine the system `python` has no pytest. Everything below runs through
`./.venv/Scripts/python.exe -m pytest`. Same interpreter the 131 came from.

next: A1, ETA 2:20.

---

## 0:20 — A1 STARTED

branch: `arsha/a1-judge`
building against `tests/fixtures/ledger_fixture.json` only. No dependency on Ritik's lane.

---

## 1:5x — A1 READY TO MERGE

branch: `arsha/a1-judge`
tests: **202 passed, 1 skipped** (131 -> 202; the skip is the live AIR test, see below)
publishes:

```python
judge_reference(ref, ev, fallback_fn=None) -> Verdict      # NEVER raises
gate_batch(verdicts, total: int) -> list[Verdict]
stub_status(ev) -> tuple[str, float, str]                  # the default fallback
```

files: `src/judge/{__init__,prompts,agent,gate}.py`, `tests/test_judge.py`.

notes:

- `judge_model` records the path every time: the configured model name, `fallback:stub`,
  `fallback:rule_based`, or `fallback:<name>` for anything else injected. Honest
  degradation is a property you can read off the ledger.
- ladder: no JSON -> retry once (`llm.max_retries`) -> fallback. JSON with a bad schema,
  gateway error, timeout, or no key -> fallback immediately.
- two prompt rules are enforced in code as well, **D-201**: the retraction floor and the
  parse-noise ceiling.
- the gate is code-only, **D-200 closes D-004**. No critic key comes back.
- chaos test: 600 `judge_reference` calls against randomly-raising / garbage-returning
  clients across three shapes of evidence. Zero exceptions.

next: A2 dashboard, ETA 4:10.

---

## REQUEST — @ritik (1:5x)

```
NEED: P2's extractor to send its gateway calls through
      client.with_options(max_retries=0), the same one line agent.py now uses.
WHY:  the OpenAI SDK retries TWICE by default, underneath us and invisibly. On top of
      llm.max_retries that is up to six requests per item. Measured today: one
      reference took 182 SECONDS of wall clock to reach the "gateway error" rung
      because the SDK quietly re-sent it three times at llm.timeout_seconds each.
      On thirty references in P2 that is the demo. It also makes your per-stage
      progress callback report a number nobody can interpret.
      Full reasoning and the measurement: docs/decisions.md D-202.
UNBLOCKED MEANWHILE BY: nothing — A1 already does this in its own file. This is a
      heads-up for your lane, not a blocker for mine.
BLOCKS ME AT: never.
```

---

## OBJECTION — none to log against a frozen interface

`src/contract.py` and `src/priority.py` were fine to build A1 against. Two things I would
have shaped differently, recorded here rather than changed (R3), both **PHASE2**:

- `Verdict` has nowhere to put per-call latency, so the A3 progress strip will have to
  carry timing outside the contract. Not worth a Tier 1 change mid-flight.
- `MatchEvidence.notes` is `list[str]` with no provenance, so the judge cannot tell a
  resolver note from a parser note. It reads them all the same way. Fine for Phase 1.

---

## PHASE2 — noted while working, not acted on

- The gate's re-judge path takes a `rejudge_fn` and nothing supplies one yet. A3 or the
  Reviewer Brief should wire `partial(judge_reference, ...)` into it so a poisoned verdict
  gets a real second attempt instead of going straight to forced `needs_check`.
- An LLM critic that checks the rationale is actually supported by the evidence is a good
  idea — as a Phase 2 feature, with the config key added deliberately. See D-200.

---

## NOTE — the AIR gateway is flaky today, and it is not us

Observed during A1, with nothing changed between runs:

```
test_live_air_smoke -> SKIPPED (APITimeoutError)   21.6s
test_live_air_smoke -> passed                       1.78s
test_live_air_smoke -> passed                       1.75s
```

When it answers, the judge model answers in **under two seconds**. When it does not, it
does not answer at all. **D-203** makes the live test skip rather than fail on that, so
nobody's `pytest` goes red because of the VPN. Before the demo, run it and require
**passed**, not skipped.
