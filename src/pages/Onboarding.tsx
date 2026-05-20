import { useEffect, useRef, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { sendToSidecar } from "../lib/sidecar";

interface Props {
  onComplete: () => void;
}

const TOTAL_STEPS = 5; // steps 0-4

const dotBar = (current: number) => (
  <div style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 32 }}>
    {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
      <div
        key={i}
        style={{
          width: i === current ? 24 : 8,
          height: 8,
          borderRadius: 4,
          background: i === current ? "#3b82f6" : i < current ? "#bfdbfe" : "#e2e8f0",
          transition: "all 0.2s",
        }}
      />
    ))}
  </div>
);

const wrap: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#f8fafc",
  fontFamily: "system-ui, sans-serif",
};

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 16,
  padding: "48px 56px",
  maxWidth: 560,
  width: "100%",
  boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
};

const h1Style: React.CSSProperties = {
  fontSize: 28,
  fontWeight: 700,
  color: "#0f172a",
  margin: "0 0 8px",
  textAlign: "center",
};

const subStyle: React.CSSProperties = {
  fontSize: 15,
  color: "#64748b",
  textAlign: "center",
  margin: "0 0 32px",
};

const btnPrimary: React.CSSProperties = {
  width: "100%",
  padding: "12px 0",
  fontSize: 15,
  fontWeight: 600,
  borderRadius: 8,
  border: "none",
  background: "#3b82f6",
  color: "#fff",
  cursor: "pointer",
  marginTop: 24,
};

const btnDisabled: React.CSSProperties = {
  ...btnPrimary,
  background: "#cbd5e1",
  cursor: "not-allowed",
};

// ── Step 0 — Welcome ─────────────────────────────────────────────────────────

function Step0({ onNext }: { onNext: () => void }) {
  return (
    <>
      {dotBar(0)}
      <h1 style={h1Style}>Personal Process Miner</h1>
      <p style={subStyle}>Learn your boring computer habits. Get free shortcuts.</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 8 }}>
        {[
          "🔒 Everything stays on your machine — nothing sent to the cloud",
          "👁 Watches which apps you use and when — not what you type",
          "⚡ Detects repeated workflows and offers one-click automations",
        ].map((txt) => (
          <div
            key={txt}
            style={{
              padding: "12px 16px",
              background: "#f8fafc",
              borderRadius: 8,
              fontSize: 14,
              color: "#334155",
              border: "1px solid #e2e8f0",
            }}
          >
            {txt}
          </div>
        ))}
      </div>
      <button style={btnPrimary} onClick={onNext}>
        Get Started →
      </button>
    </>
  );
}

// ── Step 1 — Permission check ─────────────────────────────────────────────────

function Step1({ onNext }: { onNext: () => void }) {
  const [status, setStatus] = useState<"loading" | "ok" | "denied">("loading");
  const [platform, setPlatform] = useState("");
  const advanced = useRef(false);

  const check = async () => {
    setStatus("loading");
    try {
      const resp = await sendToSidecar({ type: "check_accessibility" }) as {
        granted: boolean;
        platform: string;
      };
      setPlatform(resp.platform);
      if (resp.platform !== "darwin" || resp.granted) {
        setStatus("ok");
        if (!advanced.current) {
          advanced.current = true;
          setTimeout(onNext, 800);
        }
      } else {
        setStatus("denied");
      }
    } catch {
      setStatus("denied");
    }
  };

  useEffect(() => { check(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openSysPrefs = () => {
    openUrl("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility").catch(() => {});
  };

  return (
    <>
      {dotBar(1)}
      {status === "loading" && (
        <p style={{ textAlign: "center", color: "#64748b", fontSize: 15 }}>Checking permissions…</p>
      )}
      {status === "ok" && (
        <p style={{ textAlign: "center", fontSize: 22, color: "#16a34a", fontWeight: 700 }}>
          ✓ Ready
        </p>
      )}
      {status === "denied" && platform === "darwin" && (
        <>
          <h1 style={h1Style}>One permission needed</h1>
          <p style={subStyle}>macOS needs one permission to watch your apps</p>
          <div
            style={{
              background: "#fffbeb",
              border: "1px solid #fde68a",
              borderRadius: 8,
              padding: "14px 16px",
              fontSize: 14,
              color: "#78350f",
              marginBottom: 16,
            }}
          >
            Open <strong>System Settings</strong> → Privacy & Security → Accessibility → enable{" "}
            <strong>Personal Process Miner</strong>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={openSysPrefs}
              style={{
                flex: 1,
                padding: "10px 0",
                fontSize: 14,
                borderRadius: 8,
                border: "1px solid #e2e8f0",
                background: "#fff",
                cursor: "pointer",
              }}
            >
              Open System Settings
            </button>
            <button
              onClick={check}
              style={{
                flex: 1,
                padding: "10px 0",
                fontSize: 14,
                borderRadius: 8,
                border: "none",
                background: "#3b82f6",
                color: "#fff",
                cursor: "pointer",
              }}
            >
              Check Again
            </button>
          </div>
        </>
      )}
    </>
  );
}

// ── Step 2 — What we record ───────────────────────────────────────────────────

function Step2({ onNext }: { onNext: () => void }) {
  const [checked, setChecked] = useState(false);

  return (
    <>
      {dotBar(2)}
      <h1 style={{ ...h1Style, fontSize: 22 }}>Here's exactly what gets recorded</h1>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          margin: "24px 0",
        }}
      >
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: 8,
            padding: "14px 16px",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13, color: "#15803d", marginBottom: 8 }}>
            ✅ We record
          </div>
          {["Which apps are active", "When you switch apps", "Mouse clicks", "Window titles"].map(
            (t) => (
              <div key={t} style={{ fontSize: 13, color: "#166534", marginBottom: 4 }}>
                • {t}
              </div>
            )
          )}
        </div>
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            padding: "14px 16px",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13, color: "#dc2626", marginBottom: 8 }}>
            ❌ We never record
          </div>
          {["What you type", "Passwords", "Screen contents", "Blocked app activity"].map((t) => (
            <div key={t} style={{ fontSize: 13, color: "#991b1b", marginBottom: 4 }}>
              • {t}
            </div>
          ))}
        </div>
      </div>
      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          cursor: "pointer",
          fontSize: 14,
          color: "#334155",
          marginBottom: 4,
        }}
      >
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
        />
        I understand — let's go
      </label>
      <button
        style={checked ? btnPrimary : btnDisabled}
        onClick={checked ? onNext : undefined}
        disabled={!checked}
      >
        Continue →
      </button>
    </>
  );
}

// ── Step 3 — Demo recording ───────────────────────────────────────────────────

function Step3({ onNext }: { onNext: () => void }) {
  const [phase, setPhase] = useState<"idle" | "counting" | "done">("idle");
  const [countdown, setCountdown] = useState(60);
  const [patternCount, setPatternCount] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startDemo = async () => {
    setPhase("counting");
    setCountdown(60);
    try {
      await sendToSidecar({ type: "start_capture" });
    } catch { /* capture error non-fatal */ }

    timerRef.current = setInterval(async () => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current!);
          finishDemo();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const finishDemo = async () => {
    try {
      await sendToSidecar({ type: "stop_capture" });
      await sendToSidecar({ type: "run_segmentation" });
      const fpResp = await sendToSidecar({ type: "run_fingerprinting" }) as {
        pattern_count: number;
      };
      setPatternCount(fpResp.pattern_count ?? 0);
    } catch {
      setPatternCount(0);
    }
    setPhase("done");
  };

  const skip = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setPhase("done");
    setPatternCount(null);
  };

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  return (
    <>
      {dotBar(3)}
      <h1 style={{ ...h1Style, fontSize: 22 }}>Let's find your first workflow</h1>
      <p style={subStyle}>Use your computer normally for 60 seconds. We'll watch for patterns.</p>

      {phase === "idle" && (
        <button style={btnPrimary} onClick={startDemo}>
          Start 60-second demo
        </button>
      )}

      {phase === "counting" && (
        <div style={{ textAlign: "center", margin: "16px 0" }}>
          <div
            style={{
              fontSize: 64,
              fontWeight: 700,
              color: countdown <= 10 ? "#dc2626" : "#3b82f6",
              lineHeight: 1,
            }}
          >
            {countdown}
          </div>
          <div style={{ fontSize: 14, color: "#64748b", marginTop: 8 }}>
            seconds remaining — use your apps normally
          </div>
        </div>
      )}

      {phase === "done" && (
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: 8,
            padding: "16px 20px",
            textAlign: "center",
            margin: "16px 0",
          }}
        >
          {patternCount === null ? (
            <span style={{ fontSize: 15, color: "#15803d", fontWeight: 600 }}>
              ✓ Skipped
            </span>
          ) : patternCount > 0 ? (
            <span style={{ fontSize: 15, color: "#15803d", fontWeight: 600 }}>
              ✓ Done! Found {patternCount} pattern{patternCount === 1 ? "" : "s"}
            </span>
          ) : (
            <span style={{ fontSize: 14, color: "#15803d" }}>
              ✓ Done! Keep using the app — patterns appear after repeated workflows
            </span>
          )}
        </div>
      )}

      {phase === "idle" && (
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <button
            onClick={skip}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              color: "#94a3b8",
              textDecoration: "underline",
            }}
          >
            Skip demo
          </button>
        </div>
      )}

      {phase === "counting" && (
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <button
            onClick={skip}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              color: "#94a3b8",
              textDecoration: "underline",
            }}
          >
            Skip demo
          </button>
        </div>
      )}

      {phase === "done" && (
        <button style={btnPrimary} onClick={onNext}>
          Continue →
        </button>
      )}
    </>
  );
}

// ── Step 4 — Done ─────────────────────────────────────────────────────────────

function Step4({ onComplete }: { onComplete: () => void }) {
  const handleDone = async () => {
    try {
      await sendToSidecar({ type: "set_onboarding_complete" });
    } catch { /* non-fatal */ }
    onComplete();
  };

  return (
    <>
      {dotBar(4)}
      <h1 style={h1Style}>You're all set!</h1>
      <p style={{ ...subStyle, marginBottom: 8 }}>
        Personal Process Miner is running in the background. Come back after your normal work
        session to see your detected patterns.
      </p>
      <button style={btnPrimary} onClick={handleDone}>
        Open Dashboard →
      </button>
    </>
  );
}

// ── Wizard shell ──────────────────────────────────────────────────────────────

export default function Onboarding({ onComplete }: Props) {
  const [step, setStep] = useState(0);

  const advance = async () => {
    const next = step + 1;
    try {
      await sendToSidecar({ type: "set_onboarding_step", step: next });
    } catch { /* non-fatal */ }
    setStep(next);
  };

  return (
    <div style={wrap}>
      <div style={card}>
        {step === 0 && <Step0 onNext={advance} />}
        {step === 1 && <Step1 onNext={advance} />}
        {step === 2 && <Step2 onNext={advance} />}
        {step === 3 && <Step3 onNext={advance} />}
        {step === 4 && <Step4 onComplete={onComplete} />}
      </div>
    </div>
  );
}
