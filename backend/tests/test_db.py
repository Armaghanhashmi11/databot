from __future__ import annotations

import pandas as pd
import pytest

from v2.db import (
    UnsafeSQLError,
    get_engine,
    load_dataframe_to_sql,
    run_select,
    sanitize_table_name,
    validate_select_only,
)


def test_sanitize_table_name_strips_unsafe_chars():
    assert sanitize_table_name("my file-01.csv") == "my_file_01_csv"


def test_sanitize_table_name_leading_digit_gets_prefixed():
    assert sanitize_table_name("123abc").startswith("t_")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM t; DROP TABLE t;",
        "DROP TABLE t",
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET x = 1",
        "DELETE FROM t",
        "ATTACH DATABASE 'x' AS y",
        "",
    ],
)
def test_validate_select_only_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        validate_select_only(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM t",
        "select region, count(*) from t group by region",
        "WITH x AS (SELECT * FROM t) SELECT * FROM x",
    ],
)
def test_validate_select_only_accepts_safe(sql):
    assert validate_select_only(sql)


def test_load_and_query_roundtrip(sample_df: pd.DataFrame):
    engine = get_engine()
    table = load_dataframe_to_sql(sample_df, "roundtrip_test", engine)
    rows = run_select(f"SELECT region, quantity FROM {table} WHERE quantity > 2", engine)
    assert all(r["quantity"] > 2 for r in rows)
    assert len(rows) == sum(sample_df["quantity"] > 2)


def test_run_select_rejects_write_statement(sample_df: pd.DataFrame):
    engine = get_engine()
    table = load_dataframe_to_sql(sample_df, "write_guard_test", engine)
    with pytest.raises(UnsafeSQLError):
        run_select(f"DELETE FROM {table}", engine)


def test_run_select_respects_max_rows(sample_df: pd.DataFrame):
    engine = get_engine()
    table = load_dataframe_to_sql(sample_df, "limit_test", engine)
    rows = run_select(f"SELECT * FROM {table}", engine, max_rows=2)
    assert len(rows) == 2
