# progress — Roy (corpus, eval, demo)

## 0:15 — READY
branch: roy/r1-corpus @ 663db6a (level with main, 0 ahead / 0 behind)
tests: 131 passed (.venv, Python 3.13.14)
checks: check_secrets PASS · AIR gateway live, 48 models listed
state: eval/golden/FORMAT.md + EXAMPLE.json present; eval/corpus/ and the
       harness do not exist yet — R1 is greenfield from the format spec.
notes: main is at 663db6a, not the plan's a4d57dd (PR #8 arsha/b1-contract merged
       since the handoff docs were written). STATUS.md and progress/ did not exist;
       scripts/update_status.py is absent, so no status file to read before branching.
       Bare `python` on PATH is 3.14 without streamlit/pdfplumber and fails collection;
       all my commands use .venv/Scripts/python.exe.
       docs/decisions.md is ordered newest-first at the top, but per shared plan §8 my
       D-3NN entries go at the END of the file; the file is not reordered.
next: R1 — pick the two arXiv papers by hand, then inject the six defects. ETA 2:20.

## R1 step 3 — LABELS WRITTEN (uncommitted)
branch: roy/r1-corpus (not pushed)
files: eval/golden/paper1.json, eval/golden/control.json, eval/validate_golden.py,
       eval/check_registry.py, docs/defect_catalog.md (TBD cells for the six filled)
checklist: 26 pass, 0 fail, 1 scoped (item 9's counts, per D-302), 2 n/a — exit 0
notes: `document` is "paper1" / "control", NOT "paper1.pdf" / "control.pdf". D-025 says
       P6 "must not set Ledger.document_name to the PDF's basename-with-extension", and
       FORMAT.md checklist item 1 requires the stem to equal `document`; ".pdf" fails both.
       NEEDS CONFIRMATION against Ritik's P6 post at 4:30 — if P6 emits a different
       identifier, both label files and their filenames change together.
       Mandatory-row reasons for R02 / R19 / R30 are recorded in docs/defect_catalog.md,
       not in the label rows: FORMAT.md item 8 forbids a `defect` string on an
       `injected: false` row and the schema permits no other key.
       control R17/R18 are a duplicate pair present in the ORIGINAL bibliography, labelled
       needs_check + [duplicate_entry] per D-016. The clean control therefore expects TWO
       false alarms; that is the passing number, not a regression.
next: R1 step 4 — append D-301/D-302/D-303, then merge. ETA 2:20.

### REQUEST → @ritik  (R1 step 2)
NEED: reportlab added to requirements.txt (or requirements-dev.txt, your call).
WHY:  eval/corpus/build_corpus.py rebuilds the spiked corpus PDFs and imports it; a
      stranger cloning the repo cannot reproduce eval/corpus/ without it.
UNBLOCKED MEANWHILE BY: locally installed reportlab 5.0.1; the built PDFs are committed,
      so nothing downstream is blocked — only the rebuild is.
BLOCKS ME AT: nothing in Phase 1. Phase 2 corpus expansion if unresolved.
