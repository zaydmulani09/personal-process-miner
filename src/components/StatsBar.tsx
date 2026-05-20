import { SummaryStats } from "../lib/types";

interface Props {
  stats: SummaryStats;
}

export default function StatsBar({ stats }: Props) {
  const cards = [
    { label: "Patterns found", value: String(stats.total_workflows) },
    { label: "Total time wasted", value: stats.total_time_wasted_human },
    { label: "This week", value: stats.weekly_wasted_human },
    { label: "Top pattern", value: stats.top_workflow?.name ?? "None yet" },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: 12,
        marginBottom: 24,
      }}
    >
      {cards.map(({ label, value }) => (
        <div
          key={label}
          style={{
            background: "var(--color-background-secondary)",
            borderRadius: 8,
            padding: "1rem",
          }}
        >
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>
            {label}
          </div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: "#0f172a",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {value}
          </div>
        </div>
      ))}
    </div>
  );
}
