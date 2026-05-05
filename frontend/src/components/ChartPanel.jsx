import { useEffect, useRef, useState } from "react";

function drawChart(canvas, chart) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const { labels, values, x_label, y_label, type } = chart;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.offsetWidth * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  ctx.scale(dpr, dpr);
  const w = canvas.offsetWidth;
  const h = canvas.offsetHeight;

  ctx.clearRect(0, 0, w, h);

  const PAD = { top: 36, right: 24, bottom: 72, left: 64 };
  const chartW = w - PAD.left - PAD.right;
  const chartH = h - PAD.top - PAD.bottom;

  const maxVal = Math.max(...values) * 1.1 || 1;
  const minVal = Math.min(0, ...values);
  const range = maxVal - minVal || 1;

  // Background
  ctx.fillStyle = "#080d14";
  ctx.fillRect(0, 0, w, h);

  // Grid
  const gridCount = 5;
  for (let i = 0; i <= gridCount; i++) {
    const y = PAD.top + (chartH / gridCount) * i;
    ctx.strokeStyle = "#1a2d44";
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + chartW, y);
    ctx.stroke();
    ctx.setLineDash([]);

    const val = maxVal - range * (i / gridCount);
    ctx.fillStyle = "#4a6a88";
    ctx.font = `10px monospace`;
    ctx.textAlign = "right";
    ctx.fillText(
      Math.abs(val) >= 1000 ? (val / 1000).toFixed(1) + "k" : val.toFixed(1),
      PAD.left - 8,
      y + 4
    );
  }

  // Axes
  ctx.strokeStyle = "#2e4a6a";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(PAD.left, PAD.top);
  ctx.lineTo(PAD.left, PAD.top + chartH);
  ctx.lineTo(PAD.left + chartW, PAD.top + chartH);
  ctx.stroke();

  const n = labels.length;
  const step = chartW / Math.max(n, 1);

  const toY = (v) => PAD.top + chartH - ((v - minVal) / range) * chartH;

  if (type === "line") {
    // Filled area
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      i === 0 ? ctx.moveTo(x, toY(v)) : ctx.lineTo(x, toY(v));
    });
    ctx.lineTo(PAD.left + step * (n - 1) + step / 2, PAD.top + chartH);
    ctx.lineTo(PAD.left + step / 2, PAD.top + chartH);
    ctx.closePath();
    const areaGrad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + chartH);
    areaGrad.addColorStop(0, "#00d4ff22");
    areaGrad.addColorStop(1, "#00d4ff04");
    ctx.fillStyle = areaGrad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.strokeStyle = "#00d4ff";
    ctx.lineWidth = 2.5;
    ctx.shadowColor = "#00d4ff";
    ctx.shadowBlur = 10;
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      i === 0 ? ctx.moveTo(x, toY(v)) : ctx.lineTo(x, toY(v));
    });
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Dots
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      const y = toY(v);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#00d4ff";
      ctx.shadowColor = "#00d4ff";
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    });
  } else if (type === "scatter") {
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      const y = toY(v);
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = "#00d4ff";
      ctx.strokeStyle = "#00a8cc";
      ctx.lineWidth = 1.5;
      ctx.shadowColor = "#00d4ff";
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;
    });
  } else {
    // Bar chart
    const barWidth = step * 0.6;
    values.forEach((v, i) => {
      const x = PAD.left + step * i + (step - barWidth) / 2;
      const barH = Math.max(((v - minVal) / range) * chartH, 1);
      const y = toY(v);

      const grad = ctx.createLinearGradient(x, y, x, y + barH);
      grad.addColorStop(0, "#00d4ff");
      grad.addColorStop(1, "#003355");
      ctx.fillStyle = grad;
      ctx.shadowColor = "#00d4ff33";
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.roundRect?.(x, y, barWidth, barH, [3, 3, 0, 0]) ||
        ctx.rect(x, y, barWidth, barH);
      ctx.fill();
      ctx.shadowBlur = 0;
    });
  }

  // X labels
  ctx.fillStyle = "#5577aa";
  ctx.font = "10px monospace";
  ctx.textAlign = "center";
  labels.forEach((label, i) => {
    const x = PAD.left + step * i + step / 2;
    const s = String(label);
    const truncated = s.length > 12 ? s.slice(0, 11) + "…" : s;
    ctx.save();
    ctx.translate(x, PAD.top + chartH + 10);
    ctx.rotate(-Math.PI / 5);
    ctx.fillText(truncated, 0, 0);
    ctx.restore();
  });

  // Axis labels
  ctx.fillStyle = "#3a5a7a";
  ctx.font = "bold 11px monospace";
  ctx.textAlign = "center";
  ctx.fillText(x_label, PAD.left + chartW / 2, h - 6);

  ctx.save();
  ctx.translate(13, PAD.top + chartH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(y_label, 0, 0);
  ctx.restore();
}

export default function ChartPanel({ chart, session, tableData, messages, onChartUpdate }) {
  const canvasRef = useRef();
  const [xCol, setXCol] = useState("");
  const [yCol, setYCol] = useState("");
  const [chartType, setChartType] = useState("bar");
  const [fetching, setFetching] = useState(false);

  const columns = tableData?.columns || [];
  const numericColumns = tableData?.numeric_columns || [];

  // Sync selectors when chart or tableData arrive
  useEffect(() => {
    if (chart?.x_label) setXCol(chart.x_label);
    if (chart?.y_label) setYCol(chart.y_label);
    if (chart?.type) setChartType(chart.type);
  }, [chart?.x_label, chart?.y_label, chart?.type]);

  useEffect(() => {
    if (tableData && !xCol) {
      const nonNumeric = columns.filter((c) => !numericColumns.includes(c));
      setXCol(nonNumeric[0] || columns[0] || "");
      setYCol(numericColumns[0] || "");
    }
  }, [tableData]);

  // Redraw canvas whenever chart changes
  useEffect(() => {
    if (chart && canvasRef.current) drawChart(canvasRef.current, chart);
  }, [chart]);

  const fetchChart = async (x, y, type) => {
    if (!session || !x || !y) return;
    setFetching(true);
    try {
      const res = await fetch("http://localhost:8000/chart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: session.session_id,
          x_col: x,
          y_col: y,
          chart_type: type,
        }),
      });
      if (res.ok) onChartUpdate(await res.json());
    } catch (_) {}
    setFetching(false);
  };

  const handleX = (e) => { const v = e.target.value; setXCol(v); fetchChart(v, yCol, chartType); };
  const handleY = (e) => { const v = e.target.value; setYCol(v); fetchChart(xCol, v, chartType); };
  const handleType = (t) => { setChartType(t); fetchChart(xCol, yCol, t); };

  const downloadPDF = () => {
    const canvas = canvasRef.current;
    const img = canvas ? canvas.toDataURL("image/png") : null;

    const insights = messages
      .filter((m) => m.role === "assistant")
      .slice(-4)
      .map((m) => `<div class="block">${m.text.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>")}</div>`)
      .join("");

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>DataBot Report</title>
<style>
  body{font-family:Arial,sans-serif;padding:40px;color:#111;max-width:860px;margin:0 auto}
  h1{color:#0077aa;font-size:22px;margin-bottom:4px}
  .meta{color:#777;font-size:12px;margin-bottom:28px;border-bottom:1px solid #ddd;padding-bottom:12px}
  img{width:100%;border:1px solid #ddd;border-radius:8px;margin-bottom:28px}
  h2{color:#0077aa;font-size:16px;margin-bottom:14px}
  .block{background:#f4f8fc;border-left:3px solid #0099cc;padding:12px 16px;margin-bottom:10px;border-radius:4px;font-size:13px;line-height:1.7}
  @media print{body{padding:20px}}
</style>
</head>
<body>
<h1>⬡ DataBot Insights Report</h1>
<div class="meta">
  Generated: ${new Date().toLocaleString()}
  ${session ? ` &nbsp;|&nbsp; File: <strong>${session.filename}</strong> &nbsp;|&nbsp; ${session.shape[0].toLocaleString()} rows × ${session.shape[1]} cols` : ""}
  ${chart ? ` &nbsp;|&nbsp; Chart: ${chart.type} — ${chart.x_label} vs ${chart.y_label}` : ""}
</div>
${img ? `<img src="${img}" alt="Chart" />` : "<p><em>No chart available.</em></p>"}
<h2>AI Insights</h2>
${insights || "<p><em>No insights yet.</em></p>"}
</body>
</html>`;

    const win = window.open("", "_blank");
    if (!win) { alert("Allow popups to download the PDF report."); return; }
    win.document.write(html);
    win.document.close();
    win.addEventListener("load", () => setTimeout(() => win.print(), 300));
  };

  return (
    <div className="chart-panel">
      <div className="chart-header">
        <span className="chart-title">📈 Visualization</span>
        <div className="chart-type-group">
          {["bar", "line", "scatter"].map((t) => (
            <button
              key={t}
              className={`chart-type-btn ${chartType === t ? "active" : ""}`}
              onClick={() => handleType(t)}
              disabled={!session || fetching}
            >
              {t === "bar" ? "▊" : t === "line" ? "╱" : "◦"} {t}
            </button>
          ))}
        </div>
        {chart && (
          <button className="pdf-btn" onClick={downloadPDF} title="Download insights as PDF">
            ⬇ PDF
          </button>
        )}
      </div>

      {tableData && (
        <div className="col-selector-bar">
          <div className="col-selector-group">
            <label className="col-label">X Axis</label>
            <select className="col-select" value={xCol} onChange={handleX}>
              {columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="col-selector-divider">vs</div>
          <div className="col-selector-group">
            <label className="col-label">Y Axis</label>
            <select className="col-select" value={yCol} onChange={handleY}>
              {numericColumns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          {fetching && <div className="col-fetching">↻</div>}
        </div>
      )}

      <div className="chart-body">
        {chart ? (
          <canvas ref={canvasRef} className="chart-canvas" />
        ) : (
          <div className="chart-empty">
            <div className="chart-empty-icon">📊</div>
            <p>
              Upload a CSV, then ask about visualizations
              <br />
              or use the column selectors above.
            </p>
          </div>
        )}
      </div>

      {chart && (
        <div className="chart-footer">
          {chart.type} chart &nbsp;·&nbsp; {chart.x_label} vs {chart.y_label}
          &nbsp;·&nbsp; {chart.labels?.length} data points
        </div>
      )}
    </div>
  );
}
