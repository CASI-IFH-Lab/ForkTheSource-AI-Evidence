# RITIK — Core Pipeline Lane

**Read `00_TEAM_PLAN_SHARED.md` first. This document assumes it.**

Paste both documents into your agent at session start. For each task say:
*"Generate the prompt for P1 from my document, then execute it."*

---

## Your vertical

PDF in, `Ledger` JSON out. Six modules, one branch each, six merges. You own the spine:
if your lane stalls, the demo has no data. You are also the only person who touches
`config.yaml`, and in Phase 1 you touch it **zero times** — it is already complete.

**You own:**

```
src/ingest/          pdf_parser.py, extractor.py, claims.py, prompts.py
src/resolvers/       cache.py, crossref.py, openalex.py, arxiv.py, resolver.py
src/matching/        evidence.py, rules.py
src/pipeline.py      the orchestrator (a FILE, not a package)
scripts/             run_pipeline.py, precache_demo.py, update_status.py
app.py               the B0 shell (deleted in A3 — leave it alone until then)
tests/               test_intake, test_extractor, test_cache, test_resolvers,
                     test_evidence, test_pipeline_smoke, test_layout, test_config,
                     test_no_secrets, and tests/data/
progress/ritik.md
docs/decisions.md    D-100 – D-199 only
```

**You never touch:** `src/judge/`, `dashboard/`, `eval/`, `tests/fixtures/`, `tests/test_contract.py`,
`src/contract.py`, `src/priority.py`, `src/settings.py`, `src/llm.py`, `config.yaml`,
`docs/defect_catalog.md`, `README.md`.

Two of those will tempt you. `src/settings.py` is yours by history but it is Tier 1 now
and frozen — if a reader is missing, file a REQUEST to yourself for Phase 2 and use
`load_config()` directly. `config.yaml` already has every key you need; the four
thresholds, the resolver providers, the cache TTL, the LLM timeout, all of it. Do not add
one.

---

## Hour 0 — the tooling only you can land (0:00–0:20)

Before P1, land the status system. It is 20 minutes and it is what stops the other two
from asking you what is on main.

### Task S0 — `scripts/update_status.py` + hooks + `STATUS.md`

Branch `ritik/s0-status`. Merge it before you start P1.

**Build:**

`scripts/update_status.py` — regenerates `STATUS.md` from, in order:
1. `git log --oneline -20 main` — what has merged
2. `git branch -r` — what is in flight, with who owns it (parse `owner/module`)
3. The three `progress/*.md` files — the most recent block from each, plus every open
   `REQUEST` and `BLOCKED` anywhere in them
4. `pytest --collect-only -q | tail -1` — the test count
5. The published-interface table, hardcoded from §7 of the shared plan, with a ✅ or ⬜
   per line depending on whether the symbol is importable from `main`

`STATUS.md` layout, in this order, because the top is what people actually read:

```markdown
# STATUS — generated <timestamp>, main @ <sha>
## ⚠️ OPEN REQUESTS AND BLOCKERS      <- first. anything here is someone waiting.
## What is on main                     <- merged modules, newest first
## In flight                           <- remote branches, owner, age
## Published interfaces                <- the §7 table, ✅/⬜ per symbol
## Latest from each lane               <- last block of each progress file
## Tests: N passed
```

Hooks: `.githooks/post-commit` and `.githooks/post-merge`, both calling the script.
Ship `scripts/install_hooks.sh` (`git config core.hooksPath .githooks`) and put one line
in each teammate's hour-zero checklist to run it.

Also add `.github/workflows/status.yml`: on push to `main`, run the script, commit
`STATUS.md` back if it changed. Guard against the recursive trigger with
`if: "!contains(github.event.head_commit.message, '[status]')"` and commit with `[status]`
in the message.

**DoD:** script runs clean on the current tree; `STATUS.md` committed; hooks install with
one command; open REQUESTs from all three progress files appear at the top; running it
twice with no changes produces no diff.

**Then post in chat:** "Status tooling on main. Run `bash scripts/install_hooks.sh` once.
`cat STATUS.md` before you branch anything."

---

## P1 — PDF intake (0:20–1:20, ~50 min)

Branch `ritik/p1-intake`. Plan card: section 4, P1.

**What exists:** `extract_pages`, `extract_text`, `run(pdf, config=None)` returning
`{"pages","text","page_count"}`. `locate_bibliography` is a stub that raises.

**What you owe — the public interface, which does not exist:**

```python
parse_pdf(path) -> ParsedDocument
ParsedDocument = {name, pages: list[str], tables: list, body_text,
                  references_text, ref_start_page, notes: list[str]}
```

`ParsedDocument` is a dataclass **in `src/ingest/`**, not in `src/contract.py`. Both P2
and A3 are specced against `parse_pdf`; the three existing functions become its internals.

**Steps:**

1. Per-page `try/except`. A corrupt page appends to `notes` and yields `""`. Preserve the
   invariant that a page's index is its page number minus one.
2. References split: scan for a heading **alone on its line** matching
   `^\s*(?:\d+\.?\s*|[IVXLC]+\.?\s*)?(references|bibliography|works cited|literature cited)\.?\s*$`
   case-insensitive. Split at the **LAST** such match — papers list "References" in a
   section index. `ref_start_page` is the page containing it.
3. No-heading fallback: last 15% of pages, minimum one, plus a note. `references_text`
   must never be silently empty when the document has text.
4. `tables` ships as `[]`. Phase 2 fills it. Do not call `extract_tables()` today.
5. `run(pdf, config)` — required positional, matching every other entry point — delegates
   to `parse_pdf`. Update `app.py`'s call.

**Fixtures** under `tests/data/`: replace `sample.pdf` with a real CC-BY arXiv paper;
add `no_heading.pdf`, `false_heading.pdf` (a "References" mid-body then a real one later),
`image_only.pdf`.

**DoD:**
```
[ ] parse_pdf runs on 3 real PDFs, no exception
[ ] references split correct on sample.pdf; ref_start_page correct
[ ] no-heading fallback covered by a test, note emitted
[ ] false_heading.pdf splits at the LATER heading
[ ] image_only.pdf returns a valid ParsedDocument with a note, no raise
[ ] a page that raises is skipped with a note; other pages still return
[ ] two calls on sample.pdf produce equal ParsedDocuments
[ ] pytest green; check_secrets PASS; no network imports; no model names
```

**Merge, then post:** *"P1 merged. `from src.ingest.pdf_parser import parse_pdf`.
`ParsedDocument.references_text` is the string P2 splits."* Update `progress/ritik.md`.

---

## P2 — AIR reference extractor (1:20–2:20, ~55 min)

Branch `ritik/p2-extractor`. **This is your first AIR call and it is a demo beat.**

```python
extract_references(doc: ParsedDocument) -> list[Reference]
extract_claims(doc, refs) -> list[Claim]     # plain regex, no LLM
```

Files: `src/ingest/extractor.py`, `src/ingest/claims.py`, `src/ingest/prompts.py`.
Model from `settings.model_for("extractor")`, temperature from
`settings.temperature_for("extractor")`. **Never hardcode a model name** — the ground-rule
grep `grep -rn "qwen\|glm\|gemma\|sk-" src/` must stay at exit 1.

**Steps:**

1. **Pre-split entries in plain Python first.** Numbered markers `[1]` / `1.` / `1)`;
   blank-line fallback for author-year styles. Send the model **one entry per call**, not
   the whole block. This is what makes it deterministic and debuggable.
2. System prompt in `prompts.py`: strict JSON out, `null` for absent fields, never guess
   an identifier, never normalise a title beyond whitespace. No prose, no fences.
3. Validate each reply against `Reference`. On failure: **retry once** (`llm.max_retries`),
   then emit the entry with `raw_text` preserved and the `malformed` indicator carried
   forward. **Extraction never drops an entry** — the count of references out equals the
   count of entries in.
4. `extract_claims`: regex `[n]`, `[n,m]`, `[n-m]` in body sentences; fill
   `cited_by_claims` both directions. Never-cited entries get `orphan` in P5, not here.
5. Determinism test: two runs on `sample.pdf` produce byte-identical JSON with sorted
   keys. **This gates the merge.** If the model will not settle at temp 0.1, do not
   rewrite prompts — log a D-1NN and note it; a non-deterministic extractor is a Phase 2
   problem, not a reason to miss checkpoint 1.

Cache the per-entry responses on disk keyed by the entry text, so re-runs during
development cost nothing and the demo is instant.

**DoD:**
```
[ ] two runs on sample.pdf -> byte-identical JSON
[ ] a deliberately mangled entry yields malformed + raw_text, no crash
[ ] len(references out) == len(entries pre-split in)
[ ] claims map to correct ref_ids on sample.pdf
[ ] no model name in src/; temperature and model read from settings
[ ] pytest green; check_secrets PASS
```

**Post:** *"P2 merged. AIR extractor live on `models.extractor`. `extract_references(doc)
-> list[Reference]`. Determinism: 2 identical runs."*

---

## P3 + P4 — cache and resolvers (2:20–3:20, ~60 min, one branch)

Branch `ritik/p3-p4-resolvers`. Merge them together to save a cycle.

**P3, `src/resolvers/cache.py`:**
```python
make_key(url, params) -> str
cache_get(key) -> dict | None      # None if missing or TTL-expired
cache_set(key, payload: dict) -> None
```
SQLite at `settings.cache_dir()/resolver_cache.sqlite` (gitignored). Table
`(cache_key TEXT PRIMARY KEY, payload TEXT, fetched_at REAL)`. TTL from
`resolvers.cache_ttl_hours` (72). Non-JSON bodies stored transparently as `{"_text": body}`.
WAL mode. Two functions plus the key builder — if we ever want Redis, only this file changes.

**P4, `src/resolvers/{crossref,openalex,arxiv,resolver}.py`:**
```python
resolve(ref: Reference) -> ResolvedSource | None
```

Waterfall — **note the reorder, this is D-037 and it matters:**

1. If `ref.arxiv_id` is set **or** `ref.doi` starts with `10.48550/` → **arXiv first**,
   then OpenAlex. Crossref 404s every DataCite DOI, and a correctly-cited preprint falling
   through to `unresolvable` is byte-identical to what our eval labels a hallucinated
   reference. That would make our recall number wrong in our own favour.
2. Otherwise DOI → Crossref.
3. Otherwise title → Crossref `query.bibliographic`, then OpenAlex `?search=`.

Per provider: cached GET, 10s timeout (`resolvers.timeout_seconds`), one retry, normalise
into `ResolvedSource`, attach a trimmed raw payload **and a deterministic lookup URL** —
the dashboard's one-click evidence link depends on it.

**Always read OpenAlex `is_retracted`** (Retraction Watch data). That single field powers
the `retracted` indicator, which is the highest-severity thing we detect. When Crossref
resolves a DOI, query OpenAlex for the retraction flag on the same DOI.

**P4 also populates two fields P5 depends on — this is D-036 and it is where D-020's
implementation begins:**
- `ResolvedSource.is_preprint` — **tri-state**, from provider-native signals only:
  arXiv resolver → `True`; Crossref `type == "posted-content"` → `True`;
  Crossref `type == "journal-article"` / OpenAlex `type == "article"` with a journal
  source → `False`; anything else → `None` (provider didn't say). **Never** infer it from
  the `venue` string — live responses show `venue` is unusable for this (Crossref
  preprints return an empty container-title). And `None` is not `False`.
- `ResolvedSource.arxiv_id` — set when the arXiv resolver handled the lookup.

Crossref polite pool: `settings.crossref_mailto()` reads `CROSSREF_MAILTO` from `.env`
and **raises when unset — that is D-007's decided behaviour**, because demotion out of
the polite pool is silent. Call it once at module import of `crossref.py` so the failure
is immediate and its message tells the user exactly what to add to `.env`.

Failure returns `None` with a note. A registry outage becomes `unresolvable` downstream,
never an exception. Tests use recorded fixture responses; **no live network in the test
suite.**

**DoD:**
```
[ ] cache set/get/expiry tested with a fake clock; cache/ gitignored
[ ] second lookup of the same DOI is < 50ms and makes no network call
[ ] all three providers return a normalised ResolvedSource on fixture responses
[ ] an arXiv-DOI reference (10.48550/*) resolves — does NOT return None
[ ] timeout and outage paths return None, never raise
[ ] is_retracted set from an OpenAlex fixture for a known retracted DOI
[ ] every result carries a lookup URL
[ ] pytest green, no live network in tests
```

**Post:** *"P3+P4 merged. `resolve(ref) -> ResolvedSource | None`. arXiv-first for
DataCite DOIs per D-037. Retraction flag live."*

---

## P5 — evidence and rules (3:20–4:10, ~50 min)

Branch `ritik/p5-evidence`. `src/matching/evidence.py`, `src/matching/rules.py`.
**This is the deterministic heart, and it is also the judge's fallback**, so Arsha's A3
imports `rule_based_status` by name.

```python
build_evidence(ref, resolved, ledger_refs: list[Reference]) -> MatchEvidence
rule_based_status(ev: MatchEvidence) -> tuple[str, float, str]
```

**Signals:** `title_similarity` = token-sort fuzzy ratio on normalised titles (rapidfuzz,
difflib fallback). `author_overlap` = Jaccard on last names.
`year_delta = abs(resolved.year - reference.year)` — **the field is `ge=0` in the
contract and a signed value raises at construction.** The natural implementation,
`resolved.year - ref.year`, crashes on every reference cited too late, which is the
primary injection direction of the wrong-year defect. Compute the abs, and log a D-1NN
documenting the duty so the next person's traceback points at a rule instead of at
pydantic. `doi_match` — **tri-state**: `True` / `False` / `None` when either side lacks a
DOI. `None` is not `False`; a missing DOI is not a mismatch (D-034).

**Indicators — the closed six:**
- `retracted` — from the resolver flag
- `doi_mismatch` — printed DOI resolves to a different work
- `version_mismatch` — **exactly one of the two sides is a preprint, asserted only on
  known values.** Reference side: `ref.arxiv_id` set, or `ref.doi` starts `10.48550/`.
  Resolved side: `resolved.is_preprint is True`. If `resolved.is_preprint is None`, you
  do not know, so you do **not** fire the indicator — `None` collapsed into `False` would
  assert "definitely the published version" on missing data, the exact move D-020
  forbids. Require strong title similarity too (the plan's own wording: title+authors
  strong but the version differs). **Not** venue string divergence, **not** year alone.
  This closes D-020's P5 half — the last open decision in your lane; log the D-1NN.
- `duplicate_entry` — same normalised title+year twice in `ledger_refs` with divergent
  metadata
- `orphan` — never cited in the body
- `malformed` — carried from P2

**Classifier — thresholds ONLY via `settings.thresholds()`** (`title_strong` 0.92,
`title_weak` 0.70, `author_strong` 0.60, `year_tolerance` 1 — the reader already exists,
do not re-parse config.yaml):

```
no resolved                                      -> unresolvable
retracted or doi_mismatch                        -> conflict
strong title + year ok + (doi or authors agree)  -> verified
weak title + no author overlap                   -> conflict
otherwise                                        -> needs_check
```

**`version_mismatch` alone must NOT produce `conflict`.** It is verified-with-indicator or
`needs_check`. Write that as a named test — preprint/journal pairs are our number one
false-alarm source and Roy has planted one in the corpus specifically to catch it.

Rationales use neutral evidence language. **Add a test asserting no `banned_terms` entry
(read from `settings.banned_terms()`, never a private copy) ever appears in any rationale
`rules.py` produces.**

**DoD:**
```
[ ] all 6 indicators covered by at least one test each
[ ] version_mismatch alone does NOT yield conflict — named test
[ ] version_mismatch NOT fired when resolved.is_preprint is None — named test
[ ] year_delta stored as abs(); the cited-too-late direction covered by a test
[ ] doi_match None-vs-False distinction tested
[ ] thresholds via settings.thresholds(); changing config changes behaviour in a test
[ ] banned-language test green on every rationale (read via settings.banned_terms())
[ ] pure functions: identical output across runs
[ ] D-020 P5 half closed + the year_delta abs duty logged — two D-1NN entries
```

**Post immediately on merge — Arsha is waiting on this exact symbol:**
*"P5 merged. `from src.matching.rules import rule_based_status` — signature
`(ev) -> (status, confidence, rationale)`. This is your `fallback_fn` for A3."*

---

## P6 — orchestrator (4:10–4:30, ~25 min)

Branch `ritik/p6-pipeline`. `src/pipeline.py` — **a file, not a package** — plus
`scripts/run_pipeline.py`.

```python
run(pdf_path, judge_fn=None, progress=None) -> Ledger
```

1. Stage sequence with a `progress(stage_name, model_name)` callback at every stage.
   **Pass the real model name** for the two AIR stages, `None` for deterministic ones.
   Arsha's progress strip renders exactly this, and it is the beat where the AIR platform
   becomes visible in the demo. Stage names, exactly: `intake`, `extract`, `resolve`,
   `evidence`, `verdict`, `priority`, `ledger`.
2. `judge_fn` defaults to a wrapper around `rule_based_status` that builds a `Verdict`
   with `judge_model="rule_based"`. **`src/pipeline.py` must not import `src/judge`** —
   that is what lets P6 merge while A1 is still being built, and `tests/test_layout.py`
   asserts it.
3. Priority via `src.priority.compute_priority(ev, verdict, n_citing_claims)`. Do not
   reimplement the formula.
4. **Hard invariant before writing:** status counts sum to entry count, else raise
   `PipelineIntegrityError`. This is the app-level "refuses to render" guarantee and the
   dashboard mirrors it.
5. Write `data/output/<name>_ledger.json` via `contract.save_ledger`. CLI prints summary
   counts and the top-5 worklist.

**DoD:**
```
[ ] python scripts/run_pipeline.py tests/data/sample.pdf works end to end
    with NO AIR key on the rule-based path
[ ] counts-sum invariant enforced and tested
[ ] two consecutive runs -> identical summary counts
[ ] judge_fn injection covered by a test with a fake judge
[ ] progress callback fires for all 7 stages with the right model names
[ ] src/pipeline.py does not import src/judge (test_layout green)
```

**Post the moment it merges — this unblocks A3 and Roy's `--full`:**
*"P6 MERGED. `from src.pipeline import run`. `run(pdf, judge_fn=..., progress=...) ->
Ledger`. Sample ledger at `data/output/sample_ledger.json`. @arsha A3 is unblocked.
@roy `--full` is unblocked."*

---

## 4:30–5:00 — precache, support, demo prep

- `scripts/precache_demo.py`: run Roy's spiked paper end to end **twice** so every
  registry response is cached. Then verify the whole flow works with Wi-Fi off. "It runs
  offline" is a feature we say out loud on stage.
- Review Arsha's A3 PR — the one-line wiring plus upload flow. This is the only review in
  Phase 1 and it is 10 minutes.
- You drive the demo. Rehearse the drop once.

---

## Your fallback, if you are behind at CHECKPOINT 1 (2:20)

Cut in this order, and tell the other two which cut you took:

1. **P2's determinism gate** — merge the extractor without the two-identical-runs test,
   log a D-1NN, fix in Phase 2.
2. **P4 down to Crossref + OpenAlex**, drop arXiv. Keeps the DataCite path via OpenAlex.
3. **P4 down to Crossref only.** Recall drops, the demo still works.
4. **Skip P2 entirely** — pre-split entries with regex and populate `Reference` fields
   with a plain parser. You lose an AIR stage, so this is the last resort and it needs a
   decision entry. Tell Arsha immediately, because A1 becomes the only AIR call.

**Never cut:** P1, P5, P6. Without those there is no ledger and no demo.

---

## The five things that will bite you

1. **Two-column PDFs** interleave columns in pdfplumber's per-page text. If `sample.pdf`
   comes out scrambled in the references block, pick a single-column paper for the demo
   and note it. Do not spend 40 minutes on column detection today.
2. **The heading is not always alone on its line.** Your regex will miss some papers. The
   15% fallback is the safety net — make sure it actually fires and that the note appears.
3. **`doi_match=None` is not `False`.** Every place you compare, be explicit.
4. **A missing `CROSSREF_MAILTO`** silently demotes you from Crossref's polite pool. Warn,
   do not raise.
5. **`git merge main`, never rebase**, and if a conflict is in `src/judge/`, `dashboard/`
   or `eval/`, take `main`'s side without reading it.
