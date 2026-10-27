from __future__ import annotations

import json

import pandas as pd
import pytest

from v2.session import AgentSession
from v2.tools import UnsafeQueryError, _assert_safe_pandas_expression, build_tools


def _tool_by_name(tools, name):
    return next(t for t in tools if t.name == name)


def test_load_csv_confirms_current_dataset(agent_session: AgentSession):
    tools = build_tools(agent_session)
    load_csv = _tool_by_name(tools, "load_csv")
    result = json.loads(load_csv.invoke({"path": ""}))
    assert result["filename"] == "test.csv"
    assert result["shape"] == [5, 4]
    assert set(result["columns"]) == {"region", "quantity", "unit_price", "product"}


def test_load_csv_can_reload_a_different_file(agent_session: AgentSession, tmp_path):
    other_csv = tmp_path / "other.csv"
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(other_csv, index=False)

    tools = build_tools(agent_session)
    load_csv = _tool_by_name(tools, "load_csv")
    result = json.loads(load_csv.invoke({"path": str(other_csv)}))

    assert result["columns"] == ["a", "b"]
    assert agent_session.df.shape == (2, 2)


def test_describe_columns_reports_dtype_and_stats(agent_session: AgentSession):
    tools = build_tools(agent_session)
    describe = _tool_by_name(tools, "describe_columns")
    result = json.loads(describe.invoke({}))
    by_name = {c["column"]: c for c in result["columns"]}
    assert by_name["quantity"]["min"] == 1
    assert by_name["quantity"]["max"] == 5
    assert "sample_values" in by_name["region"]


def test_run_pandas_query_filters_rows(agent_session: AgentSession):
    tools = build_tools(agent_session)
    run_pandas_query = _tool_by_name(tools, "run_pandas_query")
    result = json.loads(run_pandas_query.invoke({"query": "quantity > 2", "limit": 50}))
    assert result["row_count"] == int((agent_session.df["quantity"] > 2).sum())
    assert all(int(row["quantity"]) > 2 for row in result["rows"])


def test_run_pandas_query_rejects_unsafe_expression(agent_session: AgentSession):
    tools = build_tools(agent_session)
    run_pandas_query = _tool_by_name(tools, "run_pandas_query")
    result = json.loads(run_pandas_query.invoke({"query": "__import__('os').system('echo hi')"}))
    assert "error" in result


def test_run_pandas_query_rejects_assignment(agent_session: AgentSession):
    tools = build_tools(agent_session)
    run_pandas_query = _tool_by_name(tools, "run_pandas_query")
    result = json.loads(run_pandas_query.invoke({"query": "quantity = 100"}))
    assert "error" in result


def test_run_pandas_query_does_not_mutate_dataframe(agent_session: AgentSession):
    original = agent_session.df.copy()
    tools = build_tools(agent_session)
    run_pandas_query = _tool_by_name(tools, "run_pandas_query")
    run_pandas_query.invoke({"query": "quantity > 1"})
    pd.testing.assert_frame_equal(agent_session.df, original)


def test_run_sql_returns_rows(agent_session: AgentSession):
    tools = build_tools(agent_session)
    run_sql = _tool_by_name(tools, "run_sql")
    result = json.loads(run_sql.invoke({"sql": f"SELECT region FROM {agent_session.table_name}"}))
    assert result["returned_rows"] == len(agent_session.df)


def test_run_sql_rejects_write_statement(agent_session: AgentSession):
    tools = build_tools(agent_session)
    run_sql = _tool_by_name(tools, "run_sql")
    result = json.loads(run_sql.invoke({"sql": f"DROP TABLE {agent_session.table_name}"}))
    assert "error" in result


@pytest.mark.parametrize(
    "expr",
    ["a.__class__", "import os", "lambda x: x", "open('f')", "os.system('x')", "`id`"],
)
def test_assert_safe_pandas_expression_rejects(expr):
    with pytest.raises(UnsafeQueryError):
        _assert_safe_pandas_expression(expr)


def test_assert_safe_pandas_expression_accepts_normal_filter():
    _assert_safe_pandas_expression("quantity > 2 and region == 'West'")
