# DataBot — AI-Powered Data Analytics Assistant

A full-stack chatbot that lets you upload any CSV and have a natural language
conversation with your data. Two backends live side by side:

- **v1** (`backend/main.py`) — the original, Ollama-only chat + canvas-chart app.
- **v2** (`backend/v2/`) — a LangChain + LangGraph agent with real tool calling
  (pandas + SQL), a model-agnostic Ollama/Anthropic switch, structured output,
  optional LangSmith tracing, and a model-comparison eval script.

v1 keeps working exactly as before; v2 is additive and reuses the same CSV
upload.

![DataBot Screenshot](./screenshot.png)

## Features

- 📂 **CSV Upload** — drag & drop any CSV file
- 🤖 **AI Analysis** — automatic dataset overview on upload
- 💬 **Natural Language Chat** — ask questions about your data in plain English (v1)
- 🧠 **LangGraph Agent (v2)** — tool-calling agent that queries your data via
  pandas and SQL instead of guessing, and returns a structured answer
- 🔀 **Model-agnostic (v2)** — switch between local Ollama models
  (`qwen2.5:7b`, `llama3.1:8b`) and Anthropic Claude with one env var or a UI
  dropdown
- 📊 **Live Charts** — bar and line charts rendered automatically based on AI suggestions
- 🔒 **Local by default** — v1 and v2-with-Ollama never send data off your machine;
  v2-with-Anthropic only sends what the agent's tool calls return, not the raw CSV

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| Backend (v1) | FastAPI (Python), direct Ollama HTTP calls |
| Backend (v2) | FastAPI + LangChain + LangGraph |
| LLMs (v2) | Ollama (`qwen2.5:7b`, `llama3.1:8b`) or Anthropic Claude, via `langchain-ollama` / `langchain-anthropic` |
| Agent data access (v2) | pandas (`DataFrame.query`) + SQLAlchemy (SQLite by default, Postgres optional) |
| Tracing (v2) | LangSmith (opt-in via env vars) |
| Charts | HTML5 Canvas (no external lib) |
| Data | Pandas |
| Tests | pytest |
| Packaging | Docker + docker-compose |

## Architecture

```mermaid
flowchart TB
    subgraph Browser["Browser — React (Vite)"]
        Upload["Upload.jsx"]
        ChatUI["Chat.jsx (v1 tab)"]
        AskV2UI["AskV2.jsx (v2 tab)<br/>provider + model dropdown"]
    end

    subgraph API["FastAPI — backend/main.py"]
        UploadEP["POST /upload<br/>GET /chat /table /chart"]
        AskEP["POST /v2/ask<br/>GET /v2/models"]
    end

    Store[("session_store.py<br/>in-memory: session_id to DataFrame")]

    subgraph V2["backend/v2"]
        Router["router.py"]
        Agent["agent.py<br/>LangGraph graph"]
        Tools["tools.py<br/>load_csv / describe_columns /<br/>run_pandas_query / run_sql"]
        LLM["llm.py<br/>get_chat_model()"]
        DB["db.py<br/>SQLAlchemy engine +<br/>SELECT-only guard"]
    end

    SQLStore[("SQLite file<br/>(or Postgres via DATABASE_URL)")]

    Ollama["Ollama (local)<br/>qwen2.5:7b / llama3.1:8b"]
    Anthropic["Anthropic API<br/>Claude Opus 5 / Sonnet 5 / Haiku 4.5"]
    LangSmith["LangSmith<br/>(opt-in tracing)"]

    Upload -->|POST /upload| UploadEP
    ChatUI -->|POST /chat| UploadEP
    AskV2UI -->|POST /v2/ask| AskEP

    UploadEP -->|writes CSV| Store
    AskEP --> Router
    Router -->|reads CSV by session_id| Store
    Router --> Agent
    Agent --> Tools
    Agent -->|bind_tools / with_structured_output| LLM
    Tools --> DB
    DB <--> SQLStore

    LLM -->|LLM_PROVIDER=ollama| Ollama
    LLM -->|LLM_PROVIDER=anthropic| Anthropic
    Agent -.->|LANGCHAIN_TRACING_V2=true| LangSmith

    UploadEP -->|direct HTTP| Ollama
```

**How a v2 question is answered:**

1. The browser uploads a CSV once via the existing `POST /upload` (v1 endpoint) — it's stored in `session_store.dataframes` keyed by `session_id`.
2. The React UI's **Agent (v2)** tab posts `{session_id, question, provider, model}` to `POST /v2/ask`.
3. `v2/router.py` looks up that session's DataFrame and wraps it in an `AgentSession`, which also mirrors it into a SQL table (SQLite by default, Postgres if `DATABASE_URL` is set).
4. `v2/agent.py` compiles a LangGraph graph: the model (bound to the 4 tools) decides whether to call `describe_columns`, `run_pandas_query`, or `run_sql`; LangGraph's `ToolNode` executes the real tool against the real data; the loop repeats until the model stops calling tools (or `AGENT_MAX_ITERATIONS` is hit).
5. A final call uses `.with_structured_output(AgentAnswer)` so the response always matches `{answer, used_columns, sql_or_code, confidence}`, regardless of which model answered.
6. If `LANGCHAIN_TRACING_V2=true`, every step of that graph is traced to LangSmith.

## Quick Start

### 1. Start Ollama (for v1, and for v2 if using Ollama)

```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt       # v1 only (Ollama chat, unchanged)
pip install -r requirements-v2.txt    # + LangChain/LangGraph agent, /v2/ask
cp .env.example .env                  # edit if you want Anthropic / Postgres / tracing

uvicorn main:app --reload --port 8000
```

v1's `requirements.txt` and v2's `requirements-v2.txt` are independent — the
app still starts (and v1 still works) with only `requirements.txt` installed;
`/v2/*` routes simply won't be mounted in that case (a warning is logged).

To use **Anthropic Claude** instead of Ollama for v2, set in `.env`:

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-5   # or claude-sonnet-5 / claude-haiku-4-5
```

(You can also leave `LLM_PROVIDER=ollama` and just pick "Anthropic Claude" per
request from the UI dropdown, or pass `"provider": "anthropic"` in the
`/v2/ask` request body — the env var is only the default.)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. Or run everything with Docker

```bash
docker compose up --build
# backend  -> http://localhost:8000
# frontend -> http://localhost:5173
```

Ollama itself is expected to run on the host (not in a container); the
backend container reaches it at `http://host.docker.internal:11434` by
default. To use Postgres instead of SQLite for the `run_sql` tool:

```bash
docker compose --profile postgres up -d
# then set DATABASE_URL=postgresql+psycopg2://databot:databot@postgres:5432/databot
# in the backend service's environment (or a .env file compose reads)
```

## Usage

1. Open `http://localhost:5173` and upload a CSV (drag & drop or click).
2. **Conversation** tab — the original v1 chat (Ollama only).
3. **Agent (v2)** tab — pick a provider/model from the dropdown and ask a
   question; the LangGraph agent calls tools against your actual data and
   returns a structured, grounded answer with the SQL/pandas it used and a
   confidence score.
4. **Data Preview** tab — inspect the uploaded table directly.

## Testing

```bash
cd backend
pip install -r requirements.txt -r requirements-v2.txt -r requirements-dev.txt
pytest
```

51 tests cover config/provider switching, the LLM factory, the SQL safety
guard, all 4 tools, the full LangGraph agent (via a scripted fake chat model,
so no live LLM is required), and the `/v2/ask` + `/v2/models` HTTP endpoints.

## Eval

`backend/eval/eval.py` runs 10 hand-verified questions (`eval/questions.json`)
against one or more models on `eval/sample_data.csv`, scores each answer
(numeric-with-tolerance or keyword match), and writes a markdown comparison
to `eval/results.md`:

```bash
cd backend
python eval/eval.py --models ollama:qwen2.5:7b ollama:llama3.1:8b
# add anthropic:claude-opus-5 once ANTHROPIC_API_KEY is set in .env
```

### Results (this run, local Ollama only — no `ANTHROPIC_API_KEY` configured in this environment)

| Model | Accuracy | Correct/Total | Avg Latency (ms) | p50 Latency (ms) | Errors |
|---|---|---|---|---|---|
| ollama/qwen2.5:7b | 90% | 9/10 | 5210 | 5172 | 0 |
| ollama/llama3.1:8b | 70% | 7/10 | 7397 | 4411 | 0 |

Full per-question detail (including the one `qwen2.5:7b` question marked
wrong only because it phrased the date as "January 5, 2025" instead of the
exact `2025-01-05` string the scorer looks for) is in
[`backend/eval/results.md`](./backend/eval/results.md). Re-run the script
after adding `ANTHROPIC_API_KEY` to compare Claude against both local models.

## Project Structure

```
databot/
├── docker-compose.yml
├── backend/
│   ├── main.py                # v1 FastAPI app (upload/chat/chart) + mounts v2 router
│   ├── session_store.py       # shared in-memory CSV store (v1 + v2)
│   ├── requirements.txt       # v1 deps
│   ├── requirements-v2.txt    # + LangChain/LangGraph/SQLAlchemy/Anthropic deps
│   ├── requirements-dev.txt   # + pytest
│   ├── Dockerfile
│   ├── .env.example
│   ├── v2/
│   │   ├── config.py          # env-driven Settings (provider, models, tracing, DB)
│   │   ├── llm.py             # get_chat_model() -- the Ollama/Anthropic switch
│   │   ├── db.py              # SQLAlchemy engine + SELECT-only guard
│   │   ├── session.py         # AgentSession: DataFrame + its SQL mirror table
│   │   ├── tools.py           # load_csv, describe_columns, run_pandas_query, run_sql
│   │   ├── schemas.py         # AgentAnswer / AskRequest / AskResponse (Pydantic)
│   │   ├── agent.py           # LangGraph graph (agent -> tools -> finalize)
│   │   └── router.py          # POST /v2/ask, GET /v2/models
│   ├── eval/
│   │   ├── sample_data.csv
│   │   ├── questions.json
│   │   ├── eval.py
│   │   └── results.md
│   └── tests/                 # pytest suite for all of the above
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── Upload.jsx      # CSV drag & drop
        │   ├── Chat.jsx        # v1 conversation UI
        │   ├── AskV2.jsx       # v2 agent UI with provider/model dropdown
        │   └── ChartPanel.jsx  # Canvas-based charts
        └── index.css
```

## Author

Armaghan Hashmi — [GitHub](https://github.com/Armaghanhashmi11) · [Portfolio](https://armaghanportfolio.vercel.app)
