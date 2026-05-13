import { useState, useEffect, useMemo } from "react";

// ── CONFIG: point this at your GitHub Pages data.json URL ───────────────────
// After enabling GitHub Pages on your repo, it will be:
// https://<your-username>.github.io/<your-repo-name>/data.json
const DATA_URL = "https://<your-username>.github.io/<your-repo-name>/data.json";

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmt = {
  mcap: (v) => {
    if (!v) return "—";
    if (v >= 1e9) return `£${(v / 1e9).toFixed(1)}B`;
    if (v >= 1e6) return `£${(v / 1e6).toFixed(0)}M`;
    return `£${v.toLocaleString()}`;
  },
  pct: (v) => (v != null ? `${v.toFixed(2)}%` : "—"),
  num: (v) => (v != null ? v.toFixed(2) : "—"),
};

const EXCHANGES = [
  { key: "ftse",   label: "FTSE All-Share" },
  { key: "nyse",   label: "NYSE" },
  { key: "nasdaq", label: "Nasdaq" },
];

const SORT_COLS = [
  { key: "market_cap",    label: "Mkt Cap" },
  { key: "pe_ratio",      label: "P/E" },
  { key: "pb_ratio",      label: "P/B" },
  { key: "current_ratio", label: "Curr. Ratio" },
  { key: "roe_5y_avg",    label: "ROE 5Y" },
  { key: "dividend_yield",label: "Div. Yield" },
];

// ── Main component ────────────────────────────────────────────────────────────
export default function StockScreener() {
  // Data state
  const [allData,      setAllData]      = useState(null);
  const [meta,         setMeta]         = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);

  // UI state
  const [exchange,     setExchange]     = useState("ftse");
  const [sortCol,      setSortCol]      = useState("market_cap");
  const [sortDir,      setSortDir]      = useState("desc");
  const [search,       setSearch]       = useState("");

  // Filter criteria (user-adjustable)
  const [maxPE,        setMaxPE]        = useState(20);
  const [maxPB,        setMaxPB]        = useState(5);
  const [minCR,        setMinCR]        = useState(1);
  const [minROE,       setMinROE]       = useState(10);

  // Fetch data once on mount
  useEffect(() => {
    fetch(DATA_URL)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        setAllData(json);
        setMeta(json.meta);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  // Filtered + sorted rows
  const rows = useMemo(() => {
    if (!allData) return [];
    const pool = allData[exchange] || [];

    return pool
      .filter((s) => {
        if (s.pe_ratio      > maxPE)  return false;
        if (s.pb_ratio      > maxPB)  return false;
        if (s.current_ratio <= minCR) return false;
        if (s.roe_5y_avg    <= minROE) return false;
        if (search) {
          const q = search.toLowerCase();
          if (!s.ticker.toLowerCase().includes(q) &&
              !s.name.toLowerCase().includes(q)   &&
              !s.sector.toLowerCase().includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const av = a[sortCol] ?? 0;
        const bv = b[sortCol] ?? 0;
        return sortDir === "desc" ? bv - av : av - bv;
      });
  }, [allData, exchange, maxPE, maxPB, minCR, minROE, search, sortCol, sortDir]);

  const toggleSort = (col) => {
    if (col === sortCol) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
  };

  const sortArrow = (col) =>
    col === sortCol ? (sortDir === "desc" ? " ↓" : " ↑") : "";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Value Stock Screener</h1>
          {meta && (
            <p style={styles.subtitle}>
              Last updated:{" "}
              {new Date(meta.last_updated).toLocaleDateString("en-GB", {
                day: "numeric", month: "short", year: "numeric",
              })}
              {" · "}
              {rows.length} stocks match current filters
            </p>
          )}
        </div>

        {/* Exchange selector */}
        <select
          value={exchange}
          onChange={(e) => setExchange(e.target.value)}
          style={styles.exchangeSelect}
        >
          {EXCHANGES.map((ex) => (
            <option key={ex.key} value={ex.key}>
              {ex.label}
            </option>
          ))}
        </select>
      </div>

      {/* Filter controls */}
      <div style={styles.filtersCard}>
        <p style={styles.filtersTitle}>Screening Criteria</p>
        <div style={styles.filtersGrid}>
          <FilterSlider label="Max P/E Ratio"     value={maxPE}  min={1}   max={50}  step={1}   onChange={setMaxPE}  display={`≤ ${maxPE}`} />
          <FilterSlider label="Max P/B Ratio"     value={maxPB}  min={0.5} max={20}  step={0.5} onChange={setMaxPB}  display={`≤ ${maxPB}`} />
          <FilterSlider label="Min Current Ratio" value={minCR}  min={0.5} max={5}   step={0.1} onChange={setMinCR}  display={`> ${minCR.toFixed(1)}`} />
          <FilterSlider label="Min 5Y Avg ROE"    value={minROE} min={1}   max={40}  step={1}   onChange={setMinROE} display={`> ${minROE}%`} />
        </div>
      </div>

      {/* Search */}
      <div style={styles.searchRow}>
        <input
          type="text"
          placeholder="Search by ticker, company or sector…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.searchInput}
        />
      </div>

      {/* Table */}
      {loading && <p style={styles.status}>Loading data…</p>}
      {error   && <p style={styles.statusError}>Error loading data: {error}<br/>Check that DATA_URL is set correctly and GitHub Pages is enabled.</p>}

      {!loading && !error && (
        <>
          {rows.length === 0 ? (
            <p style={styles.status}>No stocks match the current criteria.</p>
          ) : (
            <div style={styles.tableWrap}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <Th>Ticker</Th>
                    <Th>Company</Th>
                    <Th>Sector</Th>
                    {SORT_COLS.map((c) => (
                      <Th key={c.key} sortable onClick={() => toggleSort(c.key)}>
                        {c.label}{sortArrow(c.key)}
                      </Th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((s, i) => (
                    <tr key={s.ticker} style={i % 2 === 0 ? styles.rowEven : styles.rowOdd}>
                      <td style={{...styles.td, ...styles.tickerCell}}>{s.ticker}</td>
                      <td style={{...styles.td, ...styles.nameCell}}>{s.name}</td>
                      <td style={styles.td}><span style={styles.sectorBadge}>{s.sector}</span></td>
                      <td style={{...styles.td, ...styles.numCell}}>{fmt.mcap(s.market_cap)}</td>
                      <td style={{...styles.td, ...styles.numCell}}>{fmt.num(s.pe_ratio)}</td>
                      <td style={{...styles.td, ...styles.numCell}}>{fmt.num(s.pb_ratio)}</td>
                      <td style={{...styles.td, ...styles.numCell}}>{fmt.num(s.current_ratio)}</td>
                      <td style={{...styles.td, ...styles.numCell}}>{fmt.pct(s.roe_5y_avg)}</td>
                      <td style={{...styles.td, ...styles.numCell}}>{fmt.pct(s.dividend_yield)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <p style={styles.footer}>
        Data sourced from Yahoo Finance via yfinance · Refreshed weekly ·
        Not financial advice
      </p>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function FilterSlider({ label, value, min, max, step, onChange, display }) {
  return (
    <div style={styles.sliderGroup}>
      <div style={styles.sliderLabelRow}>
        <span style={styles.sliderLabel}>{label}</span>
        <span style={styles.sliderValue}>{display}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={styles.slider}
      />
    </div>
  );
}

function Th({ children, sortable, onClick }) {
  return (
    <th
      onClick={sortable ? onClick : undefined}
      style={{
        ...styles.th,
        ...(sortable ? styles.thSortable : {}),
      }}
    >
      {children}
    </th>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const COLORS = {
  bg:          "#0f1117",
  surface:     "#1a1d27",
  border:      "#2a2d3a",
  accent:      "#4ade80",   // green — fitting for stocks
  accentDim:   "#166534",
  text:        "#f1f5f9",
  textMuted:   "#94a3b8",
  rowEven:     "#1a1d27",
  rowOdd:      "#141720",
  tickerColor: "#4ade80",
};

const styles = {
  root: {
    fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
    background: COLORS.bg,
    color: COLORS.text,
    minHeight: "100vh",
    padding: "32px 24px",
    boxSizing: "border-box",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "24px",
    flexWrap: "wrap",
    gap: "12px",
  },
  title: {
    margin: 0,
    fontSize: "22px",
    fontWeight: 700,
    letterSpacing: "0.04em",
    color: COLORS.text,
  },
  subtitle: {
    margin: "4px 0 0",
    fontSize: "12px",
    color: COLORS.textMuted,
  },
  exchangeSelect: {
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "6px",
    color: COLORS.text,
    fontSize: "13px",
    padding: "8px 12px",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  filtersCard: {
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "10px",
    padding: "20px 24px",
    marginBottom: "16px",
  },
  filtersTitle: {
    margin: "0 0 16px",
    fontSize: "11px",
    fontWeight: 600,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    color: COLORS.textMuted,
  },
  filtersGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "20px",
  },
  sliderGroup: { display: "flex", flexDirection: "column", gap: "8px" },
  sliderLabelRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sliderLabel: { fontSize: "12px", color: COLORS.textMuted },
  sliderValue: {
    fontSize: "13px",
    fontWeight: 700,
    color: COLORS.accent,
  },
  slider: { width: "100%", accentColor: COLORS.accent, cursor: "pointer" },
  searchRow: { marginBottom: "16px" },
  searchInput: {
    width: "100%",
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "6px",
    color: COLORS.text,
    fontSize: "13px",
    padding: "10px 14px",
    fontFamily: "inherit",
    boxSizing: "border-box",
    outline: "none",
  },
  tableWrap: {
    overflowX: "auto",
    borderRadius: "10px",
    border: `1px solid ${COLORS.border}`,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "13px",
  },
  th: {
    background: COLORS.surface,
    color: COLORS.textMuted,
    fontWeight: 600,
    fontSize: "11px",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    padding: "12px 14px",
    textAlign: "left",
    borderBottom: `1px solid ${COLORS.border}`,
    whiteSpace: "nowrap",
    userSelect: "none",
  },
  thSortable: { cursor: "pointer" },
  td: {
    padding: "11px 14px",
    borderBottom: `1px solid ${COLORS.border}`,
    verticalAlign: "middle",
  },
  rowEven: { background: COLORS.rowEven },
  rowOdd:  { background: COLORS.rowOdd  },
  tickerCell: {
    fontWeight: 700,
    color: COLORS.tickerColor,
    whiteSpace: "nowrap",
  },
  nameCell: {
    color: COLORS.text,
    maxWidth: "220px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  numCell: {
    textAlign: "right",
    fontVariantNumeric: "tabular-nums",
    whiteSpace: "nowrap",
  },
  sectorBadge: {
    background: COLORS.accentDim,
    color: COLORS.accent,
    borderRadius: "4px",
    padding: "2px 8px",
    fontSize: "11px",
    fontWeight: 600,
    whiteSpace: "nowrap",
  },
  status: {
    textAlign: "center",
    color: COLORS.textMuted,
    padding: "48px 0",
    fontSize: "14px",
  },
  statusError: {
    textAlign: "center",
    color: "#f87171",
    padding: "48px 24px",
    fontSize: "13px",
    lineHeight: "1.6",
  },
  footer: {
    marginTop: "24px",
    textAlign: "center",
    fontSize: "11px",
    color: COLORS.textMuted,
    letterSpacing: "0.03em",
  },
};
