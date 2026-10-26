import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import httpx

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from session_store import dataframes

app = FastAPI(title="DataBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# v2 (LangChain + LangGraph) backend is additive and optional: if its extra
# dependencies (requirements-v2.txt) aren't installed, the original v1 app
# below still runs exactly as before, just without /v2/* routes.
try:
    from v2.config import configure_langsmith
    from v2.router import router as v2_router

    configure_langsmith()
    app.include_router(v2_router)
except ImportError as e:
    logging.getLogger(__name__).warning("v2 backend not loaded (missing dependency): %s", e)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "qwen2:0.5b"


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    chart: dict | None = None


class ChartRequest(BaseModel):
    session_id: str
    x_col: str
    y_col: str
    chart_type: str = "bar"


def df_summary(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.info(buf=buf)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    sample = df.head(5).to_csv(index=False)
    desc = df.describe(include="all").to_string() if not df.empty else ""
    return (
        f"Columns: {list(df.columns)}\n"
        f"Shape: {df.shape}\n"
        f"Numeric columns: {numeric_cols}\n"
        f"Sample (first 5 rows):\n{sample}\n"
        f"Statistics:\n{desc}"
    )


def try_extract_chart(reply: str, df: pd.DataFrame) -> dict | None:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    reply_lower = reply.lower()
    chart_type = "bar"
    if "line" in reply_lower or "trend" in reply_lower or "over time" in reply_lower:
        chart_type = "line"
    elif "scatter" in reply_lower:
        chart_type = "scatter"

    label_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    label_col = label_cols[0] if label_cols else df.columns[0]
    value_col = numeric_cols[0]

    sample = df[[label_col, value_col]].dropna().head(15)
    return {
        "type": chart_type,
        "labels": sample[label_col].astype(str).tolist(),
        "values": sample[value_col].tolist(),
        "x_label": label_col,
        "y_label": value_col,
    }


async def ask_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "No response from model.")
    except httpx.ConnectError:
        return (
            "[Ollama is not running. Start it with `ollama serve` in a terminal, "
            "then pull the model with `ollama pull tinyllama`.]"
        )
    except httpx.TimeoutException:
        return "[Ollama timed out. The model may still be loading — please try again.]"
    except Exception as e:
        return f"[Ollama error: {e}]"


@app.get("/health")
async def health():
    ollama_ok = False
    ollama_model_available = False
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                models = [m["name"] for m in r.json().get("models", [])]
                ollama_model_available = any(OLLAMA_MODEL in m for m in models)
    except Exception:
        pass
    return {
        "status": "ok",
        "ollama": ollama_ok,
        "model": ollama_model_available,
        "model_name": OLLAMA_MODEL,
    }


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files supported.")
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    session_id = (
        file.filename.replace(".csv", "").replace(" ", "_") + "_" + str(len(dataframes))
    )
    dataframes[session_id] = {"df": df, "filename": file.filename}

    summary = df_summary(df)
    prompt = (
        f"You are a data analytics assistant. A user just uploaded a CSV file named '{file.filename}'.\n"
        f"Here is a summary of the data:\n{summary}\n\n"
        f"Give a friendly, concise overview: what this dataset seems to be about, "
        f"key columns, notable stats, and 2-3 interesting questions the user could explore. "
        f"Be direct and helpful. Max 150 words."
    )
    reply = await ask_ollama(prompt)
    chart = try_extract_chart("bar chart", df)

    return {
        "session_id": session_id,
        "filename": file.filename,
        "shape": df.shape,
        "reply": reply,
        "chart": chart,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if req.session_id not in dataframes:
        raise HTTPException(404, "Session not found. Please upload a CSV first.")

    df = dataframes[req.session_id]["df"]
    filename = dataframes[req.session_id]["filename"]
    summary = df_summary(df)

    prompt = (
        f"You are a data analytics assistant. The user has uploaded a CSV file '{filename}'.\n"
        f"Dataset summary:\n{summary}\n\n"
        f"User question: {req.message}\n\n"
        f"Answer helpfully and concisely. If relevant, suggest what chart type would best show this data "
        f"(bar, line, or scatter). Max 200 words."
    )
    reply = await ask_ollama(prompt)

    chart = None
    chart_keywords = ["chart", "plot", "graph", "visuali", "show", "distribution", "compare", "trend"]
    if any(k in req.message.lower() for k in chart_keywords) or any(
        k in reply.lower() for k in chart_keywords
    ):
        chart = try_extract_chart(reply, df)

    return ChatResponse(reply=reply, chart=chart)


@app.get("/table/{session_id}")
def get_table(session_id: str):
    if session_id not in dataframes:
        raise HTTPException(404, "Session not found.")
    df = dataframes[session_id]["df"]
    rows = df.head(20).fillna("").astype(str).to_dict(orient="records")
    columns = df.columns.tolist()
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    return {"columns": columns, "rows": rows, "numeric_columns": numeric_columns}


@app.post("/chart")
def get_chart(req: ChartRequest):
    if req.session_id not in dataframes:
        raise HTTPException(404, "Session not found.")
    df = dataframes[req.session_id]["df"]
    if req.x_col not in df.columns or req.y_col not in df.columns:
        raise HTTPException(400, "Column not found in dataset.")

    sample = df[[req.x_col, req.y_col]].dropna().head(20)
    return {
        "type": req.chart_type,
        "labels": sample[req.x_col].astype(str).tolist(),
        "values": pd.to_numeric(sample[req.y_col], errors="coerce").fillna(0).tolist(),
        "x_label": req.x_col,
        "y_label": req.y_col,
    }
