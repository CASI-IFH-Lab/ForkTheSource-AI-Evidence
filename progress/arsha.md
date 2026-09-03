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
