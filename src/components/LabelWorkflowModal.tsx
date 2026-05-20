import { useEffect, useRef, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";
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
  onSave: (name: string, steps: string[]) => void;
  onClose: () => void;
}

export default function LabelWorkflowModal({ workflow, onSave, onClose }: Props) {
  const [name, setName] = useState(workflow.name || "");
  const [steps, setSteps] = useState<string[]>(() => parseSteps(workflow.steps));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    if (steps.filter(s => s.trim()).length === 0) {
      setError("At least one step is required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await sendToSidecar({
        type: "label_workflow",
        workflow_id: workflow.id,
        name: name.trim(),
        steps: steps.filter(s => s.trim()),
      });
      onSave(name.trim(), steps.filter(s => s.trim()));
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const updateStep = (i: number, value: string) => {
    setSteps(prev => prev.map((s, idx) => (idx === i ? value : s)));
  };

  const addStep = () => setSteps(prev => [...prev, ""]);

  const removeStep = (i: number) => {
    setSteps(prev => prev.filter((_, idx) => idx !== i));
  };

  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 100,
    }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: "#fff",
        borderRadius: 10,
        padding: 24,
        width: 480,
        maxWidth: "90vw",
        maxHeight: "80vh",
        overflowY: "auto",
        boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
      }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 17, fontWeight: 600 }}>
          Name this workflow
        </h2>

        <input
          ref={nameRef}
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="Name this workflow..."
          style={{
            width: "100%",
            padding: "8px 12px",
            fontSize: 14,
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            marginBottom: 16,
            boxSizing: "border-box",
          }}
        />

        <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "#475569" }}>
          Steps
        </p>

        <ol style={{ margin: "0 0 8px", padding: "0 0 0 20px" }}>
          {steps.map((step, i) => (
            <li key={i} style={{ marginBottom: 6 }}>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  value={step}
                  onChange={e => updateStep(i, e.target.value)}
                  style={{
                    flex: 1,
                    padding: "6px 10px",
                    fontSize: 13,
                    borderRadius: 6,
                    border: "1px solid #cbd5e1",
                  }}
                />
                <button
                  onClick={() => removeStep(i)}
                  style={{
                    padding: "4px 8px",
                    fontSize: 13,
                    borderRadius: 6,
                    border: "1px solid #fca5a5",
                    background: "#fff5f5",
                    color: "#dc2626",
                    cursor: "pointer",
                    flexShrink: 0,
                  }}
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ol>

        <button
          onClick={addStep}
          style={{
            padding: "5px 12px",
            fontSize: 12,
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            cursor: "pointer",
            marginBottom: 16,
          }}
        >
          + Add step
        </button>

        {error && (
          <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>{error}</p>
        )}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              padding: "8px 16px",
              fontSize: 13,
              borderRadius: 6,
              border: "1px solid #cbd5e1",
              background: "#f8fafc",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: "8px 16px",
              fontSize: 13,
              borderRadius: 6,
              border: "none",
              background: saving ? "#94a3b8" : "#3b82f6",
              color: "#fff",
              cursor: saving ? "not-allowed" : "pointer",
            }}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
