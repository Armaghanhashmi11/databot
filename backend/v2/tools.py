"""The four tools the LangGraph agent can call.

All tools are read-only: none of them can mutate the underlying CSV, drop
the SQL table, or execute arbitrary Python. Tools are built per-session via
build_tools() so each conversation only ever touches its own DataFrame/table.
"""
from __future__ import annotations

import json
import re

import pandas as pd
from langchain_core.tools import BaseTool, tool

from .db import UnsafeSQLError, run_select
from .session import AgentSession

# Denylist used to reject anything that looks like it's trying to escape the
# pandas expression parser (attribute/dunder access, imports, assignment,
# shelling out, etc). df.query()/df.eval() already restrict the grammar to
# expressions, not statements -- this is defense in depth on top of that.
_UNSAFE_QUERY_PATTERNS = [
    r"__", r"\bimport\b", r"\blambda\b", r"\bexec\b", r"\beval\b",
    r"\bopen\s*\(", r"\bos\.", r"\bsys\.", r"\bsubprocess\b", r"`",
    r"\bgetattr\b", r"\bglobals\b", r"\blocals\b",
]
_ASSIGNMENT_RE = re.compile(r"(?<![=!<>])=(?!=)")


class UnsafeQueryError(ValueError):
    pass


def _assert_safe_pandas_expression(query: str) -> None:
    for pattern in _UNSAFE_QUERY_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            raise UnsafeQueryError(f"Query contains a disallowed construct: {pattern!r}")
    if _ASSIGNMENT_RE.search(query):
        raise UnsafeQueryError("Assignment is not allowed in a read-only query.")


def _safe_number(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_tools(session: AgentSession, max_rows: int = 200) -> list[BaseTool]:
    """Returns the four agent tools, each bound (via closure) to `session`."""

    @tool
    def load_csv(path: str = "") -> str:
        """Load or reload a CSV file from disk into the active dataset.
        Pass an empty string to just confirm what dataset is already loaded
        (filename, SQL table name, shape, and column names)."""
        df = session.reload_csv(path) if path else session.df
        return json.dumps(
            {
                "filename": session.filename,
                "table_name": session.table_name,
                "shape": list(df.shape),
                "columns": list(df.columns),
            }
        )

    @tool
    def describe_columns() -> str:
        """Describe every column in the loaded dataset: dtype, null count,
        unique-value count, and either numeric min/max/mean or a few example
        values. Use this before writing a query to confirm exact column
        names and types."""
        df = session.df
        columns_info = []
        for col in df.columns:
            series = df[col]
            entry: dict = {
                "column": col,
                "dtype": str(series.dtype),
                "null_count": int(series.isna().sum()),
                "unique_count": int(series.nunique()),
            }
            if pd.api.types.is_numeric_dtype(series):
                entry["min"] = _safe_number(series.min())
                entry["max"] = _safe_number(series.max())
                entry["mean"] = _safe_number(series.mean())
            else:
                entry["sample_values"] = (
                    series.dropna().astype(str).unique()[:5].tolist()
                )
            columns_info.append(entry)
        return json.dumps(
            {"table_name": session.table_name, "row_count": len(df), "columns": columns_info}
        )

    @tool
    def run_pandas_query(query: str, columns: list[str] | None = None, limit: int = 50) -> str:
        """Filter the dataset with a read-only pandas DataFrame.query()
        expression and return the matching rows, e.g.
        query="age > 30 and country == 'US'". Optionally restrict the
        returned columns. Never mutates the underlying data."""
        try:
            _assert_safe_pandas_expression(query)
        except UnsafeQueryError as e:
            return json.dumps({"error": str(e)})

        df = session.df
        try:
            result = df.query(query, engine="python")
        except Exception as e:  # malformed expression from the model
            return json.dumps({"error": f"Invalid pandas query: {e}"})

        if columns:
            missing = [c for c in columns if c not in result.columns]
            if missing:
                return json.dumps({"error": f"Unknown columns: {missing}"})
            result = result[columns]

        capped = max(1, min(limit, max_rows))
        rows = result.head(capped).fillna("").astype(str).to_dict(orient="records")
        return json.dumps({"row_count": int(len(result)), "returned_rows": len(rows), "rows": rows})

    @tool
    def run_sql(sql: str, limit: int = 50) -> str:
        """Run a single read-only SQL SELECT (or WITH ... SELECT) statement
        against the dataset's SQL table and return the resulting rows. Any
        write/DDL statement (INSERT, UPDATE, DELETE, DROP, ...) or multiple
        statements will be rejected."""
        try:
            rows = run_select(sql, engine=session.engine, max_rows=max(1, min(limit, max_rows)))
        except UnsafeSQLError as e:
            return json.dumps({"error": str(e)})
        except Exception as e:  # bad SQL syntax/columns from the model
            return json.dumps({"error": f"SQL execution failed: {e}"})
        return json.dumps({"returned_rows": len(rows), "rows": rows})

    return [load_csv, describe_columns, run_pandas_query, run_sql]
