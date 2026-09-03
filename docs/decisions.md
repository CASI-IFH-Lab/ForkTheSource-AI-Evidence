# Decisions

Every decision on this project that constrains someone else's work, in one file, newest
first. IDs are stable: `D-001` never changes meaning, is never reused, and is safe to cite
from a PR body, a card, a commit message or another doc.

> ## The standing rule
>
> **Any decision that constrains another person's module, or that departs from the
> Module Implementation Plan, gets an entry in this file BEFORE the PR that implements it
> is opened.**
>
> The reason is narrow and practical. On a three-lane build, the expensive failure is not
> a wrong decision — it is a decision nobody can find, made by one person, discovered by
> another as a broken assumption two modules later. An entry here costs five minutes. A
> teammate re-deriving your reasoning from a diff costs an hour and usually gets it wrong.
>
> `.github/pull_request_template.md` has a checkbox for this. **A PR that establishes a
> rule and does not log it is incomplete**, and "N/A" is a perfectly good answer for a PR
> that establishes nothing.
>
> Where the plan and this file disagree, **the plan wins** and the entry is wrong — say so
> and supersede it. Where a brief and the plan disagree, see **D-003**.

## Open at Sync 1

The whole agenda, and nothing else. Four entries are unresolved; everything else in this
file is settled and only needs reading.

| ID | One line | Whose call | Why it cannot wait |
|----|----------|-----------|--------------------|
| **D-004** | Does `gate.py` want a model of its own? `models.critic` and `critic_temperature` were **removed** from `config.yaml`. | **Arsha** | If A1 wants an LLM in the gate, two config keys and a `config_reference.md` row come back — and the removal is currently pinned by a test. |
| **D-008** | `tests/test_layout.py` must be amended before A1 lands. As written it will fail on Arsha's own intra-package imports. | **Arsha + Ritik** | It breaks the first time `src/judge/agent.py` imports `src/judge/prompts.py`. She will hit it on her first commit, not at review. |
| **D-009** | The priority formula lives in `src/priority.py` as shared infra and ships with **B1**. | **Arsha** (it ships in her PR) | B1 is the critical path and this adds a file to it. Deciding it after B1 merges means a second PR touching the contract. |
| **D-020** | `version_mismatch` fires when **exactly one record is a preprint** — not on venue divergence, not on year alone. | **Ritik** (it constrains P5) | P5 is unwritten. Implemented any other way, three correctly-classified defects score as misses and recall fails the ≥ 19/21 target. |

**Implementation debt, not an open question:** **D-007** (`resolvers.mailto` → `.env` as
`CROSSREF_MAILTO`) is decided and **not yet implemented** — `config.yaml:17` still carries
the key. It needs one PR, not a discussion. See the entry.

## Index

| ID | Title |
|----|-------|
| D-021 | B0 self-merged without Arsha's review |
| D-020 | `version_mismatch` fires on preprint-ness, not venue divergence |
| D-019 | False accusation defined, and separated from false alarm |
| D-018 | Hallucinated reference → `unresolvable` + `[]`, plus a corpus requirement |
| D-017 | Orphan → `verified` + `[orphan]` |
| D-016 | Duplicate entry → `needs_check` + `[duplicate_entry]` on both rows |
| D-015 | Mangled author list → `needs_check` + `[]`, DOI-less refs only |
| D-014 | The version-pair traps count inside the 21; recall is label agreement |
| D-013 | Preprint/journal version pair → `verified` + `[version_mismatch]` |
| D-012 | Malformed entry → `unresolvable` + `[malformed]` for the corpus |
| D-011 | Wrong year → `needs_check` + `[]` |
| D-010 | `app.py` is deleted in the A3 PR; `dashboard/app.py` is the demo entrypoint |
| D-009 | The priority formula lives in `src/priority.py`, shared infra, shipping with B1 |
| D-008 | Three tiers of file ownership, and the lane rule's exception for shared infra |
| D-007 | `resolvers.mailto` moves to `.env` as `CROSSREF_MAILTO` |
| D-006 | The red contract test was written and then removed |
| D-005 | The repro stages are out of scope by omission, not by the Section 9 cut line |
| D-004 | `models.critic` and `critic_temperature` removed from `config.yaml` |
| D-003 | `src/config.py` renamed `src/settings.py` — and the plan beats the brief |
| D-002 | `src/pipeline/` split into `src/ingest/`, `src/resolvers/`, `src/matching/` |
| D-001 | The B0 docs were written against an inferred module mapping |

---

## D-021 — B0 self-merged without Arsha's review

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: B0, B2, and the project's review rule. `docs/pr/B0.md`, commit `a579dab`.

**Decision**: B0 was squash-merged to `main` without the review the plan assigns to Arsha.
The reviewer's guide in the PR body stands as a **post-merge** read; Arsha raises anything
she disagrees with at Sync 1, and any of it is reversible by a follow-up PR.

**Why**: The plan gives Arsha a review of B0 within the first hour, and it also says B0 must
be PR'd on day 0. Those two instructions came apart in practice: she had not started, and
four modules were queued behind the merge — B1, B3, P1 and R1, spanning all three lanes.
Holding B0 for a review that had not begun would have idled the entire team to protect a
process step whose purpose is to catch mistakes in one person's work. The alternative
considered was to wait: rejected because the cost is measured in blocked lane-hours on a
20-hour build, while the cost of merging early is a review that happens later against
`main` instead of against a branch — which for a skeleton with 39 passing tests and no model
calls is a small difference. What made it tolerable is that B0 contains no cross-lane
interface that Arsha cannot change later: the two seams are recorded as *targets* in
`docs/architecture_map.md`, and neither file exists yet.

This is a **deliberate deviation from the plan's review rule, not an oversight.** It is
logged precisely so that it cannot be mistaken for one later, and so that the next person
tempted to self-merge has to argue against a written precedent rather than an absence.
Items 1 and 4 of the reviewer's guide are boundary decisions inside Arsha's own lane, made
in her absence; those are the two she should read first.

**Consequence**: **Arsha** reads the reviewer's guide in `docs/pr/B0.md` against `main` and
brings disagreements to Sync 1. **Ritik** carries the review debt and does not treat
silence as agreement. The precedent is narrow: it covers a baseline module blocking
multiple lanes whose reviewer has not started, and it is not a general licence to self-merge
— A3, the one PR where two lanes share a file, is explicitly outside it.

---

## D-020 — `version_mismatch` fires on preprint-ness, not venue divergence

**Date** 2026-09-03 · **Decided by** Ritik, **reversing his own earlier ruling**, on
Claude's analysis · **Status**: **open** — constrains P5 step 2, which is unwritten. Sync 1.

**Affects**: P5 (`src/matching/evidence.py`, step 2), R1's labels `D07`-`D09` and `D20`-`D21`,
R2's recall computation. `docs/defect_catalog.md` § 3, `eval/golden/FORMAT.md` § Rulings.

**Decision**: `version_mismatch` fires when **exactly one** of the two records — the cited
reference and the resolved source — is a **preprint**, identified by a preprint-server venue
name (arXiv, bioRxiv, medRxiv, SSRN, or similar) or by the presence of an arXiv ID. It does
**not** fire on venue string divergence, and it does not fire on year divergence.

**Why**: The earlier ruling was that the indicator must require *venue divergence*, which
was right in spirit — a preprint and its journal version differ in venue, and that is what
makes them a version pair rather than a citation error — but wrong as a test, in two ways
that only show up in code. First, there is no threshold to compare venues against: the four
matching keys in `config.yaml` are `title_strong`, `title_weak`, `author_strong` and
`year_tolerance`, so a venue *similarity* test needs either a fifth config key nobody has
specified or a hardcoded comparison inside P5 — and hardcoding a matching constant is
exactly what the config layer exists to prevent. Second, and worse, venue strings are the
least normalised field in a bibliography. `Journal of Machine Learning Research` and
`J. Mach. Learn. Res.` are the same venue and differ on every character. Implemented as
string inequality, `version_mismatch` would fire on **correctly-cited references throughout
the corpus, including the clean control** — the one paper whose false-accusation count has
to be zero for R2's release gate to mean anything. The rejected alternative was therefore
the original ruling itself, and it was rejected because it converts a fragile string
comparison into a release-gate dependency.

The categorical test is a boolean. It needs no threshold and no new key, it is immune to
abbreviation noise, and it encodes the plan's own words for the indicator — "preprint vs
journal" — rather than a proxy for them. The decisive point for the corpus is that **every
label is identical under either formulation**: only the code that has to satisfy them
changes, which is why B3 was safe to merge before this was settled.

Recording the reversal matters more than the ruling. The original was a preference about
wording; this one is load-bearing reasoning about what the code can actually compute, and
the difference between those two is the most useful thing this file can tell a reader.

**Consequence**: **Ritik** implements the preprint test in P5 step 2 and must not reach for
a venue comparison. **Roy** keeps every label as written. If P5 sets the indicator on year
divergence instead, `D07`-`D09` return `needs_check` + `[version_mismatch]` against a label
of `needs_check` + `[]`, and because indicator matching is exact-set all three score as
misses on a correct classification — recall drops to 18/21 and fails the plan's ≥ 19/21
target while the pipeline is behaving properly. On the Sync 1 agenda so this is implemented
deliberately rather than discovered from a red eval run.

---

## D-019 — False accusation defined, and separated from false alarm

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R2's release gate, R3, A1's `gate.py`, `config.yaml: banned_terms`.
`eval/golden/FORMAT.md` § False accusation vs false alarm.

**Decision**: A **false accusation** is exactly two things, and both are hard FAIL,
release-blocking: (1) `conflict` on any reference labelled `injected: false`, in any paper;
(2) any `banned_terms` hit anywhere in any output text. A `needs_check` on a clean reference
is a **false alarm** — tracked and reported as its own metric, **non-blocking**.
`unresolvable` on a clean reference is neither.

**Why**: The project's defensible claim is "verifiability, never accusations", and a gate
is only as good as the thing it measures. Two distinctions do the work. The first is that
wording counts as accusation independently of classification: a correct `needs_check` whose
rationale calls a citation "fabricated" has done the exact damage the project promises not
to do, so the banned-term scan has to sit inside the release gate rather than beside it.
The second is that over-caution must not be punished. `needs_check` means "a human should
look at this", and the whole product is a worklist for a human — a gate that fails the
build for producing an extra item on that worklist would push the tool toward silence,
which is the one failure mode nobody would notice. The rejected alternative was a single
"false positive" rate covering both: rejected because it makes over-caution and defamation
the same number, and the correct response to those two is opposite — tune one, ship a fix
for the other.

Keeping the false-alarm rate as a *reported, non-blocking* metric rather than dropping it
preserves the information without giving it a veto.

**Consequence**: **Roy** implements both checks in R2, and the accusation check reads
`control: true` rather than inferring the control. **Arsha** implements the same banned-term
scan in `gate.py`, which is deliberate duplication: the guard appears at three layers (A1's
prompt hard rules, `gate.py`'s scan, R2's release gate plus R3's adversarial suite) because
this is the failure the plan's risk register says kills the pitch.

---

## D-018 — Hallucinated reference → `unresolvable` + `[]`, plus a corpus requirement

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R1 (labels `D04`-`D06` and every spiked paper), R2's precision on
`unresolvable`. `docs/defect_catalog.md` § 2.

**Decision**: A fabricated-but-plausible reference is labelled `unresolvable` + `[]`. And a
corpus requirement follows: **every spiked paper must retain at least one *genuine*
`unresolvable` reference** with `injected: false`.

**Why**: A hallucinated reference is output-identical to a legitimately unresolvable one —
a book, a thesis, a standard, a web page. Nothing in the closed indicator vocabulary
distinguishes "this work does not exist" from "this work exists but no registry holds it",
and inventing an indicator to draw the line was rejected: the vocabulary is closed and
frozen at Sync 1, and adding to it for one defect type would need all three owners. Given
that the two are indistinguishable in the output, the label has to be the honest one.

The corpus requirement is the interesting half. If a paper's only `unresolvable` entries are
the injected hallucinations, then every `unresolvable` the pipeline emits on that paper is
by construction a hit, and **precision on `unresolvable` is unmeasurable** — the metric
would report 100% and mean nothing. Mixing in genuine unresolvables is what turns the status
into something that can be got wrong. This is a case where the ground truth had to be
designed, not just recorded.

**Consequence**: **Roy** must pick papers that contain at least one genuinely unresolvable
reference each — a real constraint on paper selection, not a labelling detail — and record
the reason for each in the catalog's table so a later reader does not read them as
unexplained gaps. It is checklist item 13 in `FORMAT.md`.

---

## D-017 — Orphan → `verified` + `[orphan]`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R1 (label `D15`), P5's indicator logic, A1. `docs/defect_catalog.md` § 6.

**Decision**: A reference present in the bibliography but cited by no in-text claim is
labelled `verified` + `[orphan]`, and the corpus injects it on a reference that otherwise
resolves cleanly.

**Why**: `orphan` is derived from the **claim map**, not from resolution. It says something
about how the bibliography is used, not about whether the cited work exists — so it can
co-occur with any of the four statuses, and pinning it to a status of its own would be a
category error. An uncited reference that resolves perfectly *is* verified: the citation is
sound and the note is that nothing points at it. The rejected alternative was `needs_check`,
on the reasoning that an orphan is a defect and defects deserve a human — rejected because
an uncited reference is frequently deliberate (a "see also", a data-availability citation,
an editing leftover) and putting it on the worklist spends a reviewer's attention on the
lowest-value item in the file.

Isolating it on an otherwise-clean reference is what makes the label unambiguous: if the
same reference also had a wrong year, the expected status would be contested and the row
would teach R2 nothing.

**Consequence**: **Roy** injects `D15` on a clean, resolvable reference and nothing else.
**Ritik** must compute `orphan` from the claim map in P5 rather than from the resolver
result. The corpus diagnostic depends on whether the papers use numeric or author-year
citations, which is one of the two places paper selection matters — see the catalog's
handoff notes.

---

## D-016 — Duplicate entry → `needs_check` + `[duplicate_entry]` on both rows

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R1 (label `D06`, two rows), R2's recall grouping, the `defect_id` rule.
`docs/defect_catalog.md` § 5, `eval/golden/FORMAT.md` § The `defect_id` matching rule.

**Decision**: The same work cited twice with divergent metadata is labelled `needs_check` +
`[duplicate_entry]` on **both** rows. Both rows share one `defect_id`, and the id counts as
matched only when **both** rows match.

**Why**: Divergent metadata means at least one of the two copies is wrong, and nothing in
the evidence says which — that is precisely the state `needs_check` describes, and precisely
the kind of thing a human resolves in five seconds and a rule cannot resolve at all. The
rejected alternative was `verified` on the grounds that the work does resolve: rejected
because it would assert the bibliography is fine when it demonstrably is not, and because a
`verified` row carries severity `0.0` and would drop the defect off the worklist entirely.

The all-rows-must-match rule is the part that took thought. Scoring the pair as two
independent rows would let a pipeline catch one and miss the other and be credited with half
a detection — but a half-detected duplicate means the pipeline **did not understand the two
rows are the same defect**, which is the entire thing the label exists to test. Partial
credit for a wrong answer is worse than no credit, because it moves the metric without
moving the capability. This is why the resolution is a field (`defect_id`) and not a
convention: R2 groups by id and requires unanimity.

**Consequence**: **Roy** writes two label rows sharing one `defect_id`. **Roy** implements
grouping-with-unanimity in R2 rather than per-row scoring. The 21-vs-23 gap in the corpus
totals is caused by this decision and one other multi-row defect: **21 injections, 23 label
rows**, and recall is measured over `defect_id`s.

---

## D-015 — Mangled author list → `needs_check` + `[]`, DOI-less refs only

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R1 (labels `D10`-`D12`), P5 step 3's rule order, the indicator vocabulary's
limits. `docs/defect_catalog.md` § 4.

**Decision**: A reference whose author list is truncated or corrupted is labelled
`needs_check` + `[]`, and it must be **injected only on references that have no DOI**.

**Why**: The empty indicator set is not an omission — it is a documented limitation of the
closed vocabulary. There is **no indicator for an author mismatch**, just as there is none
for a year mismatch, and the six that exist are frozen. Inventing one was rejected on the
same grounds as in D-018: a closed vocabulary that grows whenever a defect does not fit is
not closed, and the freeze is what lets R2 compare indicator arrays as exact sets. Recording
the gap as a limitation is more useful than patching it, because the gap is real and the
next person will hit it too.

The DOI-less constraint is the load-bearing half. Walk P5 step 3 on a DOI-bearing reference
with mangled authors: the DOI matches, the title is strong, and the rule reaches `verified`
before author overlap ever becomes decisive — which is *correct behaviour*, since a matching
DOI is strong evidence, but it means the defect is **untestable** on such a reference. Left
unconstrained, the label would demand `needs_check` from a pipeline that is right to say
`verified`, and R2 would report a bug that does not exist.

**Consequence**: **Roy** injects `D10`-`D12` on DOI-less references and nowhere else, which
constrains paper selection slightly. **Ritik** does not need to add an author indicator; the
catalog's mapping walk for this defect is the reference for how the rule order gets there.

---

## D-014 — The version-pair traps count inside the 21; recall is label agreement

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R2's recall denominator and its report, the plan's ≥ 19/21 target.
`eval/golden/FORMAT.md` § Recall, precisely.

**Decision**: The two preprint/journal traps (`D20`, `D21`) are inside the 21-injection
recall denominator like every other injection. Recall is redefined as **label agreement**:
an injection is "detected" when the pipeline produces the labelled status and indicator set,
which for a trap means producing `verified` + `[version_mismatch]` and **not** `conflict`.
R2 additionally prints the traps as their own named row.

**Why**: The traps are not defects — they are correctly-cited references that a naive
pipeline will flag. Counting them as detections under a "defect detection" definition of
recall would be incoherent, since there is nothing to detect. Two alternatives were
rejected. Excluding them from the 21 would leave the denominator at 19 and quietly change
the plan's target from a number the plan states to a number nobody agreed. Keeping
"detection" as the definition and special-casing the traps would put a conditional inside
the metric, which is how metrics stop being comparable. Redefining recall as label agreement
dissolves the problem instead: every row is scored the same way, the trap rows score
correct when the pipeline behaves, no measurements are mixed, and the plan's ≥ 19/21 stays
intact and means what it says.

The separate named row exists because the aggregate answers "how much of the corpus did we
get right" and the named row answers "did we avoid the specific false alarm that destroys a
reviewer's trust". The second is a demo beat and should be readable without arithmetic.

**Consequence**: **Roy** implements recall as label agreement over `defect_id`s and prints
`false-alarm on version pairs: n/2` as its own line. **Roy** must also assert that no trap
appears in the top-3 worklist — it is `verified`, severity `0.0`, so it belongs at the
bottom of the ordering, and that is assertable from the existing labels with no new field.

---

## D-013 — Preprint/journal version pair → `verified` + `[version_mismatch]`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R1 (labels `D20`, `D21`), P5 step 5's named test, A1, the worklist ordering.
`docs/defect_catalog.md` § 9.

**Decision**: A reference citing the arXiv preprint of a work later published in a journal
is labelled `verified` + `[version_mismatch]`. It must **not** produce `conflict`.

**Why**: A preprint and its published version are the same work. The citation points at
something real, by the same authors, with substantially the same content — a tool that calls
this a conflict is not being careful, it is wrong, and it is wrong in the way that costs it
a reviewer's trust permanently. Consider how it plays: a researcher runs this on their own
paper and the tool flags a citation they made correctly, following normal practice in their
field. Everything else the tool says is now suspect. One `conflict` here costs more than
three genuine misses elsewhere, because misses are invisible and false alarms are personal.

The plan permits either `verified`-with-indicator or `needs_check`, and the format's
one-defect-one-status rule forces a choice. `needs_check` was rejected: it puts a correct
citation on the human worklist, and the worklist's entire value is that everything on it
deserves a human's time. `verified` + `[version_mismatch]` says what is actually true — the
citation is sound, and here is a note about which version was cited.

**Consequence**: **Ritik** must keep `version_mismatch` out of the conflict branch in P5;
the plan puts a named test on this at P5 step 5 and R1 plants two live cases, so it is
verified twice on purpose. **Arsha**'s judge must not escalate on this indicator either.
See **D-020** for what makes the indicator fire at all.

---

## D-012 — Malformed entry → `unresolvable` + `[malformed]` for the corpus

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: R1 (labels `D13`, `D14`), P5's status rule, A1's confidence rule.
`docs/defect_catalog.md` § 8.

**Decision**: A reference with broken or missing fields is labelled `unresolvable` +
`[malformed]` for the corpus, and R1 injects the **severe** variant so the label is
unambiguous. The milder real-world variant is documented but not injected.

**Why**: This one looked like a contradiction in the plan and is not, and the distinction is
worth stating carefully because it will come up again. P5's line governs **status derived
from evidence**: nothing resolved, so the status is `unresolvable`. A1's line governs
**confidence direction**: "never toward conflict" forbids *escalation* on a malformed entry.
Those two rules operate on different outputs and never meet. Reading "never toward conflict"
as "must be `needs_check`" is the error — it forbids one destination, it does not mandate
another. The rejected alternative was `needs_check` + `[malformed]`, chosen to honour A1's
line: rejected because it would assert that a human can resolve an entry from which the
identifying fields are absent, and because it made the two plan sentences contradictory when
they are not.

Injecting only the severe variant is a corpus-integrity choice, not a modelling one. A
half-mangled entry may legitimately resolve, which would make its expected status arguable —
and one ambiguous defect poisons every metric it feeds. The mild variant is recorded in the
catalog so that a future reader knows it was considered.

**Consequence**: **Roy** injects the severe variant — the identifying fields genuinely gone.
**Ritik**'s P2 must keep `raw_text` and set `malformed` rather than dropping the entry
(`extraction_failed` is not a status). **Arsha**'s judge must not escalate a malformed entry
toward `conflict`.

---

## D-011 — Wrong year → `needs_check` + `[]`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active
(the P5 constraint it carries is **open** — see D-020)

**Affects**: R1 (labels `D07`-`D09`), P5 step 3's rule order and step 2's indicator logic.
`docs/defect_catalog.md` § 3.

**Decision**: A reference correct in every field except a publication year off by two or
three is labelled `needs_check` + `[]`, and injected on references with **no DOI**.

**Why**: The status follows from P5's own rule order rather than from taste, which is why
the catalog records the walk step by step: the work resolves (not `unresolvable`), no
retraction or DOI mismatch (not `conflict` by that branch), the `verified` branch fails on
`|year_delta| > year_tolerance` while the title is strong, the `conflict` branch does not
apply because the title is strong rather than weak — so the `else` lands on `needs_check`.
The first draft had `[version_mismatch]` in the indicator set; that was **changed**, and the
reasoning is D-020's. The empty set is then forced: no indicator in the closed vocabulary
describes a year error, the same gap as D-015's author mismatch.

The DOI-less constraint has the same shape as D-015's. On a DOI-bearing reference the DOI
matches, the year never enters the decision, and the pipeline correctly returns `verified` —
so the defect is untestable there and the label would be demanding the wrong answer.

Wrong-year is in the corpus because it is the most common *genuine* citation error in real
papers. It is the case a reviewer will actually meet.

**Consequence**: **Roy** injects `D07`-`D09` on DOI-less references. **Ritik** must not let
`version_mismatch` fire on year divergence — the single most likely cause of a wrong-year
miss, and it would be a P5 bug rather than a corpus bug. See **D-020**.

---

## D-010 — `app.py` is deleted in the A3 PR; `dashboard/app.py` is the demo entrypoint

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: A2, A3, R4. `app.py`, `dashboard/app.py`, `README.md`, `docs/setup.md`,
`tests/test_app.py`.

**Decision**: `app.py` at the repo root is the B0 shell and is **deleted as part of the A3
PR**. From A3 onward, `dashboard/app.py` is the one entrypoint anyone runs.

**Why**: Between A2 and A3 the repo has two Streamlit entrypoints, and two entrypoints means
a stranger — a judge, a teammate on a fresh clone — can run the wrong one and conclude the
project does less than it does. Deciding *when* it goes matters as much as that it goes.
Deleting it earlier was rejected because `app.py` is the only running demo until A2 lands,
and `tests/test_app.py` drives it through `AppTest` as B0's definition of done; removing it
before the dashboard works would leave the repo with nothing to show and one fewer
regression test. Leaving it indefinitely was rejected because the plan's pre-submission
sweep includes a label-and-wording check, and a stale entrypoint is exactly the kind of
thing that survives such a sweep by looking intentional.

A3 is the right seam because it is the PR where the dashboard first talks to the real
pipeline — the moment `dashboard/app.py` becomes strictly better than `app.py` for every
purpose.

**Consequence**: **Arsha** deletes `app.py` and `tests/test_app.py` in the A3 PR, and the
test count drops by 3 — expected, and it should be stated in that PR body so it does not
read as a regression. **Roy**'s R4 README and `docs/setup.md` point only at
`dashboard/app.py`. Until A3, `docs/setup.md` step 7 correctly says `streamlit run app.py`.

---

## D-009 — The priority formula lives in `src/priority.py`, shared infra, shipping with B1

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: **open** — Arsha's, since it ships
with B1

**Affects**: B1, P6, A1. `src/priority.py` (does not exist yet), `src/pipeline.py`,
`src/judge/priority.py`.

**Decision**: The priority formula — severity × claim-weight × confidence, `+0.3` if
retracted, capped at `1.0` — lives in **`src/priority.py`** as shared infrastructure, and
lands with **B1**.

**Why**: The plan says two things that do not obviously agree. P6's card says the formula
lives "here or A1", leaving it to whoever gets there first; A1 step 4 calls it a
"contract-adjacent module". The second resolves the first: contract-adjacent means it
belongs beside `src/contract.py`, not inside either lane, and the ambiguity in P6's card is
a genuine ambiguity rather than a licence to pick. The rejected alternative was to let P6
own it and have A1 import from `src/pipeline.py` — rejected because it inverts the lane
dependency exactly the wrong way: `src/judge/` would then import Ritik's orchestrator, which
is the one import direction the whole layout is built to prevent, and it would block A1 on
P6 (queue #14) when A1 is queue #6.

Shipping it with B1 rather than as its own PR follows from what it is. A formula that both
lanes call is contract-shaped, and B1 is the PR where the shared vocabulary is agreed and
frozen. Two callers, one definition, one review.

**Consequence**: **Arsha** adds `src/priority.py` to the B1 PR. **Ritik**'s P6 imports it
without importing `src/judge`; **Arsha**'s A1 imports it without importing `src/pipeline`.
Related and still unresolved: the three constants in the formula — the `0.4`/`0.2` claim
weighting, the `+0.3` retraction bonus, and the `1.0` cap — are **not** in `config.yaml`.
Key names were deliberately not invented, because naming them belongs to whoever lands the
formula. That is now Arsha, and it is five minutes at Sync 1.

---

## D-008 — Three tiers of file ownership, and the lane rule's exception for shared infra

**Date** 2026-09-03 · **Decided by** Ritik, refined by Claude's analysis of the lane rule ·
**Status**: **open** — `tests/test_layout.py` must be amended

**Affects**: every module. `docs/module_status.md` § File ownership, `tests/test_layout.py`.

**Decision**: File ownership has **three** tiers, not two.

1. **Shared infrastructure** — anyone imports it, nobody redefines it:
   `src/settings.py`, `src/llm.py`, `src/contract.py`, `src/priority.py`.
2. **Lane-exclusive** — one owner, no cross-lane edits: `src/ingest/`, `src/resolvers/`,
   `src/matching/` (Ritik); `src/judge/`, `dashboard/` (Arsha); `eval/` (Roy).
3. **Integration** — the one file two lanes touch, at A3 only.

**Why**: The plan's lane rule, read literally, forbids any import across a lane boundary.
Applied to `src/llm.py` — which sits in Ritik's file list — it would forbid A1 from calling
`src.llm.get_client()`, and the only way to satisfy it would be a **second gateway client
inside `src/judge/`**, with its own timeout handling, its own retry logic and its own
base-URL error message. That is the opposite of what the rule is for. The rule exists to
stop two people editing the same *feature* code and to stop one lane depending on another's
unmerged work; it was never meant to forbid two lanes calling the same settled utility. A
client, a settings loader and a contract are settled utilities: they are written once, and a
second copy is a bug rather than an isolation win.

The rejected alternative was to keep two tiers and let each lane own its own client:
rejected because duplicated infrastructure diverges silently — the day someone changes
`llm.timeout_seconds` and only one client reads it, the failure surfaces as an inexplicable
difference between the judge and the extractor.

**The test does not yet encode this, and it is worse than that.** `tests/test_layout.py`
forbids any file under `src/` from importing `src.judge.*` or `dashboard.*`. Two things
follow. First, `src.llm` is *not* in the forbidden list, so A1 importing it passes today —
the conflict is with the plan's prose, not with the test. Second, and this is the live bug:
the check walks **every** file under `src/`, so the moment `src/judge/agent.py` exists and
imports `src/judge/prompts.py`, the test will flag **Arsha's own intra-package import** as a
lane violation. She will hit it on her first A1 commit.

**Consequence**: **Arsha and Ritik** amend `tests/test_layout.py` before A1 lands, so that
the check exempts files that are themselves inside the lane they import from, while still
forbidding genuine cross-lane *feature* imports. Nobody writes a second gateway client.
Nobody redefines a tier-1 file in their own lane. Sync 1.

---

## D-007 — `resolvers.mailto` moves to `.env` as `CROSSREF_MAILTO`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active — **NOT YET IMPLEMENTED**

**Affects**: B2, P4. `config.yaml:17`, `.env.example`, `src/settings.py`,
`tests/test_config.py:68`, `docs/config_reference.md`, `docs/setup.md`.

**Decision**: The Crossref polite-pool contact address moves out of `config.yaml` and into
`.env` as **`CROSSREF_MAILTO`**. P4 must **refuse to start** when it is unset.

**Why**: `mailto` is per-person, not per-project. It is the one value in `config.yaml` that
is different for each of the three of us, and a tracked file with a per-person value in it
has exactly two outcomes: everyone commits their own address over each other's, or the
placeholder ships. `.env` is already the mechanism for per-person values and is already
gitignored. The rejected alternative was to leave it in `config.yaml` with a placeholder and
a comment telling each teammate to edit it — which is what the file does today, and the
reason it was rejected is the failure mode: **demotion out of Crossref's polite pool is
silent.** Nothing errors. The API keeps answering, more slowly and with tighter rate limits,
and P4 looks like it has a performance problem rather than a configuration problem. A
placeholder that still works is worse than a missing value that stops the module, because
the placeholder produces a plausible-looking wrong state that nobody investigates.

Hence the fail-fast half of the decision, which matters more than the file it lives in: an
unset `CROSSREF_MAILTO` must raise before P4 makes its first request, naming the variable
and pointing at `.env.example`, exactly as `src/llm.py` already does for `AIR_API_KEY` and
`AIR_BASE_URL`.

**Consequence**: **Ritik** implements this — it is a four-file change and it is **not done**.
`config.yaml:17` still carries `mailto: your-asurite@asu.edu`,
`tests/test_config.py:68` still asserts `"@" in config["mailto"]`, and
`docs/config_reference.md` still documents it as a config key whose failure mode is silent
demotion. Landing it means: remove the key, add `CROSSREF_MAILTO` to `.env.example`, add a
reader to `src/settings.py` that raises when unset, replace the config test with one that
asserts the key is *absent* (the pattern already used for the dropped critic keys — see
D-004), and update `config_reference.md` and `docs/setup.md`. Sensible to land with P4,
whose card is the first code that needs it, but it must not be forgotten in between — which
is why it is called out under the Sync 1 section as implementation debt rather than left in
the body of this file.

---

## D-006 — The red contract test was written and then removed

**Date** 2026-09-03 · **Decided by** Ritik, on Claude's analysis · **Status**: active
(a **reversal**)

**Affects**: B1, and how this project uses failing tests. `tests/test_layout.py`.

**Decision**: A test that would **fail** until `src/contract.py` existed was written into
the B0 branch and then **removed** before the PR. What shipped instead is
`tests/test_layout.py::test_contract_does_not_exist_yet`, which asserts the file's
**absence**, passes today, and whose docstring instructs Arsha to delete it as part of the
B1 diff.

**Why**: The intent behind the red test was sound — make the critical path impossible to
ignore by putting it in the test output, where nobody can miss it. The reason it was
reversed is what a red suite would actually have taught. Arsha's **first experience of this
repo** would have been `git checkout -b`, `pytest`, and a failure she did not cause. The
available responses to that are: fix it (impossible — B1 is hours of work), ignore it (and
now the suite is permanently red, so the next real failure is invisible), or **delete the
assertion to get to green**. The third is the one people actually pick under time pressure,
and it is a habit that generalises: on a 20-hour build with a release gate that depends on
tests meaning something, training a teammate that assertions are negotiable is a far worse
outcome than a forgotten to-do.

The absence-assertion gets the same reminder without the cost. It is green, so the suite
stays trustworthy; it is named for the thing it is waiting on, so it appears in every test
run; and deleting it is *legitimately* part of B1's diff rather than a workaround, so the
correct action and the tempting action are the same action. A red test says "someone has
failed"; a green test named `test_contract_does_not_exist_yet` says "this is the next thing".

Recorded as a reversal because the reasoning is transferable and the conclusion is not
obvious: **do not use a failing test as a to-do list for another person.**

**Consequence**: **Arsha** deletes `test_contract_does_not_exist_yet` as part of the B1 PR;
the docstring says so. Nobody adds a red test to signal unfinished work — the mechanism for
that is this file, `docs/module_status.md`, and an absence-assertion.

**Traceability**: the surviving artifact is verified —
`tests/test_layout.py:46`, green in the 39-test suite on `main`. The red variant that was
written and removed **is not verified from the tree**: both feature branches were
squash-merged, so the intermediate commits no longer exist and
`git log --all -S "test_contract"` returns only the squash commit `a579dab`.

---

## D-005 — The repro stages are out of scope by omission, not by the Section 9 cut line

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: scope, R4's pitch wording, `README.md`. `docs/descoped.md`.

**Decision**: `repro_extractor` and `repro_judge` are **descoped**, and the reason is
recorded precisely: they are absent from the plan **by omission**. They are **not** on the
plan's Section 9 cut line.

**Why**: Both stages were built into the M0 skeleton from the project's working title,
before the plan was in the repo, and neither appears anywhere in it. They had to go. The
decision worth logging is not the removal but the *distinction*, because the two reasons
have opposite consequences and are trivially easy to conflate in a month.

Section 9's cut line is explicit and ordered — biomed resolvers and batch mode, then the
claim-evidence detail view, then the donut chart — and it names what to drop **from the
planned build** if the clock runs short. Everything on it is in scope, prioritised, and
already designed; if an hour appears, you build the next item down. Reproducibility
extraction is not on that list, because it was never in the build to be cut. It is a
different question about a different object: the plan's seven steps all ask "does this
reference point at a real work, and does the record match what the paper printed", whereas
reproducibility asks whether the paper's *own* results can be reproduced.

Why the distinction is load-bearing: "cut for time" invites someone to restore it in the
hours 17-20 buffer, and Section 7's rule is "nothing new starts after hour 17". "Never in
scope" tells them it needs a design conversation, a golden-label corpus in R1 and a metrics
row in R2 first. The scope-integrity argument is the same one: the project's defensible
claim is measured against Roy's labels, and reproducibility claims have no labels and no
metrics row, so shipping them would mean shipping an unmeasured feature next to a measured
one — and R2's metrics table *is* the pitch.

**Consequence**: **Nobody** restores these two stages during this build. If the team wants
them afterwards, `docs/descoped.md` records the signatures, the slot-back-in path, and the
one blocker that needs all three owners in a room: `orphan` and `malformed` transfer to
reproducibility claims but the other four indicators do not, and the indicator vocabulary is
a **closed list frozen at Sync 1**. **Roy** owns the loose end this creates — the README
tagline still says "Provenance + reproducibility verification", which now overstates scope.

---

## D-004 — `models.critic` and `critic_temperature` removed from `config.yaml`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: **open** — Arsha's call at Sync 1

**Affects**: B2, A1. `config.yaml`, `tests/test_config.py`, `docs/config_reference.md`,
`src/judge/gate.py` (unwritten).

**Decision**: `models.critic` and `critic_temperature` are **removed** from `config.yaml`,
and `tests/test_config.py` asserts both stay absent.

**Why**: There is no critic stage. The plan folds the critic into **A1's `gate.py`**, and
`gate.py` is three code checks, not a model call: every `ref_id` has exactly one verdict;
the status counts sum to the entry total; and a case-insensitive scan of every rationale and
check against `banned_terms`. None of those is an LLM call, so both keys were configuration
that nothing could ever read. The rejected alternative was to leave them in place as
harmless: rejected because an unread config key is not harmless — it is a claim about the
architecture. Someone reads `models.critic`, concludes a critic model exists, and either
looks for the stage that reads it or writes one. Dead config is documentation that lies.

Pinning the absence with a test rather than simply deleting the keys is the deliberate part.
It means re-adding a critic model is a decision someone makes on purpose, arriving with a
failing test that points at this entry, rather than a key quietly reappearing in a diff.

**Status is open because it is not my call to close.** `gate.py` is Arsha's file. If she
concludes the gate wants a model of its own — an LLM check that the rationale is supported
by the evidence, say, which is a defensible design and not what the plan describes — then
the keys come back, the test changes, and `config_reference.md` gains two rows. What is
settled is that they do not exist *speculatively*.

**Consequence**: **Arsha** decides at Sync 1 whether `gate.py` needs a model. Until then
nobody adds a critic key back, and A1 implements the gate as three code checks. The same
accusation guard is deliberately duplicated at three layers — see **D-019**.

---

## D-003 — `src/config.py` renamed `src/settings.py` — and the plan beats the brief

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: B2 and every module that reads configuration. `src/settings.py`.

**Decision**: `src/config.py` is renamed **`src/settings.py`**. And the general rule this
establishes: **where a brief and the plan disagree, the plan wins.**

**Why**: The plan's B2 card names `settings.py`, and so does the plan's own file-ownership
table. The brief that requested this work said `config.py`, and the brief was wrong. The
rejected alternative was to follow the brief — the more deferential option, and the one that
would have been chosen by default — and it was rejected because every module card downstream
is written against the plan's paths. A future card that says `from src.settings import
model_for` would find nothing, and the person hitting that would have no way to know whether
the file had moved, been renamed, or never existed. Renaming one file now costs one `git mv`;
discovering the mismatch at P4 costs a debugging session in someone else's lane.

The general rule matters more than the rename. Three people are working from a shared plan
and separately-worded briefs, and briefs are written from memory while the plan is a
committed artifact. Making the plan authoritative means disagreements resolve the same way
every time, by anyone, without asking — and it means a brief being wrong is a normal,
correctable event rather than a conflict. **D-001** is the same principle applied to the
docs, and **D-020** is a case where the *plan's* own wording needed interpretation, which is
the harder situation and the one that goes to Sync 1.

**Consequence**: **Everyone** imports from `src.settings`. Every card, doc and PR body uses
plan paths; where a brief says otherwise, the plan is followed and the divergence is flagged
in the PR — as it was in `docs/pr/B0.md`'s flags section. One `git mv` reverses it if Sync 1
disagrees.

---

## D-002 — `src/pipeline/` split into `src/ingest/`, `src/resolvers/`, `src/matching/`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: every module in Ritik's and Arsha's lanes. `src/ingest/`, `src/resolvers/`,
`src/matching/`, `src/pipeline.py` (reserved), `tests/test_layout.py`.

**Decision**: The `src/pipeline/` **package** is gone. Its contents are redistributed into
`src/ingest/`, `src/resolvers/` and `src/matching/`, and **`src/pipeline.py` is reserved as
a FILE** for the P6 orchestrator. A test asserts both that `src/pipeline.py` does not exist
yet and that `src/pipeline/` is not a directory.

**Why**: Two collisions, one of them serious. The plan reserves `src/pipeline.py` as a file
for P6; the skeleton had `src/pipeline/` as a **package at that exact path**, so P6 could
not have been created without first undoing the layout. Worse, that package contained
`src/pipeline/judge.py` owned by Ritik, while the plan gives Arsha `src/judge/agent.py`. Had
Arsha and Roy branched off that tree, both lanes would have collided in the one place the
plan's Section 3 is engineered to keep disjoint, and the "conflicts are near-zero by design"
property would have been gone on day one — not as a merge conflict, which is visible, but as
two people writing the same module in different files.

The rejected alternative was to keep the package and put P6 somewhere else. It was rejected
because it inverts the authority: every later card in the plan is written against the plan's
paths, so moving P6 means every card that references it becomes wrong, and each person
discovers that separately. Realigning once, before anyone else branches, costs one commit;
the alternative costs an unbounded number of small corrections in three lanes. The timing
was the whole point — this was done while `main` was still at the initial commit and nobody
else had branched.

The `src/pipeline/` package came from the same source as the repro stages: an inferred
seven-stage uniform-`run()` architecture invented before the plan was in the repo. See
**D-001**, and the M0 commit message, which described exactly that: *"Streamlit skeleton
with the seven-stage pipeline scaffolded"*.

**Consequence**: **Nobody** creates `src/pipeline.py` before P6, and nobody re-creates
`src/pipeline/` as a package. **Ritik** lands P1-P5 in the three new packages. `src/judge/`
and `dashboard/` were deliberately **not** pre-created, so they arrive on **Arsha**'s branch
with an owner attached. The payoff is recorded in `docs/module_status.md`: A3 is one line of
wiring rather than a big-bang merge, and that is a direct consequence of this split.

---

## D-001 — The B0 docs were written against an inferred module mapping

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active

**Affects**: all five B0 docs, and every doc written from here on.
`docs/module_implementation_plan.pdf`.

**Decision**: The Module Implementation Plan is **committed to the repo** at
`docs/module_implementation_plan.pdf`. It is ground truth. **No doc in this repo may state
a module mapping that is not traceable to it.**

**Why**: The first five B0 docs were written before the plan was in the repo, against a
mapping inferred from the working title and the skeleton's file names. The inference was
confidently wrong in four specific ways, and the specifics matter more than the apology:
P3 and P4 were **merged** into a single resolver stage; **P4 was mistaken for the judge**;
the judge was placed in **Ritik's lane instead of Arsha's**; and **A1 was described as a
critic**, a stage the plan does not contain (see **D-004**). Every one of those errors is
about *ownership* or *interface* — precisely the class of error that a three-lane parallel
build cannot absorb, because each person reads the doc for their own lane and starts
building against it.

The rejected alternative was to fix the mapping and leave the plan out of the repo, on the
grounds that the PDF is a large binary in git. Rejected because it treats the symptom: a
correct doc with no citable source is one memory away from drifting again, and there would
be no way for a reader to tell whether a mapping is authoritative or inferred. The plan
being *in the tree* is what makes "traceable to it" a checkable claim rather than a
statement of intent — and one PDF is a cheap price for that.

The generalisation is **D-003**: a committed artifact beats anyone's recollection, including
mine. This entry is the reason that rule exists.

**Consequence**: **Everyone** treats the PDF as authoritative; where a doc and the plan
disagree, the plan wins and the doc is a bug. **Ritik** rewrote all five B0 docs against it
(commit `5f7cf6f`). Any doc asserting a module mapping cites the plan, and readers were told
explicitly not to trust a stale local copy of any doc in this repo — that warning is at the
top of `docs/pr/B0.md`.
