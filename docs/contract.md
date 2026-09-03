# Module B1 — the shared data contract

`src/contract.py` (`CONTRACT_VERSION = "v0"`) defines the types every lane
(intake, resolvers, matching, judge, dashboard) reads and writes when
crossing a lane boundary. A type only one lane touches is not a contract
type — see the module docstring for what's deliberately excluded and why
(`ParsedDocument` → `src/ingest/`, matching thresholds → `config.yaml`,
prompts → each lane's own `prompts.py`).

> **The contract is `v0` and freezes as `v1` at Sync 1.** Until then a field
> or a validator can still change with an entry in
> [decisions.md](decisions.md). After Sync 1 the status vocabulary and the
> indicator vocabulary are **closed lists** (D-005), and changing either
> needs all three owners — the indicator set in particular, because D-024
> compares indicator arrays as exact sets, so adding a seventh value
> silently rewrites what every existing golden label means. P4 is the
> merge-queue gate that enforces the freeze.

## Models

**Reference** — one entry from a document's reference list, as intake
extracted it. Written by `src/ingest/`. `raw_text` is always kept, even when
nothing else parses. `doi` normalizes on assignment (lowercased, prefix and
trailing punctuation stripped) but is never invented — an absent DOI stays
`None`. `cited_by_claims` is the inverse of the claims' `ref_ids`.

**Claim** — one in-text statement that cites one or more references.
Written by `src/ingest/`.

**ResolvedSource** — what an external provider (arXiv, Crossref, an
anthology, …) returned when a resolver looked a reference up. Written by
`src/resolvers/`. `raw` keeps the provider's original payload for
auditability; everything else is the fields the rest of the pipeline
actually needs. **Its `doi` is normalized by exactly the same rule as
`Reference.doi`** — lowercased, `doi:`/`doi.org/` prefix stripped, trailing
whitespace and punctuation stripped, `None` left as `None` — so that the two
sides of a DOI comparison are like-for-like and a provider returning
`https://doi.org/10.1/X` never reads as a mismatch against a citation
printing `10.1/x` (**D-035**).

It also carries **`is_preprint`** and **`arxiv_id`**, both optional
(**D-036**). `is_preprint` is **tri-state**, with the same discipline as
`doi_match`: `True` = the provider says preprint, `False` = the provider
says not, `None` = **the provider did not say**. `None` must not be read as
`False` — that would turn "we could not tell" into "definitely published",
which is the assertion D-020's test must never make on missing data.

> **Note for P5 — set `is_preprint` from provider-native signals, never
> from `venue`.** Live API responses (quoted in full in **D-036**) show
> `venue` cannot carry this: Crossref preprints return
> `container-title = []` with the server name in `institution` and
> `publisher` reading `'openRxiv'`; arXiv DOIs are **404 in Crossref**
> entirely (they are DataCite); and for a work with both versions the
> resolved record's venue is either the conference name or, in OpenAlex,
> `null` — so a venue test can **never** detect the version pair it exists
> for. The rules that do work:
>
> | provider | rule |
> |----------|------|
> | Crossref | `type == "posted-content"` (or `subtype == "preprint"`) |
> | OpenAlex | `primary_location.version == "submittedVersion"` **or** `primary_location.source.type == "repository"` |
> | arXiv | always `True` |
>
> D-020 is then "**exactly one side is a preprint**" — `Reference.arxiv_id`
> on the citation side, `ResolvedSource.is_preprint` on the resolved side.
> If both are `None`, the indicator does not fire. `arxiv_id` is free for
> the arXiv resolver and optional elsewhere; the contract does not parse it
> out of `raw`.

**MatchEvidence** — the comparison between a `Reference` and its
`ResolvedSource` (or the absence of one). Written by `src/matching/`.
`indicators` is deduplicated on assignment, order preserved. If
`resolved.is_retracted` is `True`, the `retracted` indicator must be
present — that invariant is enforced in the model, not left to callers to
remember (**D-035**). **`doi_match` is tri-state and all three values
matter**: `True` = both sides have a DOI and they agree, `False` = both have
one and they **disagree**, `None` = **at least one side has no DOI, so no
comparison happened**. `None` is not a synonym for `False`; reading it as
one turns every legitimately DOI-less reference (books, theses, standards)
into a `doi_mismatch` → `conflict`, which is a false accusation under D-019
(**D-034**).

**Verdict** — the judge's call on a reference: a status, a confidence, why,
and up to three suggested checks for a human reviewer. Written by
`src/judge/`.

**LedgerEntry** — one `Reference` plus its `MatchEvidence`, `Verdict`, and
computed `priority`, with all three `ref_id`s required to agree.

**Ledger** — the whole document's `Claim`s and `LedgerEntry`s, plus
`document_name` and the `contract_version` it was written under. Assembled
by `src/pipeline.py`; read by `dashboard/`.

## Status vocabulary (`VerdictStatus` / `STATUSES`)

| status | meaning |
|---|---|
| `verified` | Resolves to a record that matches the citation; nothing outstanding. |
| `needs_check` | Resolves, but the evidence is ambiguous in a way only a human can settle (e.g. a duplicate pair with divergent metadata, where one copy is wrong and nothing says which). |
| `conflict` | Resolves, but to something that contradicts the citation (wrong DOI, retracted, duplicate). |
| `unresolvable` | No resolver returned a matching record, whether or not the citation itself parsed. |

There is deliberately no `extraction_failed` status. A reference whose
extraction failed keeps its `raw_text`, gets the `malformed` indicator, and
stays in the ledger as one of the four statuses above like any other entry
— extraction failure is not a fifth category of judgment.

## Indicator vocabulary (`Indicator` / `INDICATORS`)

Indicators are **orthogonal to status**: they describe *why* a reference
looks the way it does, while status describes *what to do about it*. Any
indicator can in principle co-occur with any status; the fixture's
`version_mismatch` → `verified` pairing (below) exists specifically to
guard against collapsing "why" into "what to do."

| indicator | meaning |
|---|---|
| `retracted` | The resolved source is marked retracted by its publisher. |
| `version_mismatch` | The citation and the resolved source are different versions/stages of the same work (e.g. preprint vs. published). |
| `doi_mismatch` | The citation's printed DOI and the DOI of the work it names disagree (`doi_match` is `False`, never `None`). |
| `duplicate_entry` | This entry's resolved source is also the resolved source of another entry, with conflicting metadata between them. |
| `orphan` | The reference resolves cleanly but no claim in the document cites it. |
| `malformed` | The citation text couldn't be parsed into a structured reference. |

## Priority formula

`src/priority.py`'s `compute_priority(ev, verdict, n_citing_claims, weights=None)`:

```
severity(status)
  * min(1.0, usage_base + usage_step * max(0, n_citing_claims))
  * confidence
  + (retracted_bonus if 'retracted' in ev.indicators else 0)
```

...clamped to `[0, cap]` and rounded to 3 decimal places. An unknown status
in `severity` raises `KeyError` — it never silently scores as 0.

All five numbers are configuration, read from `config.yaml`'s `priority.*`
block via `src.settings` (never inlined, no fallback — **D-032**).
`priority.severity` is already on `main` from B2; the other four keys are
**named by D-032 but not yet in `config.yaml`**, because that file is
Ritik's. Until they land, `_load_priority_config()` raises a `RuntimeError`
naming exactly the missing keys when called without `weights=`. That is
deliberate rather than a gap to paper over: a wrong priority score is
invisible — it only shows up as a mis-ordered worklist — so failing loudly
beats scoring from stale constants. Every caller in this codebase (tests,
the fixture generator) passes `weights=` explicitly, so nothing is blocked.
The full block, once the four keys are added:

```yaml
priority:
  severity:
    conflict: 1.0
    needs_check: 0.6
    unresolvable: 0.5
    verified: 0.0
  usage_base: 0.4
  usage_step: 0.2
  retracted_bonus: 0.3
  cap: 1.0
```

## The 8-entry fixture

`tests/fixtures/build_ledger_fixture.py` builds `tests/fixtures/ledger_fixture.json`
through the real models and `compute_priority` (weights passed explicitly).
Re-run it to regenerate the file — nothing in it is hand-typed.

Every status/indicator pairing below matches the ruling that governs it in
[decisions.md](decisions.md) and the mapping table in
[defect_catalog.md](defect_catalog.md), so the fixture and the golden labels
teach the same thing:

| ref | status | indicator | resolved? | scenario | ruling |
|---|---|---|---|---|---|
| R01 | verified | — | yes, no DOI | clean match via arXiv id | — |
| R02 | verified | version_mismatch | yes | preprint cited, journal version resolved — must **not** be conflict | D-013, D-020 |
| R03 | conflict | doi_mismatch | yes | title/authors identify the work; the printed DOI belongs to a different record, so `doi_match=False` | D-034 |
| R04 | conflict | retracted | yes | resolves correctly but the source is retracted | catalog D16/D17 |
| R05 | unresolvable | — | no | plausible entry, no record found | D-018 |
| R06 | unresolvable | malformed | no | unparseable "ibid." entry, `raw_text` preserved | D-012 |
| R07 | **verified** | orphan | yes | resolves perfectly, cited by no claim | **D-017** |
| R08 | **needs_check** | duplicate_entry | yes | same underlying DOI as R02, divergent printed venue | **D-016** |

Status counts: `{verified: 3, needs_check: 1, conflict: 2, unresolvable: 2}`.
Evidence coverage: `0.75` (R05/R06 are the two unresolved entries — the
fixture also asserts `resolved is None ⇔ status == unresolvable`). All six
indicators appear exactly once.

Two things about R07 and R08 that are easy to get backwards, which is why
each is pinned by its own test:

- **`orphan` is `verified`, not `needs_check`** (D-017). The indicator is
  derived from the claim map, not from resolution — it says how the
  bibliography is *used*, not whether the work exists. An uncited reference
  that resolves cleanly is a sound citation with a note attached, and
  putting it on the reviewer's worklist spends attention on the
  lowest-value item in the file.
- **`duplicate_entry` is `needs_check`, not `conflict`** (D-016). Divergent
  metadata means at least one copy is wrong and the evidence does not say
  which — exactly what `needs_check` describes. `conflict` would assert the
  bibliography is definitely wrong and, at severity `1.0`, would crowd the
  top of the worklist.

**Known fixture simplification.** D-016 puts `duplicate_entry` on **both**
rows of a duplicate pair, sharing one `defect_id`. Here only R08 carries it:
R02 is the version-pair example, and a second indicator on it would blur the
one row that exists to prove `version_mismatch` never means `conflict`.
Doing both properly needs a ninth entry (D-023's "split the injection"
rule). Roy's golden labels, not this fixture, are what R2 actually scores.
