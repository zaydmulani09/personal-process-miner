import { useEffect, useRef, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";
import { Step } from "../lib/types";

const TYPE_ICONS: Record<string, string> = {
  click: "🖱",
  type: "⌨",
  keypress: "⏎",
  scroll: "↕",
  wait: "⏳",
};

interface NLStep extends Step {
  description: string;
}

interface Props {
  onNavigate: (page: string) => void;
}

export default function NLBuilder({ onNavigate }: Props) {
  const [instruction, setInstruction] = useState("");
  const [plan, setPlan] = useState<NLStep[] | null>(null);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [refineInput, setRefineInput] = useState("");
  const [refining, setRefining] = useState(false);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [aiOk, setAiOk] = useState<boolean | null>(null);
  const [executing, setExecuting] = useState(false);
  const [execProgress, setExecProgress] = useState<string | null>(null);
  const [execResult, setExecResult] = useState<{ ok: boolean; message: string } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    sendToSidecar({ type: "check_ai" })
      .then((r) => setAiOk((r as { available: boolean }).available))
      .catch(() => setAiOk(false));
  }, []);

  const build = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setPlan(null);
    setSummary("");
    try {
      const resp = await sendToSidecar({
        type: "parse_nl_instruction",
        instruction: instruction.trim(),
      }) as { steps: NLStep[]; summary: string };
      setPlan(resp.steps ?? []);
      setSummary(resp.summary ?? "");
    } catch (e: unknown) {
      setToast(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setTimeout(() => setToast(null), 4000);
    } finally {
      setLoading(false);
    }
  };

  const refine = async () => {
    if (!refineInput.trim() || !plan) return;
    setRefining(true);
    try {
      const resp = await sendToSidecar({
        type: "refine_nl_plan",
        instruction: instruction.trim(),
        steps: plan,
        feedback: refineInput.trim(),
      }) as { steps: NLStep[]; summary: string };
      setPlan(resp.steps ?? []);
      setSummary(resp.summary ?? summary);
      setRefineInput("");
    } catch (e: unknown) {
      setToast(`Refine error: ${e instanceof Error ? e.message : String(e)}`);
      setTimeout(() => setToast(null), 4000);
    } finally {
      setRefining(false);
    }
  };

  const commitEdit = (idx: number) => {
    if (plan) {
      const updated = [...plan];
      updated[idx] = { ...updated[idx], description: editValue };
      setPlan(updated);
    }
    setEditingIdx(null);
  };

  const addStep = () => {
    setPlan((prev) => [
      ...(prev ?? []),
      { type: "click", description: "New step" },
    ]);
  };

  const removeStep = (idx: number) => {
    setPlan((prev) => (prev ?? []).filter((_, i) => i !== idx));
  };

  const runNow = async () => {
    if (!instruction.trim()) return;
    setExecuting(true);
    setExecResult(null);
    setExecProgress("Executing...");
    try {
      const resp = await sendToSidecar({
        type: "execute_nl_instruction",
        instruction: instruction.trim(),
      }) as { result: { ok: boolean; steps_completed: number; total: number; error?: string } };
      const r = resp.result;
      if (r.ok) {
        setExecResult({ ok: true, message: `Completed ${r.steps_completed} of ${r.total} steps` });
      } else {
        const stepNum = (r.steps_completed ?? 0) + 1;
        const errMsg = r.error ? `step ${stepNum}: ${r.error}` : `step ${stepNum}`;
        setExecResult({ ok: false, message: `Failed at ${errMsg}` });
      }
    } catch (e: unknown) {
      setExecResult({ ok: false, message: e instanceof Error ? e.message : String(e) });
    } finally {
      setExecuting(false);
      setExecProgress(null);
    }
  };

  const save = async () => {
    if (!plan || plan.length === 0) return;
    setSaving(true);
    try {
      const resp = await sendToSidecar({
        type: "save_nl_automation",
        instruction: instruction.trim(),
        steps: plan,
        summary,
      }) as { id: number };
      void resp.id;
      setToast("✓ Automation saved!");
      setTimeout(() => {
        setToast(null);
        onNavigate("automations");
      }, 1500);
    } catch (e: unknown) {
      setToast(`Save error: ${e instanceof Error ? e.message : String(e)}`);
      setTimeout(() => setToast(null), 4000);
    } finally {
      setSaving(false);
    }
  };

  const btnBase: React.CSSProperties = {
    padding: "9px 18px",
    fontSize: 13,
    borderRadius: 7,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
  };

  return (
    <div
      style={{
        padding: 32,
        maxWidth: 640,
        margin: "0 auto",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
          ✨ Build Automation
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#64748b" }}>
          Describe what you want to automate in plain English
        </p>
      </div>

      {/* AI not configured banner */}
      {aiOk === false && (
        <div
          style={{
            padding: "12px 16px",
            background: "#fef3c7",
            border: "1px solid #fde68a",
            borderRadius: 8,
            fontSize: 13,
            color: "#78350f",
            marginBottom: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <span>
            ⚠ AI Assistant is not configured. Go to{" "}
            <strong>Settings → AI Assistant</strong> to add an API key.
          </span>
          <button
            onClick={() => onNavigate("settings")}
            style={{
              ...btnBase,
              padding: "5px 12px",
              background: "#f59e0b",
              color: "#fff",
              flexShrink: 0,
            }}
          >
            Open Settings
          </button>
        </div>
      )}

      {/* Instruction input */}
      <div
        style={{
          background: "#fff",
          border: "1px solid #e2e8f0",
          borderRadius: 10,
          padding: "20px 24px",
          marginBottom: 20,
        }}
      >
        <textarea
          ref={textareaRef}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && e.metaKey && build()}
          placeholder="Describe what you want to automate..."
          rows={3}
          style={{
            width: "100%",
            fontSize: 14,
            padding: "10px 12px",
            borderRadius: 7,
            border: "1px solid #e2e8f0",
            outline: "none",
            resize: "vertical",
            fontFamily: "inherit",
            boxSizing: "border-box",
            color: "#0f172a",
          }}
        />
        <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6, marginBottom: 14 }}>
          Example: Open Slack, go to #general, type &ldquo;good morning team&rdquo; and send it
        </div>

        <button
          onClick={build}
          disabled={loading || !instruction.trim() || aiOk === false}
          style={{
            ...btnBase,
            background: loading || !instruction.trim() || aiOk === false ? "#94a3b8" : "#8b5cf6",
            color: "#fff",
            cursor: loading || !instruction.trim() || aiOk === false ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          {loading ? (
            <>
              <span
                style={{
                  display: "inline-block",
                  width: 13,
                  height: 13,
                  border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff",
                  borderRadius: "50%",
                  animation: "spin 0.7s linear infinite",
                }}
              />
              Analyzing your screen...
            </>
          ) : "✨ Build Automation"}
        </button>
      </div>

      {/* Plan review */}
      {plan !== null && (
        <div
          style={{
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 10,
            padding: "20px 24px",
          }}
        >
          {/* Summary */}
          {summary && (
            <div
              style={{
                background: "#f0f9ff",
                border: "1px solid #bae6fd",
                borderRadius: 7,
                padding: "10px 14px",
                fontSize: 13,
                color: "#0369a1",
                fontWeight: 500,
                marginBottom: 16,
              }}
            >
              {summary}
            </div>
          )}

          {/* Step list */}
          <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
            Steps
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 12 }}>
            {plan.map((step, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "7px 10px",
                  borderRadius: 6,
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  fontSize: 13,
                }}
              >
                <span style={{ color: "#64748b", width: 20, textAlign: "center", flexShrink: 0 }}>
                  {TYPE_ICONS[step.type] ?? "•"}
                </span>
                <span style={{ fontSize: 11, color: "#94a3b8", width: 20, flexShrink: 0 }}>
                  {i + 1}.
                </span>

                {editingIdx === i ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => commitEdit(i)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitEdit(i);
                      if (e.key === "Escape") setEditingIdx(null);
                    }}
                    style={{
                      flex: 1,
                      fontSize: 13,
                      padding: "2px 6px",
                      borderRadius: 4,
                      border: "1px solid #3b82f6",
                      outline: "none",
                    }}
                  />
                ) : (
                  <span style={{ flex: 1, color: "#334155" }}>
                    {(step as Record<string, unknown>).reason as string || step.description || (step as Record<string, unknown>).action as string || step.type}
                  </span>
                )}

                {step.value && editingIdx !== i && (
                  <span style={{ fontSize: 11, color: "#64748b", fontStyle: "italic", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    "{step.value}"
                  </span>
                )}

                <button
                  onClick={() => { setEditingIdx(i); setEditValue((step as Record<string, unknown>).reason as string || step.description || ""); }}
                  title="Edit step"
                  style={{ background: "none", border: "none", cursor: "pointer", fontSize: 13, color: "#94a3b8", padding: "0 2px" }}
                >
                  ✎
                </button>
                <button
                  onClick={() => removeStep(i)}
                  title="Remove step"
                  style={{ background: "none", border: "none", cursor: "pointer", fontSize: 14, color: "#94a3b8", padding: "0 2px" }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={addStep}
            style={{
              ...btnBase,
              padding: "5px 12px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              color: "#475569",
              fontWeight: 400,
              marginBottom: 16,
            }}
          >
            + Add step
          </button>

          {/* Refine with AI */}
          <div
            style={{
              background: "#f8fafc",
              borderRadius: 8,
              padding: "12px 14px",
              marginBottom: 16,
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 8 }}>
              ✎ Refine with AI
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={refineInput}
                onChange={(e) => setRefineInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && refine()}
                placeholder='e.g. "add a wait after clicking the search bar"'
                style={{
                  flex: 1,
                  fontSize: 13,
                  padding: "7px 10px",
                  borderRadius: 6,
                  border: "1px solid #e2e8f0",
                  outline: "none",
                  fontFamily: "inherit",
                }}
              />
              <button
                onClick={refine}
                disabled={refining || !refineInput.trim() || aiOk === false}
                style={{
                  ...btnBase,
                  padding: "7px 14px",
                  background: refining || !refineInput.trim() ? "#94a3b8" : "#8b5cf6",
                  color: "#fff",
                  cursor: refining || !refineInput.trim() ? "not-allowed" : "pointer",
                }}
              >
                {refining ? "..." : "Refine"}
              </button>
            </div>
          </div>

          {/* Execution result */}
          {execResult && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 7,
                marginBottom: 12,
                fontSize: 13,
                fontWeight: 500,
                background: execResult.ok ? "#d1fae5" : "#fee2e2",
                color: execResult.ok ? "#065f46" : "#991b1b",
                border: `1px solid ${execResult.ok ? "#6ee7b7" : "#fca5a5"}`,
              }}
            >
              {execResult.ok ? `✓ ${execResult.message}` : `✗ ${execResult.message}`}
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              onClick={runNow}
              disabled={executing || !instruction.trim()}
              style={{
                ...btnBase,
                background: executing || !instruction.trim() ? "#94a3b8" : "#3b82f6",
                color: "#fff",
                cursor: executing || !instruction.trim() ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              {executing ? (
                <>
                  <span
                    style={{
                      display: "inline-block",
                      width: 12,
                      height: 12,
                      border: "2px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                      animation: "spin 0.7s linear infinite",
                    }}
                  />
                  {execProgress ?? "Executing..."}
                </>
              ) : "▶ Run Now"}
            </button>
            <button
              onClick={save}
              disabled={saving || plan.length === 0}
              style={{
                ...btnBase,
                background: saving || plan.length === 0 ? "#94a3b8" : "#10b981",
                color: "#fff",
                cursor: saving || plan.length === 0 ? "not-allowed" : "pointer",
              }}
            >
              {saving ? "Saving…" : "💾 Save Automation"}
            </button>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            left: "50%",
            transform: "translateX(-50%)",
            background: "#1e293b",
            color: "#f8fafc",
            padding: "10px 20px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 500,
            zIndex: 20000,
            boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
          }}
        >
          {toast}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
