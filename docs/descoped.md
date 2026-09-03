# Descoped: reproducibility-claim verification

Two stage modules existed in the B0 skeleton and were deleted in the layout realignment:
`src/pipeline/repro_extractor.py` and `src/pipeline/repro_judge.py`. They were written
before the Module Implementation Plan was in the repo, from the project's working title.
Neither appears anywhere in the plan.

The code is gone. The idea is recorded here so that if the team ever wants it, nobody has
to re-derive it from scratch.

## What they were

**`repro_extractor` — reproducibility claim extraction (LLM).**
Signature as built: `run(document_text: str, config: dict) -> list[dict]`. It was to read
the paper's *body* text — not its bibliography, making it the only stage that did — and
pull out the paper's own claims about its reproducibility: shared code, shared data,
environment and dependency details, hardware used. Output was structured JSON, one record
per claim, schema-validated with the same retry-once-then-mark-failed rule as every other
model call.

**`repro_judge` — reproducibility claim verification (LLM).**
Signature as built: `run(claims: list[dict], config: dict) -> list[dict]`. It was to take
each extracted claim and rate how well the evidence actually backs it, emitting one
verdict per claim. The interesting design constraint was linguistic rather than technical:
a claim with no supporting artifact is `unresolvable`, and the write-up must never call it
`irreproducible`. That word is in `banned_terms` in `config.yaml` precisely because this
is the stage where the temptation to editorialize arises.

## Why they are out of scope

**The honest reason is that the plan does not contain them at all.** This is worth being
precise about, because it is easy to misremember as a cut:

- They are **not** on the plan's Section 9 cut line. That line is explicit and ordered —
  (1) biomed resolvers / batch mode, (2) the claim-evidence map detail view, (3) the donut
  chart — and it names what to drop *from the planned build* if the clock runs short.
  Reproducibility extraction is not on it, because it was never in the build to be cut.
- They are out of scope by **omission**. The plan's seven-step flow is
  `intake → extract → resolve → evidence → verdict → priority → ledger`, and every one of
  those steps is about citation provenance: does this reference point at a real work, and
  does the cited record match what the paper printed? Reproducibility of the paper's *own*
  results is a different question about a different object.
- The clock makes it moot regardless. Section 7 budgets 20 hours, and every hour to 17 is
  allocated across three lanes; hours 17-20 are explicitly buffer with the rule "nothing
  new starts after hour 17." Two new LLM stages, with prompts, schemas, tests and golden
  labels, do not fit in buffer. The plan's own risk register puts the emphasis elsewhere:
  the thing that "kills the pitch" is accusatory wording, not missing scope.

There is also a scope-integrity argument. The project's defensible claim is
*"verifiability, never accusations"* over citations, measured against Roy's golden labels.
Reproducibility claims have no golden-label corpus in R1 and no metrics row in R2, so
shipping them would mean shipping an unmeasured feature next to a measured one — and R2's
metrics table is the pitch.

## Where it would slot back in

If the team wants this after the Spark Challenge, it is additive rather than invasive:

1. **A parallel evidence lane, not a pipeline extension.** Reproducibility claims are a
   second evidence source producing a second verdict dimension. They do not belong
   between existing steps — they belong beside `src/matching/`, feeding a second entry
   type into the ledger.
2. **`Claim` in the contract is already close.** `src/contract.py` (B1) defines
   `Claim {claim_id, text, page?, ref_ids[]}` for in-text citation markers. A
   reproducibility claim is the same shape with a different provenance and an empty
   `ref_ids`. Extending that model is a smaller change than adding a new one.
3. **The status vocabulary transfers unchanged.** `verified` / `needs_check` /
   `conflict` / `unresolvable` describe "is this claim backed by evidence?" just as well
   as they describe a citation match. No new statuses would be needed — which is the
   strongest signal the idea is compatible with the architecture.
4. **`orphan` and `malformed` transfer; the other four do not.** `retracted`,
   `version_mismatch`, `doi_mismatch` and `duplicate_entry` are all registry concepts with
   no analogue for a reproducibility claim. A new indicator would be needed, and the
   contract's indicator list is a **closed vocabulary** frozen at Sync 1 — so this is the
   one change that would need all three owners in a room.
5. **It needs its own golden labels first.** Following the plan's own discipline: R1-style
   ground truth and an R2 metrics row before the feature, not after.

## One loose end this creates

The README's tagline describes the project as *"Provenance + reproducibility
verification"*. With these two stages gone, the second half of that phrase overstates what
the build does. It is flagged in the B0 PR and belongs to R4 (`README.md` is R4's file),
but it should not survive to the pitch unaddressed — the plan's own pre-submission sweep
includes a label-wording check across UI, deck and script.
