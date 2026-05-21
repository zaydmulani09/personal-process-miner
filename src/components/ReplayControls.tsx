import { useEffect, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";
import { Step } from "../lib/types";

interface PlanItem {
  step: number;
  type: string;
  description: string;
  will_use_vision: boolean;
}

interface StepResult {
  ok: boolean;
  method: "vision" | "recorded";
  confidence: number | null;
  error: string | null;
}

interface RunResult {
  ok: boolean;
  stepsCompleted: number;
  total: number;
  failedAt?: number;
  observation?: string;
}

interface Props {
  automationId: number;
  steps: Step[];
  onClose: () => void;
  onRunComplete?: () => void;
}

const TYPE_ICONS: Record<string, string> = {
  click: "🖱",
  type: "⌨",
  scroll: "↕",
  keypress: "🔑",
};

function Toggle({
  label,
  checked,
  onChange,
  disabled,
  tooltip,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  tooltip?: string;
}) {
  return (
    <label
      title={tooltip}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: 13,
        color: disabled ? "#94a3b8" : "#0f172a",
        cursor: disabled ? "not-allowed" : "pointer",
        userSelect: "none",
      }}
    >
      <div
        onClick={() => !disabled && onChange(!checked)}
        style={{
          width: 36,
          height: 20,
          borderRadius: 10,
          background: checked && !disabled ? "#3b82f6" : "#e2e8f0",
          position: "relative",
          transition: "background 0.2s",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 3,
            left: checked ? 18 : 3,
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: "#fff",
            transition: "left 0.2s",
            boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
          }}
        />
      </div>
      {label}
      {disabled && tooltip && (
        <span style={{ fontSize: 11, color: "#94a3b8" }}>({tooltip})</span>
      )}
    </label>
  );
}

export default function ReplayControls({ automationId, steps: initialSteps, onClose, onRunComplete }: Props) {
  const [steps, setSteps] = useState<Step[]>(initialSteps);
  const [plan, setPlan] = useState<PlanItem[]>([]);
  const [stepResults, setStepResults] = useState<(StepResult | null)[]>([]);
  const [useVision, setUseVision] = useState(true);
  const [verifyEach, setVerifyEach] = useState(false);
  const [visionAvailable, setVisionAvailable] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [screenshotB64, setScreenshotB64] = useState<string | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(true);

  useEffect(() => {
    const init = async () => {
      try {
        // check vision availability
        const vs = await sendToSidecar({ type: "check_vision" }) as { available: boolean };
        setVisionAvailable(vs.available);
        if (!vs.available) setUseVision(false);

        // fetch steps if not provided
        let resolvedSteps = initialSteps;
        if (!resolvedSteps || resolvedSteps.length === 0) {
          const resp = await sendToSidecar({ type: "get_automation_steps", automation_id: automationId }) as { steps: Step[] };
          resolvedSteps = resp.steps ?? [];
          setSteps(resolvedSteps);
        }

        // get plan
        const planResp = await sendToSidecar({ type: "describe_replay_plan", steps: resolvedSteps }) as { plan: PlanItem[] };
        setPlan(planResp.plan ?? []);
        setStepResults(new Array(resolvedSteps.length).fill(null));
      } catch (e) {
        // keep empty plan
      } finally {
        setLoadingPlan(false);
      }
    };
    init();
  }, [automationId]);

  const handleRun = async () => {
    setRunning(true);
    setRunResult(null);
    setScreenshotB64(null);

    if (!useVision) {
      // fallback: direct script execution via run_automation
      try {
        const resp = await sendToSidecar({ type: "run_automation", automation_id: automationId }) as { status: string; stderr: string };
        const ok = resp.status === "success";
        setRunResult({ ok, stepsCompleted: ok ? steps.length : 0, total: steps.length, observation: resp.stderr || undefined });
        if (onRunComplete) onRunComplete();
      } catch (e: unknown) {
        setRunResult({ ok: false, stepsCompleted: 0, total: steps.length, observation: e instanceof Error ? e.message : String(e) });
      } finally {
        setRunning(false);
      }
      return;
    }

    // vision-guided: step-by-step with real-time updates
    const results: (StepResult | null)[] = new Array(steps.length).fill(null);
    setStepResults([...results]);

    for (let i = 0; i < steps.length; i++) {
      try {
        const resp = await sendToSidecar({
          type: "replay_step",
          step: steps[i],
          use_vision: useVision,
        }) as { result: StepResult };
        results[i] = resp.result;
        setStepResults([...results]);

        if (!resp.result.ok) {
          setRunResult({ ok: false, stepsCompleted: i, total: steps.length, failedAt: i, observation: resp.result.error ?? undefined });
          setRunning(false);
          if (onRunComplete) onRunComplete();
          return;
        }

        if (verifyEach && visionAvailable) {
          const vResp = await sendToSidecar({
            type: "verify_action",
            expected_state: `completed: ${steps[i].description || `step ${i + 1}`}`,
          }) as { result: { success: boolean; confidence: number; observation: string } };
          const v = vResp.result;
          if (v.confidence < 0.5) {
            setRunResult({ ok: false, stepsCompleted: i, total: steps.length, failedAt: i, observation: v.observation });
            setRunning(false);
            if (onRunComplete) onRunComplete();
            return;
          }
        }
      } catch (e: unknown) {
        results[i] = { ok: false, method: "recorded", confidence: null, error: e instanceof Error ? e.message : String(e) };
        setStepResults([...results]);
        setRunResult({ ok: false, stepsCompleted: i, total: steps.length, failedAt: i, observation: results[i]?.error ?? undefined });
        setRunning(false);
        if (onRunComplete) onRunComplete();
        return;
      }
    }

    setRunResult({ ok: true, stepsCompleted: steps.length, total: steps.length });
    setRunning(false);
    if (onRunComplete) onRunComplete();
  };

  const viewScreenshot = async () => {
    try {
      const resp = await sendToSidecar({ type: "take_screenshot" }) as { data: string };
      setScreenshotB64(resp.data);
    } catch {
      // ignore
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 10000,
        fontFamily: "system-ui, sans-serif",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          width: 480,
          maxHeight: "85vh",
          overflowY: "auto",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 20px",
            borderBottom: "1px solid #e2e8f0",
            position: "sticky",
            top: 0,
            background: "#fff",
            zIndex: 1,
          }}
        >
          <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>▶ Smart Replay</span>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "#94a3b8", padding: 0 }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: "16px 20px" }}>
          {/* Plan */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
              Replay Plan
            </div>

            {loadingPlan ? (
              <div style={{ color: "#94a3b8", fontSize: 13 }}>Loading plan…</div>
            ) : plan.length === 0 ? (
              <div style={{ color: "#94a3b8", fontSize: 13 }}>No executable steps found in this automation.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {plan.map((item, i) => {
                  const res = stepResults[i];
                  let statusIcon = "";
                  if (res !== null) statusIcon = res.ok ? "✅" : "❌";
                  else if (running && i === stepResults.findIndex(r => r === null)) statusIcon = "⏳";

                  return (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 10px",
                        borderRadius: 6,
                        background: res?.ok === false ? "#fef2f2" : res?.ok === true ? "#f0fdf4" : "#f8fafc",
                        fontSize: 13,
                        color: "#334155",
                      }}
                    >
                      <span style={{ color: "#64748b", width: 18, textAlign: "center" }}>{TYPE_ICONS[item.type] ?? "•"}</span>
                      <span style={{ flex: 1 }}>{item.description}</span>
                      {item.will_use_vision && (
                        <span title="AI will locate this element" style={{ fontSize: 11, color: "#3b82f6" }}>👁</span>
                      )}
                      {res && (
                        <span style={{ fontSize: 11, color: "#64748b" }}>
                          {res.method === "vision" ? `vision ${Math.round((res.confidence ?? 0) * 100)}%` : "recorded"}
                        </span>
                      )}
                      <span>{statusIcon}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Options */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 10,
              padding: "12px 14px",
              background: "#f8fafc",
              borderRadius: 8,
              marginBottom: 16,
            }}
          >
            <Toggle
              label="Use AI vision to find elements"
              checked={useVision}
              onChange={setUseVision}
              disabled={!visionAvailable}
              tooltip={!visionAvailable ? "Vision not configured" : undefined}
            />
            <Toggle
              label="Verify each step"
              checked={verifyEach}
              onChange={setVerifyEach}
              disabled={!visionAvailable}
              tooltip={!visionAvailable ? "Requires vision" : undefined}
            />
          </div>

          {/* Run button */}
          <button
            onClick={handleRun}
            disabled={running || plan.length === 0}
            style={{
              width: "100%",
              padding: "10px 0",
              borderRadius: 8,
              border: "none",
              background: running || plan.length === 0 ? "#94a3b8" : "#3b82f6",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
              cursor: running || plan.length === 0 ? "not-allowed" : "pointer",
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            {running ? (
              <>
                <span
                  style={{
                    display: "inline-block",
                    width: 14,
                    height: 14,
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderTopColor: "#fff",
                    borderRadius: "50%",
                    animation: "spin 0.7s linear infinite",
                  }}
                />
                Running…
              </>
            ) : "▶ Run Automation"}
          </button>

          {/* Result banner */}
          {runResult && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: runResult.ok ? "#f0fdf4" : "#fef2f2",
                border: `1px solid ${runResult.ok ? "#bbf7d0" : "#fecaca"}`,
                color: runResult.ok ? "#15803d" : "#dc2626",
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              <div>
                {runResult.ok
                  ? `✓ Completed ${runResult.stepsCompleted}/${runResult.total} steps`
                  : `✗ Failed at step ${(runResult.failedAt ?? 0) + 1}${runResult.observation ? `: ${runResult.observation}` : ""}`}
              </div>
              {!runResult.ok && (
                <button
                  onClick={viewScreenshot}
                  style={{
                    marginTop: 6,
                    padding: "4px 10px",
                    fontSize: 12,
                    borderRadius: 5,
                    border: "1px solid #fca5a5",
                    background: "#fff",
                    color: "#dc2626",
                    cursor: "pointer",
                  }}
                >
                  View screenshot
                </button>
              )}
              {screenshotB64 && (
                <img
                  src={`data:image/png;base64,${screenshotB64}`}
                  alt="Current screen"
                  style={{ width: "100%", marginTop: 8, borderRadius: 6, border: "1px solid #fecaca" }}
                />
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
