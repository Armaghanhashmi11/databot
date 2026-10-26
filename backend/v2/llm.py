"""Model-agnostic chat model factory.

Single switch point: callers ask for a chat model by provider/name and get
back a LangChain BaseChatModel, regardless of whether it is backed by a local
Ollama server or the Anthropic API. Nothing above this module should import
langchain_ollama or langchain_anthropic directly.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from .config import Settings, get_settings


class UnknownProviderError(ValueError):
    pass


class MissingAPIKeyError(RuntimeError):
    pass


def _build_ollama(settings: Settings, model: str | None) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=model or settings.ollama_model,
        temperature=settings.llm_temperature,
    )


def _build_anthropic(settings: Settings, model: str | None) -> BaseChatModel:
    if not settings.anthropic_api_key:
        raise MissingAPIKeyError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file to use "
            "LLM_PROVIDER=anthropic."
        )
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=model or settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=settings.llm_temperature,
    )


_BUILDERS = {
    "ollama": _build_ollama,
    "anthropic": _build_anthropic,
}


def get_chat_model(
    provider: str | None = None,
    model: str | None = None,
    settings: Settings | None = None,
) -> BaseChatModel:
    """Returns a LangChain chat model for the requested provider.

    provider/model override the configured defaults -- this is what lets the
    frontend's model dropdown pick a model per-request without restarting
    the backend.
    """
    settings = settings or get_settings()
    provider = (provider or settings.llm_provider).strip().lower()

    builder = _BUILDERS.get(provider)
    if builder is None:
        raise UnknownProviderError(
            f"Unknown LLM_PROVIDER '{provider}'. Supported: {sorted(_BUILDERS)}"
        )
    return builder(settings, model)


@lru_cache(maxsize=16)
def get_cached_chat_model(provider: str, model: str) -> BaseChatModel:
    """Cached variant keyed by (provider, model) to avoid re-creating clients
    for every request when the agent is invoked repeatedly with the same
    configuration (e.g. in the eval script)."""
    return get_chat_model(provider=provider, model=model)
