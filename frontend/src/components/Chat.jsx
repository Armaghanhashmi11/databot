import { useState, useRef, useEffect } from "react";

export default function Chat({ messages, onSend, loading }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    onSend(text);
  };

  const suggestions = [
    "Show me a chart of the data",
    "What are the key insights?",
    "Which column has highest values?",
    "Describe the distribution",
  ];

  return (
    <div className="chat-wrapper">
      <div className="messages-list">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="msg-avatar">{m.role === "assistant" ? "⬡" : "▸"}</div>
            <div className="msg-bubble">{m.text}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="msg-avatar">⬡</div>
            <div className="msg-bubble typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="suggestions">
        {suggestions.map((s) => (
          <button key={s} className="suggestion-chip" onClick={() => onSend(s)}>
            {s}
          </button>
        ))}
      </div>

      <div className="input-row">
        <input
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask anything about your data…"
          disabled={loading}
        />
        <button className="send-btn" onClick={send} disabled={loading || !input.trim()}>
          {loading ? "…" : "→"}
        </button>
      </div>
    </div>
  );
}
