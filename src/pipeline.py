"""P6 - the orchestrator. Owner: Ritik. The one place the seven stages are wired together.

    run(pdf_path, judge_fn=None, progress=None) -> Ledger

This is a FILE, not a package, and `tests/test_layout.py` keeps it that way: a
`src/pipeline/` directory would collide with the name every other lane imports.

## What it does, in the order it does it

    intake     parse_pdf                      plain code
    extract    extract_references + claims    AIR - models.extractor
    resolve    resolve                        network, no model
    evidence   build_evidence                 plain code
    verdict    judge_fn                       AIR - models.judge, or the rule baseline
    priority   compute_priority               plain code
    ledger     save_ledger                    plain code

## The seven stage keys are frozen by D-204 and a misspelling fails SILENTLY

`STAGE_KEYS` below is the exact vocabulary Arsha's progress strip looks up. A stage name
that is not in that tuple lights no chip and raises nothing - so `"extraction"` where the
strip expects `"extract"` costs the demo its one visible AIR beat and produces no error
anywhere. `tests/test_pipeline.py` asserts the emitted sequence against its own local
copy of the tuple; it does NOT import `dashboard`, because that would cross a lane
boundary in exactly the direction `test_layout.py` forbids.

`extract` and `verdict` are the two AIR stages and the only two that pass a `model_name`.
The key is `verdict`, not `judge` - the chip is *labelled* "judge" for the reviewer, but
the key is the pipeline stage and the contract's word.

**The model name on `verdict` is the one that will actually run.** On the default path
that is the string `"rule_based"`, which is also the `judge_model` the `Verdict` carries,
so the strip and the ledger say the same thing. Naming the configured AIR judge there
while `rule_based_status` does the work would put a model on screen that was never
called, and the whole point of the strip is that it is true.

## This module must not import src/judge

Deliberate, and asserted by `tests/test_layout.py`. `judge_fn` is dependency injection -
A3 passes Arsha's wired judge in, P6 never reaches for it - and that is what lets this
merge while A1 is still being built. The default is a wrapper around P5's
`rule_based_status`, so the whole pipeline runs end to end with no AIR key on the judge
side and no import of anyone else's lane.

## The counts invariant is the app-level refusal, not a sanity check

Before anything is written, status counts must sum to the entry count. If they do not,
`PipelineIntegrityError` and no file. The dashboard mirrors the same guard and refuses to
render. A ledger whose counters disagree with its own rows is worse than no ledger,
because the number a reviewer reads at the top of the page is the one they trust without
checking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src import settings
from src.contract import (
    Claim,
    Ledger,
    LedgerEntry,
    MatchEvidence,
    Reference,
    Verdict,
    save_ledger,
)
from src.ingest.extractor import extract_claims, extract_references
from src.ingest.pdf_parser import PdfSource, parse_pdf
from src.matching.evidence import build_evidence
from src.matching.rules import rule_based_status
from src.priority import compute_priority
from src.resolvers.resolver import resolve

__all__ = [
    "STAGE_KEYS",
    "PipelineIntegrityError",
    "default_judge",
    "ledger_path_for",
    "run",
]

#: D-204. Exactly these seven strings, in this order. Do not rename one; if a stage is
#: needed that is not here, it needs a chip in Arsha's strip first.
STAGE_KEYS: tuple[str, ...] = (
    "intake",
    "extract",
    "resolve",
    "evidence",
    "verdict",
    "priority",
    "ledger",
)

#: The two AIR stages - the only two that pass a model name to the progress callback.
AIR_STAGE_KEYS: tuple[str, ...] = ("extract", "verdict")

#: `judge_model` on a Verdict the rule baseline produced. Also the model name reported
#: for the `verdict` stage on the default path, so the strip and the ledger agree.
RULE_BASED_MODEL = "rule_based"

#: Where ledgers land. Gitignored - the file is handed over by path, not committed.
DEFAULT_OUTPUT_DIR = settings.PROJECT_ROOT / "data" / "output"

#: `Callable[[Reference, MatchEvidence], Verdict]` - the frozen §7 injection seam.
JudgeFn = Callable[[Reference, MatchEvidence], Verdict]

#: `Callable[[stage_name: str, model_name: str | None], None]` - D-204.
ProgressFn = Callable[[str, str | None], None]


class PipelineIntegrityError(RuntimeError):
    """The ledger disagrees with itself, so nothing is written.

    Raised only for a defect in this code, never for a data problem: a bad PDF, a dead
    registry and an unreadable reference all have statuses of their own and stay in the
    ledger. This is the one failure that has to stop the run.
    """


def default_judge(ref: Reference, ev: MatchEvidence) -> Verdict:
    """P5's rule baseline in the shape of a `judge_fn`. The default, and never an import.

    `ref` is unused and stays in the signature because the seam is
    `Callable[[Reference, MatchEvidence], Verdict]` and A1's judge reads both.
    """
    status, confidence, rationale = rule_based_status(ev)
    return Verdict(
        ref_id=ev.ref_id,
        status=status,
        confidence=confidence,
        rationale=rationale,
        checks=[],
        judge_model=RULE_BASED_MODEL,
    )


def ledger_path_for(document_name: str, output_dir: str | Path | None = None) -> Path:
    """`data/output/<name>_ledger.json`, with the PDF suffix dropped from the stem.

    A function rather than an f-string at the call site so the CLI can print the path it
    is about to write without re-deriving the rule and getting it subtly different.
    """
    directory = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    return directory / f"{Path(document_name).stem}_ledger.json"


def _emit(progress: ProgressFn | None, stage: str, model_name: str | None) -> None:
    """Fire the progress callback, and never let it take the run down with it.

    The callback belongs to whoever is watching - a CLI printer, Arsha's strip, a test
    spy. A run that produced a correct ledger must not fail because a chip failed to
    light, so an exception in the callback is swallowed. It stays a hard error that the
    STAGE NAME is one of D-204's seven: that is our bug, not the watcher's.
    """
    if stage not in STAGE_KEYS:
        raise PipelineIntegrityError(
            f"{stage!r} is not one of D-204's seven stage keys {STAGE_KEYS}. "
            "An unrecognised name lights no chip and raises nothing downstream, so it "
            "is caught here instead."
        )
    if progress is None:
        return
    try:
        progress(stage, model_name)
    except Exception:  # noqa: BLE001 - see docstring
        pass


def _check_counts(ledger: Ledger) -> None:
    """The hard invariant: status counts sum to the entry count, or nothing is written.

    Split out of `run` so a test can arm it against a stub. Through `Ledger` alone it is
    close to unfailable - pydantic will not let a status outside the vocabulary onto a
    `Verdict` - and an invariant that cannot be observed failing is an invariant nobody
    can trust.
    """
    counts = ledger.summary_counts()
    total = sum(counts.values())
    if total != len(ledger.entries):
        raise PipelineIntegrityError(
            f"status counts sum to {total} but the ledger has {len(ledger.entries)} "
            f"entries: {counts}. Refusing to write a ledger whose counters disagree "
            "with its own rows."
        )


def run(
    pdf_path: PdfSource,
    judge_fn: JudgeFn | None = None,
    progress: ProgressFn | None = None,
    config: dict[str, Any] | None = None,
    client: Any = None,
    output_dir: str | Path | None = None,
) -> Ledger:
    """Run one PDF through all seven stages and write its ledger.

    `pdf_path` is a path, raw bytes or an open binary file - whatever `parse_pdf` takes,
    so A3's upload flow can hand this the bytes it already has.

    `judge_fn` and `progress` are the frozen §7 arguments. `config`, `client` and
    `output_dir` are trailing keywords added for testability and are not part of the
    contract: `client` injects a stub LLM client into the extractor so the offline tests
    never touch the network, and `output_dir` redirects the write into a tmp path.

    Returns the `Ledger` it wrote. Raises `PipelineIntegrityError` if the ledger
    disagrees with itself; everything softer than that - a page that will not parse, a
    registry that is down, an entry extraction could not read - is a status in the
    ledger, not an exception.
    """
    judge = judge_fn if judge_fn is not None else default_judge
    config = config if config is not None else settings.load_config()

    extract_model = settings.model_for("extractor", config)
    # The model that will actually produce the verdicts. On the default path nothing is
    # called, and saying so is the honest thing to put on the strip - see the docstring.
    verdict_model = RULE_BASED_MODEL if judge_fn is None else settings.model_for("judge", config)

    # --- intake -----------------------------------------------------------
    _emit(progress, "intake", None)
    document = parse_pdf(pdf_path)

    # --- extract (AIR) ----------------------------------------------------
    _emit(progress, "extract", extract_model)
    references, malformed_ref_ids = extract_references(document, config=config, client=client)
    # Fills Reference.cited_by_claims in place, which is where the priority formula's
    # citation count comes from.
    claims: list[Claim] = extract_claims(document, references)

    # --- resolve ----------------------------------------------------------
    _emit(progress, "resolve", None)
    resolved_by_id = {ref.ref_id: resolve(ref) for ref in references}

    # --- evidence ---------------------------------------------------------
    _emit(progress, "evidence", None)
    # malformed_ref_ids is P2's side-channel (D-102) and P6 is the caller that has it.
    # It is an optional kwarg on build_evidence, so omitting it here would silently cost
    # every unreadable entry its `malformed` indicator with nothing raising.
    evidence_by_id: dict[str, MatchEvidence] = {
        ref.ref_id: build_evidence(
            ref,
            resolved_by_id[ref.ref_id],
            references,
            malformed_ref_ids=malformed_ref_ids,
        )
        for ref in references
    }

    # --- verdict (AIR, or the rule baseline) ------------------------------
    _emit(progress, "verdict", verdict_model)
    verdicts_by_id: dict[str, Verdict] = {
        ref.ref_id: judge(ref, evidence_by_id[ref.ref_id]) for ref in references
    }

    # --- priority ---------------------------------------------------------
    _emit(progress, "priority", None)
    weights = settings.priority_weights(config)
    entries: list[LedgerEntry] = []
    for ref in references:
        evidence = evidence_by_id[ref.ref_id]
        verdict = verdicts_by_id[ref.ref_id]
        entries.append(
            LedgerEntry(
                reference=ref,
                evidence=evidence,
                verdict=verdict,
                # The citation count comes from Reference.cited_by_claims, which
                # extract_claims filled in place during the extract stage.
                priority=compute_priority(
                    evidence, verdict, len(ref.cited_by_claims), weights=weights
                ),
            )
        )

    # --- ledger -----------------------------------------------------------
    _emit(progress, "ledger", None)
    ledger = Ledger(document_name=document.name, claims=claims, entries=entries)
    _check_counts(ledger)  # before the write, always
    save_ledger(ledger, ledger_path_for(document.name, output_dir))
    return ledger
