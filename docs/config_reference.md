# Config reference

Everything tunable about this project lives in one of two files, and they have a strict
division of labour:

- **`config.yaml`** — settings. Tracked in git, identical for every teammate, safe to
  read in a PR. Model names, temperatures, timeouts, banned terms.
- **`.env`** — credentials. Never tracked, different for every teammate, never printed.
  Two names only: `AIR_API_KEY` and `AIR_BASE_URL`. Template in `.env.example`.

If you are about to add a tunable number to a stage, it belongs in `config.yaml`. If you
are about to add a second credential, it belongs in `.env` **and** in `.env.example` as a
name with a placeholder value.

`src/config.py` is the only module in the repo that opens `config.yaml`. Nothing else
should, ever — a second reader is a second place for the defaults to drift.

## Every key in `config.yaml`

Values below are current as of commit `4328eb7`.

| Key | Type | Current value | What reads it | What breaks if it is wrong or absent |
|-----|------|---------------|---------------|--------------------------------------|
| `models.extractor` | string | `qwen3-30b-a3b-instruct-2507` | `model_for("extractor")` | **Absent:** `KeyError` naming the stage, at the moment P2 first runs. **Wrong:** a `NotFoundError` from the gateway, or — worse — a model that answers but cannot hold the JSON schema, which shows up as every reference landing on `extraction_failed`. |
| `models.judge` | string | `qwen3-235b-a22b-thinking-2507` | `model_for("judge")` | **Absent:** `KeyError` when P4 runs. **Wrong:** if swapped for a non-reasoning model, verdicts get noticeably worse without any error being raised. This is the one to leave alone. |
| `models.repro_extractor` | string | `qwen3-30b-a3b-instruct-2507` | `model_for("repro_extractor")` | Same as `models.extractor`. Deliberately the same model — an instruct model doing structured extraction. |
| `models.repro_judge` | string | `qwen3-235b-a22b-thinking-2507` | `model_for("repro_judge")` | Same as `models.judge`. Deliberately the same reasoning model. |
| `models.critic` | string | `gemma4-31b-it` | `model_for("critic")` | **Absent:** `KeyError` when A1 runs. **Wrong in a specific way that matters:** the critic must be a *different model family* from the judge, so it does not inherit the judge's blind spots. Setting this to a Qwen model silently defeats the point of the stage while everything still passes. |
| `temperature` | float | `0.1` | `temperature_for(stage)` for every stage except the critic | **Absent:** `KeyError` from `temperature_for`. **Wrong:** raise it and extraction stops being reproducible run to run, which breaks R2's eval comparisons before it breaks anything visible. |
| `critic_temperature` | float | `0.0` | `temperature_for("critic")` only | **Absent:** `KeyError`, but only on the critic path — the other five stages keep working, so this fails late. **Wrong:** a non-zero critic gives different verdicts on identical write-ups, which makes the banned-terms check non-deterministic. |
| `resolvers.cache_dir` | string (path, relative to repo root) | `cache/` | `resolver_settings()`, `cache_dir()` | **Absent:** `KeyError` from `cache_dir()`. **Wrong:** a path outside the repo means the cache is not covered by `.gitignore`'s `cache/` line, so cached catalogue responses get committed. |
| `resolvers.timeout_seconds` | int (seconds) | `10` | `resolver_settings()` | **Absent:** `KeyError`. **Wrong:** too low and slow catalogues turn into spurious `unresolvable` statuses; too high and one dead endpoint stalls a whole document. This is the resolver's **HTTP** timeout, not an LLM timeout — see the gaps section. |
| `banned_terms` | list of strings | 11 terms: `fake`, `fabricated`, `invented`, `nonexistent`, `fraud`, `plagiarism`, `irreproducible`, `not reproducible`, `sloppy`, `AI-generated`, `AI-written` | `banned_terms()` | **Absent:** `KeyError` from `banned_terms()`. **Wrong:** this list is the project's accusation guard — it is what stops the write-up saying a paper is fraudulent when the evidence only supports `needs_check`. Shortening it is a reputational risk, not a technical one. Quote any entry containing a space or a hyphen, or YAML will surprise you. |

## The no-defaults rule, and why it is deliberate

`src/config.py` has **no fallback values anywhere.** A missing key raises. There is no
`config.get("temperature", 0.1)` in the codebase and there should never be one.

Two reasons, and the second is the one that matters:

1. **Determinism.** A default is a value that is in effect but not written down. If
   `temperature` silently defaults to `0.1` when the key is deleted, then two teammates
   with different `config.yaml` files get different results and the diff between their
   configs does not explain why. Every value that affects output has to be visible in a
   file that is tracked in git.

2. **The "models only from config" ground rule.** A default model name is a hardcoded
   model name — it just lives in `src/config.py` instead of in a stage. The CI check
   `grep -rn "openai\.rc\|sk-\|qwen\|glm\|gemma" src/` must find nothing, and that check
   is only meaningful because there is no default to hide a name in. This is also why
   `model_for()` raises a `KeyError` that names the missing stage rather than returning
   `None`: `None` would reach the gateway as a request and fail somewhere far away from
   the cause.

The trade is that a malformed `config.yaml` fails loudly and early. That is the intended
behaviour. If you want a stage to be optional, make the *caller* handle its absence —
do not make the config lie about it.

## The `src/config.py` API

All five public readers take an optional `config` argument. Pass one when you are making
several reads in a row, so the file is parsed once instead of once per call:

```python
from src import config

settings = config.load_config()          # parse once
model = config.model_for("judge", settings)
temp  = config.temperature_for("judge", settings)
```

Omit it for a one-off read and it loads the file for you.

### `load_config(path: Path | None = None) -> dict[str, Any]`

Reads `config.yaml` from the repo root — or from `path`, which exists so tests can point
at a fixture. Raises `FileNotFoundError` if the file is missing and `ValueError` if it
parses to anything other than a mapping.

```python
settings = config.load_config()
```

### `model_for(stage: str, config: dict | None = None) -> str`

The model name for one stage. `stage` is the module name: `extractor`, `judge`,
`repro_extractor`, `repro_judge`, `critic`. Raises `KeyError` naming the stage if it is
not under `models:`. Note that `intake` and `resolver` are deliberately absent — they are
plain code and make no model call, so asking for their model is a bug and raising is the
correct response.

```python
model = config.model_for("critic")       # -> "gemma4-31b-it"
```

### `temperature_for(stage: str, config: dict | None = None) -> float`

The temperature for one stage, as a float.

**The `critic_temperature` special case:** this function reads a *different key*
depending on the stage. For `stage == "critic"` it returns `critic_temperature`; for
every other stage it returns `temperature`. The critic gets its own knob because it is
the last gate before a human reads a verdict, and it is pinned at `0.0` so that gate does
not move between runs. Callers do not need to know which key is which — they pass their
own stage name and get the right number.

```python
temp = config.temperature_for("critic")     # -> 0.0  (reads critic_temperature)
temp = config.temperature_for("judge")      # -> 0.1  (reads temperature)
```

### `banned_terms(config: dict | None = None) -> list[str]`

The accusation guard, as a list of strings, every entry coerced to `str`. Raises
`KeyError` if the key is missing or is not a list — a bare string would otherwise iterate
character by character and match nothing.

```python
for term in config.banned_terms():
    if term in draft.lower():
        ...
```

### `resolver_settings(config: dict | None = None) -> dict[str, Any]`

The whole `resolvers:` block as a dict, unvalidated beyond being a mapping. Raises
`KeyError` if absent or not a mapping. Deliberately returns the raw block rather than
named accessors, so P3 can add keys under `resolvers:` without touching `src/config.py`.

```python
timeout = config.resolver_settings()["timeout_seconds"]     # -> 10
```

### `cache_dir(config: dict | None = None) -> Path`

An absolute `Path` to the resolver cache, resolved relative to the repo root, **created
if it does not exist** — this function has a side effect, which is unusual for a config
reader and worth knowing before you call it in a test.

```python
path = config.cache_dir()                # -> /…/ForkTheSource-AI-Evidence/cache
```

## Gaps — keys that exist with no reader, and readers with no key

This section is the P3/P5 pre-work list. It is also the honest answer to "is the config
finished?", which is no.

### Keys that exist but nothing in the running app reads

**Today that is all of them.** `app.py` imports only `src.pipeline.intake`, and
`intake.run` ignores its `config` argument entirely. Every key in `config.yaml` is
currently exercised only by `tests/test_config.py`. This is correct for M0 — there are no
model calls to configure — but it means the config path has never run outside a test, and
the first stage to land will be the first real exercise of it.

One narrower case worth naming: **`cache_dir()` has no caller at all**, not even a test.
`tests/test_config.py` checks `resolver_settings()["cache_dir"]` instead. So the
directory-creating side effect above is untested. P3 will be the first to call it.

### Keys a later module needs that are not there yet

| Needed by | Key that does not exist | Suggested shape | Why it cannot just be hardcoded |
|-----------|------------------------|-----------------|--------------------------------|
| **P3** (resolver cache) | cache TTL | `resolvers.cache_ttl_hours: 168` | A cached catalogue response goes stale — a paper can be retracted after we cached it as fine, which is exactly the `retracted` indicator failing silently. The TTL is a correctness knob, not a performance one. |
| **P4** (judge) | LLM request timeout | `llm.timeout_seconds: 60` | `resolvers.timeout_seconds: 10` is an HTTP timeout for catalogue lookups. A reasoning model on a long bibliography needs far more than 10s, so reusing that key would time out every judge call. These are two different numbers and need two keys. |
| **P4** (judge) | retry count | `llm.max_retries: 1` | The ground rule is "retry once, then mark `extraction_failed`". That `1` is currently written nowhere — it will end up hardcoded in whichever stage lands first, and then differ between stages. |
| **P5** (thresholds) | the status cutoffs | `thresholds: {verified: 0.9, needs_check: 0.6, conflict: 0.3}` | These decide which of the four statuses a reference gets. They are the most likely thing in the project to need tuning against R2's eval set, and tuning a number that lives in code means a code review per tweak. |
| **P5** (thresholds) | per-indicator severity | `indicators: {retracted: blocking, version_mismatch: warn, …}` | The six indicators are not equally serious — `retracted` and `doi_mismatch` are not the same finding. If severity is implicit in the code, it cannot be reviewed. Shape depends on B1, so this one waits for Arsha. |
| **A1** (critic) | *nothing missing* | — | `banned_terms` is already present and already readable. A1 is unblocked on config. |

Two smaller ones, listed for completeness:

- **No per-source resolver config.** `resolvers:` has a cache dir and a timeout but no
  list of which catalogues to query or in what order. P3 will need that, and it belongs
  under `resolvers:` so `resolver_settings()` picks it up with no change to
  `src/config.py`.
- **No schema version.** Every model reply is validated against a schema. When a schema
  changes, cached responses from the old shape are silently wrong. A
  `schema_version: 1` key would let P3's cache invalidate itself.
