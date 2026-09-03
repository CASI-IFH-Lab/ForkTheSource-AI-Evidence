"""config.yaml is the only source of model names, so guard its shape."""

import pytest

from src import config

LLM_STAGES = ("extractor", "judge", "repro_extractor", "repro_judge", "critic")


def test_every_llm_stage_has_a_model():
    settings = config.load_config()
    for stage in LLM_STAGES:
        assert config.model_for(stage, settings).strip()


def test_unknown_stage_fails_loudly_instead_of_guessing():
    with pytest.raises(KeyError):
        config.model_for("not-a-stage", config.load_config())


def test_critic_has_its_own_temperature():
    settings = config.load_config()
    assert config.temperature_for("critic", settings) == 0.0
    assert config.temperature_for("extractor", settings) == 0.1


def test_banned_terms_are_loaded():
    terms = config.banned_terms()
    assert "fabricated" in terms
    assert "not reproducible" in terms


def test_resolver_settings_are_loaded():
    settings = config.resolver_settings()
    assert settings["timeout_seconds"] == 10
    assert settings["cache_dir"] == "cache/"
