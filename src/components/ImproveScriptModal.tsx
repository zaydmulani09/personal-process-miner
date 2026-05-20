import { useEffect, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";
import { Automation } from "../lib/types";

interface Props {
  automation: Automation;
  onImproved: (updated: Automation) => void;
  onClose: () => void;
}

type Status =
  | "checking"
  | "unavailable"
  | "ready"
  | "improving"
  | "done"
  | "error";

export default function ImproveScriptModal({
  automation,
  onImproved,
  onClose,
}: Props) {
  const [status, setStatus] = useState<Status>("checking");
  const [backend, setBackend] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string>("");
  const [improvedScript, setImprovedScript] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = (await sendToSidecar({ type: "check_llm" })) as {
          available: boolean;
          backend: string | null;
        };
        setBackend(resp.backend);
        setStatus(resp.available ? "ready" : "unavailable");
      } catch (e) {
        setError(String(e));
        setStatus("error");
      }
    })();
  }, []);

  const handleImprove = async () => {
    setStatus("improving");
    setError(null);
    try {
      const resp = (await sendToSidecar({
        type: "improve_automation",
        automation_id: automation.id,
      })) as {
        ok: boolean;
        automation_id: number;
        explanation: string;
        improved_script?: string;
        error?: string;
      };
      if (resp.ok) {
        setExplanation(resp.explanation);
        setImprovedScript(resp.improved_script ?? "");
        setStatus("done");
      } else {
        setError(resp.error ?? "Improvement failed");
        setStatus("error");
      }
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  };

  const handleUseImproved = () => {
    onImproved({ ...automation, script_body: improvedScript });
  };

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
        if (e.target === e.currentTarget && status !== "improving") onClose();
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
          ✨ Improve Script with AI
        </h2>

        {/* Checking */}
        {status === "checking" && (
          <div className="skeleton" style={{ height: 80, borderRadius: 6 }} />
        )}

        {/* Unavailable — setup instructions */}
        {status === "unavailable" && (
          <div
            style={{
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              padding: "16px 20px",
              marginBottom: 16,
              fontSize: 13,
              color: "#334155",
              lineHeight: 1.7,
            }}
          >
            <p style={{ margin: "0 0 10px", fontWeight: 600, color: "#0f172a" }}>
              AI improvement is optional.
            </p>
            <p style={{ margin: "0 0 6px" }}>To enable it:</p>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>
                <strong>Local (free):</strong> Install{" "}
                <a
                  href="https://ollama.com"
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: "#3b82f6" }}
                >
                  Ollama
                </a>
                , run <code>ollama pull llama3</code>, set{" "}
                <code>PPM_LLM_BACKEND=ollama</code>
              </li>
              <li style={{ marginTop: 4 }}>
                <strong>Cloud:</strong> Set <code>PPM_LLM_BACKEND=claude</code>{" "}
                and <code>PPM_CLAUDE_API_KEY=your_key</code>
              </li>
            </ul>
          </div>
        )}

        {/* Ready — show current script + button */}
        {status === "ready" && (
          <>
            <div
              style={{
                fontSize: 12,
                color: "#64748b",
                marginBottom: 6,
              }}
            >
              Current script — {automation.script_type} · backend:{" "}
              <strong>{backend}</strong>
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
                fontFamily:
                  "'Cascadia Code', 'Fira Mono', 'Consolas', monospace",
              }}
            >
              {automation.script_body || "# (no script body)"}
            </pre>
          </>
        )}

        {/* Improving — spinner */}
        {status === "improving" && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              padding: "32px 0",
              color: "#64748b",
              fontSize: 14,
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                border: "3px solid #e2e8f0",
                borderTopColor: "#3b82f6",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            Analyzing your script…
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Done — explanation callout + improved script */}
        {status === "done" && (
          <>
            {explanation && (
              <div
                style={{
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  borderRadius: 8,
                  padding: "12px 16px",
                  marginBottom: 12,
                  fontSize: 13,
                  color: "#1e40af",
                  lineHeight: 1.6,
                }}
              >
                <strong style={{ display: "block", marginBottom: 4 }}>
                  What this script does:
                </strong>
                {explanation}
              </div>
            )}
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>
              Improved script
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
                fontFamily:
                  "'Cascadia Code', 'Fira Mono', 'Consolas', monospace",
              }}
            >
              {improvedScript}
            </pre>
          </>
        )}

        {/* Error */}
        {status === "error" && (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#dc2626",
              fontSize: 13,
              padding: "24px 0",
            }}
          >
            {error}
          </div>
        )}

        {/* Buttons */}
        <div style={{ display: "flex", gap: 8, flexShrink: 0, flexWrap: "wrap" }}>
          {status === "ready" && (
            <button
              onClick={handleImprove}
              style={{
                padding: "8px 16px",
                fontSize: 13,
                borderRadius: 6,
                border: "none",
                background: "#7c3aed",
                color: "#fff",
                cursor: "pointer",
                boxShadow: "none",
              }}
            >
              Improve with AI
            </button>
          )}

          {status === "done" && (
            <>
              <button
                onClick={handleUseImproved}
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
                Use Improved Version
              </button>
              <button
                onClick={onClose}
                style={{
                  padding: "8px 16px",
                  fontSize: 13,
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#f8fafc",
                  cursor: "pointer",
                  boxShadow: "none",
                }}
              >
                Keep Original
              </button>
            </>
          )}

          {status === "error" && (
            <button
              onClick={() => { setError(null); setStatus("ready"); }}
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
              Try Again
            </button>
          )}

          {status !== "improving" && (
            <button
              onClick={onClose}
              style={{
                padding: "8px 16px",
                fontSize: 13,
                borderRadius: 6,
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                cursor: "pointer",
                marginLeft:
                  status === "done" || status === "error" ? 0 : "auto",
                boxShadow: "none",
              }}
            >
              {status === "unavailable" ? "Close" : status === "done" ? "Cancel" : "Close"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
