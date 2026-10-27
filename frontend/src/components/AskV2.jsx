import { useEffect, useRef, useState } from "react";

const FALLBACK_MODELS = {
  ollama: ["qwen2.5:7b", "llama3.1:8b"],
  anthropic: ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"],
};

export default function AskV2({ session }) {
  const [models, setModels] = useState(FALLBACK_MODELS);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState(FALLBACK_MODELS.ollama[0]);
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef();

  useEffect(() => {
    fetch("http://localhost:8000/v2/models")
      .then((r) => r.json())
      .then((data) => {
        setModels(data);
        if (data[provider]?.length) setModel(data[provider][0]);
      })
      .catch(() => {
        /* keep fallback list -- v2 backend may not be installed */
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [exchanges, loading]);

  const onProviderChange = (next) => {
    setProvider(next);
    const options = models[next] || FALLBACK_MODELS[next] || [];
    setModel(options[0] || "");
  };

  const ask = async () => {
    const text = question.trim();
    if (!text || loading || !session) return;
    setQuestion("");
    setError(null);
    setLoading(true);
    setExchanges((ex) => [...ex, { question: text, pending: true }]);

    try {
      const res = await fetch("http://localhost:8000/v2/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: session.session_id,
          question: text,
          provider,
          model,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setExchanges((ex) => {
        const copy = [...ex];
        copy[copy.length - 1] = { question: text, ...data };
        return copy;
      });
    } catch (e) {
      setExchanges((ex) => ex.slice(0, -1));
      setError(e.message);
    }
    setLoading(false);
  };

  const modelOptions = models[provider] || FALLBACK_MODELS[provider] || [];

  return (
    <div className="askv2-wrapper">
      <div className="askv2-toolbar">
        <div className="askv2-field">
          <label>Provider</label>
          <select value={provider} onChange={(e) => onProviderChange(e.target.value)}>
            <option value="ollama">Ollama (local)</option>
            <option value="anthropic">Anthropic Claude</option>
          </select>
        </div>
        <div className="askv2-field">
          <label>Model</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {modelOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
        <span className="askv2-badge">LangGraph agent · structured output</span>
      </div>

      <div className="askv2-list">
        {exchanges.length === 0 && (
          <div className="askv2-empty">
            Ask a question and the LangGraph agent will call tools
            (describe_columns, run_pandas_query, run_sql) against your data
            and return a structured answer.
          </div>
        )}

        {exchanges.map((ex, i) => (
          <div key={i} className="askv2-exchange">
            <div className="askv2-question">{ex.question}</div>

            {ex.pending ? (
              <div className="askv2-answer-card pending">
                <span className="spinner-warm" /> thinking…
              </div>
            ) : (
              <div className="askv2-answer-card">
                <p className="askv2-answer-text">{ex.answer}</p>

                <div className="askv2-meta-row">
                  <span className="askv2-pill">{ex.provider} / {ex.model}</span>
                  <span className="askv2-pill">{Math.round(ex.latency_ms)} ms</span>
                  {typeof ex.confidence === "number" && (
                    <span className="askv2-pill confidence">
                      confidence {(ex.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>

                {ex.used_columns?.length > 0 && (
                  <div className="askv2-columns">
                    {ex.used_columns.map((c) => (
                      <span key={c} className="askv2-column-chip">{c}</span>
                    ))}
                  </div>
                )}

                {ex.sql_or_code && <pre className="askv2-code">{ex.sql_or_code}</pre>}
              </div>
            )}
          </div>
        ))}

        {error && <div className="upload-error">{error}</div>}
        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <input
          className="chat-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask the LangGraph agent about your data…"
          disabled={loading}
        />
        <button className="send-btn" onClick={ask} disabled={loading || !question.trim()} aria-label="Send">
          {loading ? "…" : "→"}
        </button>
      </div>
    </div>
  );
}
