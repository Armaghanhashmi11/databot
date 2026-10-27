"""/v2/ask tested through FastAPI's TestClient with run_agent monkeypatched,
so no real LLM call happens here either."""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import v2.router as router_module
from session_store import dataframes
from v2.schemas import AgentAnswer


@pytest.fixture
def client(monkeypatch):
    from main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _seed_session():
    dataframes["api_test_session"] = {
        "df": pd.DataFrame({"region": ["West", "East"], "quantity": [3, 1]}),
        "filename": "api_test.csv",
    }
    router_module._agent_sessions.clear()
    yield
    dataframes.pop("api_test_session", None)
    router_module._agent_sessions.clear()


def test_ask_unknown_session_returns_404(client):
    resp = client.post("/v2/ask", json={"session_id": "does-not-exist", "question": "hi?"})
    assert resp.status_code == 404


def test_ask_returns_structured_answer(client, monkeypatch):
    fake_answer = AgentAnswer(
        answer="West wins.", used_columns=["region"], sql_or_code="SELECT 1", confidence=0.8
    )
    monkeypatch.setattr(router_module, "run_agent", lambda *a, **kw: fake_answer)

    resp = client.post(
        "/v2/ask",
        json={"session_id": "api_test_session", "question": "which region?", "provider": "ollama"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "West wins."
    assert body["provider"] == "ollama"
    assert body["used_columns"] == ["region"]
    assert "latency_ms" in body


def test_ask_unknown_provider_returns_400(client, monkeypatch):
    from v2.llm import UnknownProviderError

    def _raise(*a, **kw):
        raise UnknownProviderError("nope")

    monkeypatch.setattr(router_module, "run_agent", _raise)
    resp = client.post(
        "/v2/ask", json={"session_id": "api_test_session", "question": "x", "provider": "nope"}
    )
    assert resp.status_code == 400


def test_models_endpoint_lists_providers(client):
    resp = client.get("/v2/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "ollama" in body and "anthropic" in body
    assert "qwen2.5:7b" in body["ollama"]
