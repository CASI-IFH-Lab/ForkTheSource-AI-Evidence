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

The whole agenda, and nothing else. **Two entries**, plus one config key-name ratification
carried over from B1. Everything else in this file is settled and only needs reading.

| ID | One line | Whose call | Why it cannot wait |
|----|----------|-----------|--------------------|
| **D-004** | Does `gate.py` want a model of its own? `models.critic` and `critic_temperature` were **removed** from `config.yaml`. | **Arsha** | If A1 wants an LLM in the gate, two config keys and a `config_reference.md` row come back — and the removal is currently pinned by a test. |
| **D-020** | `version_mismatch` fires when **exactly one record is a preprint** — not on venue divergence, not on year alone. | **Ritik** (it constrains P5) | P5 is unwritten. Implemented any other way, three correctly-classified defects score as misses and recall fails the ≥ 19/21 target. |
| **D-032**, part 2 only | The four `priority.*` key **names** are chosen and implemented; adding them to `config.yaml` needs Ritik, whose file it is. | **Ritik** (one four-line edit) | Until they land, `compute_priority()` fails closed unless `weights=` is passed. Nothing is blocked — every caller passes `weights=` — but the default path is dead code until it happens. |

**D-004 is NOT settled by B1.** B1 adds no model call anywhere and takes no position on
whether `gate.py` wants one; that question belongs to A1 and stays Arsha's to bring to
Sync 1. Nothing in D-032 to D-035 touches it.

**Closed since this table was first written.** Three in the B1-unblock PR:

- **D-006** — the contract-absence assertion is removed. B1's diff touches no test in
  `tests/test_layout.py`, so Arsha's first commit leaves the suite green.
- **D-007** — `CROSSREF_MAILTO` is implemented: out of `config.yaml`, into `.env`, with a
  reader that raises on unset. No longer implementation debt.
- **D-008** — `tests/test_layout.py` now encodes the three tiers as constants, permits
  intra-package and shared-infra imports, and enforces cross-lane isolation in **both**
  directions.

And one in **B1** itself:

- **D-009** — **resolved by D-032.** `src/priority.py` ships in the B1 PR as shared infra,
  the formula is implemented, and the three previously un-named constants are named. Only
  the `config.yaml` edit remains, and it is Ritik's — see the D-032 row above.

## Index

| ID | Title |
|----|-------|
| D-036 | `ResolvedSource` carries `is_preprint` and `arxiv_id`; `venue` is not a preprint signal |
| D-035 | `MatchEvidence` refuses a retracted source without the indicator, and both DOIs normalise identically |
| D-034 | `doi_match` is tri-state: `None` means "no DOI to compare", not "the DOIs disagree" |
| D-033 | `Indicator` is an enum, not `list[str]` — a typo is a load-time error |
| D-032 | The priority formula, its five config keys, and why it fails closed — **resolves D-009** |
| D-031 | `check_secrets.sh` reads the gateway host out of `.env.example` |
| D-030 | `llm.timeout_seconds` is deliberately separate from `resolvers.timeout_seconds` |
| D-029 | The confidence-band `thresholds` shape was rejected |
| D-028 | Document-level defects are excluded from the golden labels and reassigned to P1 |
| D-027 | R2 must assert worklist correctness from the labels that already exist |
| D-026 | `ref_id` is an opaque string, and a labels/ledger mismatch is a HARD ERROR |
| D-025 | `document` matches `Ledger.document_name`, not the PDF filename |
| D-024 | Indicator matching is exact-set, not subset |
| D-023 | One defect, one expected status — and an ambiguous defect gets SPLIT |
| D-022 | The B3 label schema extends the plan's example with three more fields |
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
| D-006 | No test asserts the contract's absence, in either direction |
| D-005 | The repro stages are out of scope by omission, not by the Section 9 cut line |
| D-004 | `models.critic` and `critic_temperature` removed from `config.yaml` |
| D-003 | `src/config.py` renamed `src/settings.py` — and the plan beats the brief |
| D-002 | `src/pipeline/` split into `src/ingest/`, `src/resolvers/`, `src/matching/` |
| D-001 | The B0 docs were written against an inferred module mapping |

---

> ### D-022 to D-031 were logged retroactively
>
> These ten decisions were **established earlier** — most of them inside B3, two in the B2
> config pass — and were **logged in the B1-unblock pass** after a sweep of the tree found
> them unrecorded. Each carries both dates. They are ordered by ID like everything else in
> this file; the ID order is the order they were assigned, not the order they were made.
>
> Every one of them constrains a module nobody has written yet, which is why they are here
> rather than left as prose in the file that established them. That is the standing rule
> working late rather than not at all.

---

## D-036 — `ResolvedSource` carries `is_preprint` and `arxiv_id`; `venue` is not a preprint signal

**Date** 2026-09-03 (B1) · **Decided by** Arsha, on Ritik's question and live API evidence ·
**Status**: active

**Affects**: **P4** (must set `is_preprint`), **P5** (implements D-020 with it), A1.
`src/contract.py`, `docs/contract.md`. **Supersedes** the "Note for P5" paragraph in
`docs/contract.md`, which said only the venue half of D-020's test was available.

**The question**, from Ritik's review of B1: `ResolvedSource` had no `arxiv_id`, while
`Reference` did. D-020 identifies a preprint by "a preprint-server venue name **or** the
presence of an arXiv ID", so on the resolved side only the venue half looked available. Is
`venue` a reliable preprint signal? If yes, the contract ships unchanged. If no, the field
is one line **before** the Sync 1 freeze and a three-owner change after it.

**Decision**: `venue` is **not** a preprint signal. `ResolvedSource` gains two optional
fields:

```python
is_preprint: bool | None = None
arxiv_id:    str  | None = None
```

`is_preprint` is **tri-state**, with the same discipline as `doi_match` (D-034): `True` =
the provider says preprint, `False` = the provider says not, `None` = **the provider did not
say**. `None` must not be read as `False`. Resolvers set it from **provider-native signals**,
never by string-matching a venue:

| provider | rule |
|----------|------|
| Crossref | `type == "posted-content"` (or `subtype == "preprint"`) |
| OpenAlex | `primary_location.version == "submittedVersion"` **or** `primary_location.source.type == "repository"` |
| arXiv | always `True` |

`arxiv_id` is free for the arXiv resolver and optional elsewhere. The contract does **not**
parse it out of `raw`; a resolver that has it sets it, and one that does not leaves `None`.

**Why**: This was settled from live API responses, not from documentation, because the
documentation reads as though venue would work. It does not, in four separate ways.

**1. Crossref preprints have an empty venue.** `10.1101/2020.03.22.002386` (bioRxiv) returns
`type='posted-content'`, `subtype='preprint'`, and **`container-title = []`**. The server
name is not in the venue at all — it is in `institution=[{'name': 'bioRxiv'}]`, while
`publisher` reads `'openRxiv'`, which is not a string any "arXiv/bioRxiv/medRxiv/SSRN" name
list would match. A second Crossref preprint (`10.2196/preprints.40992`) is worse:
`container-title = None`, **no `institution` key at all**, `publisher = 'JMIR Publications
Inc.'` — no preprint-server name anywhere in the record.

**2. arXiv is not in Crossref at all.** `https://api.crossref.org/works/10.48550/arXiv.2005.14165`
and the same call for BERT's `10.48550/arXiv.1810.04805` both return **HTTP 404**. arXiv DOIs
are DataCite-registered; DataCite returns `publisher='arXiv'`,
`types.resourceTypeGeneral='Preprint'`, and **`container = {}`** — again an empty venue.

**3. For the version-pair case D-020 exists for, the venue names the wrong thing or
nothing.** Resolving BERT through Crossref by title gives the NAACL record
(`10.18653/v1/n19-1423`, `type='proceedings-article'`) whose `container-title` is the
conference proceedings — it names the **journal side**, never the preprint. Through OpenAlex
the same work returns `primary_location.source = null` outright, with
`locations[0].source.display_name = None`. So a venue test on the R02 row sees either a
conference name or nothing, and **can never detect that a preprint is involved**. That is the
exact scenario the indicator exists for, so a venue-based implementation of D-020 would fail
on the case it was written for.

**4. The provider-native flags, by contrast, are unambiguous and present.** The OpenAlex
preprint record returns `type='preprint'`, `primary_location.version='submittedVersion'`,
`primary_location.source.type='repository'`, `is_published=False`. The published record
returns `version='publishedVersion'`, `is_published=True`, `type='conference-paper'`. Those
are booleans in all but name; the venue is a string that is variously `[]`, `None`, a
conference title, or absent.

`arxiv_id` is added alongside because **OpenAlex has no first-class arXiv id either**: the
preprint's `ids` keys are `['openalex', 'doi', 'mag']`, and the identifier is only
recoverable by parsing `ids.doi` (`10.48550/arxiv.2005.14165`), `primary_location.id`
(`pmh:oai:arXiv.org:2005.14165`) or a PDF URL. Parsing those inside the contract would put
provider-specific string surgery in the one module that must stay provider-agnostic, so the
resolver that already knows the id sets it instead.

The rejected alternative was to ship the contract unchanged and have P5 string-match venues
against a preprint-server name list. Rejected on evidence 1-3: it would miss every Crossref
preprint (empty venue), miss arXiv entirely (absent from Crossref), and fail on the
version-pair row. It would also reintroduce exactly the fragile string comparison **D-020
itself rejected** — that entry reversed an earlier venue-divergence rule for the same reason,
and a venue *name* test is the same mistake wearing different clothes.

**Timing is the whole reason this is one line today.** The contract freezes at Sync 1 and the
vocabulary and shape then need all three owners to change. Adding two optional fields before
the freeze costs a field declaration and two tests; discovering the gap at P5 costs a
contract amendment, a fixture regeneration and a renegotiation with Roy's labels already
written.

**Consequence**: **Ritik** — P4 sets `is_preprint` from the three provider rules in the table
above, and leaves it `None` when a provider says nothing rather than guessing `False`. The
arXiv resolver sets `arxiv_id`; other resolvers may leave it `None`. **P5 implements D-020 as
"exactly one side is a preprint"** — `reference.arxiv_id`/preprint venue on the citation side,
`resolved.is_preprint` on the resolved side — and **must not** branch on venue strings. If
both sides are `None`, the indicator does not fire; absence of evidence is not evidence of a
version pair. **Arsha** — A1 must not read `is_preprint is None` as `False`. The B1 fixture
sets it explicitly on both sides of R02 so the "exactly one" reading is demonstrated rather
than described.

---

## D-035 — `MatchEvidence` refuses a retracted source without the indicator, and both DOIs normalise identically

**Date** 2026-09-03 (B1) · **Decided by** Arsha · **Status**: active

**Affects**: **P4** (which builds `ResolvedSource`), **P5** (which builds `MatchEvidence`),
A1. `src/contract.py`, `tests/test_contract.py`.

**Decision**: Two model-level guarantees, both enforced in `src/contract.py` rather than
left to callers.

1. Constructing a `MatchEvidence` whose `resolved.is_retracted` is `True` **raises** unless
   `retracted` is in `indicators`. There is no way to build the inconsistent object.
2. `ResolvedSource.doi` is normalised by **exactly the same rule** as `Reference.doi` —
   lowercased, `doi:`/`doi.org/` prefix stripped, trailing whitespace and punctuation
   stripped, `None` left as `None`, and never invented.

**Why**: Both are cases where the *obvious* implementation puts a false accusation one
mistake away.

On the first: a retraction is the single highest-severity signal in the system — D-032
gives it a flat `+0.3` and it is the one thing that reliably lifts an entry into the
reviewer's top-3. If P5 sets `is_retracted` and forgets the indicator, the entry resolves,
looks ordinary, scores low and **sinks below correctly-cited references**. Nothing fails;
the run is simply silently wrong in the one place it most matters, and the failure is
invisible in every aggregate metric because the counts still sum. A validator turns that
into a stack trace at the moment of construction, which is the cheapest possible place to
find it. The rejected alternative was a lint or a gate check in A1: rejected because the
object would already have been built, serialised and possibly scored by then, and because
two lanes construct `MatchEvidence` independently — a guarantee that lives in the type
holds for both without either having to remember it.

On the second: P5 compares `Reference.doi` against `ResolvedSource.doi` to set `doi_match`.
If only the citation side were normalised, a reference printing
`https://doi.org/10.1/X` against a resolver returning `10.1/x` compares **unequal**, and
the pipeline emits `doi_mismatch` → `conflict` on a **correctly-cited reference**. That is
a false accusation under D-019 — release-blocking, on the clean control, caused entirely by
string formatting. Crossref and OpenAlex genuinely differ in how they return DOIs (bare vs.
resolver-URL form), so this is a live case, not a hypothetical. Normalising one side only
is the natural thing to write, because `Reference.doi` is the field the brief talks about.

**Consequence**: **Ritik** — P4 may return whatever form a provider gives; the model
normalises it. P5 may compare `reference.doi == resolved.doi` directly and must not add its
own normalisation step (that would be a second, drifting implementation — the D-008
argument). P5 must set the `retracted` indicator whenever it sets `is_retracted`, or
construction raises. **Arsha** — A1 may rely on a retracted entry always carrying the
indicator. `tests/test_contract.py` pins both, including the four-case parametrised DOI test
run against **both** models.

---

## D-034 — `doi_match` is tri-state: `None` means "no DOI to compare", not "the DOIs disagree"

**Date** 2026-09-03 (B1) · **Decided by** Arsha · **Status**: active

**Affects**: **P5** (`src/matching/evidence.py`), A1, R2's precision on `conflict`.
`src/contract.py`, `docs/defect_catalog.md` § 1.

**Decision**: `MatchEvidence.doi_match` is `bool | None`, and the three values are distinct
and load-bearing:

| value | meaning |
|-------|---------|
| `True` | both records carry a DOI and they agree |
| `False` | both records carry a DOI and they **disagree** |
| `None` | **at least one side has no DOI**, so no comparison was possible |

`None` is not a default, not "unknown", and specifically **not** a synonym for `False`.

**Why**: Collapsing `None` into `False` is the most natural simplification available here —
`Optional[bool]` is awkward, and "not a match" reads like it covers both — and it converts
**every DOI-less reference into a DOI mismatch**. DOI-less references are common and
entirely legitimate: books, theses, standards, older papers, and by D-011's and D-015's
explicit injection constraints they are exactly where the wrong-year and mangled-author
defects live. Under the collapse, all of them acquire `doi_mismatch`, and `doi_mismatch` is
the branch that maps to `conflict` — so a correctly-cited book becomes a `conflict` on the
clean control, which is a release-blocking false accusation under D-019.

The reverse collapse is just as bad in the other direction: treating a real disagreement as
`None` because "we could not confirm it" hides D-01–D-03 entirely. `docs/defect_catalog.md`
already names this as **the** likely swapped-DOI failure mode — *"`doi_match` is coming back
`None` (treated as 'no DOI to compare') instead of `False`"* — so Roy's catalog is already
written against this tri-state. Recording it here means P5 is built against the same reading
rather than rediscovering it from a red eval run.

The rejected alternative was a plain `bool` defaulting to `False`, which is what the field
would be if nobody thought about it, plus a separate `has_doi` flag. Rejected because two
fields that must be read together are a worse contract than one field with three values —
the second field is the one someone forgets.

**Consequence**: **Ritik**'s P5 sets `None` whenever either side lacks a DOI, and must not
branch to `doi_mismatch` on `None`. **Arsha**'s A1 must not read `None` as evidence of
anything. The B1 fixture models `False` on its `doi_mismatch` entry (R03) precisely so the
distinction is demonstrated rather than described.

---

## D-033 — `Indicator` is an enum, not `list[str]` — a typo is a load-time error

**Date** 2026-09-03 (B1) · **Decided by** Arsha · **Status**: active

**Affects**: **P5** (emits indicators), A1, **R2** (compares them). `src/contract.py`,
`eval/golden/FORMAT.md`.

**Decision**: The six indicators are a `str`-valued `Enum`, and `MatchEvidence.indicators`
is `list[Indicator]`, not `list[str]`. An unrecognised value raises `ValidationError` when
the object is built or the ledger is loaded. Duplicates are collapsed on assignment, order
preserved. `INDICATORS` is exported as a tuple of the string values for anyone who wants to
iterate the vocabulary without importing the enum.

**Why**: The vocabulary is **closed and frozen at Sync 1** (D-005), and D-024 compares
indicator arrays as **exact sets**. Those two facts together mean a misspelling is not a
cosmetic problem — it is a scoring failure. `version_mismatch` typed as `version-mismatch`
or `versionmismatch` produces an indicator set that matches no label, so a **correctly
classified** reference scores as a miss, and it does so with no error anywhere: the string
is valid, the JSON is valid, the ledger loads, the counts sum. It surfaces as unexplained
recall loss in R2, attributed to the classifier rather than to a keystroke — which is
precisely the failure D-029 describes for the wrong config shape, arriving by a different
route.

Three lanes emit or read these strings independently, which is what makes a free `str`
untenable: there is no single place a typo would be caught, and the value crosses a JSON
boundary where any type information is lost. The enum puts the check at the boundary in both
directions — construction *and* `load_ledger()` — so a hand-edited fixture or a
hand-written label file fails loudly rather than scoring quietly.

`use_enum_values=True` keeps the runtime and JSON representation a plain string, so this
costs no ergonomics: `"orphan" in ev.indicators` works, and the serialised ledger is
unchanged. The rejected alternative was `list[str]` plus a validator checking membership —
functionally close, rejected because the enum is also the *documentation*: it gives the
vocabulary one definition that IDEs complete and that `INDICATORS` is derived from, rather
than a list that has to be kept in step with a docs table by hand.

**Consequence**: **Ritik**'s P5 and **Arsha**'s A1 import `Indicator` rather than writing
string literals. **Roy**'s R2 can trust that any ledger which loads has a valid indicator
vocabulary, so an unmatched indicator is a real classification difference rather than a
typo. Adding a seventh indicator changes this enum and needs all three owners (D-005).

---

## D-032 — The priority formula, its five config keys, and why it fails closed

**Date** 2026-09-03 (B1) · **Decided by** Arsha · **Status**: active — **resolves D-009**

**Affects**: **P6** and **A1** (both call it), B1. `src/priority.py`, `config.yaml`
(`priority.*`), `src/settings.py`, `tests/test_layout.py` (`SHARED_INFRA`).

**Decision**, in three parts.

**1. `src/priority.py` is shared infrastructure and ships in the B1 PR.** This is D-009's
question, and the answer is yes, as written. The reasoning that settles it is the **mutual
independence** of the two callers: P6 imports it without importing `src/judge`, and A1
imports it without importing `src/pipeline`. Neither lane has to exist for the other to
call the formula. Had it lived in either lane, one lane would import the other's feature
code — the single import direction the whole layout is built to prevent (D-008) — and A1
(queue #6) would block on P6 (queue #14). A file both lanes call, that calls neither, is
the definition of tier 1.

**2. The formula, and the five numbers it reads.** Implemented exactly as:

```
severity(status)
  * min(1.0, usage_base + usage_step * max(0, n_citing_claims))
  * confidence
  + (retracted_bonus if 'retracted' in ev.indicators else 0)
```

clamped to `[0, cap]`, rounded to 3dp. **All five come from `config.yaml` under
`priority.*` — none is inlined.** `priority.severity` already exists (B2). The other four
are the constants D-009 left un-named and `docs/pr/B0.md` flag 3 deferred; naming them was
B1's to do, and the names are:

| key | value | what it does |
|-----|-------|--------------|
| `priority.usage_base` | `0.4` | floor for a reference cited by zero claims |
| `priority.usage_step` | `0.2` | added per citing claim, saturating at 3 claims |
| `priority.retracted_bonus` | `0.3` | flat addition when `retracted` is present |
| `priority.cap` | `1.0` | upper clamp |

**They are not yet in `config.yaml`, because `config.yaml` is Ritik's file.** Adding those
four lines is the only outstanding piece of D-009 and is on the Sync 1 list.

**3. It fails closed.** With the keys absent, `compute_priority()` raises `RuntimeError`
naming exactly which are missing. It does **not** fall back to the numbers in the table
above, even though they are written down right here.

**Why**: Parts 1 and 2 are covered above. Part 3 is the one worth arguing.

A hardcoded fallback is the obvious kindness — the numbers are known, the formula would just
work, and nobody is blocked. It is rejected because **priority is invisible when it is
wrong.** Every other value in the ledger is checkable against something: a status has a
label, an indicator has an exact-set comparison, a DOI either resolves or does not. A
priority score is a float nobody can eyeball, and its only observable effect is the
*ordering of the worklist* — which D-027 makes a demo beat and R2 asserts only indirectly.
If code and config ever disagreed, the run would produce a plausible ordering derived from
stale constants, and the first person to notice would be a reviewer wondering why a retracted
paper was fourth. A loud failure at the moment of the first call costs one traceback; a quiet
one costs the credibility of the thing the demo is built around.

This also keeps faith with B2's own rule, which `src/settings.py` states in its docstring and
implements with no `.get(key, fallback)` anywhere: *there are no defaults in code.* A
fallback in `src/priority.py` would be the first exception to it, and exceptions to that rule
are how a config layer stops being the source of truth.

The cost is real and accepted: until the four keys land, the no-argument call path raises.
It is survivable precisely because `weights=` exists — every caller in the tree passes the
block explicitly, so B1 merges and unblocks A1, A2 and R2 with the formula fully exercised.

**Consequence**: **Ritik** adds the four keys above to `config.yaml` (and a
`docs/config_reference.md` row each), after which the default path goes live with no code
change. **Ritik**'s P6 and **Arsha**'s A1 both call
`compute_priority(ev, verdict, n_citing_claims)` and neither reimplements it; P6 must keep
`verified` at severity `0.0` so D-027's version-pair assertion holds. **Nobody** adds a
default to `src/priority.py`.

`tests/test_contract.py::test_priority_config_is_either_complete_or_fails_closed` pins this
**as a contract rather than as the current state of the file**, and passes in both states:
with the four keys present it asserts the default path scores from config; with them absent
it asserts the `RuntimeError` names exactly the missing keys and contains none of the
formula's numbers, which is what would give away a hardcoded default. Which branch runs is
read from `config.yaml` through `src.settings`, never assumed. **So adding the four keys
does not turn the suite red** — the fail-closed branch simply stops being exercised, and
nothing needs deleting or updating alongside the config edit.

That is deliberate. An earlier draft of this test asserted the keys were *absent*, which
would have gone red the moment Ritik made the change this entry asks him for — reading as
"your config PR broke B1", inviting a revert of a correct change, and breaking the ground
rule that the suite is green when a PR opens. A test that fails when someone does the right
thing is a to-do list wearing a test's clothes, which is the trap **D-006** already names.

---

## D-031 — `check_secrets.sh` reads the gateway host out of `.env.example`

**Established** 2026-09-03 (B0 secrets pass) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: every PR, via `tests/test_no_secrets.py`. `scripts/check_secrets.sh`,
`.env.example`.

**Decision**: Check 2 of `scripts/check_secrets.sh` — "the gateway host appears nowhere
outside `.env.example`" — obtains the host by **parsing it out of `.env.example`'s
`AIR_BASE_URL` line at runtime**, never from a literal in the script.

**Why**: The script exists to forbid the gateway host from appearing in any tracked file
except `.env.example`. `scripts/check_secrets.sh` is itself a tracked file. Hardcoding the
host in it would therefore **violate the rule the script enforces** — the guard would be
the first thing it should flag, and either the check has to special-case its own source
file or the rule quietly becomes "everywhere except two files". The rejected alternative
was exactly that: hardcode the host and exempt the script. It was rejected because a rule
with a carve-out for the enforcement mechanism stops being checkable — the next person to
add a "temporary" exemption has a precedent, and the exemption list is where this kind of
guard goes to die.

Reading the value from the template also makes the check follow a change it would otherwise
silently miss: if the gateway moves, `.env.example` is the one file that must be updated,
and the guard re-targets itself with no second edit.

The cost is a real dependency: the script hard-fails if `.env.example` is missing, and says
so with the `git checkout --` command to restore it. That is the correct trade — a guard
that cannot find its source of truth must refuse to report PASS.

**Consequence**: **Everyone** — do not hardcode the host in the guard, and do not add an
exemption list to it. If a check needs a value that lives in `.env.example`, read it from
there. `tests/test_no_secrets.py` proves the guard catches a planted host as well as a
planted key, so the mechanism cannot rot into a script that always passes.

---

## D-030 — `llm.timeout_seconds` is deliberately separate from `resolvers.timeout_seconds`

**Established** 2026-09-03 (B2 config pass) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: P2, P4, A1. `config.yaml`, `src/settings.py` (`llm_settings()`,
`resolver_settings()`), `docs/config_reference.md`.

**Decision**: Two separate timeout keys. `resolvers.timeout_seconds: 10` is the **HTTP**
timeout for catalogue lookups; `llm.timeout_seconds: 60` applies to **every model call, at
any stage**. `tests/test_config.py` asserts they are not equal.

**Why**: They are measuring different things and one number cannot serve both. A Crossref
or OpenAlex lookup is a REST call that should come back in under a second; ten seconds is
already generous, and a longer value means one dead endpoint stalls a whole document. A
reasoning model judging a long bibliography is a different order of wait entirely — the
judge model is `qwen3-235b-a22b-thinking-2507`, and ten seconds would time out **every
judge call**. The rejected alternative was a single `timeout_seconds` reused by both, which
is the obvious first shape and is what the config had before this pass: rejected because
whichever value you pick breaks the other caller, and the failure is asymmetric and
misleading. At 10s the judge never answers and A1 looks broken; at 60s a dead resolver
endpoint holds a document open for a minute per reference and P4 looks slow.

The test pinning them unequal is the load-bearing part. The two keys sitting in different
blocks is not self-explaining — the natural instinct on reading two timeouts is to
"simplify" them into one — so the reason is asserted rather than left in a comment.

**Consequence**: **Ritik**'s P2 and P4, and **Arsha**'s A1, read the right one:
`llm_settings()["timeout_seconds"]` for anything that calls a model,
`resolver_settings()["timeout_seconds"]` for HTTP. Setting them equal reintroduces the bug
and fails `test_llm_settings_are_separate_from_http_settings`.

---

## D-029 — The confidence-band `thresholds` shape was rejected

**Established** 2026-09-03 (B2 config pass) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active (a **reversal** — the shape was proposed, then
discarded)

**Affects**: P5, R2, A1. `config.yaml` (`thresholds:`), `tests/test_config.py`.

**Decision**: `thresholds:` holds **signal cutoffs** — `title_strong: 0.92`,
`title_weak: 0.70`, `author_strong: 0.60`, `year_tolerance: 1`. The proposed shape
`thresholds: {verified: 0.9, needs_check: 0.6, conflict: 0.3}` — a confidence cutoff per
status — was **discarded**.

**Why**: The two shapes look interchangeable and describe completely different classifiers.
The plan's P5 is a **rule mapping over signals**: compare title similarity, author overlap,
year delta and DOI match against cutoffs, and walk an ordered set of branches to a status.
The proposed shape describes something else entirely — a model or heuristic that emits a
confidence number, which is then **banded** into a status. That is not P5, and more
importantly it is not what R2 measures. R2 scores status agreement against Roy's golden
labels, and those labels were derived by walking P5's rule order (see the mapping walks in
D-011 and D-015). A confidence-band classifier would produce different statuses for the
same evidence, so the labels would be measuring a classifier that does not exist.

The reason this is worth an entry rather than a config comment: **the wrong shape would
have shipped silently and looked right.** Four plausible keys under a plausible name, and
nothing in the config layer can tell that a threshold is being compared against the wrong
quantity. It would have surfaced as unexplained recall loss at R2, attributed to the model
rather than to the config shape. Recording it means the next person who reaches for a
confidence band has to argue with the reason instead of rediscovering it.

**Consequence**: **Ritik**'s P5 compares these four values against *signals*, never against
a confidence. **Nobody** adds a per-status confidence cutoff to `thresholds:` — if a
confidence band is ever wanted, it is a new key and a new entry, because it changes what
R2's numbers mean. `tests/test_config.py::test_thresholds_match_the_plan` pins all four
values, so retuning them requires saying so in a PR.

---

## D-028 — Document-level defects are excluded from the golden labels and reassigned to P1

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: R1, R2, **and P1 — this is B3 assigning work into Ritik's lane**.
`eval/golden/FORMAT.md` § *Two things this format deliberately does not express*.

**Decision**: Defects that apply to a whole document rather than to one reference — chiefly
P1's no-heading fallback, the last-15%-of-pages path — are **out of the golden-label
system**. They belong in a **separate fixture PDF under `tests/`, owned by P1**.

**Why**: The label file's unit is the reference. Every row is keyed by `ref_id` and every
assertion is about one bibliography entry, so a document-level defect has **nothing to
attach to**. Two alternatives were rejected. Adding a document-level defect block to the
schema was rejected because it would give R2 a second, differently-shaped thing to score
for a single test case, and because it would not compose with the `defect_id` recall
denominator — a document-level defect is not one of the 21. Attaching it to a synthetic
`ref_id` was worse: it would **re-index every other label in the file**, and `ref_id`
assignment is already flagged in FORMAT.md as the fragile coupling point between the
labels and the ledger.

The reassignment to `tests/` follows from where the defect actually is. The no-heading
fallback is P1's behaviour, it is deterministic plain code, and a unit test over a
purpose-built fixture PDF tests it far more precisely than a golden-label run over a real
paper — where the fallback would be one signal among twenty-three rows of noise.

**Consequence**: **Ritik** owns this: P1's card should carry a fixture PDF with no
`References` heading, plus a test asserting the last-15% fallback fires and records its
note. **Roy** does not label it, and should not accept a request to. FORMAT.md carries the
one-line statement so the question does not get reopened at R1.

---

## D-027 — R2 must assert worklist correctness from the labels that already exist

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: R2, and **P6's ordering**. `eval/golden/FORMAT.md` § *`confidence`, `priority`
and `checks[]` stay unlabelled*; `docs/defect_catalog.md` § 9.

**Decision**: `confidence`, `priority` and `checks[]` are **not labelled**. But R2 must
still assert the worklist, using only the fields already in the labels: **every reference in
the top-3 worklist has `injected: true`**, and **no version-pair trap appears in the top-3
worklist**.

**Why**: Labelling a confidence number would pin ground truth to an uncalibrated scale —
there is no agreed meaning for 0.7, so the label would encode whatever the pipeline happened
to emit, which is the failure D-023 exists to prevent. That rules out labelling the
ordering directly.

But the ordering is exactly what a reviewer looks at, and it can be wrong while every
aggregate metric passes. Per-status precision and recall are **order-blind**: a pipeline
that classifies all 23 rows correctly and then sorts the worklist by `ref_id` scores a
perfect metrics table and presents a useless top-3. **The top-3 worklist is a demo beat**,
so that failure is both invisible to the metrics and highly visible to an audience.

The insight is that the assertion needs no new field. `injected: true` already identifies
which references should rank; the version-pair traps are already labelled `verified`, whose
severity weight is `0.0`, so they belong at the bottom by construction. Two checks over
existing data catch the whole failure class. The rejected alternative — adding an
`expected_rank` or `expected_priority` field — was rejected because it would make R1 hand-
compute a formula that D-009 has not finished deciding, and every label would need rewriting
the day a formula constant changes.

**Consequence**: **Roy** implements both assertions in R2. **Ritik**'s P6 must order the
worklist by priority, and must keep `verified` at severity `0.0` so the traps sink — if P6
ever gives `verified` a non-zero weight, this assertion fails and it should. Also related:
D-014's separate named row for the traps.

---

## D-026 — `ref_id` is an opaque string, and a labels/ledger mismatch is a HARD ERROR

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: **P2** (which generates `ref_id`s), R1, R2. `eval/golden/FORMAT.md` § *`ref_id`
assignment — the one coupling point*.

**Decision**: `ref_id` is compared as an **opaque string**: `"R03"` and `"R3"` are different
ids and neither normalises to the other. A `ref_id` in the labels with no matching ledger
entry — or a ledger entry with no matching label — is a **hard error that stops the run**,
not a miss.

**Why**: Two decisions in one, and the second is the important one.

Opaque comparison, rather than parsing the number out and comparing integers, because
normalisation is where quiet wrongness lives. If R2 treats `R3` and `R03` as equal, then a
labels file using one convention and a pipeline using the other appear to join correctly,
and the join silently misaligns the moment padding width changes between papers — say a
paper with 100+ references. Comparing opaquely means the *format* is part of the contract,
which is checkable, rather than an implementation detail of two independent parsers.

Hard error rather than miss, because the two failures need opposite responses and look
identical in a score. A `ref_id` that does not join is not "the pipeline got this reference
wrong" — it is "the labels and the ledger are describing different bibliographies", and
every other number in the report is then meaningless. Scored as a miss, it produces a
plausible slightly-lower recall figure that invites tuning; raised as an error, it says the
one true thing: stop, the join is broken. FORMAT.md notes this is easy to misdiagnose,
which is exactly why it must not be absorbed into a metric.

**Consequence**: **Ritik**'s P2 must emit `ref_id` in the `R` + zero-padded-position form,
with a **consistent width within one file**. **Roy**'s R1 uses the same form and R2 raises
rather than scoring on any unmatched id. Nobody adds a normalisation step to "be helpful" —
that is the bug, not the fix.

---

## D-025 — `document` matches `Ledger.document_name`, not the PDF filename

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: **P6** (which sets `document_name`), R1, R2. `eval/golden/FORMAT.md` top-level
schema and § *Rulings*.

**Decision**: A label file's top-level `document` field joins to
**`Ledger.document_name`** — not to the PDF's filename on disk. It must also match the
label file's own filename stem (checklist item 1), with `EXAMPLE.json` exempted as a
documented specimen.

**Why**: The join has to be to something the pipeline actually emits. `Ledger.document_name`
is in the contract; the PDF's path is not, and it is the more volatile of the two — a
corpus file gets renamed, moved under `eval/corpus/`, or copied, and none of that should
break a scoring run. Joining on the filename would also make the labels depend on how a
particular machine stores the file, which is the same class of mistake as the `.venv`
absolute paths.

The filename-stem requirement is a separate, cheap consistency check rather than a second
join key: it means a human writing a label file cannot silently create one whose `document`
points at a different paper than its own name suggests. That bug was actually caught by the
13-item checklist on its first run against `EXAMPLE.json` — the specimen's stem did not
match its `document` field, which would have made R2 fail on a human-written file. Being
two independent statements (join on `document_name`; keep the stem in step) is what let the
checklist find it.

**Consequence**: **Ritik**'s P6 sets `Ledger.document_name` to a short identifier with no
spaces or path separators, and must not set it to the PDF's basename-with-extension.
**Roy** names each label file `<document>.json`. **Roy**'s R2 joins on `document_name` and
may check the stem.

---

## D-024 — Indicator matching is exact-set, not subset

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: R2, and through it **every** indicator decision — D-011, D-013, D-015, D-018,
D-020. `eval/golden/FORMAT.md` § *`expected_indicators` is a SET, not a sequence*.

**Decision**: `expected_indicators` is compared as an **unordered set, exactly**. Not as a
subset, not as a "contains at least". `[]` is therefore a **positive assertion that the
pipeline emitted no indicators**, not a wildcard.

**Why**: This is the decision that gives every other indicator ruling force, and it is easy
to underrate because it reads like a serialisation detail.

Under subset matching, `[]` matches anything — so a label of `needs_check` + `[]` for a
wrong year would be satisfied by a pipeline emitting
`needs_check` + `[version_mismatch, duplicate_entry, orphan]`. **D-011 and D-020 would have
no teeth at all**: the entire argument for why `version_mismatch` must not fire on year
divergence rests on a spurious indicator being *detectable*, and under subset matching a
spurious indicator is free. The same applies to D-015 and D-018, whose empty sets are
deliberate records of a gap in the closed vocabulary rather than "we did not check".

Unordered, because indicator order carries no meaning and ordering it would make R2 fail on
a pipeline that is right — a set semantics with a list serialisation.

The rejected alternative was subset matching, on the reasonable-sounding grounds that it is
more forgiving of a pipeline that adds a useful extra signal. It was rejected because
"forgiving" here means "cannot detect a false alarm", and false alarms are the failure mode
the plan's risk register says kills the pitch. A metric that cannot see the thing you are
most afraid of is not a lenient metric, it is the wrong metric.

**Consequence**: **Roy**'s R2 compares indicator arrays with set equality and no duplicates
within an array (checklist item 7). **Ritik**'s P5 and **Arsha**'s A1 must not emit
"informational" extra indicators — every indicator emitted is scored, and an unlabelled one
is a miss on an otherwise-correct classification.

---

## D-023 — One defect, one expected status — and an ambiguous defect gets SPLIT

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: **R1's corpus construction**, R2's recall. `eval/golden/FORMAT.md` § *Rule: one
defect, one expected status*. Not in the plan.

**Decision**: Every injected defect maps to **exactly one** `expected_status`. If a defect
could plausibly land on two statuses, **the injection is wrong and must be split into two
separate injections**, each with a single unambiguous outcome. The label is never the thing
that gets adjusted.

**Why**: This is the rule that keeps recall honest, and the direction of the fix is the
whole point.

The failure it prevents: someone finds a defect whose correct status is genuinely arguable,
writes down whichever status the pipeline produced that day, and the label becomes a
**description of current behaviour rather than of correct behaviour**. Recall then measures
agreement between the pipeline and itself, which is a number that can only go up. One
ambiguous label poisons every metric it feeds, and it does so invisibly — nothing in the
report says "this row is circular".

The rejected alternative was to allow a set of acceptable statuses per defect, scoring a
hit if the pipeline produced any of them. That is superficially more honest about genuine
ambiguity, and it was rejected for two reasons. It makes recall non-comparable between runs
(a pipeline that flips between two accepted answers scores identically to one that is
stable), and it removes the pressure that makes the corpus good: the discipline of having to
produce an unambiguous outcome is what forces the injection to be *sharp*. D-012 is this
rule in action — the malformed defect has a mild variant whose status is arguable and a
severe variant whose status is not, and the corpus injects only the severe one.

**Consequence**: **Roy** — when you find yourself writing "this should be `needs_check`, or
maybe `conflict`", stop and change the **injection**, not the label. Two clean defects score
honestly. This constrains how the corpus is built, not just how it is written down, and it
is the reason several catalog entries carry an injection constraint (DOI-less references in
D-011 and D-015, the severe variant in D-012, an otherwise-clean reference in D-017).

---

## D-022 — The B3 label schema extends the plan's example with three more fields

**Established** 2026-09-03 (B3) · **Logged** 2026-09-03 (B1-unblock) ·
**Decided by** Ritik · **Status**: active

**Affects**: **R1** (writes 23 rows against it) and **R2** (reads all of it).
`eval/golden/FORMAT.md` top-level and per-label schema, `eval/golden/EXAMPLE.json`.

**Decision**: The label format adds three things beyond the plan's minimum example:
**`control`** (top level), **`source: {license, origin_url, origin_file}`** (top level), and
**`verified_by` / `verified_on`** (per label, optional). `defect_id` is the fourth addition
and is covered separately by **D-016** — see there for the 21-vs-23 rule and the
all-rows-must-match requirement.

Specifying this format *is* B3's job, and the plan's example is explicitly a minimum shape,
so extending it is in scope. Each field exists to stop R2 inferring something from the
`defect` free text, which FORMAT.md is explicit is never scored.

**Why**:

**`control` is the load-bearing one.** R2's release-blocking check is "zero false
accusations on the clean control", so R2 has to know which file *is* the control. The
rejected alternative was to infer it — the control is the file where every label has
`injected: false`. That inference is wrong in a way that fails silently and at the worst
moment: it holds only while every spiked paper has its labels written, and it breaks the
instant a spiked paper is committed before its label file is finished. At that point a
second file looks like a control, and the release gate either runs twice or runs on the
wrong paper. A read field cannot drift; an inference over data that arrives incrementally
can. Explicit beats derived whenever the derivation depends on the completeness of
something else.

**`source` makes an R1 DoD box checkable.** R1's card requires "no copyright-restricted or
student material", which as written is a claim someone asserts in a PR body and nobody can
verify afterwards. `license` — one of five allowed strings, anything else a hard error —
turns it into a property of the tree. `origin_url` and `origin_file` do the same for
provenance: `origin_file` names the untouched original so anyone can reproduce R1 step 3's
diff, which is why `eval/corpus/originals/` stays tracked. **This also constrains paper
selection**: Roy can only use papers whose licence is one of the five.

**`verified_by` / `verified_on` are optional on purpose.** R1's test plan has a teammate
spot-verify five random labels. Without a field, that verification exists only in a Slack
message. Making it *required* would be worse than useless — most labels will never be
spot-checked, so a required field would be filled with placeholder noise, and a field
everyone fills in mechanically records nothing. Optional means its presence is information.

**Consequence**: **Roy** — R1 writes all three; `source.license` restricts which papers are
eligible; R2 must **read** `control` and must never infer it. `verified_by`/`verified_on`
are paired (checklist item 10) — one without the other is an error. **Nobody** adds a field
to this schema without an entry here, because R1 writes 23 rows against it and a schema
change after R1 starts is 23 hand-edits.

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

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: **RESOLVED by D-032** (B1). The
ruling below stands as written and was implemented unchanged; **D-032** adds the reasoning
that settles it, names the three un-named constants, and records why the reader fails closed
rather than defaulting. The only outstanding piece is the four-line `config.yaml` edit, which
is Ritik's — see the *Open at Sync 1* table.

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
**Status**: active, **CLOSED** by the B1-unblock PR — `tests/test_layout.py` now encodes
all three tiers

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

**Consequence — DONE.** `tests/test_layout.py` was rewritten in the B1-unblock PR so the
test encodes the rule instead of approximating it:

- **`SHARED_INFRA` and `LANES` are module-level constants** with a comment citing this
  entry, so moving a file between tiers is a data change rather than a logic change.
- **`lane_of(module)` returns `None` for shared infra** — belonging to no lane is exactly
  what makes it importable from every lane — and **`cross_lane_offenders(owner, names)`
  skips a file's own lane**, so `src/judge/agent.py` importing `src/judge/prompts.py` is
  fine. That was the live bug.
- **Shared infra is asserted POSITIVELY** (`test_shared_infra_is_importable_from_any_lane`,
  parametrised over all four modules), so a future "tightening" that adds `src.llm` to a
  lane's prefix list fails with a pointer back here.
- **Both directions are enforced.** `test_arshas_lane_may_not_import_ritiks_pipeline` is
  new and is A2's own DoD box — the dashboard renders `ledger_fixture.json` fully offline,
  and nothing previously stopped `dashboard/app.py` importing `src/pipeline`.
- **The rules are armed, not vacuously true** while `src/judge/` and `dashboard/` are
  absent: three tests assert that the classifier *does* reject the forbidden imports.

Verified by simulation before merge: a realistic `src/judge/{__init__,prompts,agent}.py`
plus `dashboard/{app,theme}.py` importing intra-package **and** `src.llm`, `src.settings`,
`src.contract` → **17 passed**. `dashboard/app.py` importing `src.pipeline` → caught.
`src/matching/rules.py` importing `src.judge.agent` → caught.

Standing obligations: **nobody** writes a second gateway client, and **nobody** redefines a
tier-1 file inside their own lane.

---

## D-007 — `resolvers.mailto` moves to `.env` as `CROSSREF_MAILTO`

**Date** 2026-09-03 · **Decided by** Ritik · **Status**: active, **IMPLEMENTED** in the
B1-unblock PR

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

**A third reason, found while implementing this.** A real mailbox in a tracked file is the
same *category* of mistake as a pasted key — not the same severity, since nobody can spend
your inbox, but the same shape: a real personal identifier, committed under an org name
that looks public, discoverable by anyone who clones, and permanent in the history once
pushed. The B0 pass already had one near-miss of exactly this shape with the first 16
characters of a live key (`docs/worklog.md`, session 2). The lesson generalised: the
control has to be mechanical. Behind `.env`, `.gitignore` enforces the rule instead of a
comment asking each teammate to remember it.

**Consequence — DONE.** Landed in the B1-unblock PR:

| Change | Where |
|--------|-------|
| `resolvers.mailto` removed, replaced by a comment pointing here | `config.yaml` |
| `CROSSREF_MAILTO` added as a name with a placeholder value | `.env.example` |
| `crossref_mailto() -> str` — reads the env, raises on unset **or whitespace** | `src/settings.py` |
| `mailto` asserted **absent** from config; reader asserted to raise unset and to strip when set | `tests/test_config.py` (+3 tests) |
| `mailto` row removed; API section and a *why it is a credential* section added | `docs/config_reference.md` |
| Step 4 now lists all three env names, with the failure mode for each | `docs/setup.md` |
| P4 row records the obligation and marks this implemented | `docs/module_status.md` |

**Ritik**'s P4 must call `settings.crossref_mailto()` before its first request and let it
raise. **Arsha and Roy** need to add `CROSSREF_MAILTO` to their own `.env` — nothing calls
it yet, so an absent value is currently silent, and P4 will be the first code to notice.
The reader raises rather than returning `""` so a caller cannot pass emptiness through to a
`User-Agent` header and get the demotion anyway.

---

## D-006 — No test asserts the contract's absence, in either direction

**Date** 2026-09-03, **amended 2026-09-03** (B1-unblock pass) · **Decided by** Ritik, on
Claude's analysis · **Status**: active, **closed by the B1-unblock PR** (a **reversal**,
twice)

**Affects**: B1, and how this project uses tests to signal unfinished work.
`tests/test_layout.py`.

**Decision**: `tests/test_layout.py` contains **no assertion about `src/contract.py` at
all** — neither that it exists nor that it does not. **B1's diff therefore touches no test
in that file**, and creating `src/contract.py` leaves the suite green.

This entry records two passes at the same problem:

1. **A red test was written and removed before the B0 PR.** It would have failed until
   `src/contract.py` existed.
2. **The green absence-assertion that replaced it was itself removed** in the B1-unblock
   pass, before Arsha branched. That is the amendment, and it is the operative half.

**Why**: The intent behind the red test was sound — make the critical path impossible to
ignore by putting it in the test output, where nobody can miss it. What a red suite would
actually have taught is the problem. Arsha's **first experience of this repo** would have
been `git checkout -b`, `pytest`, and a failure she did not cause. The available responses
are: fix it (impossible — B1 is hours of work), ignore it (and now the suite is permanently
red, so the next real failure is invisible), or **delete the assertion to get to green**.
The third is what people pick under time pressure, and the habit generalises: on a 20-hour
build whose release gate depends on tests meaning something, teaching a teammate that
assertions are negotiable costs more than a forgotten to-do.

`test_contract_does_not_exist_yet` looked like it escaped that, and for a while the
argument was that it did: green today, named for the thing it was waiting on, and deleting
it was *legitimately* part of B1's diff rather than a workaround. **That argument does not
survive contact with the actual sequence of events.** Arsha's first B1 commit is
`src/contract.py`. The moment she makes it, the suite goes red — for doing exactly the
right thing — and the prescribed fix is *deleting an assertion*. The docstring saying
"DELETE THIS TEST IN THE B1 PR" makes it discoverable, not harmless: it makes
delete-the-assertion the **documented, correct, first-thing-you-learn** response to a red
suite. That is the precise habit the first pass rejected, arrived at by a longer route.

The rejected alternative, both times, was keeping a test as the reminder. It was rejected
because a test is the wrong instrument for the job. A test says "this is broken". A to-do
says "this is next". They are different statements and the test suite can only make the
first one. The reminder belongs where reminders belong — `docs/module_status.md`, which now
carries it in prose, and this file.

**The generalisation, which is the transferable part:** *do not use a test as a to-do list
for another person — and that includes a green test whose resolution is deleting an
assertion.* If removing an assertion is the intended outcome of someone else's work, the
assertion was documentation wearing a test's clothes.

**Consequence**: **Arsha** creates `src/contract.py` and the suite stays green; there is
nothing in `tests/test_layout.py` for her to delete. **Nobody** adds a test — red or green
— to signal unfinished work. `src/pipeline.py`'s absence assertion
(`test_pipeline_module_is_reserved_for_p6`) is **deliberately kept** and is not an exception
to this rule: nobody is scheduled to create `src/pipeline.py` as a package, so that test
guards against a mistake rather than waiting on a task, and its resolution is not "delete
the assertion" but "stop doing that".

**Traceability**: the removal is verified — `tests/test_layout.py` collected 11 tests
before this PR including `test_contract_does_not_exist_yet`, and 17 after, without it. The
**red** variant from pass 1 is **not verified from the tree**: both feature branches were
squash-merged, so the intermediate commits no longer exist and
`git log --all -S "test_contract"` returns only the squash commit `a579dab`.

**One correction to this entry's own earlier wording.** As first written, its title and
Decision said the contract test "was written and then REMOVED", which read as though the
*absence*-assertion had already been removed. It had not — it was live on `main` at
`278fccd`, and `docs/module_status.md` was correct to say so. The two documents did not
actually contradict each other; the entry was describing the red variant and was easy to
misread as describing the green one. Rewritten above to state what is true of the tree.

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

---

## Documented choices that are deliberately NOT decisions

The sweep that produced D-022 to D-031 also found four choices that were considered for an
entry and **left out on purpose**. They are real, they are written down, and their owner
should be free to change them without amending a decision log:

- **The 7-7-7 defect split across three papers** — Roy's, in `docs/defect_catalog.md`. The
  plan says only "~21 across three papers"; a different split may suit the papers he picks.
- **The `defect_id` numbering, fixed before paper selection** — Roy's, same file. Ids that
  never shift let R2 be written before a PDF exists, at the cost of not grouping by paper.
  Renumbering is cheap **before** R1 starts and expensive after, which is a note, not a
  rule.
- **The clean control being in the same field and of similar length** as the spiked papers —
  Roy's, same file. Guidance for paper selection, and he is the one selecting.
- **`tests/data/sample.pdf` vs the plan's `tests/sample.pdf`** — Ritik's, in
  `docs/module_status.md` § Deviations. P1's card calls for a real open-access paper, so P1
  replaces the file anyway and should settle the path then.

**Why this distinction is worth keeping.** An entry in this file is a commitment that
someone else may now be relying on, and the standing rule at the top makes changing one a
documented act. That is exactly right for a rule that constrains another person's module,
and exactly wrong for a working choice inside one's own lane — logging those would convert
every revision an owner makes into a decision reversal, which raises the cost of improving
your own work. **The test is not "was this a choice" but "does someone else's unwritten code
depend on it".** All four of these fail that test; all ten of D-022 to D-031 pass it.
