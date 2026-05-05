# DataBot — AI-Powered Data Analytics Assistant

A full-stack chatbot that lets you upload any CSV and have a natural language conversation with your data, powered by a local LLM (Ollama).

![DataBot Screenshot](./screenshot.png)

## Features

- 📂 **CSV Upload** — drag & drop any CSV file
- 🤖 **AI Analysis** — automatic dataset overview on upload (local LLM, no API key needed)
- 💬 **Natural Language Chat** — ask questions about your data in plain English
- 📊 **Live Charts** — bar and line charts rendered automatically based on AI suggestions
- 🔒 **100% Local** — data never leaves your machine (Ollama runs locally)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| Backend | FastAPI (Python) |
| AI | Ollama (TinyLlama / Mistral) |
| Charts | HTML5 Canvas (no external lib) |
| Data | Pandas |

## Quick Start

### 1. Start Ollama

```bash
ollama serve
ollama pull tinyllama   # or: ollama pull mistral
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## Usage

1. Open `http://localhost:5173`
2. Upload a CSV file (drag & drop or click)
3. The AI will describe your dataset automatically
4. Ask questions like:
   - *"Show me a chart of sales by region"*
   - *"What are the top 5 values in column X?"*
   - *"What trends do you see?"*
   - *"Which column has the most missing values?"*

## Project Structure

```
databot/
├── backend/
│   ├── main.py          # FastAPI app (upload, chat, chart endpoints)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── Upload.jsx      # CSV drag & drop
    │   │   ├── Chat.jsx        # Conversation UI
    │   │   └── ChartPanel.jsx  # Canvas-based charts
    │   └── index.css
    └── package.json
```

## Author

Armaghan Hashmi — [GitHub](https://github.com/Armaghanhashmi11) · [Portfolio](https://armaghanportfolio.vercel.app)
