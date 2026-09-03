"""Warm every cache the demo touches, then prove the run works with the network off.

    python scripts/precache_demo.py                      # the spiked corpus paper
    python scripts/precache_demo.py path/to/other.pdf

Runs the paper end to end TWICE. The first run fills whatever is cold - the extractor's
per-entry replies (`cache/extractor_cache.json`) and every registry response
(`cache/`) - and the second proves the first one actually landed on disk rather than
merely appearing to work.

**The second run is the test, not a repeat.** A cache that is written but keyed wrong
looks identical to a warm cache on the run that wrote it; it only shows up on the next
one. So this compares the two runs on three things: the stored reply count must not grow,
the second run must be markedly faster, and the summary counts must be identical. Any of
those failing means the demo is one Wi-Fi outage away from a blank screen.

"It runs offline" is a line we say out loud on stage. `--check-offline` is how we earn it:
turn the Wi-Fi off and run it again.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingest import extractor  # noqa: E402
from src.pipeline import run  # noqa: E402

#: Roy's spiked corpus paper - the paper the demo actually runs.
DEFAULT_PDF = REPO_ROOT / "eval" / "corpus" / "paper1.pdf"

#: Below this the second run cannot have been making network calls. Generous on purpose:
#: this is a smoke threshold, not a benchmark.
_WARM_SECONDS = 8.0


def _stored_replies() -> int:
    return len(extractor._load_cache())


def _one_run(pdf: Path, label: str) -> tuple[dict[str, int], float, int]:
    started = time.perf_counter()
    ledger = run(pdf)
    elapsed = time.perf_counter() - started
    counts = ledger.summary_counts()
    stored = _stored_replies()
    print(
        f"  {label:<8} {elapsed:6.2f}s  {len(ledger.entries):>3} refs  "
        f"{stored:>4} stored replies  {counts}"
    )
    return counts, elapsed, stored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="precache_demo",
        description="Run the demo paper twice to warm every cache, then verify it is warm.",
    )
    parser.add_argument("pdf", type=Path, nargs="?", default=DEFAULT_PDF)
    parser.add_argument(
        "--check-offline",
        action="store_true",
        help="single run, asserting it completes without touching the network "
        "(turn the Wi-Fi off first - this does not turn it off for you)",
    )
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"no such file: {args.pdf}", file=sys.stderr)
        return 2

    if args.check_offline:
        print(f"offline check: {args.pdf}")
        counts, elapsed, _stored = _one_run(args.pdf, "offline")
        if elapsed > _WARM_SECONDS:
            print(
                f"\nSLOW: {elapsed:.1f}s. Either the cache is cold or something reached "
                "the network and timed out. Do not present this.",
                file=sys.stderr,
            )
            return 1
        print(f"\nOK - ran offline in {elapsed:.1f}s. Counts {counts}")
        return 0

    print(f"precaching {args.pdf}")
    first_counts, first_elapsed, first_stored = _one_run(args.pdf, "cold")
    second_counts, second_elapsed, second_stored = _one_run(args.pdf, "warm")

    problems: list[str] = []
    if second_stored != first_stored:
        problems.append(
            f"the second run stored {second_stored - first_stored} MORE replies - the "
            "cache key is not stable across runs, so the demo will call the model live"
        )
    if second_counts != first_counts:
        problems.append(f"summary counts differ: {first_counts} then {second_counts}")
    if second_elapsed > _WARM_SECONDS:
        problems.append(
            f"the second run took {second_elapsed:.1f}s, over the {_WARM_SECONDS:.0f}s "
            "warm threshold - something is still going to the network"
        )

    if problems:
        print("\nNOT DEMO-READY:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"\nwarm. {first_elapsed:.1f}s -> {second_elapsed:.1f}s, "
        f"{first_stored} stored replies, counts stable.\n"
        "Now turn the Wi-Fi OFF and run:\n"
        f"  python scripts/precache_demo.py {args.pdf} --check-offline"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
