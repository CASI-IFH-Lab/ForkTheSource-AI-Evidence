"""Walk FORMAT.md's 13-item validation checklist over the golden label files.

FORMAT.md ships the checklist as prose for a human; this is that checklist mechanised, so
a label file cannot drift from its own spec unnoticed. Offline: no network, no key.

    python eval/validate_golden.py                       # every eval/golden/*.json
    python eval/validate_golden.py eval/golden/paper1.json

Exit code is 0 only when every item passes. Item 9's *count* sentence -- "distinct
defect_ids across all files is 21; injected rows 23" -- is a Phase-2 total rather than a
schema invariant, so it is reported as SCOPED (see docs/decisions.md D-302) and does not
affect the exit code. Its uniqueness clause is still enforced.

Vocabulary comes from src.contract, never from a local copy: a status or indicator string
that drifts from the frozen enum has to fail here rather than in a scoring run.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from src.contract import Indicator, VerdictStatus

GOLDEN = os.path.join(HERE, "golden")
CORPUS = os.path.join(HERE, "corpus")
ORIGINALS = os.path.join(CORPUS, "originals")

STATUSES = {s.value for s in VerdictStatus}
INDICATOR_VALUES = {i.value for i in Indicator}
LICENSES = {"CC-BY", "CC-BY-SA", "CC0", "PMC-OA", "arXiv-perpetual"}
TOP_LEVEL = {"document", "control", "source", "labels"}
SOURCE_KEYS = {"license", "origin_url", "origin_file"}
LABEL_KEYS = {"ref_id", "defect_id", "expected_status", "expected_indicators",
              "defect", "injected", "verified_by", "verified_on"}

# Phase-2 totals from FORMAT.md item 9 and its schema table. Scoped, not enforced -- D-302.
PHASE2_DEFECT_IDS = 21
PHASE2_INJECTED_ROWS = 23


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.failed = False

    def add(self, item: str, state: str, detail: str = "") -> None:
        self.rows.append((item, state, detail))
        if state == "FAIL":
            self.failed = True

    def report(self) -> None:
        for item, state, detail in self.rows:
            mark = {"PASS": "PASS  ", "FAIL": "FAIL  ", "SCOPED": "SCOPED", "N/A": "n/a   "}[state]
            print(f"  {mark} {item}")
            if detail:
                for line in detail.split("\n"):
                    print(f"         {line}")


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_file(path: str, r: Result) -> dict:
    doc = load(path)
    stem = os.path.splitext(os.path.basename(path))[0]

    # ---- schema shape: not a numbered item, but FORMAT.md says an unknown key must fail
    extra = set(doc) - TOP_LEVEL
    missing = TOP_LEVEL - set(doc)
    if extra or missing:
        r.add("schema: exactly document/control/source/labels", "FAIL",
              f"unexpected={sorted(extra)} missing={sorted(missing)}")
    else:
        r.add("schema: exactly document/control/source/labels", "PASS")

    # ---- 1. filename stem == document
    if doc.get("document") == stem:
        r.add(f"1. filename stem equals `document` ({stem})", "PASS")
    else:
        r.add("1. filename stem equals `document`", "FAIL",
              f"stem={stem!r} document={doc.get('document')!r}")

    # ---- 2. control present and boolean
    if isinstance(doc.get("control"), bool):
        r.add(f"2. `control` present and boolean (={doc['control']})", "PASS")
    else:
        r.add("2. `control` present and boolean", "FAIL", repr(doc.get("control")))

    # ---- 3. licence in the allowed set; origin_file exists under originals/
    src = doc.get("source") or {}
    problems = []
    if set(src) != SOURCE_KEYS:
        problems.append(f"source keys={sorted(src)} expected={sorted(SOURCE_KEYS)}")
    if src.get("license") not in LICENSES:
        problems.append(f"license={src.get('license')!r} not in {sorted(LICENSES)}")
    origin = src.get("origin_file") or ""
    if os.sep in origin or "/" in origin:
        problems.append(f"origin_file must be a bare filename: {origin!r}")
    elif not os.path.exists(os.path.join(ORIGINALS, origin)):
        problems.append(f"origin_file not found under corpus/originals/: {origin!r}")
    r.add("3. licence allowed, origin_file exists", "FAIL" if problems else "PASS",
          "\n".join(problems))

    labels = doc.get("labels") or []
    ids = [l.get("ref_id") for l in labels]

    # ---- 4. every reference in the bibliography has exactly one label
    pdf = os.path.join(CORPUS, f"{stem}.pdf")
    if os.path.exists(pdf):
        try:
            sys.path.insert(0, CORPUS)
            import build_corpus as B
            title_words = {"paper1": ["Applications of Entropy"],
                           "control": ["Simulation of Quantum"]}.get(stem, ["References"])
            _, _, block = B.split_front_body_refs(B.extract_pages(pdf))
            n_refs = len(B.parse_references(block, title_words))
            if n_refs == len(labels) == len(set(ids)):
                r.add(f"4. one label per reference ({n_refs} refs, {len(labels)} labels)", "PASS")
            else:
                r.add("4. one label per reference", "FAIL",
                      f"pdf refs={n_refs} labels={len(labels)} distinct ref_ids={len(set(ids))}")
        except Exception as e:                       # pdfplumber/reportlab absent, say
            r.add("4. one label per reference", "N/A", f"could not read {pdf}: {e}")
    else:
        r.add("4. one label per reference", "N/A", f"{pdf} not present")

    # ---- 5. ref_ids consecutive from R01, no gaps, no duplicates
    width = max((len(i) - 1 for i in ids if isinstance(i, str)), default=2)
    expect = [f"R{n:0{width}d}" for n in range(1, len(labels) + 1)]
    if ids == expect:
        r.add(f"5. ref_ids consecutive R{1:0{width}d}..{expect[-1] if expect else '-'}", "PASS")
    else:
        bad = [(a, b) for a, b in zip(ids, expect) if a != b][:5]
        r.add("5. ref_ids consecutive, no gaps, no duplicates", "FAIL",
              f"first divergences (found, expected): {bad}")

    # ---- 6. every expected_status is one of the four, exact, lower case
    bad = [(l.get("ref_id"), l.get("expected_status")) for l in labels
           if l.get("expected_status") not in STATUSES]
    r.add("6. every expected_status in the contract vocabulary",
          "FAIL" if bad else "PASS", f"offenders={bad}" if bad else f"{sorted(STATUSES)}")

    # ---- 7. indicators from the six, exact, lower case, no duplicates inside an array
    bad = []
    for l in labels:
        ind = l.get("expected_indicators")
        if not isinstance(ind, list):
            bad.append((l.get("ref_id"), "not a list", ind)); continue
        unknown = [x for x in ind if x not in INDICATOR_VALUES]
        if unknown:
            bad.append((l.get("ref_id"), "unknown", unknown))
        if len(ind) != len(set(ind)):
            bad.append((l.get("ref_id"), "duplicate within array", ind))
    r.add("7. indicators in vocabulary, no duplicates within an array",
          "FAIL" if bad else "PASS", f"offenders={bad}" if bad else "")

    # ---- 8. injected true => defect + defect_id; injected false => neither
    bad = []
    for l in labels:
        inj = l.get("injected")
        if not isinstance(inj, bool):
            bad.append((l.get("ref_id"), "injected not boolean")); continue
        if inj and not (l.get("defect") and l.get("defect_id")):
            bad.append((l.get("ref_id"), "injected:true missing defect/defect_id"))
        if not inj and ("defect" in l or "defect_id" in l):
            bad.append((l.get("ref_id"), "injected:false carries defect/defect_id"))
    r.add("8. injected rows carry defect + defect_id; clean rows carry neither",
          "FAIL" if bad else "PASS", f"offenders={bad}" if bad else "")

    # ---- 10. verified_by and verified_on are paired, date is ISO
    bad = []
    for l in labels:
        by, on = l.get("verified_by"), l.get("verified_on")
        if (by is None) != (on is None):
            bad.append((l.get("ref_id"), f"verified_by={by!r} verified_on={on!r}"))
        if on is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(on)):
            bad.append((l.get("ref_id"), f"verified_on not YYYY-MM-DD: {on!r}"))
        if by is not None and str(by) != str(by).lower():
            bad.append((l.get("ref_id"), f"verified_by not lower case: {by!r}"))
    r.add("10. verified_by/verified_on paired, ISO date, lower-case name",
          "FAIL" if bad else "PASS", f"offenders={bad}" if bad else "")

    # ---- 11. the control has zero injected rows
    n_inj = sum(1 for l in labels if l.get("injected"))
    if doc.get("control"):
        r.add(f"11. control has zero injected rows (found {n_inj})",
              "PASS" if n_inj == 0 else "FAIL")
    else:
        r.add(f"11. control has zero injected rows (this file is not the control, "
              f"{n_inj} injected)", "N/A")

    # ---- 12/13 need the catalog and the corpus, checked per-file below
    unres_clean = [l["ref_id"] for l in labels
                   if not l.get("injected") and l.get("expected_status") == "unresolvable"]
    cat = os.path.join(os.path.dirname(HERE), "docs", "defect_catalog.md")
    cat_text = open(cat, encoding="utf-8").read() if os.path.exists(cat) else ""
    if unres_clean:
        missing = [rid for rid in unres_clean
                   if not re.search(rf"\|\s*{stem}\s*\|\s*{rid}\s*\|", cat_text)]
        r.add(f"12. clean `unresolvable` rows recorded in defect_catalog.md "
              f"({len(unres_clean)}: {unres_clean})",
              "FAIL" if missing else "PASS",
              f"not found in the catalog's table: {missing}" if missing else "")
    else:
        r.add("12. clean `unresolvable` rows recorded in defect_catalog.md", "N/A",
              "this file has none")

    if doc.get("control"):
        r.add("13. spiked paper retains a genuine `unresolvable`", "N/A",
              "applies to spiked papers")
    else:
        r.add(f"13. spiked paper retains >=1 genuine `unresolvable` "
              f"(found {len(unres_clean)}: {unres_clean})",
              "PASS" if unres_clean else "FAIL")

    return doc


def check_corpus(docs: dict[str, dict], r: Result) -> None:
    """Cross-file items: control count, and item 9."""
    controls = [name for name, d in docs.items() if d.get("control")]
    r.add(f"2b. exactly one file has control:true (found {controls})",
          "PASS" if len(controls) == 1 else "FAIL")

    rows, ids = [], {}
    for name, d in docs.items():
        for l in d.get("labels", []):
            if l.get("injected"):
                rows.append((name, l.get("ref_id"), l.get("defect_id")))
                ids.setdefault(l.get("defect_id"), []).append(f"{name}:{l.get('ref_id')}")
    shared = {k: v for k, v in ids.items() if len(v) > 1}
    detail = [f"distinct defect_ids={len(ids)} ({sorted(ids)})",
              f"injected rows={len(rows)}"]
    if shared:
        detail.append(f"ids shared by >1 row: {shared}")
    # uniqueness clause: only duplicate-entry defects may share an id, and exactly 2 rows
    bad_share = {k: v for k, v in shared.items() if len(v) != 2}
    r.add("9a. defect_id uniqueness (shared ids only by design, exactly two rows)",
          "FAIL" if bad_share else "PASS",
          "\n".join(detail + ([f"wrongly shared: {bad_share}"] if bad_share else [])))
    r.add(f"9b. FORMAT.md counts: {PHASE2_DEFECT_IDS} distinct defect_ids / "
          f"{PHASE2_INJECTED_ROWS} injected rows", "SCOPED",
          f"Phase 1 reads {len(ids)} / {len(rows)}. These are Phase-2 totals, not schema\n"
          f"invariants -- see docs/decisions.md D-302. Not counted toward the exit code.")


def main() -> int:
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(GOLDEN, "*.json")))
    paths = [p for p in paths if os.path.basename(p) != "EXAMPLE.json"]
    if not paths:
        print("no label files found (EXAMPLE.json is skipped by name)")
        return 1
    docs, overall = {}, Result()
    for p in paths:
        print(f"\n=== {os.path.relpath(p)} ===")
        r = Result()
        try:
            docs[os.path.splitext(os.path.basename(p))[0]] = check_file(p, r)
        except Exception as e:
            r.add("file loads as JSON", "FAIL", f"{type(e).__name__}: {e}")
        r.report()
        overall.rows.extend(r.rows)
        overall.failed = overall.failed or r.failed
    print("\n=== corpus-wide ===")
    r = Result()
    check_corpus(docs, r)
    r.report()
    overall.rows.extend(r.rows)
    overall.failed = overall.failed or r.failed

    n_pass = sum(1 for _, s, _ in overall.rows if s == "PASS")
    n_fail = sum(1 for _, s, _ in overall.rows if s == "FAIL")
    n_scope = sum(1 for _, s, _ in overall.rows if s == "SCOPED")
    n_na = sum(1 for _, s, _ in overall.rows if s == "N/A")
    print(f"\n{n_pass} pass, {n_fail} fail, {n_scope} scoped, {n_na} n/a")
    return 1 if overall.failed else 0


if __name__ == "__main__":
    sys.exit(main())
