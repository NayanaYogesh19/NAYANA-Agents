import importlib

import config


def test_settings_prefers_openrouter_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    reloaded = importlib.reload(config)

    assert reloaded.settings.LLM_PROVIDER == "openrouter"
    assert reloaded.settings.OPENROUTER_API_KEY == "or-key"
    assert reloaded.settings.OPENROUTER_MODEL == "openai/gpt-4o-mini"
