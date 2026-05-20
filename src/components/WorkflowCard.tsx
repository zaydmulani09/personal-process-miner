import { Workflow } from "../lib/types";

function parseSteps(stepsJson: string): string[] {
  try {
    const parsed = JSON.parse(stepsJson);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((s: unknown) => {
      if (typeof s === "string") return s;
      if (typeof s === "object" && s !== null && "app" in s) return (s as { app: string }).app;
      return String(s);
    });
  } catch {
    return [];
  }
}

interface Props {
  workflow: Workflow;
  onLabel: (workflow: Workflow) => void;
  onDelete: (id: number) => void;
}

export default function WorkflowCard({ workflow, onLabel, onDelete }: Props) {
  const steps = parseSteps(workflow.steps);
  const isLabeled = workflow.is_labeled === 1;

  const handleDelete = () => {
    if (window.confirm(`Delete "${workflow.name || "this workflow"}"?`)) {
      onDelete(workflow.id);
    }
  };

  return (
    <div style={{
      border: "1px solid #e2e8f0",
      borderRadius: 8,
      padding: "16px 20px",
      marginBottom: 12,
      background: "#fff",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 15 }}>
          {workflow.name || "Unnamed workflow"}
        </span>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: 12,
          background: isLabeled ? "#dcfce7" : "#f1f5f9",
          color: isLabeled ? "#16a34a" : "#64748b",
        }}>
          {isLabeled ? "Labeled" : "Auto-detected"}
        </span>
      </div>

      {steps.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
          {steps.map((step, i) => (
            <span key={i} style={{
              fontSize: 12,
              padding: "2px 10px",
              borderRadius: 12,
              background: "#f1f5f9",
              color: "#334155",
            }}>
              {step}
            </span>
          ))}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 13, color: "#64748b", marginBottom: 12 }}>
        <span>Seen <strong>{workflow.frequency}×</strong></span>
        {workflow.time_wasted_human && (
          <span>Time wasted: <strong>{workflow.time_wasted_human}</strong></span>
        )}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => onLabel(workflow)}
          style={{
            padding: "6px 14px",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            cursor: "pointer",
          }}
        >
          Name this
        </button>
        <button
          onClick={handleDelete}
          style={{
            padding: "6px 14px",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid #fca5a5",
            background: "#fff5f5",
            color: "#dc2626",
            cursor: "pointer",
          }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}
