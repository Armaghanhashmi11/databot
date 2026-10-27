from __future__ import annotations

from v2.config import configure_langsmith, get_settings


def test_default_provider_is_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    settings = get_settings()
    assert settings.llm_provider == "ollama"


def test_provider_switch_via_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    settings = get_settings()
    assert settings.llm_provider == "anthropic"


def test_tracing_off_by_default(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    settings = get_settings()
    assert settings.langsmith_tracing is False


def test_tracing_opt_in(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "fake-key")
    settings = get_settings()
    assert settings.langsmith_tracing is True

    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    configure_langsmith(settings)
    import os

    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGCHAIN_API_KEY") == "fake-key"


def test_configure_langsmith_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    import os

    os.environ.pop("LANGCHAIN_TRACING_V2", None)
    configure_langsmith(get_settings())
    assert "LANGCHAIN_TRACING_V2" not in os.environ
