import { useEffect, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";

interface Props {
  workflowId: number;
  workflowName: string;
  onSaved: (automationId: number, scriptPath: string) => void;
  onClose: () => void;
}

export default function ScriptPreviewModal({
  workflowId,
  workflowName,
  onSaved,
  onClose,
}: Props) {
  const [script, setScript] = useState<string | null>(null);
  const [stepCount, setStepCount] = useState(0);
  const [scriptName, setScriptName] = useState(`${workflowName} playwright`);
  const [status, setStatus] = useState<"loading" | "ready" | "saving" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = (await sendToSidecar({
          type: "preview_playwright",
          workflow_id: workflowId,
        })) as { type: string; script: string; step_count: number };
        if (cancelled) return;
        setScript(resp.script);
        setStepCount(resp.step_count);
        setStatus("ready");
      } catch (e) {
        if (cancelled) return;
        setError(String(e));
        setStatus("error");
      }
    })();
    return () => { cancelled = true; };
  }, [workflowId]);

  const handleSave = async () => {
    if (!scriptName.trim()) {
      setError("Script name is required.");
      return;
    }
    setStatus("saving");
    setError(null);
    try {
      const resp = (await sendToSidecar({
        type: "generate_playwright",
        workflow_id: workflowId,
        name: scriptName.trim(),
      })) as {
        type: string;
        automation_id: number;
        script_path: string;
        step_count: number;
      };
      onSaved(resp.automation_id, resp.script_path);
    } catch (e) {
      setError(String(e));
      setStatus("ready");
    }
  };

  const isSaving = status === "saving";
  const isLoading = status === "loading";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSaving) onClose();
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 10,
          padding: 24,
          width: 640,
          maxWidth: "92vw",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
        }}
      >
        <h2 style={{ margin: "0 0 16px", fontSize: 17, fontWeight: 600 }}>
          Playwright Script Preview
        </h2>

        <input
          value={scriptName}
          onChange={(e) => setScriptName(e.target.value)}
          disabled={isSaving || isLoading}
          placeholder="Script name…"
          style={{
            width: "100%",
            padding: "8px 12px",
            fontSize: 14,
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            marginBottom: 12,
            boxSizing: "border-box",
          }}
        />

        {isLoading && (
          <div
            className="skeleton"
            style={{ height: 280, borderRadius: 6, marginBottom: 12 }}
          />
        )}

        {status !== "loading" && script !== null && (
          <>
            <div
              style={{
                fontSize: 12,
                color: "#64748b",
                marginBottom: 6,
              }}
            >
              {stepCount} browser step{stepCount !== 1 ? "s" : ""} detected
            </div>
            <pre
              style={{
                flex: 1,
                overflowY: "auto",
                background: "#0f172a",
                color: "#e2e8f0",
                padding: "14px 16px",
                borderRadius: 6,
                fontSize: 12,
                lineHeight: 1.6,
                margin: "0 0 16px",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontFamily: "'Cascadia Code', 'Fira Mono', 'Consolas', monospace",
              }}
            >
              {script}
            </pre>
          </>
        )}

        {status === "error" && !script && (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#dc2626",
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            Failed to generate preview: {error}
          </div>
        )}

        {error && script && (
          <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          {status === "ready" && (
            <button
              onClick={handleSave}
              style={{
                padding: "8px 16px",
                fontSize: 13,
                borderRadius: 6,
                border: "none",
                background: "#3b82f6",
                color: "#fff",
                cursor: "pointer",
                boxShadow: "none",
              }}
            >
              Save Script
            </button>
          )}
          {isSaving && (
            <button
              disabled
              style={{
                padding: "8px 16px",
                fontSize: 13,
                borderRadius: 6,
                border: "none",
                background: "#94a3b8",
                color: "#fff",
                cursor: "not-allowed",
                boxShadow: "none",
              }}
            >
              Saving…
            </button>
          )}
          <button
            onClick={onClose}
            disabled={isSaving}
            style={{
              padding: "8px 16px",
              fontSize: 13,
              borderRadius: 6,
              border: "1px solid #cbd5e1",
              background: "#f8fafc",
              cursor: isSaving ? "not-allowed" : "pointer",
              boxShadow: "none",
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
