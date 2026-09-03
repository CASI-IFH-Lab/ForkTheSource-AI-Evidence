"""config.yaml is the only source of model names and tuning numbers, so guard its shape.

The threshold and severity values asserted here are taken from the Module Implementation
Plan (P5 step 3 and the P6 priority formula), not chosen. They are pinned deliberately: if
someone retunes them casually, the deterministic baseline moves and every metric Roy has
already reported becomes incomparable. Changing a number here should require changing this
test, which means saying so in a PR.
"""

import pytest

from src import settings

# Only two stages make LLM calls. intake, cache, resolvers and the rule classifier are
# plain code, and the critic is folded into A1's gate.py as a code check, not a model.
LLM_STAGES = ("extractor", "judge")


def test_every_llm_stage_has_a_model():
    config = settings.load_config()
    for stage in LLM_STAGES:
        assert settings.model_for(stage, config).strip()


def test_unknown_stage_fails_loudly_instead_of_guessing():
    with pytest.raises(KeyError):
        settings.model_for("not-a-stage", settings.load_config())


def test_plain_code_stages_have_no_model():
    """Asking for a model for a non-LLM stage is a bug, and raising is the right answer."""
    config = settings.load_config()
    for stage in ("intake", "resolver", "cache", "matching", "critic"):
        with pytest.raises(KeyError):
            settings.model_for(stage, config)


def test_one_temperature_for_every_stage():
    config = settings.load_config()
    assert settings.temperature_for("extractor", config) == 0.1
    assert settings.temperature_for("judge", config) == 0.1


def test_critic_keys_are_gone():
    """There is no critic model. A1's gate.py is a code check, not an LLM call.

    Asserted rather than merely absent, so that re-adding them is a deliberate act with a
    failing test attached.
    """
    config = settings.load_config()
    assert "critic" not in config["models"]
    assert "critic_temperature" not in config


def test_banned_terms_are_loaded():
    terms = settings.banned_terms()
    assert "fabricated" in terms
    assert "not reproducible" in terms
    assert len(terms) == 11


def test_resolver_settings_are_loaded():
    config = settings.resolver_settings()
    assert config["cache_dir"] == "cache/"
    assert config["timeout_seconds"] == 10
    assert config["cache_ttl_hours"] == 72
    assert config["providers"] == ["crossref", "openalex", "arxiv"]


def test_mailto_is_not_a_config_key():
    """D-007. The polite-pool address is per-person, so it lives in .env, not here.

    Asserted rather than merely absent, for the same reason as the critic keys: a
    per-person value in a tracked file is either overwritten by whoever commits last or
    shipped as the placeholder. Re-adding it should arrive with a failing test.
    """
    assert "mailto" not in settings.resolver_settings()
    assert "mailto" not in settings.load_config()


def test_crossref_mailto_raises_when_unset(monkeypatch):
    """No-defaults rule, applied to the environment.

    Returning "" would let P4 build a User-Agent with no contact address and get demoted
    out of the polite pool silently - slower and rate-limited with no error. That is the
    failure D-007 exists to make loud.
    """
    monkeypatch.setattr(settings, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("CROSSREF_MAILTO", raising=False)
    with pytest.raises(RuntimeError, match="CROSSREF_MAILTO"):
        settings.crossref_mailto()

    monkeypatch.setenv("CROSSREF_MAILTO", "   ")
    with pytest.raises(RuntimeError, match="CROSSREF_MAILTO"):
        settings.crossref_mailto()


def test_crossref_mailto_reads_the_environment(monkeypatch):
    monkeypatch.setattr(settings, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("CROSSREF_MAILTO", "  someone@asu.edu  ")
    assert settings.crossref_mailto() == "someone@asu.edu"


def test_llm_settings_are_separate_from_http_settings():
    llm = settings.llm_settings()
    assert llm["timeout_seconds"] == 60
    assert llm["max_retries"] == 1
    # The distinction is the point: a REST lookup and a reasoning model are not the
    # same wait.
    assert llm["timeout_seconds"] != settings.resolver_settings()["timeout_seconds"]


def test_thresholds_match_the_plan():
    t = settings.thresholds()
    assert t["title_strong"] == 0.92
    assert t["title_weak"] == 0.70
    assert t["author_strong"] == 0.60
    assert t["year_tolerance"] == 1


def test_priority_severity_covers_all_four_statuses():
    severity = settings.priority_severity()
    assert severity == {
        "conflict": 1.0,
        "needs_check": 0.6,
        "unresolvable": 0.5,
        "verified": 0.0,
    }


def test_cache_schema_version_is_set():
    assert settings.cache_settings()["schema_version"] == 1


def test_cache_dir_is_created_under_the_repo():
    path = settings.cache_dir()
    assert path.is_dir()
    assert path.name == "cache"
