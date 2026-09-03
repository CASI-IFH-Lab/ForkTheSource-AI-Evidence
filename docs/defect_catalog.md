# Defect catalog

**Module B3, merge-queue #4. Written by Ritik in Roy's absence so R1 is not blocked when
he is back. Roy owns this file from here on.**

> **This file doubles as the demo cheat-sheet** (R1 step 5). Somebody will be reading it on
> a laptop, on stage, ninety seconds before a judge asks "so what did it actually catch?".
> Keep it skimmable: the summary table near the top, one section per defect type, no
> paragraph longer than it needs to be. If a change makes it more precise but less
> readable under pressure, make the change somewhere else.

Twenty-one defects across three papers, plus one untouched clean control. Every defect
here maps to exactly one expected status and one expected indicator set, per
[`eval/golden/FORMAT.md`](../eval/golden/FORMAT.md).

**Nothing in this file has been injected yet.** Paper and `ref_id` cells are `TBD` because
they are decided at R1, when the actual PDFs are picked. This is the specification of what
to inject, not a record of what was injected.

> Ground truth is the Module Implementation Plan, R1 step 2 and R2 step 2. The plan lands
> in the repo at `docs/module_implementation_plan.pdf` when B0 (merge-queue #1) merges.

## Two counts that are not the same number

- **21 injections.** The defect-recall denominator in R2's target (`≥ 19/21`).
- **23 labelled entries with `injected: true`.** Each duplicate-entry defect is one
  injection that produces **two** ledger entries, and both carry the indicator.

Do not let these drift together. R2's recall is over injections; the label files contain
23 injected rows. See the *duplicate entry* section.

## Summary distribution

Papers are slots, not titles — Paper 1/2/3 are assigned at R1. **Do not invent paper
titles here.**

| Defect type | Paper 1 | Paper 2 | Paper 3 | Injections | Labelled rows |
|---|---|---|---|---|---|
| Swapped DOI | 1 | 1 | 1 | 3 | 3 |
| Hallucinated reference | 1 | 1 | 1 | 3 | 3 |
| Wrong year (±2-3) | 1 | 1 | 1 | 3 | 3 |
| Mangled author list | 1 | — | 1 | 2 | 2 |
| Duplicate entry, divergent metadata | 1 | — | 1 | 2 | **4** |
| Orphan citation | 1 | 1 | — | 2 | 2 |
| Citation to a retracted paper | — | 1 | 1 | 2 | 2 |
| Malformed entry | — | 1 | 1 | 2 | 2 |
| Preprint/journal version pair | 1 | 1 | — | 2 | 2 |
| **Total** | **7** | **7** | **7** | **21** | **23** |
| Clean control | — | — | — | **0** | **0** |

Seven per paper is deliberate: enough that a single paper exercises most of the
vocabulary, few enough that no paper becomes implausibly broken. A paper where a third of
the bibliography is wrong stops resembling the thing we claim to check.

## The injection worklist — defect → paper → ref_id → expected outcome

Fill `Paper` and `ref_id` at R1. This is the table a teammate spot-verifies five random
rows from, and the one to read on stage.

| # | Defect type | Paper | ref_id | expected_status | expected_indicators |
|---|---|---|---|---|---|
| 1 | Swapped DOI | TBD | TBD | `conflict` | `[doi_mismatch]` |
| 2 | Swapped DOI | TBD | TBD | `conflict` | `[doi_mismatch]` |
| 3 | Swapped DOI | TBD | TBD | `conflict` | `[doi_mismatch]` |
| 4 | Hallucinated reference | TBD | TBD | `unresolvable` | `[]` |
| 5 | Hallucinated reference | TBD | TBD | `unresolvable` | `[]` |
| 6 | Hallucinated reference | TBD | TBD | `unresolvable` | `[]` |
| 7 | Wrong year (±2-3) | TBD | TBD | `needs_check` | `[version_mismatch]` |
| 8 | Wrong year (±2-3) | TBD | TBD | `needs_check` | `[version_mismatch]` |
| 9 | Wrong year (±2-3) | TBD | TBD | `needs_check` | `[version_mismatch]` |
| 10 | Mangled author list | TBD | TBD | `needs_check` | `[]` |
| 11 | Mangled author list | TBD | TBD | `needs_check` | `[]` |
| 12 | Duplicate entry (original) | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| 13 | Duplicate entry (the copy) | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| 14 | Duplicate entry (original) | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| 15 | Duplicate entry (the copy) | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| 16 | Orphan citation | TBD | TBD | `verified` | `[orphan]` |
| 17 | Orphan citation | TBD | TBD | `verified` | `[orphan]` |
| 18 | Retracted paper | TBD | TBD | `conflict` | `[retracted]` |
| 19 | Retracted paper | TBD | TBD | `conflict` | `[retracted]` |
| 20 | Malformed entry | TBD | TBD | `unresolvable` | `[malformed]` |
| 21 | Malformed entry | TBD | TBD | `unresolvable` | `[malformed]` |
| 22 | Preprint/journal version pair | TBD | TBD | `verified` | `[version_mismatch]` |
| 23 | Preprint/journal version pair | TBD | TBD | `verified` | `[version_mismatch]` |

Rows 12-15 are two injections, four labels. Rows are numbered 1-23 by label, so the last
row number is 23 while the injection count is 21.

---

# The nine defect types

Each section: what it looks like, how to inject it, what we expect, and **how it could be
misdetected and what that misdetection would tell us.** The last part is the point. A
failed eval that only says "recall 14/21" is a number; a failed eval read against these
sections is a diagnosis.

## 1. Swapped DOI

**In the bibliography:** the reference looks completely normal — correct title, correct
authors, correct venue — and the DOI at the end belongs to a different paper entirely.
Invisible to a human reader, who does not resolve DOIs by eye.

**How to inject:** replace the DOI string with the DOI of a **real, resolvable, unrelated**
paper. Pick something from a different field so the title similarity is near zero. Leave
every other field untouched.

**Expected:** `conflict` + `[doi_mismatch]`. Per P5's mapping, `doi_mismatch → conflict`.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `verified` + `[]` | **The most likely failure.** The resolver matched on *title* and found the right paper, never noticing the printed DOI pointed elsewhere. Means the waterfall is not DOI-first, or `doi_match` is coming back `None` (treated as "no DOI to compare") instead of `False`. The tri-state in `MatchEvidence.doi_match` exists precisely for this distinction. |
| `needs_check` + `[]` | The DOI *was* resolved — fetching the wrong work — and title similarity came out low, but nothing compared printed DOI against resolved DOI. P5 is computing signals and not deriving the indicator from them. |
| `unresolvable` | An **injection** error, not a pipeline error: the substituted DOI does not resolve. The defect has degenerated into a hallucinated reference. Re-inject with a DOI you have confirmed resolves. |
| `conflict` + `[]` | Right answer, wrong reason — the conflict came from the title mismatch, not the DOI. Exact-set indicator matching catches this; subset matching would hide it. |

## 2. Hallucinated reference (plausible but nonexistent)

**In the bibliography:** a reference that reads perfectly — plausible author names for the
field, a title that sounds like a real paper, a real venue, a plausible year — for a work
that does not exist. This is the defect the whole project exists to catch.

**How to inject:** write a new entry from scratch. Use author surnames that are common in
the field but not a real collaboration, a title assembled from real terminology, and a
real journal or conference. **No DOI and no arXiv ID** — a fabricated identifier would make
this trivially detectable and would be testing a different thing.

**Expected:** `unresolvable` + `[]`. No registry has it, so there is nothing to compare
and no indicator fires.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `verified` | **The worst outcome in the project.** The resolver fuzzy-matched a fabricated citation onto a real paper and endorsed it. Means `title_strong` (0.92) is too low for the search path, or a provider's `?search=` endpoint returned a best-effort result the resolver accepted without checking similarity. If this fires, stop and fix it before anything else — the tool is now laundering fabrications. |
| `conflict` | Over-eager, and a principle violation: absence of a registry record is not evidence of wrongdoing. Means "no resolved record" is being mapped to `conflict` instead of `unresolvable`. Contradicts A1's prompt rule that parse noise and gaps move confidence toward `needs_check`, never toward `conflict`. |
| `needs_check` | Defensible in the abstract but wrong against this label. Means the classifier is not distinguishing "no record found" from "weak match found". Those are different states and `MatchEvidence.resolved` is `null` in only one of them. |

**Measurement caveat:** a hallucinated reference and a legitimately unresolvable one (a
book, a thesis, a standard) produce **identical output** — `unresolvable` with no
indicators. The pipeline cannot tell them apart, and neither can R2. Recall on this defect
type is only meaningful because we know which `ref_id`s we fabricated. Do not expect a
metric that separates them.

## 3. Wrong year (±2-3)

**In the bibliography:** everything correct except the publication year, off by two or
three. The most common *genuine* citation error in real papers, which is why it belongs in
the corpus.

**How to inject:** change the year by +2, +3, or −2. Leave title, authors, venue
untouched. **Inject on a reference that has no DOI** — see the misdetection table for why.

**Expected:** `needs_check` + `[version_mismatch]`.

The status: `year_delta` exceeds `year_tolerance` (1), so the reference does not reach
`verified`, and a year error is nowhere near a `conflict`. That leaves `needs_check`.

The indicator is the uncomfortable part. There is **no `year_mismatch` in the closed
vocabulary**, and `version_mismatch` is defined as "title+authors strong but venue/year
differ" — which a wrong-year defect satisfies literally. So `version_mismatch` is the only
available indicator, and it will fire. See the collision note below.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `verified` + `[]` | The reference had a DOI, the DOI matched, and the year never entered the decision. Not necessarily wrong behaviour — a matching DOI *is* strong evidence — but it means this defect type is untestable on DOI-bearing references. Inject only on DOI-less ones. |
| `verified` + `[version_mismatch]` | The pipeline treated it as a preprint/journal pair. **Structurally indistinguishable** — see the collision note. Not a bug so much as a limit of the vocabulary. |
| `conflict` | Over-eager: `year_delta` is being treated as decisive. A three-year error is a typo or a sloppy citation. Flagging it as a conflict is the kind of false alarm that costs the tool its credibility on the first real paper someone tries. |

### The wrong-year / version-pair collision

Defect types 3 and 9 both produce `version_mismatch`, with **different expected statuses**
(`needs_check` vs `verified`). The pipeline has no signal that separates them: both are
"title and authors strong, year differs".

The only real discriminator is whether the two records are the *same work* published
twice (preprint → journal) or one work cited with a wrong year — and that requires
comparing venues, which is exactly what `version_mismatch` already collapses.

**Consequence for R2:** the confusion between rows 7-9 and 22-23 is expected, and it is a
vocabulary limitation, not a detector bug. Roy should decide before the first metrics run
whether to (a) accept it and report both types under one line, (b) label wrong-year as
`needs_check` + `[]` and let `version_mismatch` mean only the preprint case, or (c) raise
adding a `year_mismatch` indicator — which needs all three owners present, since the
indicator list is a closed vocabulary frozen at Sync 1. **Option (b) is the cheapest and
is what I would pick**, but it is Roy's call and it changes rows 7-9 of the worklist.

## 4. Mangled author list

**In the bibliography:** correct title and venue, but the author list is wrong — names
dropped, initials scrambled, a co-author replaced, or the order reversed in a way that
changes who the first author is.

**How to inject:** drop the second and third authors, or replace one surname with a
different plausible surname from the field. Keep the title exact. **Inject on a reference
with no DOI.**

**Expected:** `needs_check` + `[]`.

Title similarity stays strong, `author_overlap` drops below `author_strong` (0.60), so the
"strong title + year ok + (doi or authors agree)" path to `verified` is not available and
it falls through to `needs_check`. **No indicator exists for an author mismatch**, so the
set is empty — the status is the only signal this defect produces.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `verified` | Either the reference had a matching DOI (inject on DOI-less ones), or `author_overlap` is being computed too generously — Jaccard on last names is sensitive to how initials and particles like "van der" are normalised. Worth checking the normaliser on a name with a particle. |
| `conflict` | The "weak title + no author overlap → conflict" rule is firing on a *strong* title. Means the rule mapping is being evaluated in the wrong order, or the title branch is not gating the author branch. A real risk of accusing on a citation whose title matches perfectly. |
| `needs_check` + some indicator | Something is inventing an indicator for author divergence. Nothing in the closed vocabulary covers it, so whatever fired is being set for the wrong reason. |

## 5. Duplicate entry with divergent metadata

**In the bibliography:** the same work appears twice, with details that disagree — one
copy has the journal version's year and volume, the other has the preprint's; or one has
the full author list and the other has "et al."; or one has a DOI and the other does not.

**How to inject:** copy an existing reference to a new position in the list and alter two
or three fields of the copy. Add an in-text citation marker for the new position so it is
not also an orphan. Keep the normalised title identical, since that is the key duplicate
detection matches on.

**Expected:** `needs_check` + `[duplicate_entry]` on **both** entries.

**One injection, two labels.** Both rows go in the label file; the recall denominator
counts the injection once. This is the sole reason the 21 and 23 counts differ.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| Indicator on only one of the pair | Duplicate detection is comparing each entry only against *earlier* entries, so the first copy never learns about the second. The scan is not symmetric. Easy fix, easy to miss. |
| Neither entry flagged | Title normalisation for duplicate detection is too strict, and the divergent metadata pushed the two normalised titles apart. Duplicate detection needs a *looser* normaliser than registry matching — that they share one is the likely cause. |
| `conflict` on either | The divergence is being read as a mismatch against the registry rather than against the sibling entry. Means duplicate detection and record matching are entangled. |
| `verified` + `[duplicate_entry]` | Arguably reasonable — both copies resolve to a real work, and the duplication is a bibliography-hygiene problem. Contradicts this label; see the ambiguity list. Decide once, not per paper. |

## 6. Orphan citation

**In the bibliography:** a reference that is listed but never cited anywhere in the body
text. Common in real papers after a round of edits.

**How to inject:** pick an existing, correct reference and delete every in-text citation
marker pointing at it. Change nothing about the reference itself.

**Expected:** `verified` + `[orphan]`.

The work exists and the record matches, so the citation is `verified`; being uncited is a
hygiene observation recorded as an indicator, not a doubt about the work. Note that P5's
status mapping does not mention orphan at all — see the ambiguity list.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `verified` + `[]` | Either `extract_claims` matched a marker that is not there (over-matching regex — `[1]` inside a table caption, or a bracketed year), or `cited_by_claims` is populated but the orphan rule never reads it. |
| `needs_check` | "Not cited in text" is being conflated with "might not be real". Those are unrelated. An uncited reference is a housekeeping note; treating it as a provenance doubt inflates the worklist with items no reviewer needs. |
| **Orphan on many entries at once** | The single most useful diagnostic in this catalog. If more than roughly a third of a paper's references come back `orphan`, suspect the citation-marker regex, not the paper — it probably does not match this paper's style (author-year `(Smith, 2020)` vs numeric `[12]`). Check the paper's citation style before touching anything else. |

## 7. Citation to a known retracted paper

**In the bibliography:** an ordinary, correct, resolvable reference — to a paper that has
since been retracted. Nothing about the entry looks wrong; the problem is in the registry,
not the text.

**How to inject:** add a correct, complete reference to a **real retracted paper**, with
its **real DOI**, and cite it once in the body text.

> ### The DOI must be real, and verified before the label is written
>
> The `retracted` indicator comes from **OpenAlex's `is_retracted` flag** (Retraction
> Watch data), read live by P4. A fictional or altered DOI carries no flag, so a made-up
> DOI turns this defect into a swapped-DOI or hallucinated case and the label becomes
> unsatisfiable — the pipeline can never produce `retracted`, and R2 will report a
> permanent miss that is actually a corpus bug.
>
> **At R1, before writing the label:** pick the paper, then confirm OpenAlex returns
> `is_retracted: true` for that exact DOI. Record the DOI and the date checked in this
> file. Retraction data changes; a flag that was absent last month may be present now, and
> a record can be corrected.

**Expected:** `conflict` + `[retracted]`. Per P5's mapping, `retracted → conflict`, and
A1's prompt rules independently require retracted to be at least `conflict`.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `verified` + `[]` | **The most likely failure.** P4 step 5 requires that when Crossref resolves a DOI, OpenAlex is *also* queried for the retraction flag on the same DOI. If enrichment only runs when Crossref *fails*, a cleanly-resolving retracted paper never gets checked — and it will resolve cleanly, because the record is still there. |
| `conflict` + `[]` | Right status, wrong reason: the conflict came from something else and the retraction was never seen. **Worse than a plain miss**, because it passes the status check and hides a broken enrichment path behind a correct-looking number. This is the case that justifies exact-set indicator matching. |
| `unresolvable` | The DOI did not resolve — a corpus error, or a registry outage during the run. Check the run's notes before assuming the pipeline. |
| `needs_check` | The flag was read but not treated as decisive. Retraction is the one signal in the project that is categorical rather than probabilistic. |

## 8. Malformed entry (broken fields)

**In the bibliography:** an entry that is visibly damaged — truncated mid-word, missing
its year and authors, fields run together without separators, an artefact of a bad
copy-paste.

**How to inject:** take a correct reference and delete the author list and year, truncate
the title mid-word, and remove the punctuation that separates fields. Leave enough that a
human can tell something was meant to be there.

**Expected:** `unresolvable` + `[malformed]`.

`malformed` is set by P2 when schema validation of the extraction fails, and carried
forward by P5. With no usable fields there is nothing to resolve, so `unresolvable`. See
the ambiguity list — `needs_check` is also arguable here.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| **The entry is missing from the ledger entirely** | A violation of P2 step 3: *extraction never drops an entry*. For R2 this is a hard join error, not a miss — a `ref_id` in the labels with nothing to score against. Check this first, because it will also shift nothing else (ids are positional, so a dropped entry re-indexes everything after it and looks like the ref_id catastrophe in FORMAT.md). |
| `verified` | The extractor **repaired** the entry by guessing the missing fields. This is the "never guess an identifier, never normalize titles beyond whitespace" prompt rule failing, and it is serious: a model inventing plausible metadata for a damaged citation is the exact behaviour this project claims to detect in others. |
| `needs_check` + `[malformed]` | The other defensible label. See the ambiguity list; pick one and put it in R2. |
| `unresolvable` + `[]` | Resolution correctly failed but the `malformed` indicator was lost between P2 and P5. Means the indicator is being recomputed at P5 rather than carried from P2. |

## 9. Preprint / journal version pair — the false-alarm trap

**In the bibliography:** the paper cites the arXiv preprint of a work that was later
published in a journal — different venue, usually a different year, occasionally a
slightly different title. Completely normal, correct scholarly practice.

**How to inject:** find a real paper that exists as both a preprint and a published
article. Cite the **preprint** version — arXiv venue, preprint year — where the registry
will resolve to the **journal** version.

**Expected:** `verified` + `[version_mismatch]`.

### It must NOT produce `conflict`

This is the most important line in this file.

A preprint and its published version **are the same work**. The citation points at
something real, the authors are the same people, the content is substantially the same. A
tool that calls this a conflict is not being careful — it is wrong, and it is wrong in the
way that costs it a reviewer's trust permanently.

Think about how it plays: a researcher runs this on their own paper, and the tool flags a
citation they made correctly, following normal practice in their field. Everything else the
tool says is now suspect. They will not run it again, and they will tell colleagues it
produces false alarms. One `conflict` here costs more than three genuine misses elsewhere,
because misses are invisible and false alarms are personal.

The plan puts a named test on this in **P5 step 5** — *"version_mismatch alone must NOT
produce conflict"* — and a planted case here in R1. It is verified twice, deliberately.
It is also on the risk register as "version-pair false alarms".

**Why `verified` and not `needs_check`:** the plan allows either
("verified-with-indicator or needs_check"), and the format's one-defect-one-status rule
forces a choice. `verified` + `[version_mismatch]` says what is actually true — the
citation is sound, and here is a note about which version was cited. `needs_check` would
put a correct citation on the human worklist, and the worklist's value is that everything
on it is worth a human's time. See the ambiguity list.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `conflict` | **The failure this whole case exists to catch.** P5 step 5's test is not passing, or `version_mismatch` is being routed into the conflict branch alongside `doi_mismatch`. Release-blocking in spirit: fix before any demo. |
| `verified` + `[]` | Benign, but the tool has lost the ability to explain itself. Venue/year divergence was not computed, so it cannot tell a user *why* it is confident. Also means wrong-year defects have nothing to fire either. |
| `needs_check` + `[version_mismatch]` | The plan's other permitted answer, against this label. Not a bug in the pipeline — a decision that was not made. Make it, once. |
| `unresolvable` | The preprint's title differed enough from the published title that nothing matched. Reveals the title normaliser is brittle to the retitling that often happens at publication. |

---

## The clean control

One paper, **completely untouched.** Zero injections, every label `injected: false`.

Its whole job is R2's release-blocking check: on a paper with nothing wrong with it, the
number of false accusations must be **zero**. A single injected defect in the control makes
that check unusable, so the control is committed unmodified and diffed against its original
in `eval/corpus/originals/`.

Two notes for R1:

- **Expect some legitimate `unresolvable` entries.** Books, theses, standards and web pages
  will not resolve. Those get `expected_status: unresolvable`, `injected: false`, and a
  one-line reason recorded below. They are not accusations and must not count against the
  zero-accusation check.
- **Pick a control in the same field and of similar length** to the three spiked papers. A
  control with five references proves very little.

### Legitimate unresolvable entries in the corpus

Fill at R1. Recorded here so a future reader does not mistake them for unexplained gaps.

| Paper | ref_id | Why it cannot resolve |
|---|---|---|
| TBD | TBD | TBD |

### Retracted DOIs used, and when their flag was verified

Fill at R1, before writing the labels for rows 18-19.

| ref_id | DOI | OpenAlex `is_retracted` confirmed on |
|---|---|---|
| TBD | TBD | TBD |

## Handoff notes for Roy

Everything above is a specification written without the papers in hand. Four things need
your judgement and cannot be settled from here:

1. **The wrong-year / version-pair indicator collision** (section 3). My recommendation is
   option (b) — label wrong-year as `needs_check` + `[]` and reserve `version_mismatch` for
   the preprint case. That changes rows 7-9. Your call, but make it before the first
   metrics run.
2. **The `needs_check` vs `unresolvable` choice for malformed entries** (section 8).
3. **Whether the two version-pair traps count inside the 21** (section 9). Their correct
   outcome is `verified`, which is not a "detection", so including them in a recall
   denominator mixes two different measurements.
4. **Paper selection itself.** Nothing here assumes a field, a venue, or a citation style,
   and section 6's orphan diagnostic depends on knowing which style your papers use.

The full ambiguity list, including the items above, is in the B3 PR description.
