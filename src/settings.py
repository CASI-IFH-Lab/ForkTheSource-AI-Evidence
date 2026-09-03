"""Reads config.yaml, plus the one setting that is per-person rather than per-project.

This is the ONLY place in the code that opens config.yaml, and the only way any
stage learns which model to call or which temperature to use. Nothing here has a
default value for a model name - if a key is missing you get a loud error instead
of a silent fallback, which is what we want when a run has to be reproducible.

crossref_mailto() is the exception to "config.yaml is the source": it reads the
environment, because the Crossref polite-pool address differs for each of us and a
per-person value in a tracked file is either overwritten by whoever commits last or
shipped as a placeholder. See docs/decisions.md D-007. The no-defaults rule applies
there too - unset raises, it does not return an empty string.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Read config.yaml and hand back a plain dict."""
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"{config_path} did not parse into a mapping of settings.")
    return config


def _resolve(config: dict[str, Any] | None) -> dict[str, Any]:
    """Use the config we were handed, or load it fresh if we were handed nothing."""
    return config if config is not None else load_config()


def model_for(stage: str, config: dict[str, Any] | None = None) -> str:
    """Return the model name configured for one pipeline stage."""
    models = _resolve(config).get("models") or {}
    if stage not in models:
        raise KeyError(
            f"No model configured for stage '{stage}'. Add it under 'models:' in config.yaml."
        )
    return str(models[stage])


def temperature_for(stage: str, config: dict[str, Any] | None = None) -> float:
    """Return the temperature for a stage.

    Every LLM call in the plan runs at the same temperature - 0.1, for determinism, which
    is what makes Roy's evaluation meaningful. The `stage` argument is kept so that a
    per-stage override could be added to config.yaml later without touching any caller.
    """
    settings = _resolve(config)
    if "temperature" not in settings:
        raise KeyError("'temperature' is missing from config.yaml.")
    return float(settings["temperature"])


def banned_terms(config: dict[str, Any] | None = None) -> list[str]:
    """Words the write-up must never use about a paper or its authors."""
    terms = _resolve(config).get("banned_terms")
    if not isinstance(terms, list):
        raise KeyError("'banned_terms' is missing from config.yaml, or is not a list.")
    return [str(term) for term in terms]


def resolver_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Cache directory and network timeout for the lookup stage."""
    settings = _resolve(config).get("resolvers")
    if not isinstance(settings, dict):
        raise KeyError("'resolvers' is missing from config.yaml, or is not a mapping.")
    return settings


def crossref_mailto() -> str:
    """The Crossref polite-pool contact address, from CROSSREF_MAILTO in .env.

    NOT a config.yaml key - D-007. P4 must call this before its first request and let it
    raise, because the failure it prevents is silent: without a contact address Crossref
    demotes you out of the polite pool and answers more slowly with tighter rate limits,
    and nothing errors. A placeholder that still works is worse than a missing value that
    stops the module, because it produces a plausible wrong state nobody investigates.

    Raises rather than returning "" so a caller cannot pass emptiness through to the
    User-Agent header and get the demotion anyway.
    """
    load_dotenv()
    mailto = os.getenv("CROSSREF_MAILTO")
    if not mailto or not mailto.strip():
        raise RuntimeError(
            "CROSSREF_MAILTO is not set. Copy .env.example to .env and put YOUR OWN ASU "
            "address in it.\nWithout it Crossref silently drops you out of the polite "
            "pool - slower answers and tighter rate limits, with no error. See "
            "docs/decisions.md D-007."
        )
    return mailto.strip()


def cache_dir(config: dict[str, Any] | None = None) -> Path:
    """Absolute path to the resolver cache directory, created if it does not exist."""
    path = PROJECT_ROOT / str(resolver_settings(config)["cache_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def llm_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Request timeout and retry count for every LLM call.

    Distinct from resolvers.timeout_seconds, which is the HTTP timeout for catalogue
    lookups. A reasoning model on a long bibliography needs far longer than a REST call.
    """
    settings = _resolve(config).get("llm")
    if not isinstance(settings, dict):
        raise KeyError("'llm' is missing from config.yaml, or is not a mapping.")
    return settings


def thresholds(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Signal cutoffs for P5's rule-based classifier.

    title_strong, title_weak, author_strong, year_tolerance. These are the numbers the
    deterministic baseline is built on, and the baseline is what the LLM judge has to beat
    in the metrics table - so changing them changes what "better" means.
    """
    settings = _resolve(config).get("thresholds")
    if not isinstance(settings, dict):
        raise KeyError("'thresholds' is missing from config.yaml, or is not a mapping.")
    return settings


def priority_severity(config: dict[str, Any] | None = None) -> dict[str, float]:
    """Per-STATUS severity weights for the priority formula.

    One entry per contract status. There is deliberately no per-indicator severity: the
    plan does not define one, and inventing indicator weights would invent classifier
    behaviour that nothing has agreed to.
    """
    priority = _resolve(config).get("priority")
    if not isinstance(priority, dict):
        raise KeyError("'priority' is missing from config.yaml, or is not a mapping.")
    severity = priority.get("severity")
    if not isinstance(severity, dict):
        raise KeyError("'priority.severity' is missing from config.yaml, or is not a mapping.")
    return {str(status): float(weight) for status, weight in severity.items()}


def cache_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Cache-wide settings. schema_version is bumped to invalidate stored payloads."""
    settings = _resolve(config).get("cache")
    if not isinstance(settings, dict):
        raise KeyError("'cache' is missing from config.yaml, or is not a mapping.")
    return settings
