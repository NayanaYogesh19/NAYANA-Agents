import { useState } from "react";
import { SearchIcon, CalendarIcon, SparkleIcon } from "./icons";

function firstOfMonth() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function RunForm({ onSubmit, disabled }) {
  const [companyUrl, setCompanyUrl] = useState("");
  const [start, setStart] = useState(firstOfMonth());
  const [end, setEnd] = useState(today());
  const [validationError, setValidationError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!companyUrl.trim()) {
      setValidationError("Enter a company website URL.");
      return;
    }
    let normalized = companyUrl.trim();
    if (!/^https?:\/\//i.test(normalized)) {
      normalized = `https://${normalized}`;
    }
    if (end < start) {
      setValidationError("End date must be on or after the start date.");
      return;
    }
    setValidationError("");
    onSubmit({ companyUrl: normalized, start, end });
  }

  return (
    <form onSubmit={handleSubmit} className="glass-card-static p-6 md:p-8">
      <div className="flex items-center gap-2 mb-1">
        <SparkleIcon size={18} style={{ color: "var(--accent-primary)" }} />
        <h2
          className="font-display"
          style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)" }}
        >
          New PR &amp; Events report
        </h2>
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
        Works for any company website — discovery, extraction, and classification run
        dynamically against whatever URL you give it.
      </p>

      <div className="flex flex-col gap-4">
        <div>
          <label
            className="font-mono"
            style={{
              display: "block",
              fontSize: "0.68rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-muted)",
              marginBottom: "0.4rem",
            }}
          >
            Company website
          </label>
          <div style={{ position: "relative" }}>
            <span
              style={{
                position: "absolute",
                left: "1rem",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-muted)",
                pointerEvents: "none",
              }}
            >
              <SearchIcon size={16} />
            </span>
            <input
              className="glass-input search-pill"
              type="text"
              placeholder="e.g. www.example.com"
              value={companyUrl}
              onChange={(e) => setCompanyUrl(e.target.value)}
              disabled={disabled}
            />
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <label
              className="font-mono"
              style={{
                display: "block",
                fontSize: "0.68rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-muted)",
                marginBottom: "0.4rem",
              }}
            >
              <CalendarIcon size={11} style={{ display: "inline", marginRight: 4, verticalAlign: -1 }} />
              Start date
            </label>
            <input
              className="glass-input"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              disabled={disabled}
            />
          </div>
          <div className="flex-1">
            <label
              className="font-mono"
              style={{
                display: "block",
                fontSize: "0.68rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-muted)",
                marginBottom: "0.4rem",
              }}
            >
              <CalendarIcon size={11} style={{ display: "inline", marginRight: 4, verticalAlign: -1 }} />
              End date
            </label>
            <input
              className="glass-input"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              disabled={disabled}
            />
          </div>
        </div>

        {validationError && (
          <p style={{ color: "var(--status-danger)", fontSize: "0.8rem" }}>{validationError}</p>
        )}

        <button type="submit" className="btn btn-gradient" style={{ padding: "0.75rem 1.5rem", alignSelf: "flex-start" }} disabled={disabled}>
          {disabled ? "Running…" : "Run report"}
        </button>
      </div>
    </form>
  );
}
