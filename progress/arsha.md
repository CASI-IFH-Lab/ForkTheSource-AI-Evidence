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

## 2:20 — A2 STARTED
tests: 327 passed
publishes: render_ledger(ledger: Ledger) -> None
notes: branch arsha/a2-dashboard, cut from main @ ad6681c with P1-P4 already in. Built against src/contract.py and tests/fixtures/ledger_fixture.json only — no import of src/ingest, src/resolvers, src/matching or src/pipeline, asserted twice.
next: A2 merge, ETA 4:10

## 3:45 — A2 AHEAD
tests: 374 passed
publishes: render_ledger(ledger: Ledger) -> None · dashboard.theme.STAGE_KEYS · summary_rows/worklist_rows/signal_rows/entry_panel/progress_stages, all pure functions over a Ledger
notes: all three rows built — four counters with proportional bars, the seven-chip AIR strip naming the model per stage, the top-3 worklist and every entry as an expander with the as-printed/resolved pair and the signal table. doi_match renders three states, version_mismatch is deliberately not red, and the counts guard refuses to draw counters at all when counts_are_consistent() is false.
next: A2 PR, then A3 once P6 lands

## 3:45 — REQUEST -> @ritik
NEED: P6's progress callback to emit exactly these seven stage_name strings — intake, extract, resolve, evidence, verdict, priority, ledger — with the real model name on extract and verdict and None on the other five.
WHY: the AIR progress strip keys on those exact strings, so a mismatch lights no chip, raises no error, and silently kills the 0:20 demo beat where the AIR platform becomes visible — note the key is verdict, not judge, even though the chip is labelled "judge".
UNBLOCKED MEANWHILE BY: in A2 the strip renders statically from the ledger, reading the judge model off Verdict.judge_model, so nothing is blocked yet.
BLOCKS ME AT: 4:30, when A3 wires the live callback. Full entry: docs/decisions.md D-204.

## 4:05 — A1 MERGED
branch: arsha/a1-judge -> main @ ab06a80
tests: 397 passed, 1 skipped (the live AIR test, gateway unreachable at merge time — D-203)
publishes: judge_reference(ref, ev, fallback_fn=None) -> Verdict (NEVER raises) · gate_batch(verdicts, total: int) -> list[Verdict] · stub_status(ev) -> tuple[str, float, str] · src.judge.prompts.JUDGE_SYSTEM_PROMPT
notes: judge_model names the path on every verdict — the configured model, fallback:rule_based, fallback:stub, or gate-forced:<original>. Gate is three code checks, no model call (D-200 closes D-004). D-201 enforces the retraction floor and the parse-noise ceiling in code. D-202 switches off the SDK's own retry layer. @roy R3 can attack the real prompt now, offline.
next: A2 merge, then A3 once P6 lands

## 4:10 — A2 MERGED
branch: arsha/a2-dashboard -> main @ 9dbcd55
tests: 445 passed (443 passed, 2 skipped with the AIR credentials removed)
publishes: render_ledger(ledger: Ledger) -> None · dashboard.theme.STAGE_KEYS · summary_rows/headline/progress_stages/worklist_rows/signal_rows/entry_panel/lookup_url, all pure functions over a Ledger
notes: streamlit run dashboard/app.py renders any Ledger JSON offline. Four counters, the seven-chip AIR strip naming the model per stage, top-3 worklist, every entry as an expander. doi_match renders three states; version_mismatch is deliberately not red. D-204 pins the seven stage keys P6's progress callback must emit — that REQUEST to @ritik is still open.
next: A3 integration, blocked on P6

## 4:10 — A1 OBJECTION
tests: 445 passed
publishes: nothing new
notes: caught while merging A2 — the A1 test test_a_missing_api_key_falls_back_rather_than_raising patched dotenv.load_dotenv, but src/llm.py does "from dotenv import load_dotenv", so the patched name was never the one called. get_client() read .env back off disk and that "offline" test made a live gateway call, passing only on runs where the gateway happened to be down. Fixed in the A2 merge; the target is src.llm.load_dotenv. Worth knowing in every lane: patch the name in the module that CALLS it, not the module that defines it.
next: A3 integration, blocked on P6

## 4:11 — A2 OBJECTION
tests: 445 passed
publishes: nothing new
notes: heads-up for @ritik and @roy, not a request — with CROSSREF_MAILTO unset, 21 tests in tests/test_resolvers.py fail rather than skip. That is D-007 working as designed (crossref_mailto() must raise), but a stranger cloning the repo before setting .env sees 21 red instead of a clear message. Ritik's call whether that matters before the demo; my lane is unaffected and stays green with only the AIR credentials removed.
next: A3 integration, blocked on P6
