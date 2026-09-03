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

## 1:05 — S0 MERGED
branch: ritik/s0-status -> main @ 9b7af83
tests: 162 passed
publishes: scripts/update_status.py (STATUS.md generator; --check exits 1 if stale, --stdout prints), .githooks/{post-commit,post-merge}, scripts/install_hooks.sh, progress/<you>.md block format
notes: STATUS.md is generated - never hand-edit it. Run `bash scripts/install_hooks.sh` once per clone. Guard fix in 4dcef20: the Action's recursion guard was skipping real pushes.
next: P1, ETA 2:05

## 2:00 — P1 MERGED
branch: ritik/p1-intake -> main @ 6503b09
tests: 189 passed
publishes: parse_pdf(path, name=None) -> ParsedDocument(name: str, pages: list[str], tables: list, body_text: str, references_text: str, ref_start_page: int | None, notes: list[str]); ref_start_page is 1-BASED so pages[ref_start_page-1] is that page; run(pdf, config) now takes config as a REQUIRED positional
notes: extract_pages/extract_text/locate_bibliography are internals now - import parse_pdf. Extraction passes x_tolerance_ratio=0.15 because pdfplumber's default glues words on both real papers. references_text carries a 26% appendix tail on sample.pdf - P2 must cut at the last entry marker. .gitignore's `data/` was swallowing tests/data fixtures; anchored to /data/.
next: P2, ETA 3:00

## 2:15 — P2 MERGED
branch: ritik/p2-extractor -> main @ c9ab30b
tests: 241 passed
publishes: extract_references(doc, config=None, client=None) -> list[Reference]; extract_claims(doc, refs) -> list[Claim] (plain regex, fills Reference.cited_by_claims in place); split_entries(references_text) -> list[str] (plain code, no model); is_malformed(ref) -> bool. MALFORMED MECHANISM: derived predicate, is_malformed(ref) == (ref.title is None) - Reference forbids extra fields, so P5 stamps Indicator.MALFORMED on exactly the set is_malformed() returns True for. ref_id = R01..R40 per eval/golden/FORMAT.md; claim_id = C01.. same width rule.
notes: 40 entries from sample.pdf, 34 from plos_sample.pdf, 0 malformed on either. Determinism gate PASSES but see D-101 - the guarantee is the disk cache, not the model; do not score `venue`. Cold 46s/40 entries, warm 0.006s. Bump prompts.PROMPT_VERSION when you touch the prompt, it is in the cache key.
next: P3, ETA 3:15
