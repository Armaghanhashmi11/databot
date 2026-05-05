import { useState, useRef } from "react";

export default function Upload({ onUpload, ollamaStatus }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef();

  const handleFile = async (file) => {
    if (!file || !file.name.endsWith(".csv")) {
      setError("Please upload a CSV file (.csv).");
      return;
    }
    setError(null);
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("http://localhost:8000/upload", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      onUpload(data);
    } catch (e) {
      if (e.message.includes("Failed to fetch") || e.message.includes("NetworkError")) {
        setError("Cannot reach the backend. Make sure the FastAPI server is running on port 8000.");
      } else {
        setError(e.message);
      }
    }
    setUploading(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div className="upload-wrapper">
      {ollamaStatus === "down" && (
        <div className="upload-notice notice-error">
          <strong>⚠ Ollama is not running.</strong> Charts and AI analysis won't work until you start
          it. Run <code>ollama serve</code> in a terminal, then{" "}
          <code>ollama pull tinyllama</code>.
        </div>
      )}
      {ollamaStatus === "warn" && (
        <div className="upload-notice notice-warn">
          <strong>⚠ Ollama is running but the model isn't pulled.</strong> Run{" "}
          <code>ollama pull tinyllama</code> to enable AI analysis.
        </div>
      )}

      <div className="upload-hero">
        <div className="hex-icon">⬡</div>
        <h1>DataBot</h1>
        <p className="upload-subtitle">
          Upload a CSV and chat with your data.
          <br />
          <span className="privacy-note">🔒 Everything runs locally — no data leaves your machine.</span>
        </p>
      </div>

      <div
        className={`drop-zone ${dragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {uploading ? (
          <div className="upload-spinner">
            <div className="spinner" />
            <span>Analysing your data…</span>
            <span className="upload-hint-small">AI is reading the dataset</span>
          </div>
        ) : (
          <>
            <span className="drop-icon">📂</span>
            <span className="drop-text">
              Drop CSV here or <u>click to browse</u>
            </span>
            <span className="drop-hint">Sales, logs, surveys, metrics — any CSV works</span>
          </>
        )}
      </div>

      {error && (
        <div className="upload-error">
          <span>⚠</span> {error}
        </div>
      )}

      <div className="example-prompts">
        <span className="example-label">After uploading, try asking:</span>
        <ul>
          <li>"What are the top 5 values in column X?"</li>
          <li>"Show me a bar chart of sales by region"</li>
          <li>"What trends do you see in this data?"</li>
          <li>"Which column has the most missing values?"</li>
        </ul>
      </div>
    </div>
  );
}
