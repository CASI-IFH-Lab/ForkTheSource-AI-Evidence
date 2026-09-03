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
