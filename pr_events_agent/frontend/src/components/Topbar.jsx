import { SunIcon, MoonIcon, SparkleIcon } from "./icons";

export default function Topbar({ theme, onToggleTheme }) {
  return (
    <div
      className="flex items-center justify-between"
      style={{ height: "var(--topbar-height, 72px)", padding: "0 2rem", borderBottom: "1px solid var(--border-subtle)" }}
    >
      <div className="flex items-center gap-3">
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: "0.875rem",
            background: "linear-gradient(135deg, #6366F1, #7C3AED)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            boxShadow: "0 8px 20px rgba(124,58,237,0.32)",
          }}
        >
          <SparkleIcon size={20} />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: "1rem", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            PR &amp; Events Agent
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Competitor discovery, any company</div>
        </div>
      </div>

      <button
        onClick={onToggleTheme}
        className="elevated-pill btn-ghost"
        style={{ width: 44, height: 44, borderRadius: "9999px", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
        aria-label="Toggle theme"
      >
        {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      </button>
    </div>
  );
}
