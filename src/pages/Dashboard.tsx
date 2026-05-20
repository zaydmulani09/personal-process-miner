import { useCallback, useEffect, useState } from "react";
import ActivityHeatmap from "../components/ActivityHeatmap";
import CaptureControls from "../components/CaptureControls";
import LabelWorkflowModal from "../components/LabelWorkflowModal";
import StatsBar from "../components/StatsBar";
import WorkflowCard from "../components/WorkflowCard";
import { sendToSidecar } from "../lib/sidecar";
import { Automation, Session, SummaryStats, Workflow } from "../lib/types";

const EMPTY_STATS: SummaryStats = {
  total_workflows: 0,
  total_time_wasted_seconds: 0,
  total_time_wasted_human: "0 sec",
  top_workflow: null,
  weekly_wasted_seconds: 0,
  weekly_wasted_human: "0 sec",
};

function SkeletonCard() {
  return (
    <div
      className="skeleton"
      style={{ height: 120, borderRadius: 8, marginBottom: 12 }}
    />
  );
}

export default function Dashboard() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [stats, setStats] = useState<SummaryStats>(EMPTY_STATS);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);

  const fetchData = useCallback(async () => {
    setError("");
    try {
      const [wfResp, statsResp, sessResp, autoResp] = await Promise.all([
        sendToSidecar({ type: "get_ranked_workflows" }),
        sendToSidecar({ type: "get_summary_stats" }),
        sendToSidecar({ type: "get_sessions", limit: 500 }),
        sendToSidecar({ type: "get_automations" }),
      ]);
      setWorkflows((wfResp as { data: Workflow[] }).data ?? []);
      setStats((statsResp as { data: SummaryStats }).data ?? EMPTY_STATS);
      setSessions((sessResp as { data: Session[] }).data ?? []);
      setAutomations((autoResp as { data: Automation[] }).data ?? []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async (id: number) => {
    try {
      await sendToSidecar({ type: "delete_workflow", workflow_id: id });
      await fetchData();
    } catch (e) {
      alert(`Failed to delete: ${e}`);
    }
  };

  const handleSave = async () => {
    setActiveWorkflow(null);
    await fetchData();
  };

  return (
    <div
      style={{
        padding: 32,
        maxWidth: 800,
        margin: "0 auto",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 22,
            fontWeight: 700,
            margin: "0 0 4px",
            color: "#0f172a",
            textAlign: "left",
          }}
        >
          Your Workflows
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#64748b" }}>
          Patterns detected from your computer activity
        </p>
      </div>

      <CaptureControls onAnalysisComplete={fetchData} />

      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 14px",
            borderRadius: 6,
            background: "#fef2f2",
            color: "#dc2626",
            fontSize: 13,
            marginBottom: 20,
          }}
        >
          <span>{error}</span>
          <button
            onClick={fetchData}
            style={{
              marginLeft: "auto",
              padding: "4px 10px",
              fontSize: 12,
              borderRadius: 4,
              border: "1px solid #fca5a5",
              background: "#fff",
              color: "#dc2626",
              cursor: "pointer",
              boxShadow: "none",
            }}
          >
            Retry
          </button>
        </div>
      )}

      <StatsBar stats={stats} />

      <ActivityHeatmap sessions={sessions} />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 16,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            fontWeight: 600,
            margin: 0,
            color: "#0f172a",
            textAlign: "left",
          }}
        >
          Detected Patterns
        </h2>
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 12,
            background: "#f1f5f9",
            color: "#64748b",
          }}
        >
          {workflows.length}
        </span>
      </div>

      {loading ? (
        <>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </>
      ) : workflows.length === 0 ? (
        <p style={{ color: "#94a3b8", fontSize: 14 }}>
          No patterns detected yet. Start capture to begin.
        </p>
      ) : (
        workflows.map((wf) => (
          <WorkflowCard
            key={wf.id}
            workflow={wf}
            automation={automations.find((a) => a.workflow_id === wf.id)}
            onLabel={setActiveWorkflow}
            onDelete={handleDelete}
          />
        ))
      )}

      {activeWorkflow && (
        <LabelWorkflowModal
          workflow={activeWorkflow}
          onSave={handleSave}
          onClose={() => setActiveWorkflow(null)}
        />
      )}
    </div>
  );
}
