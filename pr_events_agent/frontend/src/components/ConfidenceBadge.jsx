const STYLES = {
  verified: { bg: "rgba(16,185,129,0.10)", color: "#065F46" },
  unverified: { bg: "rgba(245,158,11,0.12)", color: "#92400E" },
};

export default function ConfidenceBadge({ confidence }) {
  const s = STYLES[confidence] ?? STYLES.unverified;
  return (
    <span className="badge" style={{ background: s.bg, color: s.color }}>
      {confidence}
    </span>
  );
}
