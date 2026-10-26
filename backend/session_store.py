"""In-memory CSV session store shared by the v1 endpoints (main.py) and the
v2 LangGraph router, so a CSV uploaded once via /upload can be queried
through either /chat (v1) or /v2/ask (v2) using the same session_id.

Kept as a plain module-level dict (not a class) so the existing v1 code in
main.py can keep its original `dataframes[session_id] = {...}` call sites
unchanged -- this file only moves where that dict lives.
"""

dataframes: dict[str, dict] = {}
