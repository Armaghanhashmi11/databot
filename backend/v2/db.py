"""SQLAlchemy engine + table loading helpers for the run_sql tool.

Works against SQLite (default, zero-config) or Postgres (set DATABASE_URL to
a postgresql+psycopg2://... DSN) -- the rest of the codebase only ever talks
to a SQLAlchemy Engine, so swapping the backing database is a config change,
not a code change.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, inspect, text

from .config import get_settings

_engine_cache: dict[str, Engine] = {}

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_]")


def sanitize_table_name(name: str) -> str:
    """Turns an arbitrary session id / filename into a safe SQL identifier."""
    cleaned = _SAFE_NAME_RE.sub("_", name).strip("_") or "dataset"
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned.lower()[:63]


def get_engine(database_url: str | None = None) -> Engine:
    """Returns a cached Engine for the given DSN (or the configured default).

    SQLite URLs get their parent directory created on first use so the
    default `sqlite:///./v2_data/databot.sqlite` works out of the box.
    """
    url = database_url or get_settings().database_url
    if url not in _engine_cache:
        if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
            db_path = url.removeprefix("sqlite:///")
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine_cache[url] = create_engine(url, future=True)
    return _engine_cache[url]


def load_dataframe_to_sql(
    df: pd.DataFrame, table_name: str, engine: Engine | None = None
) -> str:
    """Writes (replacing) a DataFrame into a SQL table and returns the table name."""
    engine = engine or get_engine()
    safe_name = sanitize_table_name(table_name)
    df.to_sql(safe_name, engine, if_exists="replace", index=False)
    return safe_name


def table_exists(table_name: str, engine: Engine | None = None) -> bool:
    engine = engine or get_engine()
    return inspect(engine).has_table(table_name)


def reset_engine_cache() -> None:
    """Test helper: drops cached engines so a fresh one is built next call."""
    for engine in _engine_cache.values():
        engine.dispose()
    _engine_cache.clear()


# SQL safety: only a single read-only SELECT/WITH statement is allowed.
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|ATTACH|DETACH|PRAGMA|CREATE|REPLACE|"
    r"GRANT|REVOKE|VACUUM|TRUNCATE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    pass


def validate_select_only(sql: str) -> str:
    """Raises UnsafeSQLError unless `sql` is a single, read-only SELECT/WITH
    statement. This is the sole guard between model-generated SQL and the
    database -- keep it conservative."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise UnsafeSQLError("Empty SQL statement.")
    if ";" in stripped:
        raise UnsafeSQLError("Multiple SQL statements are not allowed.")
    first_word = stripped.split(None, 1)[0].upper()
    if first_word not in {"SELECT", "WITH"}:
        raise UnsafeSQLError("Only SELECT (or WITH ... SELECT) statements are allowed.")
    if _FORBIDDEN_KEYWORDS.search(stripped):
        raise UnsafeSQLError("Statement contains a forbidden (write/DDL) keyword.")
    return stripped


def run_select(
    sql: str, engine: Engine | None = None, max_rows: int = 200
) -> list[dict]:
    """Executes a validated read-only SELECT and returns at most max_rows rows."""
    engine = engine or get_engine()
    safe_sql = validate_select_only(sql)
    with engine.connect() as conn:
        result = conn.execute(text(safe_sql))
        columns = list(result.keys())
        rows = result.fetchmany(max_rows)
    return [dict(zip(columns, row)) for row in rows]
