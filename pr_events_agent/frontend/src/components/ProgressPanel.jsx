import { AlertIcon, SparkleIcon } from "./icons";

const STAGES = [
  "Identifying company",
  "Crawling company site",
  "Extracting and classifying company-site pages",
  "Searching for third-party coverage",
  "Extracting and classifying search results",
  "Deduplicating results",
  "Archiving sources to the Wayback Machine",
  "Done",
];

export default function ProgressPanel({ stage, error }) {
  if (error) {
    return (
      <div className="glass-card-static animate-scale-in p-6" style={{ borderColor: "rgba(220,38,38,0.3)" }}>
        <div className="flex items-center gap-2">
          <AlertIcon style={{ color: "var(--status-danger)" }} />
          <span style={{ fontWeight: 700, color: "var(--status-danger)" }}>Run failed</span>
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginTop: "0.5rem" }}>{error}</p>
      </div>
    );
  }

  const activeIndex = Math.max(STAGES.indexOf(stage), 0);

  return (
    <div className="glass-card-static animate-scale-in p-6 md:p-8">
      <div className="flex items-center gap-2 mb-4">
        <span className="spin" style={{ display: "inline-flex", color: "var(--accent-primary)" }}>
          <SparkleIcon size={18} />
        </span>
        <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{stage || "Starting…"}</span>
      </div>

      <div className="flex flex-col gap-2">
        {STAGES.map((s, i) => (
          <div key={s} className="flex items-center gap-3">
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "9999px",
                flexShrink: 0,
                background:
                  i < activeIndex
                    ? "var(--status-success)"
                    : i === activeIndex
                    ? "var(--accent-primary)"
                    : "var(--border-default)",
              }}
            />
            <span
              style={{
                fontSize: "0.8rem",
                color: i <= activeIndex ? "var(--text-secondary)" : "var(--text-muted)",
                fontWeight: i === activeIndex ? 600 : 400,
              }}
            >
              {s}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
