"""LangGraph tool-calling agent that answers questions about a loaded CSV
and returns a structured AgentAnswer.

Graph shape:

    agent --(tool_calls present)--> tools --> agent
      \\--(no tool_calls, or max iterations hit)--> finalize --> END

`agent` is the LLM with tools bound; `tools` executes whichever tool(s) it
asked for via LangGraph's prebuilt ToolNode; `finalize` makes one last call
to the same model with `.with_structured_output(AgentAnswer)` so the result
always matches the required {answer, used_columns, sql_or_code, confidence}
shape, regardless of provider.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .config import Settings, get_settings
from .llm import get_chat_model
from .schemas import AgentAnswer
from .session import AgentSession
from .tools import build_tools

SYSTEM_PROMPT_TEMPLATE = """You are DataBot, a careful data-analysis assistant.

You are answering questions about one dataset that is already loaded:
{schema_blurb}

Rules:
- Use the describe_columns tool first if you are unsure of exact column names or types.
- Prefer run_sql for aggregations, grouping, counting, and sorting; prefer run_pandas_query
  for simple row filters. Both are read-only -- never claim to have modified the data.
- Only reference columns that actually exist in the dataset above.
- Ground every claim in a tool result; do not invent numbers.
- Once you have enough information, stop calling tools and give your final answer.
"""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    final_answer: AgentAnswer | None


def _last_ai_message_has_tool_calls(state: AgentState) -> bool:
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            return bool(getattr(msg, "tool_calls", None))
    return False


def build_agent(
    session: AgentSession,
    provider: str | None = None,
    model: str | None = None,
    settings: Settings | None = None,
):
    """Compiles a fresh LangGraph agent bound to `session`'s data and the
    requested (or default) LLM provider/model."""
    settings = settings or get_settings()
    chat_model = get_chat_model(provider=provider, model=model, settings=settings)
    tools = build_tools(session, max_rows=settings.max_rows_returned)
    model_with_tools = chat_model.bind_tools(tools)
    structured_model = chat_model.with_structured_output(AgentAnswer)
    tool_node = ToolNode(tools)
    max_iterations = settings.max_tool_iterations

    def call_model(state: AgentState) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response], "iterations": state.get("iterations", 0) + 1}

    def should_continue(state: AgentState) -> str:
        if state.get("iterations", 0) >= max_iterations:
            return "finalize"
        return "tools" if _last_ai_message_has_tool_calls(state) else "finalize"

    def finalize(state: AgentState) -> dict:
        try:
            answer = structured_model.invoke(state["messages"])
        except Exception:
            # Some local models occasionally fail structured decoding on the
            # first try; retry once with an explicit nudge instead of
            # surfacing a 500 to the caller.
            nudge = HumanMessage(
                content="Give your final answer now in the required structured format."
            )
            answer = structured_model.invoke(state["messages"] + [nudge])
        return {"messages": [AIMessage(content=answer.answer)], "final_answer": answer}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", finalize)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "finalize": "finalize"})
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_agent(
    session: AgentSession,
    question: str,
    provider: str | None = None,
    model: str | None = None,
    settings: Settings | None = None,
) -> AgentAnswer:
    """Builds and runs the agent end-to-end for one question, returning the
    structured AgentAnswer."""
    graph = build_agent(session, provider=provider, model=model, settings=settings)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema_blurb=session.schema_blurb())
    initial_state: AgentState = {
        "messages": [SystemMessage(content=system_prompt), HumanMessage(content=question)],
        "iterations": 0,
        "final_answer": None,
    }
    final_state = graph.invoke(initial_state)
    answer = final_state.get("final_answer")
    if answer is None:  # defensive -- should be unreachable given finalize always runs
        answer = AgentAnswer(answer="I could not produce an answer.", confidence=0.0)
    return answer
