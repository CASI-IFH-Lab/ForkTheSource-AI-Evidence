# Golden label file format

**Module B3, merge-queue #4. Written by Ritik in Roy's absence so R1 is not blocked when
he is back. Roy owns this file from here on** — including the right to change any decision
in it, provided R2 changes with it.

One label file per document in `eval/corpus/`. The files are the project's ground truth:
R2 scores every pipeline output against them, and the metrics slide is generated from that
comparison rather than typed by hand. If a label is wrong, the number on the slide is wrong
and nobody will be able to tell.

This is a *specification*, not data. No real labels exist yet — that is R1, and it cannot
start until the corpus papers are chosen. `EXAMPLE.json` in this directory is a fictional
document that exercises the whole schema.

**The nine ambiguities this format raised on its first pass have all been ruled on** by
Ritik. They are recorded in *Rulings* at the end of this file, and each one is encoded in
the schema and rules above it. Nothing in this format is now left for R2 to decide
silently.

> Ground truth for everything below is the Module Implementation Plan, R1 and R2 cards in
> Section 6. The plan lands in the repo at `docs/module_implementation_plan.pdf` when B0
> (merge-queue #1) merges; until then, ask Ritik for a copy.

## File naming and location

```
eval/golden/<document>.json
```

The filename stem must equal the `document` field inside the file. One file per document,
including the clean control.

### The one exemption: `EXAMPLE.json`

`eval/golden/EXAMPLE.json` is a **specimen, not a corpus label file.** It describes a
fictional document, its stem deliberately does not match its `document` field, no
`example_paper` will ever exist in `eval/corpus/`, and its `source` block is illustrative
rather than a real provenance record.

**R2 must skip it by name.** R1's card globs `eval/golden/*.json`, so a harness that does
the obvious thing will pick the specimen up, look for a ledger for `example_paper`, find
none, and fail — on a file that exists purely to be read by humans. One line in the
loader:

```
if path.name == "EXAMPLE.json": continue
```

If Roy would rather not carry that special case, move the specimen to
`docs/golden_label_example.json` and delete the exemption. Either is fine; leaving it
unhandled is not.

## The schema

```json
{
  "document": "paper1",
  "control": false,
  "source": {
    "license": "CC-BY",
    "origin_url": "https://arxiv.org/abs/0000.00000",
    "origin_file": "paper1_original.pdf"
  },
  "labels": [
    {
      "ref_id": "R03",
      "defect_id": "D01",
      "expected_status": "conflict",
      "expected_indicators": ["doi_mismatch"],
      "defect": "DOI swapped with the DOI of an unrelated journal article",
      "injected": true,
      "verified_by": "arsha",
      "verified_on": "2026-09-03"
    }
  ]
}
```

Four top-level fields, three inside `source`, eight per label. **Nothing else is
permitted** — an unrecognised key should make R2 fail loudly rather than ignore it,
because a typo'd key name is indistinguishable from a missing label otherwise.

Four fields beyond the plan's minimum example were added deliberately. The plan's example
is a minimum shape and specifying this format *is* B3's job; each addition exists to stop
R2 inferring something from the `defect` free text, which this file says is never scored.
They are `defect_id`, `control`, `source`, and the `verified_by`/`verified_on` pair.

### Top level

| Field | Type | Required | Allowed values | What R2 does with it |
|-------|------|----------|----------------|----------------------|
| `document` | string | **yes** | Short identifier, no spaces or path separators. Must match the filename stem. | Pairs this label file with a pipeline `Ledger`, by `Ledger.document_name`. See *Rulings*. |
| `control` | boolean | **yes** | `true` on the clean control file, `false` on the three spiked ones. | Selects the file for the **release-blocking** zero-false-accusation check. R2 must read this field, **never infer the control** from "every label is `injected: false`" — that inference breaks the moment a spiked paper is committed before its labels are written. |
| `source` | object | **yes** | Exactly `license`, `origin_url`, `origin_file`. | Makes R1's *"no copyrighted-restricted or student material"* DoD box **verifiable from the tree** rather than merely asserted in a PR. R2 should print the licence of every scored document in its report header, next to the model names. |
| `labels` | array of objects | **yes** | May not be empty. | The scoring set. R2 iterates it and joins each entry to a `LedgerEntry` by `ref_id`. |

### Inside `source`

| Field | Type | Required | Allowed values | What R2 does with it |
|-------|------|----------|----------------|----------------------|
| `license` | string | **yes** | Exactly one of `CC-BY`, `CC-BY-SA`, `CC0`, `PMC-OA`, `arXiv-perpetual`. | Printed in the report header. A value outside this set is a hard error — it means a paper entered the corpus without its licence being checked, which is the thing the field exists to prevent. |
| `origin_url` | string | **yes** | The canonical URL the paper was obtained from. | Report text and audit only. Never scored. |
| `origin_file` | string | **yes** | Filename under `eval/corpus/originals/`, no path. | Lets anyone diff the spiked PDF against its untouched original, which is R1 step 3's whole purpose. R2 may check the file exists; it does not read it. |

### Per label

| Field | Type | Required | Allowed values | What R2 does with it |
|-------|------|----------|----------------|----------------------|
| `ref_id` | string | **yes** | `R` + zero-padded position. See *ref_id assignment*. | The join key onto `LedgerEntry.reference.ref_id`. Compared as an **opaque string** — `"R03"` and `"R3"` are different ids. A `ref_id` in the labels with no matching ledger entry, or vice versa, is a hard error, not a miss. |
| `defect_id` | string | **yes when `injected` is `true`**; omit when `false` | `D` + two digits, e.g. `D07`. **Globally unique across the whole corpus**, not per file. Assigned in `docs/defect_catalog.md` before R1 starts. | **The recall denominator.** Injections = count of distinct `defect_id`s (21). Label rows = count of `injected: true` entries (23). Recall is computed over `defect_id`s, never over rows. See the matching rule below. |
| `expected_status` | string | **yes** | Exactly one of `verified`, `needs_check`, `conflict`, `unresolvable`. | Compared by **string equality** to `Verdict.status`. Feeds the confusion matrix and per-status precision/recall. |
| `expected_indicators` | array of strings | **yes** (may be `[]`) | Zero or more of `retracted`, `version_mismatch`, `doi_mismatch`, `duplicate_entry`, `orphan`, `malformed`. No duplicates. | Compared as a **set** to `MatchEvidence.indicators`. See below. |
| `defect` | string | **yes when `injected` is `true`**; omit when `false` | Free text, one line, human-readable. | **Never scored.** It appears in R2's report next to each miss, and it is what a human reads at 2am to work out whether the label or the pipeline is wrong. Also the demo cheat-sheet text. |
| `injected` | boolean | **yes** | `true` or `false` | Partitions the corpus. `false` entries drive the false-accusation and false-alarm metrics. |
| `verified_by` | string | no | A teammate's name, lower case. | Audit trail for R1's test plan — *"a teammate spot-verifies 5 random labels against the PDFs"*. Never scored. Optional because most labels will never be spot-checked; present so the ones that were are recoverable months later. |
| `verified_on` | string | no | ISO date, `YYYY-MM-DD`. | As above. If `verified_by` is present, this should be too. |

### The `defect_id` matching rule

**A `defect_id` counts as matched only when ALL of its rows match.**

Most defects produce one row, so this is usually trivial. It matters for duplicate-entry
defects, which are one injection producing two labelled rows: if the pipeline flags one
copy and not the other, that `defect_id` is **not** detected. Half-detecting a duplicate is
not half a detection — a reviewer shown only one of the two copies cannot see that there is
a duplication at all.

This rule is what makes 21 and 23 reconcile without anyone string-matching the `defect`
free text.

## `expected_indicators` is a SET, not a sequence

**Order must never affect scoring.** `["doi_mismatch", "retracted"]` and
`["retracted", "doi_mismatch"]` are the same label and must score identically.

R2 compares them as sets: `set(expected_indicators) == set(evidence.indicators)`. It is
JSON, so the value has to be written as an array — but the array is a serialisation
detail, not an ordering.

Three consequences worth stating, because each is a bug someone will otherwise write:

- **Duplicates are invalid.** `["orphan", "orphan"]` is a malformed label. A set-based
  comparison silently accepts it, so the loader should reject it instead.
- **The comparison is exact, not subset.** A pipeline emitting `[doi_mismatch, orphan]`
  against an expected `[doi_mismatch]` is a **miss**, not a partial credit. If partial
  credit is ever wanted, that is a deliberate change to R2 with a note on the slide.
- **`[]` is a real, meaningful value.** It asserts *no indicator fires*. It is not the
  same as "we do not care what fires", and the format has no way to say "do not care" —
  deliberately, because a wildcard in ground truth is how ground truth stops being
  ground.

## Rule: one defect, one expected status

**Every injected defect maps to exactly ONE `expected_status`.** If a defect could
plausibly land on two statuses, **the label is wrong and the defect needs splitting into
two separate injections** that each have a single unambiguous outcome.

This is the rule that keeps the recall number honest. The failure mode it prevents:
someone labels an ambiguous defect with whichever status the pipeline happened to produce
on the day, the label is now a description of current behaviour rather than of correct
behaviour, and recall becomes a measure of nothing. A ground truth that bends to the
implementation is not ground truth.

Practical consequence for R1: when you find yourself writing "this should be `needs_check`,
or maybe `conflict`", stop and change the *injection*, not the label. Two clean defects
score honestly; one ambiguous defect poisons the metric it feeds.

## Rule: unmodified references get `injected: false` and `expected_status: verified`

Every reference in the bibliography gets a label, not only the spiked ones. An unmodified
reference is labelled `injected: false`, `expected_status: verified`,
`expected_indicators: []`, with `defect` omitted.

**The clean control paper is entirely `injected: false`.** That is what makes R2's
release-blocking check meaningful: on a paper with nothing wrong with it, any `conflict`
is a false accusation, and the plan's risk register rates accusatory wording as the risk
that kills the pitch. A clean control with even one injected defect in it would make that
check unusable.

### The documented exception, which R1 will hit on the first paper

Some unmodified references legitimately cannot be resolved — books, theses, standards,
technical reports, web pages, anything without a DOI or an arXiv ID and no registry
record. The correct label for those is:

```json
{"ref_id": "R14", "expected_status": "unresolvable",
 "expected_indicators": [], "injected": false}
```

`injected: false` because nobody touched it, `unresolvable` because that is the honest
correct outcome. **These must not count against the false-accusation check** —
`unresolvable` is not an accusation, it is the tool admitting it could not look something
up.

Do not force these to `verified` to satisfy the rule above. A label that expects the
impossible turns a correct pipeline into a failing metric, and the first instinct will be
to "fix" the pipeline. Expect a handful per paper; a well-chosen arXiv/PMC paper in a
computational field will have fewer.

**Each spiked paper must retain at least one of these** — a genuine `unresolvable` with
`injected: false`. A hallucinated reference produces `unresolvable` + `[]`, which is
output-identical to a legitimate one, so without a real unresolvable in the same paper
there is no negative case and **precision on `unresolvable` cannot be measured at all**.
If a chosen paper happens to have none, that is a reason to pick a different paper, not to
skip the requirement.

## `ref_id` assignment — the one coupling point

**Format:** `R` followed by the reference's **1-based position in the bibliography as
extracted**, zero-padded to two digits: `R01`, `R02`, … `R99`. For a document with 100 or
more references, pad to three digits (`R001`) **throughout that document** — never mix
widths within one file, because ids are compared as opaque strings.

Position means position in the reference list as the pipeline extracts it, which is
normally the order printed in the PDF.

### Why this is the fragile part

This is **the only place where the corpus and the pipeline are coupled.** Everything else
in R1's lane is independent of Ritik's and Arsha's code. Here, a human counts references in
a PDF and P2 splits the same references programmatically, and the two counts have to agree
exactly.

They can disagree for ordinary reasons: a reference that wraps across a page break counted
as one by a human and two by the splitter; a numbered list where `[10]` is missing and the
human keeps counting from the printed numbers while the splitter counts positions; an
appendix reference list; a "Further reading" block the splitter includes and the human
does not.

### How a mismatch presents — and why it is easy to misdiagnose

**Every label after the divergence point scores against the wrong entry.** A single
off-by-one near the top of the list can push nineteen of twenty-one defects onto the wrong
references.

It looks like **catastrophic recall** — near-zero detection, every status wrong, the
confusion matrix scattered — which reads as "the pipeline is completely broken" rather than
"the ids are shifted by one". Two hours have been lost to this in projects like this one.
The tell is that it is *too* bad: a genuinely broken detector still gets `verified` right on
the unmodified majority, because most references really are fine. Near-total failure across
*all* statuses, including the easy ones, means the join is wrong, not the judgement.

### One-line diagnosis

Print the ledger's ids against the first characters of their raw text and read whether the
reference at `R03` is the one the label's `defect` describes:

```
jq -r '.entries[] | "\(.reference.ref_id)  \(.reference.raw_text[0:70])"' <ledger>.json | head -20
```

If `R03`'s raw text is not the reference whose `defect` says "DOI swapped", the ids are
misaligned — fix the labels or the splitter, and do not touch the classifier. A constant
offset across the whole file confirms it.

## Recall, precisely

**Recall = (number of `defect_id`s whose every row's observed `(status, indicators)`
matches its label) / 21.**

The plan's target is `≥ 19/21`.

Three things this definition settles:

- **The two version-pair traps are inside the 21.** A trap is *detected* when the pipeline
  gets it **right**, and for a trap, right means **not** flagging `conflict` — it means
  producing `verified` + `[version_mismatch]`. Under this definition a trap is scored
  exactly like every other injection: label match or no match. No measurements are mixed,
  and the denominator stays 21.
- **Recall is over injections, not rows.** 21, not 23.
- **Indicator comparison is exact-set, not subset.** An extra indicator is a mismatch. This
  is what catches the "right status, wrong reason" failure — for example a retracted paper
  correctly landing on `conflict` because of a title mismatch, while the retraction was
  never actually read.

### R2 must also print the traps as their own row

Alongside the aggregate, R2 should emit a separate named metric for the two
version-pair `defect_id`s — something like `false-alarm on version pairs: 0/2`.

They are in the recall denominator *and* on their own line, and there is no contradiction
in that: the aggregate answers "how much of the corpus did we get right", and the named row
answers "did we avoid the specific false alarm that destroys a reviewer's trust". The second
question is a demo beat and deserves to be visible without arithmetic.

## False accusation vs false alarm

R2 implements the release gate from this file, so both definitions live here.

### False accusation — RELEASE-BLOCKING, hard FAIL

Exactly two things, and nothing else:

1. **`status == conflict` on any reference with `injected: false`, in any paper** — not
   only the clean control. A conflict asserted against a reference nobody touched is the
   tool making an accusation the evidence cannot support.
2. **Any `banned_terms` hit anywhere in any output text** — rationales, checks, summaries,
   exported CSV, dashboard copy. The word list is in `config.yaml`.

Either one fails the build. The plan's risk register rates accusatory wording as the risk
that *kills the pitch*, and these are its two measurable forms.

### False alarm — a separate, non-blocking metric

**`status == needs_check` on a reference with `injected: false`.**

Report it, track it, do not block on it. `needs_check` means "a human should look at this",
which on a clean reference is over-caution, not an accusation — and a gate that fires on
over-caution punishes the tool for the one behaviour the project actually wants. Conflating
the two would make the release gate unusable within a day.

`unresolvable` on an `injected: false` reference is **neither**. It is the honest correct
answer for a book, a thesis or a standard, and it is expected — see *the documented
exception* below.

## Two things this format deliberately does not express

Both were considered and both are **accepted as gaps**, not oversights. Recorded here so
nobody tries to shoehorn them in later.

### 1. Document-level defects stay out of the golden-label system

P1's card has a fallback path for a paper with no `References` heading — treat the last 15%
of pages as the reference region. Testing it needs a PDF with the heading removed, which is
a defect with **no `ref_id` to attach to**, and injecting it would re-index every other
label in the file.

It belongs in a **separate fixture PDF under `tests/`, owned by P1**, not in
`eval/corpus/`. Nothing in this format will ever describe it.

### 2. `confidence`, `priority` and `checks[]` stay unlabelled

No expected-confidence, expected-priority or expected-checks field. Labelling a confidence
number would pin ground truth to a scale nobody has calibrated.

**But the worklist is still assertable from the labels that exist**, and it should be,
because the top-3 worklist is a demo beat and nothing else validates its ordering. Two
checks R2 can run today with no new field:

- **Every reference in the top-3 worklist must have `injected: true`.** A clean reference
  ranking in the top three means the priority formula is ordering by something other than
  evidence.
- **No version-pair trap may appear in the top-3 worklist.** A trap is `verified` with
  severity `0.0`, so it should sit at the bottom of the ordering. A trap surfacing in the
  worklist is the false alarm arriving through the ranking rather than through the status.

These catch the failure where per-status precision and recall both pass while the ordering
a reviewer actually looks at is wrong.

## Validation checklist for a hand-written label file

Before committing a label file, check by hand:

1. Filename stem equals the `document` field. (`EXAMPLE.json` is exempt — see above.)
2. `control` is present and correct — `true` on exactly one file in the corpus.
3. `source.license` is one of the five allowed strings; `source.origin_file` names a file
   that exists under `eval/corpus/originals/`.
4. Every reference in the bibliography has exactly one label — count them.
5. `ref_id` values run consecutively from `R01` with no gaps and no duplicates.
6. Every `expected_status` is one of the four strings, spelled exactly, lower case.
7. Every entry of every `expected_indicators` is one of the six strings, exactly, lower
   case, with no duplicates inside a single array.
8. Every `injected: true` label has both a `defect` string and a `defect_id`; no
   `injected: false` label has either.
9. `defect_id` values are globally unique across the corpus **except** where rows share one
   by design — currently only duplicate-entry defects, which have exactly two rows each.
   The count of distinct `defect_id`s across all files is **21**; the count of
   `injected: true` rows is **23**.
10. Where `verified_by` is present, `verified_on` is too, and the date is `YYYY-MM-DD`.
11. The clean control has zero `injected: true` labels.
12. Any `unresolvable` on an `injected: false` label has a one-line reason recorded in
    `docs/defect_catalog.md`, so it is not mistaken for an unexplained gap later.
13. Each spiked paper retains **at least one** genuine `unresolvable` reference with
    `injected: false` — see the documented exception.

## Rulings

The nine ambiguities this format raised on its first pass, and the decisions taken. Each is
already encoded above; this section records *why*, so a future reader does not relitigate
them. Where a ruling matched the original recommendation, that is noted and nothing more is
said about it.

> **Every ruling here cites its D-number, and the full reasoning — including the rejected
> alternative — is in [`docs/decisions.md`](../../docs/decisions.md).** If you want to argue
> with one of these, read its entry first; if you still disagree, that is what Sync 1 is for.
> **One ruling is still open: D-020**, which constrains P5 step 2 and is listed in that
> file's *Open at Sync 1* section.

| # | Question | Ruling | Note |
|---|----------|--------|------|
| 1 | Wrong year: which status, which indicator? | **`needs_check` + `[]`** | **D-011.** Differs from the first draft, which had `[version_mismatch]`. Carries a constraint on P5 — see **D-020** and `docs/defect_catalog.md`, *A promise the corpus makes to P5 step 2*. |
| 2 | Malformed: `unresolvable` or `needs_check`? | **`unresolvable` + `[malformed]`** for the corpus | **D-012.** The plan does **not** contradict itself. P5's line governs *status from evidence*; A1's line governs *confidence direction*. "Never toward conflict" forbids escalation — it does not mandate `needs_check`. Both real-world variants documented in the catalog; R1 injects the severe one. |
| 3 | Version pair: `verified` or `needs_check`? | **`verified` + `[version_mismatch]`** | **D-013.** As recommended. A worklist is only valuable if everything on it deserves a human's time. |
| 4 | Do the version-pair traps count inside the 21? | **Yes** | **D-014.** Resolved by redefining recall as label agreement rather than defect detection — see *Recall, precisely*. A trap is detected when the pipeline gets it right, which for a trap means not flagging `conflict`. |
| 5 | Mangled author list: which status, which indicator? | **`needs_check` + `[]`** | **D-015.** As recommended, including the DOI-less injection constraint. |
| 6 | Duplicate entry: `verified` or `needs_check`, one row or two? | **`needs_check` + `[duplicate_entry]` on both rows** | **D-016.** As recommended. Divergent metadata means at least one copy is wrong and nothing in the evidence says which, so a human has to pick. `verified` would assert the bibliography is fine when it demonstrably is not. |
| 7 | Orphan: which status? | **`verified` + `[orphan]`** | **D-017.** As recommended. `orphan` is derived from the **claim map**, not from resolution, so it can co-occur with any status; the corpus injects it on a reference that otherwise resolves clean, which is what makes the label unambiguous. |
| 8 | Hallucinated reference | **`unresolvable` + `[]`** | **D-018.** As recommended. Output-identical to a legitimately unresolvable reference, so each spiked paper must retain at least one genuine `unresolvable` with `injected: false` — otherwise precision on `unresolvable` is unmeasurable. Now checklist item 13. |
| 9 | What is a false accusation? | **`conflict` on `injected: false`, plus any banned-term hit** | **D-019.** As recommended, with the banned-term clause added. `needs_check` on a clean reference is a false *alarm*: separate, non-blocking. See *False accusation vs false alarm*. |

Two smaller questions from the first pass, also settled:

- **`document` matches `Ledger.document_name`**, not the PDF filename.
- **Indicator matching is exact-set**, not subset.
