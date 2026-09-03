# progress/ — the append-only lane log

One file per person: `ritik.md`, `arsha.md`, `roy.md`. **Each file is written by
exactly one person and only ever appended to**, so two people can never conflict in
here. Never edit or delete someone else's file, and never edit your own history —
if you were wrong, append a correcting block.

`scripts/update_status.py` parses these files to build `STATUS.md`, so the block
format is strict. A block that does not parse is reported as unparseable in
`STATUS.md` rather than crashing the tool, but it also will not show up as your
status — so keep to the shape.

## A status block

```
## <clock> — <MODULE> <STATUS-WORD>
branch: <branch> -> main @ <sha>
tests: <n> passed
publishes: <the exact public symbols and signatures this module exports>
notes: <one or two lines>
next: <what you start now, with an ETA>
```

- `<clock>` is hackathon-relative, `H:MM` (`0:15`, `2:40`), not wall time.
- `<MODULE>` is the lane id: `B1`, `P2`, `R4`, `S0`.
- The separator is an em dash (`—`); a plain `-` is also accepted.
- `branch:` is **omitted unless the status word is MERGED.**
- Every other field is one line. Wrap by rewriting shorter, not by continuing
  onto the next line — a continuation line is not part of the field.

## Status words

Exactly these, nothing else, upper case:

`READY` `STARTED` `MERGED` `BLOCKED` `AHEAD` `REQUEST` `OBJECTION` `SCOPE-CUT`

## A request block

```
## <clock> — REQUEST -> @<owner>
NEED: <the change, in their file, in one sentence>
WHY: <why you cannot proceed without it eventually>
UNBLOCKED MEANWHILE BY: <the fixture or stub you are using right now>
BLOCKS ME AT: <clock time when it becomes real>
```

## How a REQUEST or a BLOCKED block gets retired

`STATUS.md` shows **every** `REQUEST` and `BLOCKED` block in every file, from
anywhere in the file, until it is retired. It errs toward showing a stale request
rather than hiding a live one, because a hidden blocker is a person sitting idle.

A block is retired when the same person later appends a `MERGED` block **for the
same module**. Since the file is append-only, retiring is an append:

- `## 1:10 — P3 BLOCKED` is retired by a later `## 2:05 — P3 MERGED`.
- `## 1:30 — REQUEST -> @arsha` is retired by a later `## 2:20 — REQUEST MERGED`
  (a request heading names no module of its own, so `REQUEST` *is* its module).

Retire your requests. An `OPEN REQUESTS AND BLOCKERS` section that is 80% noise
gets skipped, and then the one real blocker in it gets skipped too.
