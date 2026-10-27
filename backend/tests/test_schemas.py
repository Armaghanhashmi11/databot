from __future__ import annotations

import pytest
from pydantic import ValidationError

from v2.schemas import AgentAnswer, AskRequest, AskResponse


def test_agent_answer_defaults():
    answer = AgentAnswer(answer="42", confidence=0.9)
    assert answer.used_columns == []
    assert answer.sql_or_code is None


def test_agent_answer_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        AgentAnswer(answer="42", confidence=1.5)
    with pytest.raises(ValidationError):
        AgentAnswer(answer="42", confidence=-0.1)


def test_ask_request_requires_session_and_question():
    with pytest.raises(ValidationError):
        AskRequest()
    req = AskRequest(session_id="s1", question="hi")
    assert req.provider is None
    assert req.model is None


def test_ask_response_extends_agent_answer():
    resp = AskResponse(
        answer="42",
        confidence=0.9,
        provider="ollama",
        model="qwen2.5:7b",
        latency_ms=123.4,
    )
    assert resp.used_columns == []
    assert resp.provider == "ollama"
