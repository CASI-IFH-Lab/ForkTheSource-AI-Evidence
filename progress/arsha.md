# progress — arsha

**Append-only. Only arsha writes in this file.** Never edit or delete a block that
is already here, including your own — if you were wrong, append a correcting block.
Because exactly one person writes this file and only ever adds to the bottom, it can
never produce a merge conflict.

`scripts/update_status.py` parses this file into `STATUS.md`. Full format, the eight
status words, and how to retire a REQUEST: [progress/_FORMAT.md](_FORMAT.md).
The short version:

```
## <clock> — <MODULE> <STATUS-WORD>
branch: <branch> -> main @ <sha>          (omit unless MERGED)
tests: <n> passed
publishes: <the exact public symbols and signatures this module exports>
notes: <one or two lines>
next: <what you start now, with an ETA>
```

Status words, exactly these: `READY` `STARTED` `MERGED` `BLOCKED` `AHEAD`
`REQUEST` `OBJECTION` `SCOPE-CUT`. `<clock>` is hackathon-relative (`2:40`), not
wall time. One line per field.

## Worked example

The two blocks below are **inside a code fence, and the parser skips fenced text** —
they are here to copy, not to report. Your real blocks go after the horizontal rule,
unfenced, newest at the bottom.

```
## 1:05 — P2 MERGED
branch: arsha/p2-resolvers -> main @ 4f1a9c2
tests: 148 passed
publishes: resolve(ref: Reference, config: dict | None = None) -> ResolvedSource | None
notes: Crossref first, then arXiv; 404 and timeout both return None, never raise.
next: P3 evidence builder, ETA 2:10

## 1:30 — REQUEST -> @arsha
NEED: Verdict.rationale widened to str | None in src/contract.py
WHY: rule_based_status() has no rationale to give for the trivially-verified case.
UNBLOCKED MEANWHILE BY: passing the literal "rule: exact DOI match" for now.
BLOCKS ME AT: 2:30, when the judge starts writing real rationales.
```

---


## 0:15 — A1 READY
tests: 131 passed
publishes: nothing yet
notes: hour-zero checklist green — main @ 663db6a, check_secrets PASS, AIR gateway lists 48 models. System python here has no pytest, so every run below is ./.venv/Scripts/python.exe -m pytest, the same interpreter the 131 came from.
next: A1 judge on the fixture, ETA 2:20

## 0:20 — A1 STARTED
tests: 131 passed
publishes: nothing yet
notes: branch arsha/a1-judge, built against tests/fixtures/ledger_fixture.json only — zero dependency on Ritik's lane until A3.
next: A1 merge, ETA 2:20

## 1:55 — A1 OBJECTION
tests: 202 passed
publishes: nothing yet
notes: two Tier-1 shapes I would have drawn differently and did NOT change (R3) — Verdict has nowhere to put per-call latency, so A3's progress strip must carry timing outside the contract; and MatchEvidence.notes has no provenance, so the judge cannot tell a resolver note from a parser note. Both are fine for Phase 1 and both are PHASE2.
next: A1 merge, ETA 2:20

## 1:55 — REQUEST -> @ritik
NEED: P2's gateway calls to go through client.with_options(max_retries=0), the same one line src/judge/agent.py now uses.
WHY: the OpenAI SDK retries twice by default underneath us, so on top of llm.max_retries that is up to six requests per item — I measured 182 seconds of wall clock on ONE reference before it reached the gateway-error rung, and it also makes your per-stage progress timing uninterpretable.
UNBLOCKED MEANWHILE BY: nothing — A1 already does this in its own file, so this is a heads-up for your lane rather than a blocker for mine.
BLOCKS ME AT: never. Measurement and full reasoning: docs/decisions.md D-202.

## 1:56 — A1 OBJECTION
tests: 202 passed
publishes: nothing yet
notes: the AIR gateway is intermittently unreachable today and it is not us — three consecutive live-test runs with nothing changed went SKIPPED (APITimeoutError, 21.6s), passed (1.78s), passed (1.75s). When it answers, the judge answers in under two seconds. D-203 makes the live test skip rather than fail on that so nobody's pytest goes red because of the VPN; before the demo, run pytest tests/test_judge.py::test_live_air_smoke -rs and require passed, not skipped.
next: A1 merge, ETA 2:20
