import { useEffect, useRef, useState } from "react";

// Warm editorial color palette for chart bars
const WARM_PALETTE = [
  "#c45c26", // terracotta
  "#e09800", // gold
  "#6b9b6b", // sage green
  "#c47a70", // dusty rose
  "#9a7aaa", // dusty violet
  "#7a9ab0", // muted slate
  "#a09060", // warm olive
  "#c49060", // warm caramel
];

const BarIcon = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
    <rect x="1" y="8" width="3" height="6" rx="0.5" />
    <rect x="6" y="4" width="3" height="10" rx="0.5" />
    <rect x="11" y="2" width="3" height="12" rx="0.5" />
  </svg>
);
const LineIcon = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1,12 5,7 9,9 13,3" />
    <circle cx="1" cy="12" r="1.5" fill="currentColor" stroke="none" />
    <circle cx="5" cy="7" r="1.5" fill="currentColor" stroke="none" />
    <circle cx="9" cy="9" r="1.5" fill="currentColor" stroke="none" />
    <circle cx="13" cy="3" r="1.5" fill="currentColor" stroke="none" />
  </svg>
);
const ScatterIcon = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="4" cy="11" r="1.5" />
    <circle cx="7" cy="6" r="1.5" />
    <circle cx="11" cy="9" r="1.5" />
    <circle cx="13" cy="3" r="1.5" />
    <circle cx="2" cy="14" r="1.5" />
  </svg>
);
const ChartEmptyIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M3 9h18M9 21V9" />
    <path d="M7 15h2M7 18h2M13 12h4M13 15h2" />
  </svg>
);

function drawChart(canvas, chart) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const { labels, values, x_label, y_label, type } = chart;

  const dpr = window.devicePixelRatio || 1;
  canvas.width  = canvas.offsetWidth  * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  ctx.scale(dpr, dpr);
  const w = canvas.offsetWidth;
  const h = canvas.offsetHeight;

  ctx.clearRect(0, 0, w, h);

  const PAD = { top: 32, right: 28, bottom: 68, left: 62 };
  const chartW = w - PAD.left - PAD.right;
  const chartH = h - PAD.top - PAD.bottom;

  const maxVal = Math.max(...values) * 1.12 || 1;
  const minVal = Math.min(0, ...values);
  const range  = maxVal - minVal || 1;

  // ── Warm cream background ──
  ctx.fillStyle = "#fffdf9";
  ctx.fillRect(0, 0, w, h);

  // Subtle inner paper lines (very faint)
  for (let i = 0; i < h; i += 22) {
    ctx.fillStyle = "rgba(196, 92, 38, 0.018)";
    ctx.fillRect(0, i, w, 1);
  }

  // ── Grid lines ──
  const gridCount = 5;
  for (let i = 0; i <= gridCount; i++) {
    const y = PAD.top + (chartH / gridCount) * i;

    ctx.setLineDash([3, 5]);
    ctx.strokeStyle = "#e8ddd0";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + chartW, y);
    ctx.stroke();
    ctx.setLineDash([]);

    const val = maxVal - range * (i / gridCount);
    const label = Math.abs(val) >= 1000
      ? (val / 1000).toFixed(1) + "k"
      : val.toFixed(val % 1 === 0 ? 0 : 1);

    ctx.fillStyle = "#b5a898";
    ctx.font = "10px 'IBM Plex Mono', monospace";
    ctx.textAlign = "right";
    ctx.fillText(label, PAD.left - 10, y + 4);
  }

  // ── Axes ──
  ctx.strokeStyle = "#cfc0ae";
  ctx.lineWidth = 1.2;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(PAD.left, PAD.top);
  ctx.lineTo(PAD.left, PAD.top + chartH);
  ctx.lineTo(PAD.left + chartW, PAD.top + chartH);
  ctx.stroke();

  const n    = labels.length;
  const step = chartW / Math.max(n, 1);
  const toY  = (v) => PAD.top + chartH - ((v - minVal) / range) * chartH;

  // ── Draw by type ──
  if (type === "line") {
    // Area fill
    const areaGrad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + chartH);
    areaGrad.addColorStop(0, "rgba(196, 92, 38, 0.14)");
    areaGrad.addColorStop(1, "rgba(196, 92, 38, 0.01)");

    ctx.beginPath();
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      i === 0 ? ctx.moveTo(x, toY(v)) : ctx.lineTo(x, toY(v));
    });
    ctx.lineTo(PAD.left + step * (n - 1) + step / 2, PAD.top + chartH);
    ctx.lineTo(PAD.left + step / 2, PAD.top + chartH);
    ctx.closePath();
    ctx.fillStyle = areaGrad;
    ctx.fill();

    // Line stroke
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      i === 0 ? ctx.moveTo(x, toY(v)) : ctx.lineTo(x, toY(v));
    });
    ctx.strokeStyle = "#c45c26";
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.stroke();

    // Dots
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      const y = toY(v);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fffdf9";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#c45c26";
      ctx.fill();
    });

  } else if (type === "scatter") {
    values.forEach((v, i) => {
      const x = PAD.left + step * i + step / 2;
      const y = toY(v);
      // Outer ring
      ctx.beginPath();
      ctx.arc(x, y, 6, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(196, 92, 38, 0.15)";
      ctx.fill();
      // Inner dot
      ctx.beginPath();
      ctx.arc(x, y, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = "#c45c26";
      ctx.strokeStyle = "#fffdf9";
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
    });

  } else {
    // Bar chart — cycle through warm palette
    const barWidth = step * 0.58;
    values.forEach((v, i) => {
      const x    = PAD.left + step * i + (step - barWidth) / 2;
      const barH = Math.max(((v - minVal) / range) * chartH, 1);
      const y    = toY(v);
      const col  = WARM_PALETTE[i % WARM_PALETTE.length];

      // Shadow
      ctx.shadowColor = "rgba(42, 31, 20, 0.08)";
      ctx.shadowBlur  = 4;
      ctx.shadowOffsetY = 2;

      ctx.fillStyle = col;
      ctx.beginPath();

      // Rounded top corners only
      const r = Math.min(3, barWidth / 4);
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + barWidth - r, y);
      ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + r);
      ctx.lineTo(x + barWidth, y + barH);
      ctx.lineTo(x, y + barH);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
      ctx.fill();

      ctx.shadowColor = "transparent";
      ctx.shadowBlur  = 0;
      ctx.shadowOffsetY = 0;
    });
  }

  // ── X-axis labels ──
  ctx.fillStyle = "#7a6a5a";
  ctx.font = "10px 'IBM Plex Sans', sans-serif";
  ctx.textAlign = "center";
  labels.forEach((label, i) => {
    const x = PAD.left + step * i + step / 2;
    const s = String(label);
    const truncated = s.length > 12 ? s.slice(0, 11) + "…" : s;
    ctx.save();
    ctx.translate(x, PAD.top + chartH + 10);
    ctx.rotate(-Math.PI / 6);
    ctx.fillText(truncated, 0, 0);
    ctx.restore();
  });

  // ── Axis labels ──
  ctx.fillStyle = "#b5a898";
  ctx.font = "11px 'IBM Plex Sans', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(x_label, PAD.left + chartW / 2, h - 6);

  ctx.save();
  ctx.translate(14, PAD.top + chartH / 2);
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

  const columns        = tableData?.columns        || [];
  const numericColumns = tableData?.numeric_columns || [];

  useEffect(() => {
    if (chart?.x_label) setXCol(chart.x_label);
    if (chart?.y_label) setYCol(chart.y_label);
    if (chart?.type)    setChartType(chart.type);
  }, [chart?.x_label, chart?.y_label, chart?.type]);

  useEffect(() => {
    if (tableData && !xCol) {
      const nonNumeric = columns.filter((c) => !numericColumns.includes(c));
      setXCol(nonNumeric[0] || columns[0] || "");
      setYCol(numericColumns[0] || "");
    }
  }, [tableData]);

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
          x_col: x, y_col: y, chart_type: type,
        }),
      });
      if (res.ok) onChartUpdate(await res.json());
    } catch (_) {}
    setFetching(false);
  };

  const handleX    = (e) => { const v = e.target.value; setXCol(v); fetchChart(v, yCol, chartType); };
  const handleY    = (e) => { const v = e.target.value; setYCol(v); fetchChart(xCol, v, chartType); };
  const handleType = (t) => { setChartType(t); fetchChart(xCol, yCol, t); };

  const downloadPDF = () => {
    const canvas = canvasRef.current;
    const img    = canvas ? canvas.toDataURL("image/png") : null;

    const insights = messages
      .filter((m) => m.role === "assistant")
      .slice(-4)
      .map((m) =>
        `<div class="block">${m.text
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/\n/g, "<br>")
        }</div>`
      )
      .join("");

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>DataBot Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
  body { font-family:'IBM Plex Sans',sans-serif; padding:48px; color:#2a1f14; background:#faf7f2; max-width:820px; margin:0 auto; }
  h1 { font-family:'Playfair Display',serif; font-size:28px; color:#2a1f14; margin-bottom:6px; }
  .accent { color:#c45c26; }
  .meta { color:#b5a898; font-size:11px; margin-bottom:32px; border-bottom:1px solid #e8ddd0; padding-bottom:16px; font-family:monospace; }
  img { width:100%; border:1px solid #e8ddd0; border-radius:8px; margin-bottom:32px; background:#fffdf9; }
  h2 { font-family:'Playfair Display',serif; font-size:18px; color:#2a1f14; margin-bottom:16px; font-style:italic; }
  .block { border-left:3px solid #c45c26; padding:12px 18px; margin-bottom:12px; border-radius:0 6px 6px 0; background:#fffdf9; font-size:13px; line-height:1.75; }
  @media print { body { padding:24px; } }
</style>
</head>
<body>
<h1>DataBot <span class="accent">Insights Report</span></h1>
<div class="meta">
  Generated ${new Date().toLocaleString()}
  ${session ? ` &nbsp;|&nbsp; ${session.filename} &nbsp;|&nbsp; ${session.shape[0].toLocaleString()} rows &times; ${session.shape[1]} cols` : ""}
  ${chart ? ` &nbsp;|&nbsp; ${chart.type} chart &mdash; ${chart.x_label} vs ${chart.y_label}` : ""}
</div>
${img ? `<img src="${img}" alt="Chart visualization" />` : "<p><em>No chart available.</em></p>"}
<h2>Analysis &amp; Insights</h2>
${insights || "<p><em>No conversation yet.</em></p>"}
</body>
</html>`;

    const win = window.open("", "_blank");
    if (!win) { alert("Allow popups to generate the PDF report."); return; }
    win.document.write(html);
    win.document.close();
    win.addEventListener("load", () => setTimeout(() => win.print(), 400));
  };

  const TYPES = [
    { id: "bar",     label: "Bar",     Icon: BarIcon },
    { id: "line",    label: "Line",    Icon: LineIcon },
    { id: "scatter", label: "Scatter", Icon: ScatterIcon },
  ];

  return (
    <div className="chart-panel">
      {/* Header */}
      <div className="chart-header">
        <span className="chart-title">Visualization</span>

        <div className="chart-type-group">
          {TYPES.map(({ id, label, Icon }) => (
            <button
              key={id}
              className={`chart-type-btn ${chartType === id ? "active" : ""}`}
              onClick={() => handleType(id)}
              disabled={!session || fetching}
              title={label}
            >
              <span className="chart-type-icon">
                <Icon />
              </span>
              {label}
            </button>
          ))}
        </div>

        {chart && (
          <button className="pdf-btn" onClick={downloadPDF}>
            Save PDF
          </button>
        )}
      </div>

      {/* Column selectors */}
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

          <span className="col-selector-divider">vs</span>

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

      {/* Canvas / Empty state */}
      <div className="chart-body">
        {chart ? (
          <canvas ref={canvasRef} className="chart-canvas" />
        ) : (
          <div className="chart-empty">
            <div className="chart-empty-ornament">
              <ChartEmptyIcon />
            </div>
            <p className="chart-empty-title">No chart yet</p>
            <p>
              Upload a CSV and ask about visualizations,
              or use the column selectors above.
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      {chart && (
        <div className="chart-footer">
          {chart.type} &nbsp;&middot;&nbsp;
          {chart.x_label} vs {chart.y_label} &nbsp;&middot;&nbsp;
          {chart.labels?.length} points
        </div>
      )}
    </div>
  );
}
