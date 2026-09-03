"""Reads config.yaml.

This is the ONLY place in the code that opens config.yaml, and the only way any
stage learns which model to call or which temperature to use. Nothing here has a
default value for a model name - if a key is missing you get a loud error instead
of a silent fallback, which is what we want when a run has to be reproducible.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

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

    The critic gets its own setting so it can be pinned lower than everything else.
    """
    settings = _resolve(config)
    key = "critic_temperature" if stage == "critic" else "temperature"
    if key not in settings:
        raise KeyError(f"'{key}' is missing from config.yaml.")
    return float(settings[key])


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


def cache_dir(config: dict[str, Any] | None = None) -> Path:
    """Absolute path to the resolver cache directory, created if it does not exist."""
    path = PROJECT_ROOT / str(resolver_settings(config)["cache_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path
