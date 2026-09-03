# progress — ritik

**Append-only. Only ritik writes in this file.** Never edit or delete a block that
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
branch: ritik/p2-resolvers -> main @ 4f1a9c2
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

## 0:15 — S0 STARTED
tests: 131 passed
publishes: scripts/update_status.py (STATUS.md generator, --check for staleness), .githooks/{post-commit,post-merge}, scripts/install_hooks.sh
notes: Status system before P1 so the three lanes never have to ask "is P2 merged yet" in chat. STATUS.md answers it in one command.
next: S0 to main, then P1 pipeline skeleton, ETA 1:15
