import { useCallback, useEffect, useState } from "react";
import LabelWorkflowModal from "../components/LabelWorkflowModal";
import WorkflowCard from "../components/WorkflowCard";
import { sendToSidecar } from "../lib/sidecar";
import { SummaryStats, Workflow } from "../lib/types";

export default function Dashboard() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);

  const fetchData = useCallback(async () => {
    setError("");
    try {
      const [wfResp, statsResp] = await Promise.all([
        sendToSidecar({ type: "get_ranked_workflows" }) as Promise<{ data: Workflow[] }>,
        sendToSidecar({ type: "get_summary_stats" }) as Promise<{ data: SummaryStats }>,
      ]);
      setWorkflows((wfResp as { data: Workflow[] }).data ?? []);
      setStats((statsResp as { data: SummaryStats }).data ?? null);
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

  if (loading) {
    return (
      <div style={{ padding: 32, color: "#64748b", fontSize: 15 }}>Loading…</div>
    );
  }

  return (
    <div style={{ padding: 32, maxWidth: 720, margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 24px", color: "#0f172a" }}>
        Process Miner
      </h1>

      {error && (
        <div style={{
          padding: "10px 14px",
          borderRadius: 6,
          background: "#fef2f2",
          color: "#dc2626",
          fontSize: 13,
          marginBottom: 20,
        }}>
          {error}
        </div>
      )}

      {stats && (
        <div style={{ display: "flex", gap: 12, marginBottom: 28 }}>
          <StatCard label="Workflows detected" value={String(stats.total_workflows)} />
          <StatCard label="Total time wasted" value={stats.total_time_wasted_human} />
          <StatCard
            label="Top workflow"
            value={stats.top_workflow?.name ?? "—"}
          />
        </div>
      )}

      {workflows.length === 0 ? (
        <p style={{ color: "#94a3b8", fontSize: 14 }}>
          No patterns detected yet. Start capture to begin.
        </p>
      ) : (
        workflows.map(wf => (
          <WorkflowCard
            key={wf.id}
            workflow={wf}
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

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      flex: 1,
      border: "1px solid #e2e8f0",
      borderRadius: 8,
      padding: "14px 16px",
      background: "#f8fafc",
    }}>
      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a" }}>{value}</div>
    </div>
  );
}
