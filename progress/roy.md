# progress — roy

**Append-only. Only roy writes in this file.** Never edit or delete a block that
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
branch: roy/p2-resolvers -> main @ 4f1a9c2
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

## 0:15 — R1 READY
tests: 131 passed
notes: check_secrets PASS; AIR gateway live, 48 models listed. eval/golden/FORMAT.md and
       EXAMPLE.json present; eval/corpus/ and the harness are greenfield. main was at
       663db6a, not the plan's a4d57dd. Bare `python` on PATH is 3.14 without
       streamlit/pdfplumber, so every command here uses .venv/Scripts/python.exe.
next: R1 — pick the two arXiv papers, inject the six defects. ETA 2:20.

## 2:10 — R1 MERGED
branch: roy/r1-corpus -> main (squash)
tests: 131 passed
publishes: eval/corpus/paper1.pdf (30 refs, positional R01-R30, 6 injections),
           eval/corpus/control.pdf (30 refs, zero injections),
           eval/golden/paper1.json, eval/golden/control.json,
           python eval/validate_golden.py, python eval/check_registry.py,
           python eval/corpus/build_corpus.py
notes: @ritik paper1.pdf is your P6 test input; ref_ids are positional R01-R30 and the
       2:30 alignment check runs against it. Spiked from arXiv 2503.02921, control from
       2410.12660, both CC-BY 4.0, untouched originals tracked in eval/corpus/originals/.
       Defect ids are the catalog's sparse ones (D01 D04 D07 D14 D16 D20), not D01-D06 —
       D-301. `document` is "paper1"/"control" with no .pdf, per D-025; needs confirming
       against your P6 post at 4:30. control R17/R18 are a duplicate pair present in the
       ORIGINAL bibliography, labelled needs_check + [duplicate_entry] per D-016, so the
       clean control expects TWO false alarms — that is the passing number.
       Validator: 26 pass, 0 fail, 1 scoped (item 9's counts, D-302), 2 n/a.
next: R2 eval harness, --fixtures first and complete. ETA 3:20.

## 2:10 — REQUEST -> @ritik
NEED: reportlab added to requirements.txt (or requirements-dev.txt, your call).
WHY: eval/corpus/build_corpus.py rebuilds the corpus PDFs and imports it; a stranger
     cloning the repo cannot reproduce eval/corpus/ without it.
UNBLOCKED MEANWHILE BY: locally installed reportlab 5.0.1, and the built PDFs are
     committed, so nothing downstream is blocked — only the rebuild is.
BLOCKS ME AT: nothing in Phase 1. Phase 2 corpus expansion if unresolved.

## 2:10 — R1 OBJECTION
notes: FORMAT.md item 8 forbids a `defect` string on an injected:false row and the schema
       permits no other key, so the reasons the three mandatory clean rows exist (paper1
       R02 genuine unresolvable, R19 the D-037 tripwire, R30 second genuine unresolvable)
       are recorded in docs/defect_catalog.md instead of in the label rows. Implemented as
       the format specifies; noting it because a reader of the label file alone cannot see
       why those three are there.
