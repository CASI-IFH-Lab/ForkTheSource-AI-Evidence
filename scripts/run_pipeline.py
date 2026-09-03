"""P6's CLI. `python scripts/run_pipeline.py <pdf>` - one PDF in, one ledger out.

    python scripts/run_pipeline.py tests/data/sample.pdf
    python scripts/run_pipeline.py eval/corpus/paper1.pdf --output-dir /tmp/ledgers

Runs the rule-based path by default, which needs no AIR key on the judge side. The
extractor call is real, so the FIRST run on a paper needs `AIR_API_KEY`; after that P2's
disk cache serves it and the run is offline.

**The stage lines are the demo's visible AIR beat on the primary path.** The strip in the
dashboard is Arsha's; on the CLI this is the same information, and it prints the real
model name for the two stages that call one. Do not quiet it down.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.contract import STATUSES, Ledger  # noqa: E402
from src import pipeline  # noqa: E402
from src.pipeline import PipelineIntegrityError, ledger_path_for, run  # noqa: E402

#: How many worklist rows the CLI prints. The worklist is sorted by priority, so this is
#: "what a reviewer opens first", not a sample.
WORKLIST_LIMIT = 5

#: Truncation for a rationale on one terminal line.
_RATIONALE_WIDTH = 96


def _print_stage(stage: str, model_name: str | None) -> None:
    """The progress callback, printing as the run goes rather than after it.

    Flushed on every line: without it the whole strip appears at once when the process
    exits, which is precisely the opposite of what a progress display is for.
    """
    suffix = f"  [{model_name}]" if model_name else ""
    print(f"  - {stage:<9}{suffix}", flush=True)


def _shorten(text: str, width: int = _RATIONALE_WIDTH) -> str:
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= width else collapsed[: width - 1] + "…"


def _print_summary(ledger: Ledger, path: Path) -> None:
    counts = ledger.summary_counts()
    total = len(ledger.entries)

    print(f"\n{ledger.document_name}: {total} references, {len(ledger.claims)} claims")
    print("\nstatus counts")
    for status in STATUSES:
        print(f"  {status:<13} {counts[status]:>3}")
    print(f"  {'TOTAL':<13} {sum(counts.values()):>3}")

    indicators = {name: n for name, n in ledger.indicator_counts().items() if n}
    print("\nindicators   " + (", ".join(f"{k} {v}" for k, v in indicators.items()) or "none"))
    print(f"evidence coverage  {ledger.evidence_coverage():.0%}")

    print(f"\ntop {WORKLIST_LIMIT} worklist")
    for entry in ledger.worklist(WORKLIST_LIMIT):
        ref = entry.reference
        print(f"  {ref.ref_id}  {entry.priority:.3f}  {entry.verdict.status}")
        print(f"        {_shorten(ref.title or ref.raw_text, 88)}")
        print(f"        {_shorten(entry.verdict.rationale)}")

    if pipeline.last_run_notes:
        # D-109. A dropped identifier is the one thing this tool must never do quietly,
        # so it is printed above the ledger path rather than buried in a log.
        print(f"\nextraction corrections ({len(pipeline.last_run_notes)})")
        for note in pipeline.last_run_notes:
            print(f"  ! {_shorten(note, 110)}")

    print(f"\nledger  {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_pipeline",
        description="Run one PDF through the seven-stage pipeline and write its ledger.",
    )
    parser.add_argument("pdf", type=Path, help="path to the PDF")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="where to write <name>_ledger.json (default: data/output/)",
    )
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"no such file: {args.pdf}", file=sys.stderr)
        return 2

    print(f"running {args.pdf}")
    try:
        ledger = run(args.pdf, progress=_print_stage, output_dir=args.output_dir)
    except PipelineIntegrityError as exc:
        # The app-level refusal. Nothing was written, and that is the point.
        print(f"\nREFUSED: {exc}", file=sys.stderr)
        return 1

    _print_summary(ledger, ledger_path_for(ledger.document_name, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
