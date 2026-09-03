# Config reference

Everything tunable about this project lives in one of two files, and they have a strict
division of labour:

- **`config.yaml`** — settings. Tracked in git, identical for every teammate, safe to
  read in a PR. Model names, temperature, thresholds, timeouts, banned terms.
- **`.env`** — credentials **and anything per-person**. Never tracked, different for every
  teammate, never printed. Three names: `AIR_API_KEY`, `AIR_BASE_URL` and
  `CROSSREF_MAILTO`. Template in `.env.example`.

If you are about to add a tunable number to a module, it belongs in `config.yaml`. If you
are about to add a second credential — **or any value that differs per teammate** — it
belongs in `.env` **and** in `.env.example` as a name with a placeholder value.

`src/settings.py` is the only module in the repo that opens `config.yaml`. Nothing else
should, ever — a second reader is a second place for the defaults to drift.

## Every key in `config.yaml`

Current as of commit `c83f17f`. Values sourced from the Module Implementation Plan are
marked; they are not choices and should not be retuned without a PR that says why.

| Key | Type | Current value | What reads it | What breaks if it is wrong or absent |
|-----|------|---------------|---------------|--------------------------------------|
| `models.extractor` | string | `qwen3-30b-a3b-instruct-2507` *(plan, P2)* | `model_for("extractor")` | **Absent:** `KeyError` naming the stage when P2 first runs. **Wrong:** a `NotFoundError` from the gateway, or — worse — a model that answers but cannot hold the JSON schema, which surfaces as every reference getting the `malformed` indicator. The plan gates P2's merge on two byte-identical runs, so a model that will not settle at temp 0.1 fails that gate rather than shipping. |
| `models.judge` | string | `qwen3-235b-a22b-thinking-2507` *(plan, A1)* | `model_for("judge")` | **Absent:** `KeyError` when A1 runs. **Wrong:** swap the reasoning model for an instruct model and verdict quality drops with no error raised anywhere — it shows up only as a worse row in R2's metrics table. |
| `temperature` | float | `0.1` *(plan)* | `temperature_for(stage)` | **Absent:** `KeyError`. **Wrong:** raise it and extraction stops being reproducible run to run. That breaks P2's determinism gate and R2's 3-run determinism metric before it breaks anything a human would notice. |
| `resolvers.cache_dir` | string (path, relative to repo root) | `cache/` | `resolver_settings()`, `cache_dir()` | **Absent:** `KeyError` from `cache_dir()`. **Wrong:** a path outside the repo escapes `.gitignore`'s `cache/` line, so cached catalogue responses get committed. |
| `resolvers.cache_ttl_hours` | int (hours) | `72` *(plan, P3)* | `resolver_settings()` | **Absent:** `KeyError` when P3 lands. **Wrong:** too long and a paper retracted *after* we cached it stays cached as fine — the `retracted` indicator silently failing, which is the worst failure this project has. Too short and the offline demo loses its cache. |
| `resolvers.timeout_seconds` | int (seconds) | `10` *(plan, P4)* | `resolver_settings()` | **Absent:** `KeyError`. **Wrong:** too low and slow catalogues become spurious `unresolvable` statuses; too high and one dead endpoint stalls a document. This is the **HTTP** timeout — see `llm.timeout_seconds`. |
| `resolvers.providers` | list of strings | `[crossref, openalex, arxiv]` *(plan, P4)* | `resolver_settings()` | **Absent:** `KeyError` when P4 lands. **Wrong order:** the waterfall is DOI→Crossref, else arXiv-ID→arXiv, else title→Crossref then OpenAlex. Dropping `openalex` specifically breaks the `retracted` indicator — OpenAlex is where the Retraction Watch flag comes from. |
| `llm.timeout_seconds` | int (seconds) | `60` | `llm_settings()` | **Absent:** `KeyError` on the first LLM call. **Wrong:** this exists *because* reusing `resolvers.timeout_seconds: 10` would time out every judge call — a reasoning model on a long bibliography needs far more than a REST lookup. Setting them equal reintroduces exactly that bug. |
| `llm.max_retries` | int | `1` *(plan: "retry once")* | `llm_settings()` | **Absent:** `KeyError`. **Wrong:** the rule is retry once, then degrade — `malformed` for extraction, `fallback_fn` for the judge. Raising it hides a broken prompt behind latency; setting it to 0 turns one transient blip into a degraded verdict. |
| `cache.schema_version` | int | `1` | `cache_settings()` | **Absent:** `KeyError`. **Wrong:** the point of this key is that changing a stored payload's shape means bumping it so old rows are treated as misses. Forgetting to bump it after a shape change means silently reading stale data in the new code's shape. |
| `thresholds.title_strong` | float 0-1 | `0.92` *(plan, P5)* | `thresholds()` | **Absent:** `KeyError` when P5 lands. **Wrong:** this is the cutoff for "this is the same work". Lower it and unrelated papers start matching; raise it and legitimate matches fall to `needs_check`. It sets the baseline the LLM judge is measured against, so moving it moves the goalposts. |
| `thresholds.title_weak` | float 0-1 | `0.70` *(plan, P5)* | `thresholds()` | **Absent:** `KeyError`. **Wrong:** below this, with no author overlap, the rule classifier says `conflict`. Set it too low and you manufacture accusations from parse noise — the one outcome the project is built to avoid. |
| `thresholds.author_strong` | float 0-1 | `0.60` *(plan, P5)* | `thresholds()` | **Absent:** `KeyError`. **Wrong:** author overlap is the tie-breaker that lets a strong title match reach `verified` without a DOI. Too high and everything needs a DOI; too low and same-title-different-authors passes. |
| `thresholds.year_tolerance` | int (years) | `1` *(plan, P5)* | `thresholds()` | **Absent:** `KeyError`. **Wrong:** `1` exists to absorb the preprint-vs-journal year gap. Set it to `0` and every preprint/journal pair becomes a false alarm — the plan names this the #1 false-alarm source and gives it a dedicated test in P5. |
| `priority.severity` | mapping of status → float | `conflict 1.0`, `needs_check 0.6`, `unresolvable 0.5`, `verified 0.0` *(plan, P6)* | `priority_severity()` | **Absent:** `KeyError` from `priority_severity()`. **Wrong:** this orders the human-review worklist, and the top-3 of that worklist is the demo. Get it wrong and the highest-value findings sink below routine ones. Keys must be exactly the four contract statuses. |
| `priority.usage_base` | float 0-1 | `0.4` *(plan, P6 step 2)* | `priority_weights()`; B1's `src/priority.py` reads the block | **Absent:** `KeyError` naming the key; `compute_priority()` raises rather than scoring. **Wrong:** the floor for a reference cited by zero claims. Raise it and uncited references crowd the worklist; drop it to `0` and anything with no in-text citation scores `0.0` and becomes invisible — including a retracted paper cited only in a footnote. |
| `priority.usage_step` | float 0-1 | `0.2` *(plan, P6 step 2)* | `priority_weights()`; B1's `src/priority.py` | **Absent:** `KeyError`. **Wrong:** how fast usage saturates. At `0.2` a reference reaches the `1.0` ceiling at three citing claims, which is the plan's intent. Larger and everything saturates at one claim, so citation count stops discriminating at all; smaller and a heavily-cited bad reference never outranks a footnote. |
| `priority.retracted_bonus` | float 0-1 | `0.3` *(plan, P6 step 2)* | `priority_weights()`; B1's `src/priority.py` | **Absent:** `KeyError`. **Wrong:** this is what floats a retraction to the top regardless of how lightly it is cited. Set it to `0` and a retracted paper cited once ranks below a routine `needs_check` — the single worst ordering this tool can produce, and the one a reviewer would notice first. |
| `priority.cap` | float | `1.0` *(plan, P6 step 2)* | `priority_weights()`; B1's `src/priority.py` | **Absent:** `KeyError`. **Wrong:** the upper clamp. Above `1.0` and priority stops being a `[0,1]` scale, so the dashboard's formatting and any threshold written against it are both wrong; below `1.0` and every retracted entry ties at the cap, destroying the ordering *within* the most important group. |
| `banned_terms` | list of strings | 11 terms: `fake`, `fabricated`, `invented`, `nonexistent`, `fraud`, `plagiarism`, `irreproducible`, `not reproducible`, `sloppy`, `AI-generated`, `AI-written` | `banned_terms()` | **Absent:** `KeyError`. **Wrong:** this list is the accusation guard — what stops the write-up calling a paper fraudulent when the evidence only supports `needs_check`. The plan's risk register rates accusatory wording as the risk that "kills the pitch", and this list is one of its three defence layers. Quote any entry with a space or hyphen or YAML will surprise you. |

**Dropped in this PR:** `models.critic` and `critic_temperature`. There is no critic
stage — the plan folds it into A1's `gate.py` as three code checks (one verdict per
`ref_id`, counts sum to total, banned-term scan). None of that calls a model, so those
were keys nothing could ever read. `tests/test_config.py` now asserts both are absent, so
re-adding one is deliberate and comes with a failing test.

## The no-defaults rule, and why it is deliberate

`src/settings.py` has **no fallback values anywhere.** A missing key raises. There is no
`config.get("temperature", 0.1)` in the codebase and there should never be one.

Two reasons, and the second is the one that matters:

1. **Determinism.** A default is a value that is in effect but not written down. If
   `temperature` silently defaults to `0.1` when the key is deleted, then two teammates
   with different `config.yaml` files get different results and the diff between their
   configs does not explain why. Every value that affects output has to be visible in a
   file that is tracked in git.

2. **The "models only from config" ground rule.** A default model name is a hardcoded
   model name — it just lives in `src/settings.py` instead of in a module. The CI check
   `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/` must find nothing, and that check
   is only meaningful because there is no default to hide a name in. This is also why
   `model_for()` raises a `KeyError` that names the missing stage rather than returning
   `None`: `None` would reach the gateway as a request and fail somewhere far away from
   the cause.

The trade is that a malformed `config.yaml` fails loudly and early. That is the intended
behaviour. If you want a stage to be optional, make the *caller* handle its absence —
do not make the config lie about it.

## The `src/settings.py` API

All readers take an optional `config` argument. Pass one when making several reads in a
row, so the file is parsed once instead of once per call:

```python
from src import settings

config = settings.load_config()                  # parse once
model  = settings.model_for("judge", config)
temp   = settings.temperature_for("judge", config)
```

Omit it for a one-off read and it loads the file for you.

### `load_config(path: Path | None = None) -> dict[str, Any]`

Reads `config.yaml` from the repo root — or from `path`, so tests can point at a fixture.
Raises `FileNotFoundError` if missing, `ValueError` if it parses to anything but a mapping.

```python
config = settings.load_config()
```

### `model_for(stage: str, config: dict | None = None) -> str`

The model name for one stage. Only two stages have one: `extractor` and `judge`. Raises
`KeyError` naming the stage otherwise — and that includes `intake`, `resolver` and
`critic`, which are plain code, so asking for their model is a bug and raising is correct.

```python
model = settings.model_for("judge")     # -> "qwen3-235b-a22b-thinking-2507"
```

### `temperature_for(stage: str, config: dict | None = None) -> float`

The temperature for a stage, as a float. Every LLM call in the plan runs at the same
`0.1` — determinism is what makes R2's evaluation meaningful. The `stage` argument is kept
so a per-stage override could be added to `config.yaml` later without touching any caller.

```python
temp = settings.temperature_for("extractor")    # -> 0.1
```

### `banned_terms(config: dict | None = None) -> list[str]`

The accusation guard, as a list of strings, every entry coerced to `str`. Raises `KeyError`
if the key is missing or is not a list — a bare string would iterate character by
character and match nothing.

```python
for term in settings.banned_terms():
    if term in rationale.lower():
        ...
```

### `resolver_settings(config: dict | None = None) -> dict[str, Any]`

The whole `resolvers:` block, unvalidated beyond being a mapping. Deliberately returns the
raw block rather than named accessors, so P3 and P4 can add keys under `resolvers:` without
touching `src/settings.py`.

```python
timeout = settings.resolver_settings()["timeout_seconds"]      # -> 10
```

### `crossref_mailto() -> str`

**The one reader that does not read `config.yaml`.** It reads `CROSSREF_MAILTO` from the
environment, and it takes no `config` argument because there is no config key to pass.
Unset, or set to whitespace, **raises `RuntimeError`** naming the variable and pointing at
`.env.example` — the same pattern as `src/llm.py`'s two credential checks.

```python
mailto = settings.crossref_mailto()      # -> your own address, or RuntimeError
```

**P4 must call this before its first request and let it raise.** See D-007 and the section
below.

### `cache_dir(config: dict | None = None) -> Path`

An absolute `Path` to the resolver cache, relative to the repo root, **created if it does
not exist** — a side effect, unusual for a config reader and worth knowing before calling
it in a test. P3's SQLite file lives inside it.

```python
path = settings.cache_dir()          # -> /…/ForkTheSource-AI-Evidence/cache
```

### `llm_settings(config: dict | None = None) -> dict[str, Any]`

Timeout and retry count for every LLM call. Separate from `resolver_settings()` on purpose:
a REST lookup and a reasoning model are not the same wait.

```python
timeout = settings.llm_settings()["timeout_seconds"]           # -> 60
```

### `thresholds(config: dict | None = None) -> dict[str, Any]`

The four signal cutoffs P5's rule classifier is built on. These define the deterministic
baseline, and the baseline is what the LLM judge has to beat in the metrics table — so
changing them changes what "better" means.

```python
if evidence.title_similarity >= settings.thresholds()["title_strong"]:
    ...
```

### `priority_severity(config: dict | None = None) -> dict[str, float]`

Per-**status** severity weights for the priority formula, keyed by the four contract
statuses. There is deliberately no per-indicator severity — the plan does not define one,
and inventing indicator weights would invent classifier behaviour nobody agreed to.

```python
weight = settings.priority_severity()[verdict.status]          # conflict -> 1.0
```

### `priority_weights(config: dict | None = None) -> dict[str, Any]`

The whole validated `priority:` block: the four scalars as floats, plus `severity` under
its own key. **Companion to `priority_severity()`, not a replacement** — `severity` is
delegated to that function so the map has one definition of its validation, and existing
callers are unaffected.

```python
w = settings.priority_weights()
# {'usage_base': 0.4, 'usage_step': 0.2, 'retracted_bonus': 0.3, 'cap': 1.0,
#  'severity': {'conflict': 1.0, 'needs_check': 0.6, 'unresolvable': 0.5, 'verified': 0.0}}
```

`PRIORITY_SCALARS` is exported alongside it as the tuple of the four scalar key names, so
a caller can report what is missing without restating the list.

A missing key raises `KeyError` naming **every** missing key at once, not just the first —
someone fixing `config.yaml` wants the whole list. Raising matters more here than anywhere
else in this module: a missing model name fails visibly on the next API call, whereas a
wrong priority weight produces a plausible score that silently reorders the reviewer
worklist. See **D-009** and **D-032**.

**B1's `src/priority.py` does not call this**, and does not need to. It reads
`config["priority"]` directly after `settings.load_config()`, taking `severity` through
`priority_severity(config)`. That call path is pinned by
`tests/test_config.py::test_b1s_priority_call_path_sees_all_five_keys`, so a refactor that
moved the scalars behind an accessor would fail here rather than in someone else's module.

### `cache_settings(config: dict | None = None) -> dict[str, Any]`

Cache-wide settings. `schema_version` is bumped to invalidate stored payloads after a
shape change.

```python
version = settings.cache_settings()["schema_version"]          # -> 1
```

## Gaps

### Closed in this PR

Every gap the first B0 docs pass identified is now closed, and the values came from the
plan rather than from guesswork:

| Was missing | Now | Source |
|-------------|-----|--------|
| P3 cache TTL | `resolvers.cache_ttl_hours: 72` | P3 card |
| P4 LLM timeout | `llm.timeout_seconds: 60` | separated from the HTTP timeout |
| P4 retry count | `llm.max_retries: 1` | "retry once" in P2/A1 |
| P4 provider list | `resolvers.providers` | P4 waterfall order |
| P4 Crossref polite pool | **`CROSSREF_MAILTO` in `.env`** — *not* a `config.yaml` key. See D-007 and *Why the polite-pool address is a credential* below. | P4 step 1 |
| P5 thresholds | `thresholds.*` — four keys | P5 step 3, verbatim |
| Cache invalidation | `cache.schema_version: 1` | — |
| Priority weights | `priority.severity` — four statuses | P6 formula |
| P6 priority formula constants | `priority.usage_base`, `usage_step`, `retracted_bonus`, `cap` | P6 step 2 — **all four plan-sourced**, closing D-009 |

The first pass proposed `thresholds: {verified: 0.9, needs_check: 0.6, conflict: 0.3}` — a
confidence cutoff per status. **That shape was wrong and was discarded.** P5's classifier
is a rule mapping over *signal* thresholds (title similarity, author overlap, year delta,
DOI match), not a confidence band per status. Shipping the proposed shape would have
quietly built a different classifier than the one R2 measures.

### Why the polite-pool address is a credential, not a setting — D-007

`resolvers.mailto` was a `config.yaml` key with the placeholder `your-asurite@asu.edu`. It
is now `CROSSREF_MAILTO` in `.env`, for two reasons that are worth separating.

**It is per-person, so a tracked file is the wrong home.** It is the only value in
`config.yaml` that differs for each of the three of us, and a tracked per-person value has
exactly two outcomes: everyone commits their own address over each other's, or the
placeholder ships. `.env` is already the mechanism for per-person values and is already
gitignored.

**And a real mailbox in a tracked file is the same category of mistake as a pasted key.**
Not the same severity — nobody can spend your inbox — but the same *shape*: a real personal
identifier, committed to a repo under an org name that looks public, discoverable by anyone
who clones it and permanent in the history once pushed. The B0 pass already had one
near-miss of exactly this shape with the first 16 characters of a live key (see
`docs/worklog.md`), and the lesson generalised: the control has to be mechanical. Putting
the address behind `.env` means `.gitignore` enforces the rule instead of a comment asking
each teammate to remember it.

**The failure it prevents is silent, which is why the reader raises.** Without a contact
address, Crossref does not error — it drops you out of the polite pool and answers more
slowly with tighter rate limits. P4 then looks like it has a performance problem rather
than a configuration problem. A placeholder that still works is worse than a missing value
that stops the module, because it produces a plausible wrong state nobody investigates.
Hence `crossref_mailto()` raises rather than returning `""`, and hence P4 calls it before
its first request.

### Still genuinely open

1. **Nothing outside tests reads any of these keys yet.** `app.py` imports only
   `src.ingest.pdf_parser`, whose `run()` ignores its `config` argument. Every key here is
   exercised only by `tests/test_config.py`. Correct for B0 — no LLM calls exist — but the
   config path has never run in anger, and P1 will be its first real user.
2. **`cache_dir()` still has no caller** that uses its return value. P3 will be the first.
3. **~~Three constants in the priority formula are not in config.~~ CLOSED.** All five
   priority numbers are now named keys: `priority.severity` plus `usage_base`,
   `usage_step`, `retracted_bonus` and `cap`, every one taken from the plan's P6 step 2
   rather than chosen. B1 named them (**D-032**) and this file's owner added them,
   resolving **D-009** and `docs/pr/B0.md` flag 3. `src/priority.py` has no hardcoded
   fallback for any of them and raises instead — the reasoning is in D-032 part 3, and it
   is the right call: priority is the one ledger value nobody can eyeball, so a plausible
   wrong score is worse than a traceback.
4. **Cache settings are split across two blocks.** `resolvers.cache_dir` and
   `resolvers.cache_ttl_hours` sit under `resolvers:`, while `cache.schema_version` is
   top-level. P3 owns the cache and may want them together; left as specified rather than
   moved unilaterally.
5. **No per-provider settings.** `resolvers.providers` is an order, not a config. If
   Crossref and OpenAlex need different timeouts or base URLs, that goes under
   `resolvers:` so `resolver_settings()` picks it up with no loader change.
6. **Dependencies the plan needs are not in `requirements.txt` yet**: `pydantic` (B1, and
   currently present only transitively via `openai`), `rapidfuzz` (P5 signals, with a
   `difflib` fallback), `pandas` (A2's CSV export). Each lands with its own module rather
   than being pre-installed here.
