from pathlib import Path

from forge_agent.config import load_settings
from forge_agent.core.errors import ConfigurationError
from forge_agent.models import create_provider


def test_cli_overrides_environment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FORGE_MODEL", "env-model")
    settings = load_settings(cwd=tmp_path, overrides={"model": "cli-model", "max_iterations": "7"})
    assert settings.model == "cli-model"
    assert settings.max_iterations == 7
    assert settings.cwd == tmp_path.resolve()


def test_keys_are_not_exposed_in_public_config(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-print")
    settings = load_settings(cwd=tmp_path)
    public = settings.public_dict()
    assert public["api_key_present"] is True
    assert "do-not-print" not in str(public)


def test_groq_selects_groq_defaults_and_key(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GROQ_API_KEY", "do-not-print")
    settings = load_settings(cwd=tmp_path, overrides={"provider": "groq"})
    assert settings.api_key == "do-not-print"
    assert settings.api_key_env == "GROQ_API_KEY"
    assert settings.api_base_url == "https://api.groq.com/openai/v1"
    assert settings.model == "llama-3.3-70b-versatile"
    assert "do-not-print" not in str(settings.public_dict())


def test_groq_missing_key_names_groq_environment(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = load_settings(cwd=tmp_path, overrides={"provider": "groq"})
    try:
        create_provider(settings)
    except ConfigurationError as exc:
        assert "GROQ_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing Groq credentials to fail clearly")