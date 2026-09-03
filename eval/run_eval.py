"""Score pipeline Ledger JSON against the golden labels and print the metrics table.

Phase 1 is ``--fixtures`` only -- it scores any Ledger JSON that already exists on disk,
which is why it lands before the pipeline is finished. ``--full`` (import ``src.pipeline``,
run the corpus end to end, determinism and latency rows) is REPLAN-cut to Phase 2 row 1.

    python eval/run_eval.py --fixtures <ledger.json> [<ledger2.json> ...]
                            [--labels-dir eval/golden]

Which label file applies is resolved from the ledger's own ``document_name`` against
``--labels-dir``, so a fixture ledger whose labels are deliberately not corpus ground truth
is scored by pointing ``--labels-dir`` somewhere else (see ``eval/golden_fixtures/``).

Exit codes -- the release gate is the exit code, not a line of prose in the output:

    0   every gate clean
    1   RELEASE GATE FAIL: conflict on an injected:false row, or a banned term in a
        rationale, a check or an evidence note (D-019)
    2   hard error: a ref_id join mismatch (D-026), a missing or malformed label file

Offline: no network, no key. Vocabulary comes from ``src.contract`` and the banned-term
list from ``src.settings.banned_terms()`` -- never a private copy of either.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from src.contract import Indicator, VerdictStatus, load_ledger
from src.settings import banned_terms, model_for, temperature_for

GOLDEN = HERE / "golden"
OUTPUTS = HERE / "outputs"

STATUSES = [s.value for s in VerdictStatus]
INDICATOR_VALUES = {i.value for i in Indicator}
LICENSES = {"CC-BY", "CC-BY-SA", "CC0", "PMC-OA", "arXiv-perpetual"}
TOP_LEVEL = {"document", "control", "source", "labels"}
SOURCE_KEYS = {"license", "origin_url", "origin_file"}
LABEL_KEYS = {"ref_id", "defect_id", "expected_status", "expected_indicators",
              "defect", "injected", "verified_by", "verified_on"}

# The stages that own a model in config.yaml. Printed in the header so the metrics table
# says what produced the numbers rather than the reader having to trust a slide.
MODEL_STAGES = ("extractor", "judge")


class HardError(Exception):
    """A join or label-file failure. Never a silent miss -- exit code 2."""


# --------------------------------------------------------------------------- labels


def resolve_label_path(document_name: str, labels_dir: Path) -> Path:
    """``Ledger.document_name`` -> its label file.

    Two candidates, in order: the name as printed, then the name with a ``.pdf`` suffix
    dropped. D-025 says ``document`` matches ``Ledger.document_name``, and the Phase 1
    labels read "paper1" while P6's ledgers are not yet on main to confirm against -- so
    both spellings resolve rather than one of them being a silent miss.
    """
    stem = document_name[:-4] if document_name.lower().endswith(".pdf") else document_name
    candidates = [labels_dir / f"{document_name}.json"]
    if stem != document_name:
        candidates.append(labels_dir / f"{stem}.json")
    for path in candidates:
        if path.name == "EXAMPLE.json":
            continue  # the specimen is read by humans, never scored -- FORMAT.md
        if path.is_file():
            return path
    tried = ", ".join(str(p) for p in candidates)
    available = sorted(p.name for p in labels_dir.glob("*.json")) if labels_dir.is_dir() else []
    raise HardError(
        f"no label file for document_name {document_name!r}.\n"
        f"  tried:     {tried}\n"
        f"  available: {', '.join(available) or '(none)'}\n"
        f"  pass --labels-dir if this ledger's labels live outside {labels_dir}."
    )


def load_labels(path: Path) -> dict:
    """Read one label file, failing loudly on anything FORMAT.md does not permit.

    An unrecognised key is a hard error and not an ignored key: a typo'd key name is
    otherwise indistinguishable from a missing label. Top-level keys prefixed with ``_``
    are the one exemption -- they carry a human note and cannot be a typo of a schema key.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HardError(f"{path}: cannot read label file: {exc}") from exc

    top = {k for k in data if not k.startswith("_")}
    if top != TOP_LEVEL:
        raise HardError(
            f"{path}: top-level keys are {sorted(top)}, expected {sorted(TOP_LEVEL)}"
        )
    if set(data["source"]) != SOURCE_KEYS:
        raise HardError(f"{path}: source keys are {sorted(data['source'])}")
    if data["source"]["license"] not in LICENSES:
        raise HardError(f"{path}: license {data['source']['license']!r} is outside the allowed set")
    if not data["labels"]:
        raise HardError(f"{path}: labels is empty")

    seen: set[str] = set()
    for label in data["labels"]:
        unknown = set(label) - LABEL_KEYS
        if unknown:
            raise HardError(f"{path}: label {label.get('ref_id')!r} has unknown keys {sorted(unknown)}")
        ref_id = label["ref_id"]
        if ref_id in seen:
            raise HardError(f"{path}: duplicate ref_id {ref_id!r} in the labels")
        seen.add(ref_id)
        if label["expected_status"] not in STATUSES:
            raise HardError(f"{path}: {ref_id} expected_status {label['expected_status']!r} is not a status")
        indicators = label["expected_indicators"]
        bad = [i for i in indicators if i not in INDICATOR_VALUES]
        if bad:
            raise HardError(f"{path}: {ref_id} expected_indicators has non-vocabulary {bad}")
        if len(set(indicators)) != len(indicators):
            raise HardError(f"{path}: {ref_id} expected_indicators has duplicates {indicators}")
        if label["injected"] and not label.get("defect_id"):
            raise HardError(f"{path}: {ref_id} is injected:true with no defect_id")
    return data


# --------------------------------------------------------------------------- scoring


def is_trap(rows: list[dict]) -> bool:
    """A version-pair false-alarm trap, derived from label shape rather than a defect_id.

    A trap expects ``verified`` while ``version_mismatch`` fires -- getting it right means
    not raising a conflict (D-013, D-014). Deriving it means Phase 2's additional traps
    need no edit here.
    """
    return all(
        row["expected_status"] == VerdictStatus.VERIFIED.value
        and Indicator.VERSION_MISMATCH.value in row["expected_indicators"]
        for row in rows
    )


def scan_banned(text: str | None, terms: list[str]) -> list[str]:
    """Banned terms in one string, case-insensitive substring.

    Substring, not word-boundary, to match ``gate.py``'s documented semantics: "fraud" has
    to catch "fraudulent". The harness gate must never be weaker than the judge's own.
    """
    lowered = (text or "").lower()
    return [t for t in terms if t.lower() in lowered]


def score_document(ledger_path: Path, labels_dir: Path, terms: list[str]) -> dict:
    """Join one ledger to its label file and score every row. Raises HardError on a join gap."""
    ledger = load_ledger(ledger_path)
    label_path = resolve_label_path(ledger.document_name, labels_dir)
    labels = load_labels(label_path)

    by_ref = {label["ref_id"]: label for label in labels["labels"]}
    entries = {entry.reference.ref_id: entry for entry in ledger.entries}

    label_ids, ledger_ids = set(by_ref), set(entries)
    if label_ids != ledger_ids:
        raise HardError(_join_report(ledger_path, label_path, sorted(ledger_ids), sorted(label_ids)))

    rows: list[dict] = []
    for ref_id in sorted(ledger_ids):
        label, entry = by_ref[ref_id], entries[ref_id]
        observed_status = entry.verdict.status
        observed_status = getattr(observed_status, "value", observed_status)
        observed = {getattr(i, "value", i) for i in entry.evidence.indicators}
        expected = set(label["expected_indicators"])
        hits = scan_banned(entry.verdict.rationale, terms)
        for check in entry.verdict.checks:
            hits += [t for t in scan_banned(check, terms) if t not in hits]
        for note in entry.evidence.notes:
            hits += [t for t in scan_banned(note, terms) if t not in hits]
        rows.append({
            "ref_id": ref_id,
            "defect_id": label.get("defect_id"),
            "injected": label["injected"],
            "defect": label.get("defect", ""),
            "expected_status": label["expected_status"],
            "expected_indicators": sorted(expected),
            "observed_status": observed_status,
            "observed_indicators": sorted(observed),
            "matched": label["expected_status"] == observed_status and expected == observed,
            "banned": hits,
        })

    return {
        "document": labels["document"],
        "control": labels["control"],
        "license": labels["source"]["license"],
        "ledger_path": str(ledger_path),
        "label_path": str(label_path),
        "rows": rows,
    }


def _join_report(ledger_path: Path, label_path: Path, ledger_ids: list[str], label_ids: list[str]) -> str:
    """The side-by-side id lists, so an off-by-one is diagnosable in one look (D-026)."""
    only_ledger = [i for i in ledger_ids if i not in set(label_ids)]
    only_labels = [i for i in label_ids if i not in set(ledger_ids)]
    width = max(len(ledger_ids), len(label_ids))
    lines = [
        f"ref_id join mismatch -- {len(ledger_ids)} ledger entries vs {len(label_ids)} labels."
        " This is a hard error, never a miss (D-026).",
        f"  ledger: {ledger_path}",
        f"  labels: {label_path}",
        "",
        f"  {'LEDGER':<12} {'LABELS':<12}",
        f"  {'-' * 12} {'-' * 12}",
    ]
    for i in range(width):
        left = ledger_ids[i] if i < len(ledger_ids) else ""
        right = label_ids[i] if i < len(label_ids) else ""
        flag = "" if left == right else "   <-- diverges here" if left and right else "   <-- unpaired"
        lines.append(f"  {left:<12} {right:<12}{flag}")
    lines += [
        "",
        f"  in the ledger, not labelled: {', '.join(only_ledger) or '(none)'}",
        f"  labelled, not in the ledger: {', '.join(only_labels) or '(none)'}",
        "",
        "  A constant offset across the whole list means the ids are shifted, not that the",
        "  classifier is broken -- fix the labels or the splitter, not the classifier.",
    ]
    return "\n".join(lines)


def aggregate(docs: list[dict]) -> dict:
    """Roll the scored documents into the numbers the table prints."""
    rows = [r for d in docs for r in d["rows"]]

    defects: dict[str, list[dict]] = {}
    for row in rows:
        if row["injected"] and row["defect_id"]:
            defects.setdefault(row["defect_id"], []).append(row)
    detected = {d: all(r["matched"] for r in rs) for d, rs in defects.items()}
    traps = {d: detected[d] for d, rs in defects.items() if is_trap(rs)}

    per_status = []
    for status in STATUSES:
        expected_rows = [r for r in rows if r["expected_status"] == status]
        observed_rows = [r for r in rows if r["observed_status"] == status]
        per_status.append({
            "status": status,
            "expected": len(expected_rows),
            "observed": len(observed_rows),
            "matched": sum(1 for r in expected_rows if r["matched"]),
        })

    verified = VerdictStatus.VERIFIED.value
    needs_check = VerdictStatus.NEEDS_CHECK.value
    conflict = VerdictStatus.CONFLICT.value

    return {
        "rows": rows,
        "defects": defects,
        "detected": detected,
        "traps": traps,
        "per_status": per_status,
        "misses": [r for r in rows if not r["matched"]],
        # RELEASE-BLOCKING, both of them (D-019).
        "conflict_on_clean": [r for r in rows if not r["injected"] and r["observed_status"] == conflict],
        "banned": [r for r in rows if r["banned"]],
        # Reported, non-blocking. A false alarm is LABEL DIVERGENCE: the label expected
        # verified and the tool asked for a human. An injected:false row the labels
        # already expect on needs_check -- the control's duplicate pair -- is a match, and
        # gets its own line so it cannot read as a failure.
        "false_alarms": [r for r in rows
                         if r["observed_status"] == needs_check and r["expected_status"] == verified],
        "expected_needs_check": [r for r in rows
                                 if r["observed_status"] == needs_check
                                 and r["expected_status"] == needs_check and r["matched"]],
    }


# --------------------------------------------------------------------------- report


def render(docs: list[dict], agg: dict) -> tuple[str, bool]:
    """The plain-text metrics table. Returns the text and whether a release gate failed."""
    rows = agg["rows"]
    n_defects = len(agg["defects"])
    n_detected = sum(1 for v in agg["detected"].values() if v)
    n_traps = len(agg["traps"])
    n_traps_ok = sum(1 for v in agg["traps"].values() if v)
    failed = bool(agg["conflict_on_clean"] or agg["banned"])

    out: list[str] = []
    add = out.append

    add("# ForkTheSource -- eval metrics")
    add("")
    add(f"generated:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add(f"mode:        --fixtures ({len(docs)} ledger{'s' if len(docs) != 1 else ''} scored)")
    for stage in MODEL_STAGES:
        add(f"model:       {stage} = {model_for(stage)} @ temperature {temperature_for(stage)}")
    add(f"banned list: {len(banned_terms())} terms, read from settings.banned_terms()")
    add(f"denominator: {n_defects} distinct injected defect_ids in the loaded labels"
        " (derived, never hardcoded -- D-302)")
    add("")
    for d in docs:
        kind = "control" if d["control"] else "spiked"
        add(f"document:    {d['document']} ({kind}, {d['license']})")
        add(f"             ledger {d['ledger_path']}")
        add(f"             labels {d['label_path']}")
    add("")

    add("## Release gates (hard FAIL, non-zero exit -- D-019)")
    add("")
    add(f"  {'FAIL' if agg['conflict_on_clean'] else 'PASS'}  conflict on an injected:false reference: "
        f"{len(agg['conflict_on_clean'])}")
    for r in agg["conflict_on_clean"]:
        add(f"          {r['ref_id']}: expected {r['expected_status']}, observed conflict "
            f"{r['observed_indicators']}")
    add(f"  {'FAIL' if agg['banned'] else 'PASS'}  banned terms in a rationale, check or note: "
        f"{sum(len(r['banned']) for r in agg['banned'])}")
    for r in agg["banned"]:
        add(f"          {r['ref_id']}: {', '.join(r['banned'])}")
    add("")

    add("## Metrics")
    add("")
    add(f"  {'defect recall (all rows match)':<44} {n_detected}/{n_defects}")
    add(f"  {'version-pair traps not false-alarmed':<44} {n_traps_ok}/{n_traps}")
    add(f"  {'rows matching their label':<44} {sum(1 for r in rows if r['matched'])}/{len(rows)}")
    add(f"  {'false alarms (label divergence, non-blocking)':<44} {len(agg['false_alarms'])}")
    add(f"  {'needs_check rows matching their label':<44} {len(agg['expected_needs_check'])}")
    add("")

    add("## Per status")
    add("")
    add(f"  {'status':<14} {'expected':>9} {'observed':>9} {'matched':>8}")
    add(f"  {'-' * 14} {'-' * 9} {'-' * 9} {'-' * 8}")
    for s in agg["per_status"]:
        add(f"  {s['status']:<14} {s['expected']:>9} {s['observed']:>9} {s['matched']:>8}")
    add("")

    add("## Defects")
    add("")
    add(f"  {'defect_id':<11} {'rows':>4}  {'trap':<5} {'detected':<9} ref_ids")
    add(f"  {'-' * 11} {'-' * 4}  {'-' * 5} {'-' * 9} {'-' * 20}")
    for defect_id in sorted(agg["defects"]):
        drows = agg["defects"][defect_id]
        add(f"  {defect_id:<11} {len(drows):>4}  {'yes' if defect_id in agg['traps'] else '-':<5} "
            f"{'yes' if agg['detected'][defect_id] else 'NO':<9} "
            f"{', '.join(r['ref_id'] for r in drows)}")
    add("")

    if agg["misses"]:
        add("## Misses")
        add("")
        for r in agg["misses"]:
            add(f"  {r['ref_id']} ({r['defect_id'] or 'injected:false'})")
            add(f"      expected {r['expected_status']} {r['expected_indicators']}")
            add(f"      observed {r['observed_status']} {r['observed_indicators']}")
            if r["defect"]:
                add(f"      defect: {r['defect'][:160]}")
        add("")

    if agg["false_alarms"]:
        add("## False alarms -- label divergence, reported, NOT blocking")
        add("")
        for r in agg["false_alarms"]:
            add(f"  {r['ref_id']}: label expects verified, tool asked for a human check")
        add("")

    add(f"RESULT: {'RELEASE GATE FAIL' if failed else 'gates clean'}"
        f" -- recall {n_detected}/{n_defects}, traps {n_traps_ok}/{n_traps},"
        f" false alarms {len(agg['false_alarms'])}")
    return "\n".join(out) + "\n", failed


def write_metrics(text: str) -> Path:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_eval.py",
        description="Score Ledger JSON against the golden labels.",
    )
    parser.add_argument("--fixtures", nargs="+", metavar="LEDGER", required=True,
                        help="one or more Ledger JSON files to score")
    parser.add_argument("--labels-dir", default=str(GOLDEN), metavar="DIR",
                        help="where the label files live (default: eval/golden)")
    args = parser.parse_args(argv)

    labels_dir = Path(args.labels_dir)
    terms = banned_terms()

    try:
        docs = [score_document(Path(p), labels_dir, terms) for p in args.fixtures]
    except HardError as exc:
        print(f"\nHARD ERROR\n{exc}\n", file=sys.stderr)
        return 2

    agg = aggregate(docs)
    text, failed = render(docs, agg)
    print(text, end="")
    path = write_metrics(text)
    print(f"\nwritten: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
