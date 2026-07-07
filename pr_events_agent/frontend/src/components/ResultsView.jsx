import { ExternalLinkIcon, ArchiveIcon, InboxIcon } from "./icons";
import ConfidenceBadge from "./ConfidenceBadge";
import SourcePill from "./SourcePill";

const CATEGORY_META = [
  { key: "press_releases", label: "Press Releases", accent: "#7C3AED" },
  { key: "webinars", label: "Webinars", accent: "#0EA5E9" },
  { key: "events", label: "Events / Exhibitions", accent: "#F59E0B" },
  { key: "awards", label: "Awards / Wins", accent: "#10B981" },
];

function ItemRow({ item, accent }) {
  return (
    <tr style={{ borderBottom: "1px solid rgba(15,23,42,0.04)" }}>
      <td style={{ padding: "0.75rem 1rem" }}>
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          style={{
            color: "var(--text-primary)",
            fontWeight: 600,
            fontSize: "0.85rem",
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.35rem",
          }}
        >
          {item.title}
          <ExternalLinkIcon style={{ color: "var(--text-muted)", flexShrink: 0 }} />
        </a>
      </td>
      <td style={{ padding: "0.75rem 1rem", whiteSpace: "nowrap" }}>
        <span className="font-mono" style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          {item.published_date || "Unknown"}
        </span>
      </td>
      <td style={{ padding: "0.75rem 1rem", whiteSpace: "nowrap" }}>
        <SourcePill sourceType={item.source_type} />
      </td>
      <td style={{ padding: "0.75rem 1rem", whiteSpace: "nowrap" }}>
        <ConfidenceBadge confidence={item.confidence} />
      </td>
      <td style={{ padding: "0.75rem 1rem", whiteSpace: "nowrap" }}>
        {item.archived_url ? (
          <a
            href={item.archived_url}
            target="_blank"
            rel="noreferrer"
            style={{
              color: accent,
              fontSize: "0.78rem",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              textDecoration: "none",
            }}
          >
            <ArchiveIcon /> Archived
          </a>
        ) : (
          <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>—</span>
        )}
      </td>
    </tr>
  );
}

function CategorySection({ label, accent, items }) {
  return (
    <div className="glass-card-static" style={{ padding: 0, overflow: "hidden" }}>
      <div
        className="flex items-center justify-between"
        style={{
          padding: "1rem 1.25rem",
          borderBottom: "1px solid var(--border-subtle)",
          background: "var(--surface-card-header)",
        }}
      >
        <div className="flex items-center gap-2">
          <span style={{ width: 4, height: 18, borderRadius: 2, background: accent, display: "inline-block" }} />
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)" }}>{label}</h3>
        </div>
        <span
          className="badge"
          style={{ background: `${accent}15`, color: accent }}
        >
          {items.length} found
        </span>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2" style={{ padding: "2rem 1rem" }}>
          <InboxIcon style={{ color: "var(--text-muted)" }} />
          <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
            Nothing found in this window
          </span>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Title", "Date", "Source", "Confidence", "Archive"].map((h) => (
                  <th
                    key={h}
                    className="font-mono"
                    style={{
                      textAlign: "left",
                      padding: "0.6rem 1rem",
                      fontSize: "0.65rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      color: "var(--text-muted)",
                      borderBottom: "1px solid var(--border-subtle)",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <ItemRow key={item.url} item={item} accent={accent} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ResultsView({ report }) {
  const total =
    report.press_releases.length + report.webinars.length + report.events.length + report.awards.length;

  return (
    <div className="flex flex-col gap-5 animate-fade-in">
      <div className="glass-card-static flex items-center justify-between p-6">
        <div>
          <h2 className="font-display" style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)" }}>
            {report.company_name}
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginTop: "0.2rem" }}>
            {report.period_start} — {report.period_end} · {report.company_url}
          </p>
        </div>
        <div className="text-right">
          <div className="font-display" style={{ fontSize: "2rem", fontWeight: 800, color: "var(--accent-primary)" }}>
            {total}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            items found
          </div>
        </div>
      </div>

      <p style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
        Review before sending anywhere external — classification and dates are
        best-effort, especially for items marked <ConfidenceBadge confidence="unverified" />.
      </p>

      <div className="flex flex-col gap-5 stagger">
        {CATEGORY_META.map((cat) => (
          <CategorySection key={cat.key} label={cat.label} accent={cat.accent} items={report[cat.key]} />
        ))}
      </div>
    </div>
  );
}
