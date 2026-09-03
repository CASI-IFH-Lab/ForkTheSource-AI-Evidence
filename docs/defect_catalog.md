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

**All nine ambiguities from the first pass have been ruled on.** Each expected outcome below
is now a decision, not a proposal. The rulings and their reasoning are tabulated at the end
of [`eval/golden/FORMAT.md`](../eval/golden/FORMAT.md#rulings). One of them —
ruling 1 — places a constraint on P5, which is unwritten code; see *A promise the corpus
makes to P5 step 2* below, and raise it at Sync 1.

> Ground truth is the Module Implementation Plan, R1 step 2 and R2 step 2. The plan lands
> in the repo at `docs/module_implementation_plan.pdf` when B0 (merge-queue #1) merges.

## Two counts that are not the same number

- **21 injections** = 21 distinct `defect_id`s, `D01`-`D21`. The recall denominator in R2's
  target (`≥ 19/21`).
- **23 labelled rows with `injected: true`.** Each duplicate-entry defect is one injection
  producing **two** ledger entries, and both carry the indicator and **share one
  `defect_id`**.

The `defect_id` field is what reconciles these without anyone string-matching the `defect`
free text. Recall is computed over distinct `defect_id`s, and **a `defect_id` counts as
matched only when every one of its rows matches** — half-detecting a duplicate is not half
a detection, because a reviewer shown only one of the two copies cannot see there is a
duplication at all.

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

**Injections: 21. Labelled rows: 23.** The two duplicate-entry defects contribute two rows
each under one `defect_id`. Every other defect is one row, one id.

Each of the three spiked papers must **also** retain at least one genuine `unresolvable`
reference as `injected: false` — a book, thesis or standard. That is a corpus requirement,
not a defect: without it, precision on `unresolvable` cannot be measured, because a
hallucinated reference and a real unresolvable one produce identical output. See section 2.

## The injection worklist — defect → paper → ref_id → expected outcome

Fill `Paper` and `ref_id` at R1. This is the table a teammate spot-verifies five random
rows from, and the one to read on stage.

| defect_id | Defect type | Paper | ref_id | expected_status | expected_indicators |
|---|---|---|---|---|---|
| `D01` | Swapped DOI | paper1 | R11 | `conflict` | `[doi_mismatch]` |
| `D02` | Swapped DOI | TBD | TBD | `conflict` | `[doi_mismatch]` |
| `D03` | Swapped DOI | TBD | TBD | `conflict` | `[doi_mismatch]` |
| `D04` | Hallucinated reference | paper1 | R21 | `unresolvable` | `[]` |
| `D05` | Hallucinated reference | TBD | TBD | `unresolvable` | `[]` |
| `D06` | Hallucinated reference | TBD | TBD | `unresolvable` | `[]` |
| `D07` | Wrong year (±2-3) | paper1 | R06 | `needs_check` | `[]` |
| `D08` | Wrong year (±2-3) | TBD | TBD | `needs_check` | `[]` |
| `D09` | Wrong year (±2-3) | TBD | TBD | `needs_check` | `[]` |
| `D10` | Mangled author list | TBD | TBD | `needs_check` | `[]` |
| `D11` | Mangled author list | TBD | TBD | `needs_check` | `[]` |
| `D12` | Duplicate entry — first copy | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| `D12` | Duplicate entry — second copy | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| `D13` | Duplicate entry — first copy | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| `D13` | Duplicate entry — second copy | TBD | TBD | `needs_check` | `[duplicate_entry]` |
| `D14` | Orphan citation | paper1 | R28 | `verified` | `[orphan]` |
| `D15` | Orphan citation | TBD | TBD | `verified` | `[orphan]` |
| `D16` | Retracted paper | paper1 | R23 | `conflict` | `[retracted]` |
| `D17` | Retracted paper | TBD | TBD | `conflict` | `[retracted]` |
| `D18` | Malformed entry (severe variant) | TBD | TBD | `unresolvable` | `[malformed]` |
| `D19` | Malformed entry (severe variant) | TBD | TBD | `unresolvable` | `[malformed]` |
| `D20` | Preprint/journal version pair | paper1 | R24 | `verified` | `[version_mismatch]` |
| `D21` | Preprint/journal version pair | TBD | TBD | `verified` | `[version_mismatch]` |

**23 rows, 21 distinct `defect_id`s.** `D12` and `D13` each occupy two rows — one injection,
two labelled references. Recall is over the 21 ids, and an id matches only if both its rows
match.

`defect_id`s are assigned **here, now**, and are globally unique across the whole corpus
rather than per file. They are the one column in this table that is not `TBD`: fixing them
before R1 starts means the ids never shift when papers are chosen, and R2 can be written
against them before a single PDF exists.

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

**Expected:** `conflict` + `[doi_mismatch]`. Unchanged and unambiguous. Per P5's mapping,
`doi_mismatch → conflict`.

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

**Expected:** `unresolvable` + `[]`. **Ruled**, as originally recommended. No registry has
it, so there is nothing to compare and no indicator fires.

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

### Corpus requirement, from ruling 8

**Every spiked paper must retain at least one genuine `unresolvable` reference** — a book,
thesis, standard or technical report — labelled `injected: false`,
`expected_status: unresolvable`, `expected_indicators: []`.

Without one there is no negative case in that paper, and **precision on `unresolvable`
cannot be measured at all**: every `unresolvable` the pipeline emits would be a true
positive by construction. A paper that happens to have no such reference is a reason to
pick a different paper, not to skip the requirement. Record each one in the
*legitimate unresolvable entries* table near the end of this file.

## 3. Wrong year (±2-3)

**In the bibliography:** everything correct except the publication year, off by two or
three. The most common *genuine* citation error in real papers, which is why it belongs in
the corpus.

**How to inject:** change the year by +2, +3, or −2. Leave title, authors, venue
untouched. **Inject on a reference that has no DOI** — see the misdetection table for why.

**Expected:** `needs_check` + `[]`. **Ruled.**

### The P5 mapping walk that gets there

Applying P5 step 3's mapping in order to a wrong-year reference:

1. `resolved` is null? **No** — the work exists and resolves fine. So not `unresolvable`.
2. `retracted` or `doi_mismatch` set? **No.** So not `conflict` by that branch.
3. Strong title **and** year ok **and** (DOI or authors agree) → `verified`?
   `title_similarity ≥ 0.92` ✓, but `|year_delta| > year_tolerance` (1) ✗. **Branch fails.**
4. Weak title **and** no author overlap → `conflict`? The title is *strong* (≥ 0.92), not
   weak (< 0.70). **Branch does not apply.**
5. `else` → **`needs_check`.** ✓

And the indicator set is empty, because under the rule below (D-020) `version_mismatch`
fires only when exactly one record is a preprint - never on a year difference alone - and
nothing else in the closed vocabulary describes a year error.

### A promise the corpus makes to P5 step 2

> **`version_mismatch` fires when exactly ONE of the two records is a preprint** - a
> preprint-server venue name (arXiv, bioRxiv, medRxiv, SSRN, or similar) or the presence of
> an arXiv ID. It does **not** fire on venue string divergence, and it does **not** fire on
> year divergence.
>
> **Ruled - see D-020 in [`docs/decisions.md`](decisions.md).** This is the only place in
> this catalog where the corpus imposes a requirement on the pipeline rather than merely
> describing it, and it constrains **P5 step 2**, which is unwritten. **It is on the Sync 1
> agenda** so that Ritik implements it deliberately rather than discovering it from a red
> eval run.

Why the indicator cannot fire on year alone: a year that differs while the venue is
unchanged is a **transcription error** - somebody typed 2021 for a 2019 paper. A preprint
and its journal version are a different thing entirely: the same work, in a *different
venue*, usually with a different year as a side effect. The plan's own wording for the
indicator is "preprint vs journal", and it is the preprint-ness that makes it one.

What breaks if year alone sets it: P5 emits `version_mismatch` on every wrong-year
reference, `D07`-`D09` all come back as `needs_check` + `[version_mismatch]` against a
label of `needs_check` + `[]`, and - because indicator matching is exact-set - **all three
score as misses**. Recall drops to 18/21 and fails the plan's >= 19/21 target, for a defect
the pipeline actually classified correctly. The status would be right and the metric would
say no.

**Why categorical and not a venue-similarity test.** An earlier draft of this section
required *venue divergence*, and that ruling was **reversed**; D-020 records the reversal.
Venue strings are the least normalised field in any bibliography - `Journal of Machine
Learning Research` and `J. Mach. Learn. Res.` are the same venue and differ on every
character comparison. Implemented as venue string inequality, `version_mismatch` would fire
on **correctly-cited references throughout the corpus, including the clean control**, which
is the one paper whose false-accusation count has to be zero. Implemented as venue
*similarity*, it needs a threshold, and there is none: `config.yaml`'s four matching keys
are `title_strong`, `title_weak`, `author_strong` and `year_tolerance`, so a similarity test
means either a fifth key or a hardcoded comparison. The categorical test is a boolean, needs
no threshold and no new key, is immune to abbreviation noise, and encodes the plan's actual
words rather than a proxy for them. Every label in this catalog is identical under either
formulation - only the code that has to satisfy them changes.

The corpus cannot absorb this constraint instead. Labelling wrong-year as `needs_check` +
`[version_mismatch]` to match whatever P5 happens to do would make the wrong-year and
version-pair labels differ only in status while sharing an indicator, and R2 would then be
unable to distinguish a P5 bug from correct behaviour. Ground truth that bends to the
implementation is not ground truth.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| `needs_check` + `[version_mismatch]` | The constraint above was not implemented — P5 is setting the indicator on year divergence alone. This is the single most likely cause of a wrong-year miss, and it is a P5 bug, not a corpus bug. Check it before anything else. |
| `verified` + `[]` | The reference had a DOI, the DOI matched, and the year never entered the decision. Not necessarily wrong behaviour — a matching DOI *is* strong evidence — but it means this defect type is untestable on DOI-bearing references. Inject only on DOI-less ones. |
| `conflict` | Over-eager: `year_delta` is being treated as decisive. A three-year error is a typo or a sloppy citation. Flagging it as a conflict is the kind of false alarm that costs the tool its credibility on the first real paper someone tries. |
| `unresolvable` | The year is being used as a matching key rather than a comparison signal, so shifting it prevented resolution entirely. Means the resolver is querying on year; it should query on title/DOI and compare year afterwards. |

## 4. Mangled author list

**In the bibliography:** correct title and venue, but the author list is wrong — names
dropped, initials scrambled, a co-author replaced, or the order reversed in a way that
changes who the first author is.

**How to inject:** drop the second and third authors, or replace one surname with a
different plausible surname from the field. Keep the title exact. **Inject on a reference
with no DOI.**

**Expected:** `needs_check` + `[]`. **Ruled**, as originally recommended, including the
DOI-less injection constraint.

### The P5 mapping walk that gets there

1. `resolved` is null? **No** — the work resolves on its title. Not `unresolvable`.
2. `retracted` or `doi_mismatch` set? **No.** Not `conflict` by that branch.
3. Strong title **and** year ok **and** (DOI or authors agree) → `verified`?
   `title_similarity ≥ 0.92` ✓, year ok ✓, but there is no DOI (by the injection
   constraint) and `author_overlap < author_strong` (0.60) ✗. **Branch fails.**
4. Weak title **and** no author overlap → `conflict`? Title is *strong*, not weak.
   **Branch does not apply.** This step is the one that keeps a perfect-title reference off
   an accusation.
5. `else` → **`needs_check`.** ✓

**No indicator exists for an author mismatch**, so the set is empty — the status is the only
signal this defect produces.

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

**Expected:** `needs_check` + `[duplicate_entry]` on **both** entries. **Ruled**, as
originally recommended.

Why not `verified` + `[duplicate_entry]`: divergent metadata means **at least one copy is
wrong**, and nothing in the evidence says which. A human has to pick. `verified` would
assert the bibliography is fine when it demonstrably is not.

**One injection, two labels, one shared `defect_id`.** Both rows go in the label file; the
recall denominator counts the id once, and the id matches **only if both rows match**. This
is the sole reason the 21 and 23 counts differ.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| Indicator on only one of the pair | Duplicate detection is comparing each entry only against *earlier* entries, so the first copy never learns about the second. The scan is not symmetric. Easy fix, easy to miss. |
| Neither entry flagged | Title normalisation for duplicate detection is too strict, and the divergent metadata pushed the two normalised titles apart. Duplicate detection needs a *looser* normaliser than registry matching — that they share one is the likely cause. |
| `conflict` on either | The divergence is being read as a mismatch against the registry rather than against the sibling entry. Means duplicate detection and record matching are entangled. |
| `verified` + `[duplicate_entry]` | **Ruled out.** Both copies do resolve, but divergent metadata means one of them is wrong and the evidence cannot say which — that is precisely a `needs_check`. If the pipeline produces this, it is treating duplication as cosmetic. |
| Both rows flagged but one status differs | The `defect_id` does not match, because an id matches only when all its rows do. Means duplicate detection is symmetric but the two copies are being classified independently on their own divergent metadata — which is correct behaviour for a classifier and wrong for a duplicate pair. Worth discussing rather than patching. |

## 6. Orphan citation

**In the bibliography:** a reference that is listed but never cited anywhere in the body
text. Common in real papers after a round of edits.

**How to inject:** pick an existing, correct reference and delete every in-text citation
marker pointing at it. Change nothing about the reference itself.

**Expected:** `verified` + `[orphan]`. **Ruled**, as originally recommended.

The work exists and the record matches, so the citation is `verified`; being uncited is a
hygiene observation recorded as an indicator, not a doubt about the work.

**`orphan` is derived from the claim map, not from resolution.** It comes from
`Reference.cited_by_claims` being empty, which is independent of whether the reference
resolved — so it can co-occur with **any** of the four statuses. An orphaned reference that
also has a swapped DOI would be `conflict` + `[doi_mismatch, orphan]`.

That is exactly why the corpus injects it on a reference that **otherwise resolves clean**:
it isolates the indicator, so the label is `verified` + `[orphan]` with nothing else in
play, and a mismatch can only mean the orphan detection itself is wrong. P5's status mapping
does not mention orphan at all, and under this ruling it does not need to — orphan never
changes a status, it only annotates one.

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

**Expected:** `conflict` + `[retracted]`. Unchanged and unambiguous. Per P5's mapping,
`retracted → conflict`, and A1's prompt rules independently require retracted to be at
least `conflict`.

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

**Expected:** `unresolvable` + `[malformed]`. **Ruled.**

`malformed` is set by P2 when schema validation of the extraction fails, and carried forward
by P5. With no usable fields there is nothing to resolve, so `unresolvable`.

### The plan does not contradict itself here

The first pass read P5's *"no resolved → unresolvable"* and A1's *"parse noise lowers
confidence toward needs_check, never toward conflict"* as a contradiction. They are not in
conflict, because **they govern different things**:

- **P5's line governs STATUS, derived from evidence.** No resolved record → `unresolvable`.
- **A1's line governs CONFIDENCE DIRECTION.** "Never toward conflict" *forbids escalation*
  on the strength of parse noise. It does not *mandate* `needs_check`.

A malformed entry that resolves nothing is `unresolvable` with low confidence. Both lines
are satisfied at once.

### Two real-world variants; the corpus injects only one

| Situation | Status | Indicators | In the corpus? |
|---|---|---|---|
| **Nothing resolves** — fields too damaged to query | `unresolvable` | `[malformed]` | **Yes — inject this one** |
| **Partly parseable and it resolves** — enough survives to find the work, but the entry is still visibly broken | `needs_check` | `[malformed]` | No — uncovered |

**R1 must inject the severe variant**, so the label is unambiguous. Delete the author list
*and* the year *and* truncate the title: leave nothing queryable. If enough survives that
the resolver finds the work anyway, the expected status flips to `needs_check` and the
label becomes a coin toss on how much damage was done.

The partly-parseable variant is real and will occur on genuine papers. It is **deliberately
not in the corpus**, because its outcome depends on how much of the entry survived — which
is not something a hand-written label can pin down. Noted here so that when it shows up in
a live run and produces `needs_check` + `[malformed]`, nobody logs it as a bug.

**Misdetection analysis:**

| If it comes out as | What that reveals |
|---|---|
| **The entry is missing from the ledger entirely** | A violation of P2 step 3: *extraction never drops an entry*. For R2 this is a hard join error, not a miss — a `ref_id` in the labels with nothing to score against. Check this first, because it will also shift nothing else (ids are positional, so a dropped entry re-indexes everything after it and looks like the ref_id catastrophe in FORMAT.md). |
| `verified` | The extractor **repaired** the entry by guessing the missing fields. This is the "never guess an identifier, never normalize titles beyond whitespace" prompt rule failing, and it is serious: a model inventing plausible metadata for a damaged citation is the exact behaviour this project claims to detect in others. |
| `needs_check` + `[malformed]` | Enough of the entry survived for the resolver to find the work — the partly-parseable variant above. Not a pipeline bug; an **injection** that was not severe enough. Damage the entry further and re-label. |
| `unresolvable` + `[]` | Resolution correctly failed but the `malformed` indicator was lost between P2 and P5. Means the indicator is being recomputed at P5 rather than carried from P2. |

## 9. Preprint / journal version pair — the false-alarm trap

**In the bibliography:** the paper cites the arXiv preprint of a work that was later
published in a journal — different venue, usually a different year, occasionally a
slightly different title. Completely normal, correct scholarly practice.

**How to inject:** find a real paper that exists as both a preprint and a published
article. Cite the **preprint** version — arXiv venue, preprint year — where the registry
will resolve to the **journal** version.

**Expected:** `verified` + `[version_mismatch]`. **Ruled**, as originally recommended.

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
on it is worth a human's time.

### The two traps count inside the 21

`D20` and `D21` are in the recall denominator like every other injection. This works
because recall is defined as **label agreement**, not defect detection: a trap is
"detected" when the pipeline gets it **right**, and for a trap, right means **not** flagging
`conflict` — it means producing `verified` + `[version_mismatch]`. No measurements are
mixed and the plan's ≥ 19/21 target stays intact.

R2 should **also** print these two as their own named row — `false-alarm on version pairs:
0/2` or similar. The aggregate answers "how much of the corpus did we get right"; the named
row answers "did we avoid the specific false alarm that destroys a reviewer's trust". The
second is a demo beat and should be readable without arithmetic. Both, not either.

A trap must also **not appear in the top-3 worklist**: it is `verified`, so its severity
weight is `0.0` and it belongs at the bottom of the ordering. R2 can assert that from these
labels with no new field — see `FORMAT.md`.

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

Its label file is the one with `"control": true`. **R2 must read that field, not infer the
control** from "every label is `injected: false`" — that inference breaks the moment a
spiked paper is committed before its labels are written.

Its whole job is R2's release-blocking check: on a paper with nothing wrong with it, the
number of false accusations must be **zero**. A single injected defect in the control makes
that check unusable, so the control is committed unmodified and diffed against its original
in `eval/corpus/originals/`.

**What counts, per ruling 9.** A *false accusation* is exactly two things, and both are hard
FAIL: `conflict` on any `injected: false` reference in any paper, and any `banned_terms` hit
anywhere in any output text. A `needs_check` on a clean reference is a *false alarm* —
tracked, reported, non-blocking — because `needs_check` means "a human should look at this",
and a gate that fires on over-caution punishes the tool for the one behaviour the project
actually wants. `unresolvable` on a clean reference is neither. Full definitions in
[`eval/golden/FORMAT.md`](../eval/golden/FORMAT.md#false-accusation-vs-false-alarm).

Two notes for R1:

- **Expect some legitimate `unresolvable` entries.** Books, theses, standards and web pages
  will not resolve. Those get `expected_status: unresolvable`, `injected: false`, and a
  one-line reason recorded below. They are not accusations and must not count against the
  zero-accusation check.
- **Each of the three spiked papers needs at least one too** — not just the control. See
  section 2: without a genuine `unresolvable` in the same paper as the hallucinated
  references, precision on `unresolvable` is unmeasurable.
- **Pick a control in the same field and of similar length** to the three spiked papers. A
  control with five references proves very little.

### `eval/corpus/originals/` is TRACKED, not gitignored

The untouched originals are committed to the repo. `.gitignore` excludes `eval/outputs/`
only; nothing under `eval/corpus/` is ignored, and that is deliberate on two counts:

- **R1 step 3 diffs each spiked PDF against its original**, so the original has to be in the
  tree for the diff to be reproducible by anyone other than the person who injected the
  defects.
- **R2 may check that `source.origin_file` exists.** With the originals ignored, that check
  passes on the machine that wrote the labels and fails on every clone — the worst kind of
  green.

**If any original exceeds ~10 MB, do not commit the PDF.** Store the **arXiv ID (or DOI)
plus a fetch script** under `eval/corpus/originals/` instead, and point `source.origin_file`
at the stub. A 10 MB binary in git history is permanent, and this is a hackathon repo that
three people clone. The stub has to be enough to re-fetch the exact original: identifier,
version, and the retrieval date. Prefer papers small enough to avoid this — one more reason
to pick arXiv PDFs over publisher-typeset ones.

### Legitimate unresolvable entries in the corpus

Fill at R1. Recorded here so a future reader does not mistake them for unexplained gaps.

| Paper | ref_id | Why it cannot resolve |
|---|---|---|
| paper1 | R02 | Kolmogorov, *Entropy per unit time as a metric invariant of automorphisms*, Doklady 124 (1959) 754–755. No DOI, no arXiv ID, pre-DOI Soviet proceedings. OpenAlex title search returns **count 0**; Crossref's best bibliographic hit is a different 1967 PNAS paper at similarity 0.714, below `title_strong`. Checked 2026-09-03. |
| paper1 | R30 | Körner, *Coding of an information source having ambiguous alphabet and the entropy of graphs*, 6th Prague Conference (1971) 411–425. No DOI, no arXiv ID. OpenAlex **count 0**; Crossref's best hit 0.506, below `title_weak`. The printed entry carries only a Google Scholar URL. Checked 2026-09-03. |
| control | R02 | `COMSOL AB. 2024. COMSOL Multiphysics. https://www.comsol.com/` — a software product cited by vendor URL. No DOI, no arXiv ID, and no registry record for the product itself; the nearest OpenAlex hit is a different work, *Introduction to COMSOL Multiphysics*, at 0.704. Checked 2026-09-03. |
| control | R29 | `SolidWorks Corp. 2005. Solidworks.` — a software product with no identifier, no venue and no URL. Nearest hits are books *about* SolidWorks (best 0.625, below `title_weak`). Checked 2026-09-03. |

**These are `injected: false` with `expected_status: unresolvable`.** Per D-019 they are
neither a false accusation nor a false alarm — they are the honest correct answer, and
`FORMAT.md`'s documented exception covers them. paper1's two are what make precision on
`unresolvable` measurable against `D04`: three `unresolvable` rows in that file, one
injected and two not.

### A naturally-occurring duplicate pair in the control

`control` R17 and R18 are **the same work cited twice** — Burnett et al., *Decoherence
benchmarking of superconducting qubits*, npj Quantum Information 5, 1 (2019), 54 — with
divergent metadata: R17 prints the full date and `https://doi.org/10.1038/s41534-019-0168-5`,
R18 prints neither. This is in the original bibliography; nothing was injected.

Both rows are therefore labelled **`needs_check` + `[duplicate_entry]`, `injected: false`**,
which is what D-016 says a correct pipeline produces for divergent duplicates and what the
identical normalised titles will match on. The consequence to know before reading a metrics
table: **the clean control carries two expected `needs_check` rows**, so a correct run
reports two false alarms on it rather than zero. That is non-blocking under D-019 — the
release gate fires on `conflict`, not on `needs_check` — but it means "false alarms: 2" on
the control is the *passing* number, not a regression.

### The D-037 tripwire row

`paper1` **R19** — Mao, Mohri, Zhong, *Cross-entropy loss functions: theoretical analysis
and applications*, `arXiv:2304.07288 (2023). doi:10.48550/arXiv.2304.07288.` — is
`injected: false`, `verified` + `[]`, and it is in the corpus **on purpose**: it is a
legitimately-cited arXiv preprint printing a `10.48550/` DOI, which D-037's addendum
requires so that the failure mode it describes is measurable.

If P4's waterfall ever regresses to Crossref-first, this row returns `unresolvable` + `[]`
— byte-identical to what D-018 assigns `D04` — and recall would be wrong **in our favour**.
The harness catches it as a false detection on a clean row instead. R18 and R20 are two
further `10.48550` rows, so the tripwire does not rest on a single reference.

Verified 2026-09-03: OpenAlex returns `type: preprint` for that DOI with every location on
arXiv at `version: submittedVersion` and no journal record, so both sides of D-020's
"exactly one record is a preprint" test read preprint and `version_mismatch` correctly does
**not** fire. That is what makes `[]` the right indicator set here rather than
`[version_mismatch]`.

### Retracted DOIs used, and when their flag was verified

Fill at R1, before writing the labels for rows 18-19.

| ref_id | DOI | OpenAlex `is_retracted` confirmed on |
|---|---|---|
| paper1 R23 (`D16`) | `10.1007/s00500-019-03807-9` | 2026-09-03 — `is_retracted: true`, read from `https://api.openalex.org/works/https://doi.org/10.1007/s00500-019-03807-9` at build time and confirmed independently by Roy in the browser. Record: Saravanan, Mohanraj, Senthilkumar, *A fuzzy entropy technique for dimensionality reduction in recommender systems using deep learning*, Soft Computing 23 (8) (2019) 2575–2583. |

The entry's own title carries **no retraction marker**, which is why this DOI was chosen
over two other in-field candidates whose OpenAlex titles are prefixed `RETRACTED:` /
`RETRACTED ARTICLE:`. With a prefix, writing the reference with the clean printed title
drops title similarity against the registry record and can turn `conflict` + `[retracted]`
into `conflict` + `[]` — the right status for the wrong reason, which exact-set indicator
matching (D-024) scores as a miss. Here the registry flag is the only signal.

Two prefix-free backups, both verified `is_retracted: true` on 2026-09-03, held in case
this record changes: `10.3233/jifs-223384` (Zhang, Wang, Fan, J. Intelligent & Fuzzy
Systems 44 (6) (2023) 9527–9544) and `10.1155/2022/7111034` (Wu, Security and
Communication Networks 2022, 1–10).

## Handoff notes for Roy

**All nine ambiguities from the first pass are now ruled on**, and every expected outcome in
this file is a decision rather than a proposal. The rulings and their reasoning are
tabulated at the end of
[`eval/golden/FORMAT.md`](../eval/golden/FORMAT.md#rulings).

Three things still need a person rather than a document:

1. **Raise the P5 constraint at Sync 1** (section 3, *A promise the corpus makes to P5 step
   2*). `version_mismatch` fires when **exactly one record is a preprint**, not on venue
   divergence and not on year alone — ruled as **D-020**, which reversed an earlier
   venue-divergence ruling. If P5 sets the indicator on year divergence instead, all three
   wrong-year defects score as misses on a correct classification. P5 is Ritik's module and
   it is unwritten, so this is the one item here that constrains someone else's code — but
   the corpus depends on the outcome, so you should be in the room.

2. **Paper selection.** Nothing here assumes a field, a venue, or a citation style. Two
   places where it matters: section 6's orphan diagnostic depends on knowing whether your
   papers use numeric or author-year citations, and every spiked paper needs at least one
   genuinely unresolvable reference, which constrains the choice.

3. **Verify the retracted DOIs against OpenAlex before writing labels for `D16` and
   `D17`**, and record the date in the table above. Retraction data changes.

Everything else — the format, the 21 `defect_id`s, the expected outcomes, the injection
methods — is settled and ready to execute against.
