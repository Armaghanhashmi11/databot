from __future__ import annotations

import pytest

from v2.llm import MissingAPIKeyError, UnknownProviderError, get_chat_model


def test_get_chat_model_ollama_default():
    model = get_chat_model(provider="ollama", model="qwen2.5:7b")
    assert type(model).__name__ == "ChatOllama"


def test_get_chat_model_unknown_provider_raises():
    with pytest.raises(UnknownProviderError):
        get_chat_model(provider="made-up-provider")


def test_get_chat_model_anthropic_without_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        get_chat_model(provider="anthropic")


def test_get_chat_model_anthropic_with_key_builds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    model = get_chat_model(provider="anthropic", model="claude-opus-5")
    assert type(model).__name__ == "ChatAnthropic"
