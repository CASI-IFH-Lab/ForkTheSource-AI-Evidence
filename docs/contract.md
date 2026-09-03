# Module B1 — the shared data contract

`src/contract.py` (`CONTRACT_VERSION = "v0"`) defines the types every lane
(intake, resolvers, matching, judge, dashboard) reads and writes when
crossing a lane boundary. A type only one lane touches is not a contract
type — see the module docstring for what's deliberately excluded and why
(`ParsedDocument` → `src/ingest/`, matching thresholds → `config.yaml`,
prompts → each lane's own `prompts.py`).

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
actually needs.

**MatchEvidence** — the comparison between a `Reference` and its
`ResolvedSource` (or the absence of one). Written by `src/matching/`.
`indicators` is deduplicated on assignment, order preserved. If
`resolved.is_retracted` is `True`, the `retracted` indicator must be
present — that invariant is enforced in the model, not left to callers to
remember.

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
| `needs_check` | Resolves, but something about it (e.g. no in-text citation) needs a human look. |
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
| `doi_mismatch` | The printed DOI resolves to a record that doesn't match the citation's title/authors. |
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
block via `src.settings` (never inlined). Neither exists yet, so today
`_load_priority_config()` raises `RuntimeError` naming the missing keys if
called without `weights=`; every caller in this codebase (tests, the
fixture generator) passes `weights=` explicitly. The expected block:

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

| ref | status | indicator | resolved? | scenario |
|---|---|---|---|---|
| R01 | verified | — | yes, no DOI | clean match via arXiv id |
| R02 | verified | version_mismatch | yes | preprint cited, journal version resolved — must not be conflict |
| R03 | conflict | doi_mismatch | yes | real title/authors, DOI belongs to a different record |
| R04 | conflict | retracted | yes | resolves correctly but the source is retracted |
| R05 | unresolvable | — | no | plausible entry, no record found |
| R06 | unresolvable | malformed | no | unparseable "ibid." entry, raw_text preserved |
| R07 | needs_check | orphan | yes | resolves perfectly, cited by no claim |
| R08 | conflict | duplicate_entry | yes | same underlying DOI as R02, divergent printed year/venue |

Status counts: `{verified: 2, needs_check: 1, conflict: 3, unresolvable: 2}`.
Evidence coverage: `0.75` (R05/R06 are the two unresolved entries — the
fixture also asserts `resolved is None ⇔ status == unresolvable`). All six
indicators appear exactly once.
