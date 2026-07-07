const STYLES = {
  company_site: { bg: "rgba(3,105,161,0.08)", color: "#0369A1", label: "Company site" },
  search: { bg: "rgba(124,58,237,0.08)", color: "#7C3AED", label: "Search" },
};

export default function SourcePill({ sourceType }) {
  const s = STYLES[sourceType] ?? STYLES.search;
  return (
    <span className="badge" style={{ background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}
