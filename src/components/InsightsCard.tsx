import { SummaryStats, Workflow } from "../lib/types";

export interface InsightsCardProps {
  stats: SummaryStats;
  topWorkflows: Workflow[];
  weekLabel: string;
}

function timeSaved(w: Workflow): string {
  if (w.time_wasted_human) return w.time_wasted_human;
  return "";
}

export default function InsightsCard({ stats, topWorkflows, weekLabel }: InsightsCardProps) {
  const workflows = topWorkflows.slice(0, 3);

  return (
    <div
      style={{
        width: 600,
        minHeight: 380,
        background: "#0f172a",
        borderRadius: 16,
        padding: "36px 40px 28px",
        boxSizing: "border-box",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        color: "#f8fafc",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 32,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 18, color: "#f8fafc", letterSpacing: "-0.02em" }}>
          ⚡ Process Miner
        </span>
        <span style={{ fontSize: 13, color: "#64748b" }}>{weekLabel}</span>
      </div>

      {/* Hero stat */}
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: "#38bdf8",
            lineHeight: 1,
            letterSpacing: "-0.04em",
            marginBottom: 10,
          }}
        >
          {stats.weekly_wasted_human || "0 sec"}
        </div>
        <div style={{ fontSize: 15, color: "#94a3b8" }}>
          saved this week from automated workflows
        </div>
      </div>

      {/* Divider */}
      <div
        style={{
          height: 1,
          background: "rgba(255,255,255,0.08)",
          marginBottom: 24,
        }}
      />

      {/* Workflow rows */}
      {workflows.length === 0 ? (
        <div style={{ fontSize: 14, color: "#475569", textAlign: "center", padding: "12px 0" }}>
          Keep using the app — patterns appear after repeated workflows
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 28 }}>
          {workflows.map((w, i) => (
            <div
              key={w.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "rgba(255,255,255,0.04)",
                borderRadius: 8,
                padding: "12px 16px",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: 14,
                    color: "#f1f5f9",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {i + 1}. {w.name}
                </div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 3 }}>
                  {w.frequency} run{w.frequency === 1 ? "" : "s"}
                  {w.avg_duration_seconds
                    ? ` · ${Math.round(w.avg_duration_seconds)}s avg`
                    : ""}
                </div>
              </div>
              {timeSaved(w) && (
                <div
                  style={{
                    marginLeft: 16,
                    flexShrink: 0,
                    background: "rgba(56,189,248,0.12)",
                    border: "1px solid rgba(56,189,248,0.25)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "#38bdf8",
                    whiteSpace: "nowrap",
                  }}
                >
                  {timeSaved(w)} saved
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Divider */}
      <div style={{ height: 1, background: "rgba(255,255,255,0.06)", marginBottom: 18 }} />

      {/* Bottom branding */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 12, color: "#334155", fontWeight: 600 }}>
          personal-process-miner
        </span>
        <span style={{ fontSize: 11, color: "#334155" }}>
          github.com/zaydmulani09/personal-process-miner
        </span>
      </div>
    </div>
  );
}
