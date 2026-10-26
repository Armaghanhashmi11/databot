"""In-memory agent session: a loaded DataFrame plus its SQL mirror table.

Kept separate from the agent/tool code so both the FastAPI router and the
standalone eval script can construct one the same way.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine

from .db import get_engine, load_dataframe_to_sql


class AgentSession:
    def __init__(self, session_id: str, df: pd.DataFrame, filename: str = "dataset.csv"):
        self.session_id = session_id
        self.df = df
        self.filename = filename
        self.engine: Engine = get_engine()
        self.table_name = load_dataframe_to_sql(df, session_id, self.engine)

    @classmethod
    def from_csv(cls, path: str | Path, session_id: str | None = None) -> "AgentSession":
        path = Path(path)
        df = pd.read_csv(path)
        return cls(session_id=session_id or path.stem, df=df, filename=path.name)

    @classmethod
    def from_dataframe(
        cls, df: pd.DataFrame, session_id: str, filename: str = "dataset.csv"
    ) -> "AgentSession":
        return cls(session_id=session_id, df=df, filename=filename)

    def reload_csv(self, path: str | Path) -> pd.DataFrame:
        path = Path(path)
        self.df = pd.read_csv(path)
        self.filename = path.name
        self.table_name = load_dataframe_to_sql(self.df, self.session_id, self.engine)
        return self.df

    def schema_blurb(self) -> str:
        """Short description of the session's data used in agent prompts."""
        return (
            f"SQL table name: {self.table_name}\n"
            f"Columns: {list(self.df.columns)}\n"
            f"Shape: {self.df.shape[0]} rows x {self.df.shape[1]} columns"
        )
