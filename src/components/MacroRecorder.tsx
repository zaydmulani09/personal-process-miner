import { useEffect, useRef, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";
import { Automation } from "../lib/types";

interface Props {
  workflowId: number | null;
  workflowName: string;
  onSaved: (automation: Automation) => void;
  onClose: () => void;
}

export default function MacroRecorder({
  workflowId,
  workflowName,
  onSaved,
  onClose,
}: Props) {
  const [status, setStatus] = useState<
    "idle" | "recording" | "stopping" | "saving"
  >("idle");
  const [hasStopped, setHasStopped] = useState(false);
  const [eventCount, setEventCount] = useState(0);
  const [macroName, setMacroName] = useState(`${workflowName} macro`);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (status === "recording") {
      pollRef.current = setInterval(async () => {
        try {
          const resp = (await sendToSidecar({ type: "get_recording_status" })) as {
            event_count: number;
          };
          setEventCount(resp.event_count);
        } catch {
          // ignore poll errors
        }
      }, 1000);
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [status]);

  const handleStart = async () => {
    setError(null);
    setHasStopped(false);
    setEventCount(0);
    try {
      const resp = (await sendToSidecar({
        type: "start_recording",
        workflow_id: workflowId,
      })) as { ok: boolean; error?: string };
      if (resp.ok) {
        setStatus("recording");
      } else {
        setError(resp.error ?? "Failed to start recording");
      }
    } catch (e) {
      setError(String(e));
    }
  };

  const handleStop = async () => {
    setStatus("stopping");
    try {
      const resp = (await sendToSidecar({ type: "stop_recording" })) as {
        ok: boolean;
        event_count: number;
        error?: string;
      };
      if (resp.ok) {
        setEventCount(resp.event_count);
        setHasStopped(true);
        setStatus("idle");
      } else {
        setError(resp.error ?? "Failed to stop recording");
        setStatus("recording");
      }
    } catch (e) {
      setError(String(e));
      setStatus("idle");
    }
  };

  const handleSave = async () => {
    if (!macroName.trim()) {
      setError("Macro name is required.");
      return;
    }
    setStatus("saving");
    setError(null);
    try {
      const resp = (await sendToSidecar({
        type: "save_macro",
        name: macroName.trim(),
        workflow_id: workflowId,
      })) as {
        ok: boolean;
        automation_id: number;
        script_path: string;
        event_count: number;
        error?: string;
      };
      if (resp.ok) {
        const automation: Automation = {
          id: resp.automation_id,
          workflow_id: workflowId,
          name: macroName.trim(),
          script_type: "pyautogui",
          script_body: "",
          last_run_at: null,
          run_count: 0,
          last_run_status: null,
          created_at: new Date().toISOString(),
        };
        onSaved(automation);
      } else {
        setError(resp.error ?? "Failed to save macro");
        setStatus("idle");
      }
    } catch (e) {
      setError(String(e));
      setStatus("idle");
    }
  };

  const handleDiscard = () => {
    setHasStopped(false);
    setEventCount(0);
    setError(null);
    onClose();
  };

  const isRecording = status === "recording";
  const isStopping = status === "stopping";
  const isSaving = status === "saving";
  const showSaveDiscard = status === "idle" && hasStopped;

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
        if (e.target === e.currentTarget && !isRecording) onClose();
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 10,
          padding: 24,
          width: 440,
          maxWidth: "90vw",
          boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
        }}
      >
        <h2 style={{ margin: "0 0 16px", fontSize: 17, fontWeight: 600 }}>
          Record Macro
        </h2>

        <input
          value={macroName}
          onChange={(e) => setMacroName(e.target.value)}
          disabled={isRecording || isStopping || isSaving}
          placeholder="Macro name…"
          style={{
            width: "100%",
            padding: "8px 12px",
            fontSize: 14,
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            marginBottom: 16,
            boxSizing: "border-box",
            background: isRecording ? "#f8fafc" : "#fff",
          }}
        />

        {isRecording && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 14px",
              borderRadius: 6,
              background: "#fef2f2",
              marginBottom: 16,
            }}
          >
            <span
              style={{
                color: "#dc2626",
                fontSize: 16,
                animation: "pulse 1s ease-in-out infinite",
              }}
            >
              ●
            </span>
            <span style={{ fontSize: 13, color: "#dc2626", fontWeight: 600 }}>
              Recording
            </span>
            <span style={{ fontSize: 13, color: "#64748b", marginLeft: "auto" }}>
              {eventCount} event{eventCount !== 1 ? "s" : ""}
            </span>
          </div>
        )}

        {showSaveDiscard && (
          <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 16px" }}>
            Recorded {eventCount} event{eventCount !== 1 ? "s" : ""}. Ready to
            save.
          </p>
        )}

        {error && (
          <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {!isRecording && !isStopping && !showSaveDiscard && !isSaving && (
            <button
              onClick={handleStart}
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
              Start Recording
            </button>
          )}

          {(isRecording || isStopping) && (
            <button
              onClick={handleStop}
              disabled={isStopping}
              style={{
                padding: "8px 16px",
                fontSize: 13,
                borderRadius: 6,
                border: "none",
                background: isStopping ? "#94a3b8" : "#dc2626",
                color: "#fff",
                cursor: isStopping ? "not-allowed" : "pointer",
                boxShadow: "none",
              }}
            >
              {isStopping ? "Stopping…" : "Stop Recording"}
            </button>
          )}

          {showSaveDiscard && (
            <>
              <button
                onClick={handleSave}
                disabled={isSaving}
                style={{
                  padding: "8px 16px",
                  fontSize: 13,
                  borderRadius: 6,
                  border: "none",
                  background: isSaving ? "#94a3b8" : "#3b82f6",
                  color: "#fff",
                  cursor: isSaving ? "not-allowed" : "pointer",
                  boxShadow: "none",
                }}
              >
                {isSaving ? "Saving…" : "Save Macro"}
              </button>
              <button
                onClick={handleDiscard}
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
                Discard
              </button>
            </>
          )}

          {!isRecording && !isStopping && !isSaving && (
            <button
              onClick={onClose}
              style={{
                padding: "8px 16px",
                fontSize: 13,
                borderRadius: 6,
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                cursor: "pointer",
                marginLeft: showSaveDiscard ? 0 : "auto",
                boxShadow: "none",
              }}
            >
              {showSaveDiscard ? "Cancel" : "Close"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
