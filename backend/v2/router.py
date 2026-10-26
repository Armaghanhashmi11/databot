"""FastAPI router exposing the LangGraph agent as POST /v2/ask.

Reuses the CSV already uploaded through the v1 /upload endpoint (keyed by
session_id in session_store.dataframes) rather than duplicating upload
handling -- upload once, then ask either /chat (v1, Ollama-only) or
/v2/ask (v2, model-selectable) against the same session.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from session_store import dataframes

from .agent import run_agent
from .config import SUPPORTED_MODELS, get_settings
from .llm import MissingAPIKeyError, UnknownProviderError
from .schemas import AskRequest, AskResponse
from .session import AgentSession

router = APIRouter(prefix="/v2", tags=["v2"])

# Per-session AgentSession cache so repeated questions against the same
# upload reuse the same SQL mirror table instead of rewriting it every call.
_agent_sessions: dict[str, AgentSession] = {}


def _get_agent_session(session_id: str) -> AgentSession:
    entry = dataframes.get(session_id)
    if entry is None:
        raise HTTPException(404, "Session not found. Upload a CSV via /upload first.")

    cached = _agent_sessions.get(session_id)
    if cached is not None and cached.df is entry["df"]:
        return cached

    agent_session = AgentSession.from_dataframe(
        entry["df"], session_id=session_id, filename=entry["filename"]
    )
    _agent_sessions[session_id] = agent_session
    return agent_session


@router.get("/models")
def list_models() -> dict[str, list[str]]:
    """Models the UI's dropdown can offer, grouped by provider."""
    return SUPPORTED_MODELS


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    settings = get_settings()
    provider = (req.provider or settings.llm_provider).strip().lower()
    model = req.model

    agent_session = _get_agent_session(req.session_id)

    start = time.perf_counter()
    try:
        answer = run_agent(
            agent_session, req.question, provider=provider, model=model, settings=settings
        )
    except (UnknownProviderError, MissingAPIKeyError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # model/tool failure -- surface as a clean 502
        raise HTTPException(502, f"Agent error: {e}")
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    resolved_model = model or (
        settings.ollama_model if provider == "ollama" else settings.anthropic_model
    )
    return AskResponse(
        **answer.model_dump(), provider=provider, model=resolved_model, latency_ms=latency_ms
    )
