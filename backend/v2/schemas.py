"""Pydantic models for the v2 API -- request/response and the agent's
required structured final answer."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AgentAnswer(BaseModel):
    """The LangGraph agent's final, structured answer."""

    answer: str = Field(description="Direct natural-language answer to the user's question.")
    used_columns: list[str] = Field(
        default_factory=list,
        description="Dataset column names the answer actually relies on.",
    )
    sql_or_code: str | None = Field(
        default=None,
        description="The exact SQL query or pandas expression used to derive the answer, if any tool was used.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-rated confidence in the answer, from 0.0 (guess) to 1.0 (certain).",
    )


class AskRequest(BaseModel):
    session_id: str
    question: str
    provider: str | None = Field(
        default=None, description="Override the configured LLM_PROVIDER for this request."
    )
    model: str | None = Field(
        default=None, description="Override the configured model for this request."
    )


class AskResponse(AgentAnswer):
    provider: str
    model: str
    latency_ms: float
