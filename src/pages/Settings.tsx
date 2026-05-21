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

type ProviderKey = "claude" | "openai" | "groq" | "gemini" | "grok";

const PROVIDERS: { id: ProviderKey; emoji: string; name: string; desc: string; placeholder: string; link: string }[] = [
  { id: "claude", emoji: "🟠", name: "Claude", desc: "Best quality, Anthropic", placeholder: "sk-ant-...", link: "https://console.anthropic.com" },
  { id: "openai", emoji: "🟢", name: "OpenAI", desc: "GPT-4o vision", placeholder: "sk-...", link: "https://platform.openai.com/api-keys" },
  { id: "groq", emoji: "⚡", name: "Groq", desc: "Fast & free tier", placeholder: "gsk_...", link: "https://console.groq.com" },
  { id: "gemini", emoji: "🔵", name: "Gemini", desc: "Google Gemini Flash", placeholder: "AIza...", link: "https://aistudio.google.com/apikey" },
  { id: "grok", emoji: "⬛", name: "Grok", desc: "xAI Grok vision", placeholder: "xai-...", link: "https://console.x.ai" },
];

const EMPTY_PROVIDER_MAP = (): Record<ProviderKey, string> => ({
  claude: "", openai: "", groq: "", gemini: "", grok: "",
});

const EMPTY_TEST_MAP = (): Record<ProviderKey, { ok: boolean; error?: string; model?: string } | null> => ({
  claude: null, openai: null, groq: null, gemini: null, grok: null,
});

const EMPTY_BOOL_MAP = (): Record<ProviderKey, boolean> => ({
  claude: false, openai: false, groq: false, gemini: false, grok: false,
});

export default function Settings({ onNavigate }: Props) {
  const [settings, setSettings] = useState<Settings>({});
  const [blocklist, setBlocklist] = useState<string[]>([]);
  const [newApp, setNewApp] = useState("");
  const [purgeMsg, setPurgeMsg] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [loading, setLoading] = useState(true);
  const newAppRef = useRef<HTMLInputElement>(null);

  const [sidecarHealth, setSidecarHealth] = useState<"checking" | "ok" | "error">("checking");
  const [providerKeys, setProviderKeys] = useState<Record<ProviderKey, string>>(EMPTY_PROVIDER_MAP());
  const [activeProvider, setActiveProvider] = useState<ProviderKey | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<ProviderKey, { ok: boolean; error?: string; model?: string } | null>>(EMPTY_TEST_MAP());
  const [testing, setTesting] = useState<Record<ProviderKey, boolean>>(EMPTY_BOOL_MAP());
  const [settingActive, setSettingActive] = useState<ProviderKey | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  useEffect(() => {
    Promise.race([
      sendToSidecar({ type: "ping" }),
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error("timeout")), 3000)),
    ])
      .then(() => setSidecarHealth("ok"))
      .catch(() => setSidecarHealth("error"));
  }, []);

  useEffect(() => {
    Promise.all([
      sendToSidecar({ type: "get_settings" }),
      sendToSidecar({ type: "get_blocklist" }),
      sendToSidecar({ type: "check_vision" }),
    ]).then(([sResp, bResp, vResp]) => {
      const s = (sResp as { data: Settings }).data ?? {};
      setSettings(s);
      setBlocklist((bResp as { apps: string[] }).apps ?? []);
      const vs = vResp as { available: boolean; backend: string | null; model: string | null };
      if (vs.available && vs.backend) {
        setActiveProvider(vs.backend as ProviderKey);
        setActiveModel(vs.model ?? null);
      }
      setProviderKeys({
        claude: s["vision_api_key_claude"] ?? "",
        openai: s["vision_api_key_openai"] ?? "",
        groq: s["vision_api_key_groq"] ?? "",
        gemini: s["vision_api_key_gemini"] ?? "",
        grok: s["vision_api_key_grok"] ?? "",
      });
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const testConnection = async (providerId: ProviderKey) => {
    setTesting(prev => ({ ...prev, [providerId]: true }));
    try {
      const resp = await sendToSidecar({
        type: "test_vision_connection",
        backend: providerId,
        api_key: providerKeys[providerId],
      }) as { type: string; ok: boolean; error: string | null; model: string | null };
      setTestResults(prev => ({
        ...prev,
        [providerId]: { ok: resp.ok, error: resp.error ?? undefined, model: resp.model ?? undefined },
      }));
    } catch {
      setTestResults(prev => ({ ...prev, [providerId]: { ok: false, error: "connection failed" } }));
    } finally {
      setTesting(prev => ({ ...prev, [providerId]: false }));
    }
  };

  const setAsActive = async (providerId: ProviderKey) => {
    setSettingActive(providerId);
    try {
      await sendToSidecar({
        type: "set_vision_config",
        backend: providerId,
        api_key: providerKeys[providerId],
      });
      const resp = await sendToSidecar({ type: "check_vision" }) as { available: boolean; backend: string | null; model: string | null };
      if (resp.available && resp.backend) {
        setActiveProvider(resp.backend as ProviderKey);
        setActiveModel(resp.model ?? null);
      } else {
        setActiveProvider(null);
        setActiveModel(null);
      }
    } catch {
      // ignore
    } finally {
      setSettingActive(null);
    }
  };

  const deactivateVision = async () => {
    setDeactivating(true);
    try {
      await sendToSidecar({ type: "deactivate_vision" });
      setActiveProvider(null);
      setActiveModel(null);
    } catch {
      // ignore
    } finally {
      setDeactivating(false);
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
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
          Privacy & Settings
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#64748b" }}>
          All data stays on your machine. Nothing is sent to the cloud.
        </p>
      </div>

      {/* Sidecar health */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, marginBottom: 20,
        padding: "8px 14px", borderRadius: 8,
        background: sidecarHealth === "ok" ? "#f0fdf4" : sidecarHealth === "error" ? "#fef2f2" : "#f8fafc",
        border: `1px solid ${sidecarHealth === "ok" ? "#bbf7d0" : sidecarHealth === "error" ? "#fecaca" : "#e2e8f0"}`,
        fontSize: 13,
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
          background: sidecarHealth === "ok" ? "#22c55e" : sidecarHealth === "error" ? "#ef4444" : "#94a3b8",
        }} />
        <span style={{ color: sidecarHealth === "ok" ? "#15803d" : sidecarHealth === "error" ? "#dc2626" : "#64748b", fontWeight: 500 }}>
          {sidecarHealth === "ok"
            ? "Sidecar running"
            : sidecarHealth === "error"
            ? "Sidecar not running — try restarting the app"
            : "Checking sidecar…"}
        </span>
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

        {/* Active provider status */}
        <div style={{
          marginBottom: 16, padding: "8px 12px",
          background: activeProvider ? "#f0fdf4" : "#f8fafc",
          borderRadius: 6,
          border: `1px solid ${activeProvider ? "#bbf7d0" : "#e2e8f0"}`,
          fontSize: 13,
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <span style={{ color: activeProvider ? "#15803d" : "#94a3b8", fontWeight: 500, flex: 1 }}>
            {activeProvider
              ? `Active: ${PROVIDERS.find(p => p.id === activeProvider)?.name} (${activeModel ?? ""})`
              : "No provider configured"}
          </span>
          {activeProvider && (
            <button
              onClick={deactivateVision}
              disabled={deactivating}
              style={{
                padding: "3px 10px", fontSize: 12, borderRadius: 5,
                border: "1px solid #fca5a5", background: "#fff5f5",
                color: "#dc2626", cursor: deactivating ? "not-allowed" : "pointer",
                opacity: deactivating ? 0.6 : 1,
              }}
            >
              {deactivating ? "…" : "⏹ Deactivate"}
            </button>
          )}
        </div>

        {/* Provider cards 2-col grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
          {PROVIDERS.map(p => (
            <div key={p.id} style={{
              background: "#f8fafc",
              border: `2px solid ${activeProvider === p.id ? "#3b82f6" : "#e2e8f0"}`,
              borderRadius: 8,
              padding: "14px 16px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                <span style={{ fontSize: 16 }}>{p.emoji}</span>
                <span style={{ fontWeight: 600, fontSize: 14, color: "#0f172a" }}>{p.name}</span>
                <a
                  href={p.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ marginLeft: "auto", fontSize: 11, color: "#3b82f6" }}
                >
                  Get API key ↗
                </a>
              </div>
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 10 }}>{p.desc}</div>
              <input
                type="password"
                value={providerKeys[p.id]}
                onChange={e => setProviderKeys(prev => ({ ...prev, [p.id]: e.target.value }))}
                placeholder={p.placeholder}
                style={{
                  width: "100%", fontSize: 12, padding: "6px 8px",
                  borderRadius: 6, border: "1px solid #e2e8f0",
                  marginBottom: 8, boxSizing: "border-box",
                }}
              />
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  onClick={() => testConnection(p.id)}
                  disabled={testing[p.id] || !providerKeys[p.id]}
                  style={{
                    flex: 1, padding: "5px 0", fontSize: 12, borderRadius: 6,
                    border: "1px solid #e2e8f0", background: "#fff", color: "#475569",
                    cursor: (testing[p.id] || !providerKeys[p.id]) ? "not-allowed" : "pointer",
                    opacity: (testing[p.id] || !providerKeys[p.id]) ? 0.5 : 1,
                  }}
                >
                  {testing[p.id] ? "Testing…" : "Test Connection"}
                </button>
                <button
                  onClick={() => setAsActive(p.id)}
                  disabled={settingActive === p.id || !providerKeys[p.id]}
                  style={{
                    flex: 1, padding: "5px 0", fontSize: 12, borderRadius: 6,
                    border: "none",
                    background: activeProvider === p.id ? "#3b82f6" : "#64748b",
                    color: "#fff",
                    cursor: (settingActive === p.id || !providerKeys[p.id]) ? "not-allowed" : "pointer",
                    opacity: (settingActive === p.id || !providerKeys[p.id]) ? 0.5 : 1,
                  }}
                >
                  {settingActive === p.id ? "Setting…" : activeProvider === p.id ? "✓ Active" : "Set as Active"}
                </button>
              </div>
              {testResults[p.id] !== null && (
                <div style={{ marginTop: 6, fontSize: 12, color: testResults[p.id]?.ok ? "#15803d" : "#dc2626" }}>
                  {testResults[p.id]?.ok
                    ? `✓ Connected — ${testResults[p.id]?.model}`
                    : `✗ ${testResults[p.id]?.error}`}
                </div>
              )}
            </div>
          ))}
        </div>

        <p style={{ fontSize: 12, color: "#64748b", margin: 0, lineHeight: 1.6 }}>
          API keys stored locally in SQLite. Screenshots only sent when you trigger an action — never during passive capture.
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
