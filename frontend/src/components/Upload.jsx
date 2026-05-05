import { useState, useRef } from "react";

const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 15V3m0 0-4 4m4-4 4 4" />
    <path d="M2 17l.6 2.4A2 2 0 0 0 4.5 21h15a2 2 0 0 0 1.9-1.6L22 17" />
  </svg>
);

export default function Upload({ onUpload, ollamaStatus }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef();

  const handleFile = async (file) => {
    if (!file || !file.name.endsWith(".csv")) {
      setError("Please select a CSV file (.csv extension required).");
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
        setError("Cannot reach the backend. Ensure FastAPI is running on port 8000.");
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
      {/* Editorial hero band */}
      <div className="upload-hero-band">
        <p className="upload-eyebrow">Data Intelligence</p>
        <h1 className="upload-headline">
          Ask questions of<br />
          your <em>data</em>.
        </h1>
        <p className="upload-subhead">
          Upload any CSV file and have a natural conversation
          with your dataset — powered by a local language model.
          No cloud, no subscriptions.
        </p>
      </div>

      {/* Body — notices + drop zone */}
      <div className="upload-body">
        {ollamaStatus === "down" && (
          <div className="upload-notice notice-error">
            <strong>Ollama is not running.</strong> AI analysis won't work until you start it.
            Run <code>ollama serve</code> in a terminal,
            then <code>ollama pull tinyllama</code>.
          </div>
        )}
        {ollamaStatus === "warn" && (
          <div className="upload-notice notice-warn">
            <strong>Ollama is running</strong> but the model isn't pulled yet.
            Run <code>ollama pull tinyllama</code> to enable AI analysis.
          </div>
        )}

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
            <div className="upload-progress">
              <div className="spinner-warm" />
              <span className="upload-progress-label">Analysing your data…</span>
              <span className="upload-progress-sub">AI is reading the dataset</span>
            </div>
          ) : (
            <>
              <div className="drop-zone-icon">
                <UploadIcon />
              </div>
              <span className="drop-title">
                Drop a CSV file here, or <u>browse</u>
              </span>
              <span className="drop-sub">
                Sales data, survey results, logs, metrics — any CSV works
              </span>
            </>
          )}
        </div>

        {error && <div className="upload-error">{error}</div>}

        <div className="example-prompts">
          <span className="example-label">After uploading, try asking</span>
          <ul className="example-list">
            <li>What are the top 5 values in column X?</li>
            <li>Show me a bar chart of sales by region</li>
            <li>What trends do you see in this data?</li>
            <li>Which column has the most missing values?</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
