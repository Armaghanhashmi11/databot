"""Agent graph tests using a scripted fake chat model -- no real Ollama or
Anthropic call is made, so these run anywhere (and in CI) without a local
LLM. The fake model issues one real tool call (executed by the genuine
ToolNode against the genuine tools/session), then returns a structured
AgentAnswer, exercising the full agent->tools->agent->finalize graph.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage

import v2.agent as agent_module
from v2.schemas import AgentAnswer
from v2.session import AgentSession


class _StructuredStub:
    def __init__(self, answer: AgentAnswer):
        self._answer = answer

    def invoke(self, messages):
        return self._answer


class FakeToolCallingModel:
    """Calls `tool_name` once with `tool_args`, then stops calling tools."""

    def __init__(self, tool_name: str, tool_args: dict, final_answer: AgentAnswer):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.final_answer = final_answer
        self.calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": self.tool_name,
                        "args": self.tool_args,
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content=self.final_answer.answer)

    def with_structured_output(self, schema):
        return _StructuredStub(self.final_answer)


def test_agent_runs_a_tool_then_finalizes(agent_session: AgentSession, monkeypatch):
    expected = AgentAnswer(
        answer="There are 5 rows.",
        used_columns=["region"],
        sql_or_code=None,
        confidence=0.95,
    )
    fake_model = FakeToolCallingModel("describe_columns", {}, expected)
    monkeypatch.setattr(agent_module, "get_chat_model", lambda **kwargs: fake_model)

    result = agent_module.run_agent(agent_session, "How many rows are there?")

    assert result == expected
    assert fake_model.calls == 2  # one tool-call turn, one final turn


def test_agent_tool_call_actually_executes_against_real_session(
    agent_session: AgentSession, monkeypatch
):
    """The fake model asks for run_pandas_query; the real tool + real
    DataFrame must answer it, proving the graph wires tool execution up to
    the genuine session, not a stub."""
    expected = AgentAnswer(answer="placeholder", confidence=0.5)
    fake_model = FakeToolCallingModel(
        "run_pandas_query", {"query": "quantity > 2"}, expected
    )

    monkeypatch.setattr(agent_module, "get_chat_model", lambda **kwargs: fake_model)
    graph = agent_module.build_agent(agent_session)

    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    state = {
        "messages": [
            SystemMessage(content=agent_session.schema_blurb()),
            HumanMessage(content="rows with quantity over 2?"),
        ],
        "iterations": 0,
        "final_answer": None,
    }
    final_state = graph.invoke(state)

    tool_messages = [m for m in final_state["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert "row_count" in tool_messages[0].content
    assert final_state["final_answer"] == expected


def test_agent_stops_after_max_iterations(agent_session: AgentSession, monkeypatch):
    """A model that always wants to call a tool must still terminate once
    max_tool_iterations is hit, instead of looping forever."""

    class AlwaysToolCallModel(FakeToolCallingModel):
        def invoke(self, messages):
            self.calls += 1
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "describe_columns", "args": {}, "id": f"call_{self.calls}", "type": "tool_call"}
                ],
            )

    expected = AgentAnswer(answer="gave up gracefully", confidence=0.1)
    fake_model = AlwaysToolCallModel("describe_columns", {}, expected)
    monkeypatch.setattr(agent_module, "get_chat_model", lambda **kwargs: fake_model)

    from v2.config import get_settings

    settings = get_settings()
    settings.max_tool_iterations = 2

    result = agent_module.run_agent(agent_session, "loop forever?", settings=settings)
    assert result == expected
