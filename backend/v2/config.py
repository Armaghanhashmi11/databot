"""Runtime configuration for the LangChain/LangGraph backend.

Everything here is read from environment variables (populated from .env via
python-dotenv in main.py) so the model and tracing backends can be swapped
without touching code. Values are read inside __init__, not as dataclass
field defaults, so get_settings() reflects the *current* environment on every
call -- important for tests that monkeypatch os.environ per test case.
"""
from __future__ import annotations

import os


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        # --- LLM provider switch ---------------------------------------
        # "ollama" (local, default) or "anthropic" (Claude via API key)
        self.llm_provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

        # Ollama models the UI dropdown offers; OLLAMA_MODEL picks the active one.
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

        # Anthropic (Claude) settings -- API key must come from .env, never hardcoded.
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

        # --- Data store for run_sql tool --------------------------------
        # Defaults to a local SQLite file; set DATABASE_URL to a Postgres DSN
        # (e.g. postgresql+psycopg2://user:pass@host/db) to use Postgres
        # instead -- the same tool code works against either engine via SQLAlchemy.
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./v2_data/databot.sqlite")

        # --- LangSmith tracing -- off by default, opt-in via env --------
        self.langsmith_tracing = _bool_env("LANGCHAIN_TRACING_V2", default=False)
        self.langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")
        self.langsmith_project = os.getenv("LANGCHAIN_PROJECT", "databot-v2")
        self.langsmith_endpoint = os.getenv("LANGCHAIN_ENDPOINT")

        # --- Agent behaviour ---------------------------------------------
        self.max_tool_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "8"))
        self.max_rows_returned = int(os.getenv("AGENT_MAX_ROWS", "200"))


SUPPORTED_MODELS: dict[str, list[str]] = {
    "ollama": ["qwen2.5:7b", "llama3.1:8b"],
    "anthropic": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"],
}


def get_settings() -> Settings:
    """Re-reads env vars on every call so tests can monkeypatch os.environ."""
    return Settings()


def configure_langsmith(settings: Settings | None = None) -> None:
    """Wires up the LangSmith tracing env vars understood by LangChain.

    No-ops entirely when LANGCHAIN_TRACING_V2 is unset/false, which is the
    default -- tracing must be explicitly opted into.
    """
    settings = settings or get_settings()
    if not settings.langsmith_tracing:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
