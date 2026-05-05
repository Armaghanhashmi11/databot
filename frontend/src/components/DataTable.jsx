export default function DataTable({ tableData }) {
  if (!tableData) {
    return (
      <div className="table-empty-state">
        <div className="spinner" style={{ margin: "0 auto 12px" }} />
        <p>Loading table data…</p>
      </div>
    );
  }

  const { columns, rows, numeric_columns } = tableData;

  return (
    <div className="table-shell">
      <div className="table-toolbar">
        <span className="table-title">📋 Data Preview</span>
        <span className="table-meta">
          First {rows.length} rows &nbsp;·&nbsp; {columns.length} columns
          &nbsp;·&nbsp; {numeric_columns.length} numeric
        </span>
      </div>
      <div className="table-scroll-area">
        <table className="data-table">
          <thead>
            <tr>
              <th className="row-num-col">#</th>
              {columns.map((c) => (
                <th key={c} className={numeric_columns.includes(c) ? "col-numeric" : ""}>
                  {c}
                  {numeric_columns.includes(c) && <span className="col-type-badge">123</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td className="row-num-col">{i + 1}</td>
                {columns.map((c) => (
                  <td
                    key={c}
                    className={numeric_columns.includes(c) ? "cell-numeric" : "cell-text"}
                  >
                    {row[c] === "" ? <span className="cell-null">—</span> : String(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
