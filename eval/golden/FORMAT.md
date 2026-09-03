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
fictional document, its stem deliberately does not match its `document` field, and no
`example_paper` will ever exist in `eval/corpus/`.

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
  "labels": [
    {
      "ref_id": "R03",
      "expected_status": "conflict",
      "expected_indicators": ["doi_mismatch"],
      "defect": "DOI swapped with the DOI of an unrelated journal article",
      "injected": true
    }
  ]
}
```

Two top-level fields, five fields per label. Nothing else is permitted — an unrecognised
key should make R2 fail loudly rather than ignore it, because a typo'd key name is
indistinguishable from a missing label otherwise.

### Top level

| Field | Type | Required | Allowed values | What R2 does with it |
|-------|------|----------|----------------|----------------------|
| `document` | string | **yes** | Any short identifier without spaces or path separators. Must match the filename stem. | Pairs this label file with a pipeline `Ledger`. **See the open question below** — whether it matches `Ledger.document_name` or the corpus PDF's filename is not yet settled, and R2 must pick one explicitly. |
| `labels` | array of objects | **yes** | May not be empty. | The scoring set. R2 iterates it and joins each entry to a `LedgerEntry` by `ref_id`. |

### Per label

| Field | Type | Required | Allowed values | What R2 does with it |
|-------|------|----------|----------------|----------------------|
| `ref_id` | string | **yes** | `R` + zero-padded position. See *ref_id assignment* below. | The join key onto `LedgerEntry.reference.ref_id`. Compared as an **opaque string** — `"R03"` and `"R3"` are different ids, not the same one. A `ref_id` in the labels with no matching ledger entry, or vice versa, is a hard error, not a miss. |
| `expected_status` | string | **yes** | Exactly one of `verified`, `needs_check`, `conflict`, `unresolvable`. | Compared by **string equality** to `Verdict.status`. Feeds the confusion matrix and per-status precision/recall. |
| `expected_indicators` | array of strings | **yes** (may be `[]`) | Zero or more of `retracted`, `version_mismatch`, `doi_mismatch`, `duplicate_entry`, `orphan`, `malformed`. No duplicates. | Compared as a **set** to `MatchEvidence.indicators`. See below. |
| `defect` | string | **yes when `injected` is `true`**; omit when `false` | Free text, one line, human-readable. | **Never scored.** It appears in R2's report next to each miss, and it is what a human reads at 2am to work out whether the label or the pipeline is wrong. Also the demo cheat-sheet text. |
| `injected` | boolean | **yes** | `true` or `false` | Partitions the corpus. `false` entries on the clean control drive the release-blocking zero-false-accusation check. **Note:** `true` entries are *not* the recall denominator one-for-one — the target ≥ 19/21 counts **injections**, and one duplicate-entry injection produces two `injected: true` labels. 21 injections, 23 labelled rows. See `docs/defect_catalog.md`. |

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

## Validation checklist for a hand-written label file

Before committing a label file, check by hand:

1. Filename stem equals the `document` field. (`EXAMPLE.json` is exempt — see above.)
2. Every reference in the bibliography has exactly one label — count them.
3. `ref_id` values run consecutively from `R01` with no gaps and no duplicates.
4. Every `expected_status` is one of the four strings, spelled exactly, lower case.
5. Every entry of every `expected_indicators` is one of the six strings, exactly, lower
   case, with no duplicates inside a single array.
6. Every `injected: true` label has a `defect` string; no `injected: false` label has one.
7. The count of `injected: true` labels across all files matches the **labelled-rows**
   total in `docs/defect_catalog.md` — currently **23**, not the 21 injection count. Each
   duplicate-entry defect is one injection producing two labelled entries. Checking
   against 21 will look like two missing labels.
8. The clean control has zero `injected: true` labels.
9. Any `unresolvable` on an `injected: false` label has a one-line reason recorded in
   `docs/defect_catalog.md`, so it is not mistaken for an unexplained gap later.

## Open questions R2 must answer explicitly

These are decisions the harness will otherwise make silently. Each needs a line in R2's
code and a sentence in its report header.

1. **What does `document` match against?** `Ledger.document_name`, or the corpus PDF's
   filename? They will differ the moment a filename has an extension or a space. Pick one.
2. **What counts as a false accusation?** This document assumes **`conflict` on an
   `injected: false` reference**, and nothing else. `needs_check` on a clean reference is a
   false *alarm* — worth a separate, non-blocking metric — but it is not an accusation, and
   conflating them makes the release gate fire on the tool being appropriately cautious.
3. **Is a version-pair trap part of the 21?** Its correct outcome is not a detection, so
   "recall" over a denominator that includes it is measuring two different things. See
   `docs/defect_catalog.md`.
4. **Does a duplicate-entry defect produce one label or two?** One injection creates two
   ledger entries that both carry the indicator. See `docs/defect_catalog.md`.
5. **Exact-set or subset matching on indicators?** This document specifies exact. Confirm
   before the first metrics run, because changing it later moves every number.
