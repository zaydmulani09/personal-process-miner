import { useEffect, useRef, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";

type Settings = Record<string, string>;

const RETENTION_OPTIONS = [
  { label: "7 days", value: "7" },
  { label: "30 days", value: "30" },
  { label: "90 days", value: "90" },
  { label: "Forever", value: "0" },
];

const sectionStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 10,
  padding: "20px 24px",
  marginBottom: 20,
};

const labelStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: 14,
  color: "#0f172a",
  marginBottom: 2,
};

const subStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#64748b",
  marginBottom: 12,
};

interface Props {
  onNavigate: (page: string) => void;
}

type VisionBackend = "" | "claude" | "openai" | "groq";

const VISION_BACKENDS = [
  { value: "" as VisionBackend, label: "Disabled" },
  { value: "claude" as VisionBackend, label: "Claude (Anthropic)" },
  { value: "openai" as VisionBackend, label: "OpenAI (GPT-4o)" },
  { value: "groq" as VisionBackend, label: "Groq (Fast & Free)" },
];

const VISION_PLACEHOLDERS: Record<VisionBackend, string> = {
  "": "API key",
  claude: "sk-ant-...",
  openai: "sk-...",
  groq: "gsk_...",
};

const VISION_LINKS: Record<VisionBackend, string> = {
  "": "",
  claude: "https://console.anthropic.com",
  openai: "https://platform.openai.com/api-keys",
  groq: "https://console.groq.com",
};

export default function Settings({ onNavigate }: Props) {
  const [settings, setSettings] = useState<Settings>({});
  const [blocklist, setBlocklist] = useState<string[]>([]);
  const [newApp, setNewApp] = useState("");
  const [purgeMsg, setPurgeMsg] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [loading, setLoading] = useState(true);
  const newAppRef = useRef<HTMLInputElement>(null);

  const [visionBackend, setVisionBackend] = useState<VisionBackend>("");
  const [visionKey, setVisionKey] = useState("");
  const [visionStatus, setVisionStatus] = useState<{ available: boolean; backend: string | null } | null>(null);
  const [visionSaving, setVisionSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      sendToSidecar({ type: "get_settings" }),
      sendToSidecar({ type: "get_blocklist" }),
      sendToSidecar({ type: "check_vision" }),
    ]).then(([sResp, bResp, vResp]) => {
      setSettings((sResp as { data: Settings }).data ?? {});
      setBlocklist((bResp as { apps: string[] }).apps ?? []);
      const vs = vResp as { available: boolean; backend: string | null; model: string | null };
      setVisionStatus({ available: vs.available, backend: vs.backend });
      if (vs.backend) setVisionBackend(vs.backend as VisionBackend);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const saveVisionConfig = async () => {
    setVisionSaving(true);
    try {
      await sendToSidecar({ type: "set_vision_config", backend: visionBackend, api_key: visionKey });
      const resp = await sendToSidecar({ type: "check_vision" }) as { available: boolean; backend: string | null };
      setVisionStatus({ available: resp.available, backend: resp.backend });
    } catch (e) {
      // ignore
    } finally {
      setVisionSaving(false);
    }
  };

  const setSetting = async (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    await sendToSidecar({ type: "set_setting", key, value });
  };

  const addApp = async () => {
    const app = newApp.trim();
    if (!app) return;
    await sendToSidecar({ type: "add_to_blocklist", app });
    setBlocklist((prev) => prev.includes(app) ? prev : [...prev, app]);
    setNewApp("");
    newAppRef.current?.focus();
  };

  const removeApp = async (app: string) => {
    await sendToSidecar({ type: "remove_from_blocklist", app });
    setBlocklist((prev) => prev.filter((a) => a !== app));
  };

  const cleanupNow = async () => {
    setPurgeMsg(null);
    const resp = await sendToSidecar({ type: "purge_old_events" }) as { deleted: number };
    setPurgeMsg(`Deleted ${resp.deleted} old event${resp.deleted === 1 ? "" : "s"}.`);
  };

  const purgeAll = async () => {
    const resp = await sendToSidecar({ type: "purge_all_data" }) as {
      counts: Record<string, number>;
    };
    const c = resp.counts;
    setPurgeMsg(
      `Purged: ${c.events} events, ${c.sessions} sessions, ${c.workflows} workflows, ${c.automations} automations.`
    );
    setDeleteConfirm("");
    setTimeout(() => onNavigate("dashboard"), 1500);
  };

  if (loading) {
    return (
      <div style={{ padding: 32, fontFamily: "system-ui, sans-serif" }}>
        Loading settings…
      </div>
    );
  }

  const keystrokesOn = settings["capture_keystrokes"] === "true";
  const mouseMovesOn = settings["capture_mouse_moves"] !== "false";
  const retention = settings["retention_days"] ?? "30";

  return (
    <div
      style={{
        padding: 32,
        maxWidth: 720,
        margin: "0 auto",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
          Privacy & Settings
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#64748b" }}>
          All data stays on your machine. Nothing is sent to the cloud.
        </p>
      </div>

      {/* Capture Privacy */}
      <div style={sectionStyle}>
        <div style={labelStyle}>Capture Privacy</div>
        <div style={subStyle}>Control what gets recorded during capture sessions.</div>

        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 12,
            marginBottom: 14,
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={keystrokesOn}
            onChange={(e) => setSetting("capture_keystrokes", e.target.checked ? "true" : "false")}
            style={{ marginTop: 2 }}
          />
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#0f172a" }}>
              Record keystrokes
            </div>
            {keystrokesOn && (
              <div style={{ fontSize: 12, color: "#b45309", marginTop: 2 }}>
                ⚠ Key names will be stored locally
              </div>
            )}
          </div>
        </label>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={mouseMovesOn}
            onChange={(e) =>
              setSetting("capture_mouse_moves", e.target.checked ? "true" : "false")
            }
          />
          <div style={{ fontSize: 14, fontWeight: 500, color: "#0f172a" }}>
            Record mouse movements
          </div>
        </label>
      </div>

      {/* App Filter */}
      <div style={sectionStyle}>
        <div style={labelStyle}>Never record these apps</div>
        <div style={subStyle}>Add app names to block from recording (case-insensitive substring match).</div>

        <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          <input
            ref={newAppRef}
            value={newApp}
            onChange={(e) => setNewApp(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addApp()}
            placeholder="e.g. 1password, slack"
            style={{
              flex: 1,
              fontSize: 13,
              padding: "7px 10px",
              borderRadius: 6,
              border: "1px solid #e2e8f0",
              outline: "none",
            }}
          />
          <button
            onClick={addApp}
            style={{
              padding: "7px 16px",
              fontSize: 13,
              borderRadius: 6,
              border: "none",
              background: "#3b82f6",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            Add
          </button>
        </div>

        {blocklist.length === 0 ? (
          <p style={{ fontSize: 13, color: "#94a3b8", margin: 0 }}>
            No apps blocked — all apps are being recorded
          </p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {blocklist.map((app) => (
              <span
                key={app}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  background: "#f1f5f9",
                  border: "1px solid #e2e8f0",
                  borderRadius: 20,
                  padding: "4px 12px",
                  fontSize: 13,
                  color: "#334155",
                }}
              >
                {app}
                <button
                  onClick={() => removeApp(app)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: 14,
                    color: "#94a3b8",
                    lineHeight: 1,
                  }}
                  title={`Remove ${app}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Data Retention */}
      <div style={sectionStyle}>
        <div style={labelStyle}>Data Retention</div>
        <div style={subStyle}>Events older than this will be deleted on next cleanup.</div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
          <label style={{ fontSize: 14, color: "#0f172a", fontWeight: 500 }}>
            Keep data for{" "}
          </label>
          <select
            value={retention}
            onChange={(e) => setSetting("retention_days", e.target.value)}
            style={{
              fontSize: 13,
              padding: "6px 10px",
              borderRadius: 6,
              border: "1px solid #e2e8f0",
              background: "#fff",
              cursor: "pointer",
            }}
          >
            {RETENTION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={cleanupNow}
          style={{
            padding: "7px 16px",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid #e2e8f0",
            background: "#f8fafc",
            color: "#475569",
            cursor: "pointer",
          }}
        >
          Clean up now
        </button>

        {purgeMsg && !purgeMsg.startsWith("Purged:") && (
          <span style={{ marginLeft: 12, fontSize: 13, color: "#15803d" }}>{purgeMsg}</span>
        )}
      </div>

      {/* AI Vision */}
      <div style={sectionStyle}>
        <div style={labelStyle}>AI Vision</div>
        <div style={subStyle}>
          Let AI see your screen to enable smart automations that work even when layouts change
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 14 }}>
          {VISION_BACKENDS.map((b) => (
            <label key={b.value} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14, color: "#0f172a" }}>
              <input
                type="radio"
                name="vision_backend"
                value={b.value}
                checked={visionBackend === b.value}
                onChange={() => setVisionBackend(b.value)}
              />
              {b.label}
              {b.value && VISION_LINKS[b.value] && (
                <a
                  href={VISION_LINKS[b.value]}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 12, color: "#3b82f6", marginLeft: 4 }}
                >
                  Get API key ↗
                </a>
              )}
            </label>
          ))}
        </div>

        {visionBackend !== "" && (
          <input
            type="password"
            value={visionKey}
            onChange={(e) => setVisionKey(e.target.value)}
            placeholder={VISION_PLACEHOLDERS[visionBackend]}
            style={{
              width: "100%",
              fontSize: 13,
              padding: "7px 10px",
              borderRadius: 6,
              border: "1px solid #e2e8f0",
              outline: "none",
              marginBottom: 10,
              boxSizing: "border-box",
            }}
          />
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
          <button
            onClick={saveVisionConfig}
            disabled={visionSaving}
            style={{
              padding: "7px 16px",
              fontSize: 13,
              borderRadius: 6,
              border: "none",
              background: visionSaving ? "#93c5fd" : "#3b82f6",
              color: "#fff",
              cursor: visionSaving ? "not-allowed" : "pointer",
            }}
          >
            {visionSaving ? "Saving…" : "Save"}
          </button>
          {visionStatus && (
            <span style={{ fontSize: 13, color: visionStatus.available ? "#15803d" : "#94a3b8", fontWeight: 500 }}>
              {visionStatus.available ? `✓ Vision enabled — ${visionStatus.backend}` : "✗ Not configured"}
            </span>
          )}
        </div>

        <p style={{ fontSize: 12, color: "#64748b", margin: 0, lineHeight: 1.6 }}>
          Your API key is stored locally on your machine. Screenshots are only sent to the AI when you
          trigger an automation — never during passive capture.
        </p>
      </div>

      {/* Danger Zone */}
      <div
        style={{
          ...sectionStyle,
          borderColor: "#fecaca",
          background: "#fff5f5",
        }}
      >
        <div style={{ ...labelStyle, color: "#dc2626" }}>Danger Zone</div>
        <div style={{ ...subStyle, marginBottom: 16 }}>
          Permanently delete all captured events, sessions, workflows, and automations.
          This cannot be undone.
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <input
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder='Type "DELETE" to confirm'
            style={{
              fontSize: 13,
              padding: "7px 10px",
              borderRadius: 6,
              border: "1px solid #fca5a5",
              outline: "none",
              width: 200,
            }}
          />
          <button
            onClick={purgeAll}
            disabled={deleteConfirm !== "DELETE"}
            style={{
              padding: "7px 16px",
              fontSize: 13,
              borderRadius: 6,
              border: "none",
              background: deleteConfirm === "DELETE" ? "#dc2626" : "#fca5a5",
              color: "#fff",
              cursor: deleteConfirm === "DELETE" ? "pointer" : "not-allowed",
            }}
          >
            Purge All Data
          </button>
        </div>

        {purgeMsg && purgeMsg.startsWith("Purged:") && (
          <div style={{ fontSize: 13, color: "#dc2626", fontWeight: 500 }}>{purgeMsg}</div>
        )}
      </div>
    </div>
  );
}
