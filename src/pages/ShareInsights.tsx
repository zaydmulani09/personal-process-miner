import { useCallback, useEffect, useState } from "react";
import InsightsCard from "../components/InsightsCard";
import { sendToSidecar } from "../lib/sidecar";
import { SummaryStats, Workflow } from "../lib/types";

function getMondayLabel(): string {
  const now = new Date();
  const day = now.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  return monday.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

const EMPTY_STATS: SummaryStats = {
  total_workflows: 0,
  total_time_wasted_seconds: 0,
  total_time_wasted_human: "0 sec",
  top_workflow: null,
  weekly_wasted_seconds: 0,
  weekly_wasted_human: "0 sec",
};

export default function ShareInsights() {
  const [stats, setStats] = useState<SummaryStats>(EMPTY_STATS);
  const [topWorkflows, setTopWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [copyMsg, setCopyMsg] = useState<string | null>(null);
  const weekLabel = `Week of ${getMondayLabel()}`;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsResp, wfResp] = await Promise.all([
        sendToSidecar({ type: "get_summary_stats" }),
        sendToSidecar({ type: "get_ranked_workflows" }),
      ]);
      setStats((statsResp as { data: SummaryStats }).data ?? EMPTY_STATS);
      setTopWorkflows(((wfResp as { data: Workflow[] }).data ?? []).slice(0, 3));
    } catch {
      // keep stale data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCopy = () => {
    setCopyMsg("Use your OS screenshot tool to capture the card above (Win+Shift+S / Cmd+Shift+4)");
    setTimeout(() => setCopyMsg(null), 5000);
  };

  return (
    <div
      style={{
        padding: 32,
        maxWidth: 760,
        margin: "0 auto",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
          Share Your Wins
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#64748b" }}>
          Screenshot this card and share what you've automated
        </p>
      </div>

      {/* Card area */}
      {loading ? (
        <div
          style={{
            width: 600,
            height: 380,
            background: "#0f172a",
            borderRadius: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#475569",
            fontSize: 14,
          }}
        >
          Loading stats…
        </div>
      ) : (
        <div
          style={{
            display: "inline-block",
            boxShadow: "0 20px 60px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.10)",
            borderRadius: 16,
          }}
        >
          <InsightsCard stats={stats} topWorkflows={topWorkflows} weekLabel={weekLabel} />
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 12, marginTop: 24, alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={handleCopy}
          style={{
            padding: "9px 18px",
            fontSize: 14,
            borderRadius: 8,
            border: "1px solid #e2e8f0",
            background: "#fff",
            color: "#334155",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          📋 Copy as Image
        </button>
        <button
          onClick={fetchData}
          disabled={loading}
          style={{
            padding: "9px 18px",
            fontSize: 14,
            borderRadius: 8,
            border: "none",
            background: loading ? "#cbd5e1" : "#3b82f6",
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 500,
          }}
        >
          🔄 Refresh Stats
        </button>
      </div>

      {copyMsg && (
        <div
          style={{
            marginTop: 12,
            padding: "10px 14px",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: 8,
            fontSize: 13,
            color: "#78350f",
          }}
        >
          {copyMsg}
        </div>
      )}

      {/* OS screenshot tip */}
      <p style={{ marginTop: 16, fontSize: 13, color: "#94a3b8" }}>
        Tip: Use your OS screenshot tool to capture just the card above (Windows: Win+Shift+S, macOS: Cmd+Shift+4)
      </p>
    </div>
  );
}
