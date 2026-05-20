import { useCallback, useEffect, useState } from "react";
import AutomationCard from "../components/AutomationCard";
import { sendToSidecar } from "../lib/sidecar";
import { Automation } from "../lib/types";

interface AutomationStats {
  total_automations: number;
  total_runs: number;
  successful_runs: number;
  estimated_time_saved_seconds: number;
}

const EMPTY_STATS: AutomationStats = {
  total_automations: 0,
  total_runs: 0,
  successful_runs: 0,
  estimated_time_saved_seconds: 0,
};

type FilterType = "all" | "pyautogui" | "playwright";

function formatSeconds(total: number): string {
  const s = Math.floor(total);
  if (s >= 3600)
    return `${Math.floor(s / 3600)} hr ${Math.floor((s % 3600) / 60)} min`;
  if (s >= 60) return `${Math.floor(s / 60)} min`;
  return `${s} sec`;
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: "14px 18px",
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 700, color: "#0f172a" }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{label}</div>
    </div>
  );
}

export default function Automations() {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [stats, setStats] = useState<AutomationStats>(EMPTY_STATS);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("all");
  const [runResults, setRunResults] = useState<
    Record<number, { status: string; stderr: string }>
  >({});

  const fetchData = useCallback(async () => {
    try {
      const [autoResp, statsResp] = await Promise.all([
        sendToSidecar({ type: "get_automations" }),
        sendToSidecar({ type: "get_automation_stats" }),
      ]);
      setAutomations((autoResp as { data: Automation[] }).data ?? []);
      setStats(
        (statsResp as { data: AutomationStats }).data ?? EMPTY_STATS
      );
    } catch {
      // keep stale data on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRun = async (id: number) => {
    const resp = (await sendToSidecar({
      type: "run_automation",
      automation_id: id,
    })) as { status: string; stderr: string };
    setRunResults((prev) => ({
      ...prev,
      [id]: { status: resp.status, stderr: resp.stderr },
    }));
    // Refresh to pick up updated run_count / last_run_at / last_run_status
    await fetchData();
  };

  const handleDelete = async (id: number) => {
    await sendToSidecar({ type: "delete_automation", automation_id: id });
    await fetchData();
  };

  const handleRename = async (id: number, name: string) => {
    await sendToSidecar({
      type: "update_automation_name",
      automation_id: id,
      name,
    });
    await fetchData();
  };

  const filtered =
    filter === "all"
      ? automations
      : automations.filter((a) => a.script_type === filter);

  const filterBtn = (label: string, value: FilterType) => (
    <button
      onClick={() => setFilter(value)}
      style={{
        padding: "6px 14px",
        fontSize: 13,
        borderRadius: 6,
        border: "1px solid",
        borderColor: filter === value ? "#3b82f6" : "#e2e8f0",
        background: filter === value ? "#eff6ff" : "#fff",
        color: filter === value ? "#1d4ed8" : "#475569",
        cursor: "pointer",
        fontWeight: filter === value ? 600 : 400,
        boxShadow: "none",
      }}
    >
      {label}
    </button>
  );

  return (
    <div
      style={{
        padding: 32,
        maxWidth: 800,
        margin: "0 auto",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 22,
            fontWeight: 700,
            margin: "0 0 4px",
            color: "#0f172a",
          }}
        >
          Automation Library
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#64748b" }}>
          Scripts generated from your workflows
        </p>
      </div>

      {/* Stats bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <StatCard label="Total automations" value={stats.total_automations} />
        <StatCard label="Total runs" value={stats.total_runs} />
        <StatCard
          label="Estimated time saved"
          value={formatSeconds(stats.estimated_time_saved_seconds)}
        />
      </div>

      {/* Filter row */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {filterBtn("All", "all")}
        {filterBtn("PyAutoGUI", "pyautogui")}
        {filterBtn("Playwright", "playwright")}
      </div>

      {/* Run result banners */}
      {Object.entries(runResults).map(([id, result]) => (
        <div
          key={id}
          style={{
            padding: "10px 14px",
            borderRadius: 6,
            background: result.status === "success" ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${result.status === "success" ? "#bbf7d0" : "#fecaca"}`,
            color: result.status === "success" ? "#15803d" : "#dc2626",
            fontSize: 13,
            marginBottom: 12,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>
            {result.status === "success"
              ? "✓ Script ran successfully"
              : `✗ Script error: ${result.stderr || "unknown error"}`}
          </span>
          <button
            onClick={() =>
              setRunResults((prev) => {
                const next = { ...prev };
                delete next[Number(id)];
                return next;
              })
            }
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 16,
              color: "inherit",
              padding: 0,
              marginLeft: 12,
            }}
          >
            ×
          </button>
        </div>
      ))}

      {/* Automation list */}
      {loading ? (
        <>
          {[1, 2].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: 160, borderRadius: 8, marginBottom: 12 }}
            />
          ))}
        </>
      ) : filtered.length === 0 ? (
        <p style={{ color: "#94a3b8", fontSize: 14 }}>
          {automations.length === 0
            ? "No automations yet. Record a macro or generate a Playwright script from a workflow."
            : `No ${filter} automations.`}
        </p>
      ) : (
        filtered.map((a) => (
          <AutomationCard
            key={a.id}
            automation={a}
            onRun={handleRun}
            onDelete={handleDelete}
            onRename={handleRename}
          />
        ))
      )}
    </div>
  );
}
