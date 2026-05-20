import { useState } from "react";
import { sendToSidecar } from "../lib/sidecar";

interface Props {
  onAnalysisComplete: () => void;
}

export default function CaptureControls({ onAnalysisComplete }: Props) {
  const [capturing, setCapturing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [lastAnalyzed, setLastAnalyzed] = useState<string | null>(null);

  const toggleCapture = async () => {
    try {
      if (capturing) {
        await sendToSidecar({ type: "stop_capture" });
        setCapturing(false);
      } else {
        await sendToSidecar({ type: "start_capture" });
        setCapturing(true);
      }
    } catch (e) {
      console.error("Capture toggle failed:", e);
    }
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      await sendToSidecar({ type: "run_segmentation" });
      await sendToSidecar({ type: "run_fingerprinting" });
      await sendToSidecar({ type: "get_summary_stats" });
      setLastAnalyzed(new Date().toLocaleTimeString());
      onAnalysisComplete();
    } catch (e) {
      console.error("Analysis failed:", e);
    } finally {
      setAnalyzing(false);
    }
  };

  const analyzeDisabled = analyzing || capturing;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "12px 16px",
        background: "var(--color-background-secondary)",
        borderRadius: 8,
        marginBottom: 20,
        flexWrap: "wrap",
      }}
    >
      <button
        onClick={toggleCapture}
        style={{
          padding: "7px 16px",
          fontSize: 13,
          borderRadius: 6,
          border: "none",
          background: capturing ? "#dc2626" : "#3b82f6",
          color: "#fff",
          cursor: "pointer",
          fontWeight: 500,
          boxShadow: "none",
        }}
      >
        {capturing ? "Stop Capture" : "Start Capture"}
      </button>

      <button
        onClick={runAnalysis}
        disabled={analyzeDisabled}
        style={{
          padding: "7px 16px",
          fontSize: 13,
          borderRadius: 6,
          border: "1px solid #cbd5e1",
          background: analyzeDisabled ? "#f1f5f9" : "#fff",
          color: analyzeDisabled ? "#94a3b8" : "#0f172a",
          cursor: analyzeDisabled ? "not-allowed" : "pointer",
          fontWeight: 500,
          boxShadow: "none",
        }}
      >
        {analyzing ? "Analyzing…" : "Analyze Now"}
      </button>

      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
        <span
          style={{
            color: capturing ? "#16a34a" : "#94a3b8",
            fontSize: 16,
            lineHeight: 1,
          }}
        >
          {capturing ? "●" : "○"}
        </span>
        <span style={{ color: "#64748b" }}>{capturing ? "Capturing" : "Idle"}</span>
      </div>

      {lastAnalyzed && (
        <span style={{ fontSize: 12, color: "#94a3b8", marginLeft: "auto" }}>
          Last analyzed: {lastAnalyzed}
        </span>
      )}
    </div>
  );
}
