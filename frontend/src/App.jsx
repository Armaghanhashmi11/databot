import { useState, useEffect } from "react";
import Upload from "./components/Upload";
import Chat from "./components/Chat";
import ChartPanel from "./components/ChartPanel";
import DataTable from "./components/DataTable";

export default function App() {
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chart, setChart] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");
  const [tableData, setTableData] = useState(null);
  const [ollamaStatus, setOllamaStatus] = useState(null);

  useEffect(() => {
    const checkHealth = () => {
      fetch("http://localhost:8000/health")
        .then((r) => r.json())
        .then((d) => {
          if (!d.ollama) setOllamaStatus("down");
          else if (!d.model) setOllamaStatus("warn");
          else setOllamaStatus("ok");
        })
        .catch(() => setOllamaStatus("down"));
    };
    checkHealth();
    const id = setInterval(checkHealth, 15000);
    return () => clearInterval(id);
  }, []);

  const handleUpload = async (data) => {
    setSession({ session_id: data.session_id, filename: data.filename, shape: data.shape });
    setMessages([{ role: "assistant", text: data.reply }]);
    if (data.chart) setChart(data.chart);
    setActiveTab("chat");
    try {
      const res = await fetch(`http://localhost:8000/table/${data.session_id}`);
      if (res.ok) setTableData(await res.json());
    } catch (_) {}
  };

  const handleSend = async (text) => {
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: session.session_id, message: text }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Request failed");
      }
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", text: data.reply }]);
      if (data.chart) setChart(data.chart);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${e.message}` }]);
    }
    setLoading(false);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="logo">
          <span className="logo-dot" />
          DataBot
        </span>
        <span className="tagline">Intelligent Data Analysis</span>

        <div className="topbar-right">
          {ollamaStatus === "down" && (
            <span className="status-pill status-down">
              <span className="status-dot" />
              Ollama offline — run <code>ollama serve</code>
            </span>
          )}
          {ollamaStatus === "warn" && (
            <span className="status-pill status-warn">
              <span className="status-dot" />
              Model not pulled — <code>ollama pull tinyllama</code>
            </span>
          )}
          {ollamaStatus === "ok" && (
            <span className="status-pill status-ok">
              <span className="status-dot" />
              Ollama ready
            </span>
          )}
          {session && (
            <span className="file-badge">
              {session.filename}&nbsp;&middot;&nbsp;
              {session.shape[0].toLocaleString()} &times; {session.shape[1]}
            </span>
          )}
        </div>
      </header>

      <main className="main-layout">
        <section className="left-panel">
          {!session ? (
            <Upload onUpload={handleUpload} ollamaStatus={ollamaStatus} />
          ) : (
            <div className="tab-shell">
              <div className="tab-bar">
                <button
                  className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
                  onClick={() => setActiveTab("chat")}
                >
                  Conversation
                </button>
                <button
                  className={`tab-btn ${activeTab === "table" ? "active" : ""}`}
                  onClick={() => setActiveTab("table")}
                >
                  Data Preview
                </button>
              </div>
              <div className="tab-content">
                {activeTab === "chat" ? (
                  <Chat messages={messages} onSend={handleSend} loading={loading} />
                ) : (
                  <DataTable tableData={tableData} />
                )}
              </div>
            </div>
          )}
        </section>

        <section className="right-panel">
          <ChartPanel
            chart={chart}
            session={session}
            tableData={tableData}
            messages={messages}
            onChartUpdate={setChart}
          />
        </section>
      </main>
    </div>
  );
}
