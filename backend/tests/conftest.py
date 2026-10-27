from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v2.db import reset_engine_cache  # noqa: E402
from v2.session import AgentSession  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_sql_engine(tmp_path, monkeypatch):
    """Every test gets its own throwaway SQLite file so tests never share
    tables or leak into the real v2_data/databot.sqlite."""
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine_cache()
    yield
    reset_engine_cache()


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["West", "East", "West", "South", "North"],
            "quantity": [3, 1, 2, 5, 1],
            "unit_price": [19.99, 29.99, 49.99, 19.99, 99.99],
            "product": ["Widget A", "Widget B", "Gadget X", "Widget A", "Gizmo Z"],
        }
    )


@pytest.fixture
def agent_session(sample_df) -> AgentSession:
    return AgentSession.from_dataframe(sample_df, session_id="test_session", filename="test.csv")
