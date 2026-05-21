import { useState } from "react";
import { sendToSidecar } from "../lib/sidecar";

type ScreenDescription = { description: string; elements: string[] };
type ElementLocation = { found: boolean; x: number; y: number; confidence: number; description: string };

export default function ScreenInspector() {
  const [minimized, setMinimized] = useState(true);
  const [loading, setLoading] = useState(false);
  const [screenDesc, setScreenDesc] = useState<ScreenDescription | null>(null);
  const [findQuery, setFindQuery] = useState("");
  const [foundEl, setFoundEl] = useState<ElementLocation | null>(null);
  const [findLoading, setFindLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inspect = async () => {
    setLoading(true);
    setError(null);
    setScreenDesc(null);
    setFoundEl(null);
    try {
      const resp = await sendToSidecar({ type: "describe_screen" }) as { result: ScreenDescription };
      setScreenDesc(resp.result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const findElement = async (desc: string) => {
    if (!desc.trim()) return;
    setFindLoading(true);
    setFoundEl(null);
    setError(null);
    try {
      const resp = await sendToSidecar({ type: "find_element", description: desc }) as { result: ElementLocation };
      setFoundEl(resp.result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setFindLoading(false);
    }
  };

  const panelStyle: React.CSSProperties = {
    position: "fixed",
    bottom: 16,
    right: 16,
    width: minimized ? "auto" : 320,
    background: "#1e293b",
    color: "#f8fafc",
    borderRadius: 12,
    boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
    fontFamily: "system-ui, sans-serif",
    fontSize: 13,
    zIndex: 9999,
    overflow: "hidden",
  };

  return (
    <div style={panelStyle}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          cursor: "pointer",
          userSelect: "none",
          background: "#0f172a",
        }}
        onClick={() => setMinimized((v) => !v)}
      >
        <span style={{ fontWeight: 600 }}>👁 Inspect Screen</span>
        {!minimized && <span style={{ color: "#94a3b8", fontSize: 16 }}>−</span>}
      </div>

      {!minimized && (
        <div style={{ padding: "12px 14px 14px" }}>
          <button
            onClick={inspect}
            disabled={loading}
            style={{
              width: "100%",
              padding: "8px 0",
              borderRadius: 7,
              border: "none",
              background: loading ? "#334155" : "#3b82f6",
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              marginBottom: 10,
            }}
          >
            {loading ? (
              <span>
                <span
                  style={{
                    display: "inline-block",
                    width: 11,
                    height: 11,
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderTopColor: "#fff",
                    borderRadius: "50%",
                    animation: "spin 0.7s linear infinite",
                    marginRight: 7,
                    verticalAlign: "middle",
                  }}
                />
                AI is reading your screen...
              </span>
            ) : "👁 Inspect Screen"}
          </button>

          {error && (
            <div style={{ color: "#f87171", fontSize: 12, marginBottom: 8 }}>{error}</div>
          )}

          {screenDesc && (
            <div>
              <div style={{ color: "#cbd5e1", lineHeight: 1.5, marginBottom: 10, fontSize: 12 }}>
                {screenDesc.description}
              </div>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
                Detected elements
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
                {(screenDesc.elements ?? []).map((el, i) => (
                  <button
                    key={i}
                    onClick={() => { setFindQuery(el); findElement(el); }}
                    style={{
                      padding: "3px 9px",
                      borderRadius: 12,
                      border: "1px solid #334155",
                      background: "#1e293b",
                      color: "#93c5fd",
                      fontSize: 11,
                      cursor: "pointer",
                    }}
                  >
                    {el}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 6 }}>
            <input
              value={findQuery}
              onChange={(e) => setFindQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && findElement(findQuery)}
              placeholder="Find element..."
              style={{
                flex: 1,
                padding: "6px 9px",
                borderRadius: 6,
                border: "1px solid #334155",
                background: "#0f172a",
                color: "#f8fafc",
                fontSize: 12,
                outline: "none",
              }}
            />
            <button
              onClick={() => findElement(findQuery)}
              disabled={findLoading}
              style={{
                padding: "6px 10px",
                borderRadius: 6,
                border: "none",
                background: "#3b82f6",
                color: "#fff",
                fontSize: 12,
                cursor: findLoading ? "not-allowed" : "pointer",
              }}
            >
              {findLoading ? "…" : "Find"}
            </button>
          </div>

          {foundEl && (
            <div
              style={{
                marginTop: 8,
                padding: "7px 10px",
                borderRadius: 7,
                background: foundEl.found ? "#14532d" : "#450a0a",
                fontSize: 12,
              }}
            >
              {foundEl.found ? (
                <>
                  <div style={{ color: "#86efac", fontWeight: 600 }}>Found: {foundEl.description}</div>
                  <div style={{ color: "#4ade80", marginTop: 2 }}>
                    x={foundEl.x}, y={foundEl.y} · confidence {Math.round(foundEl.confidence * 100)}%
                  </div>
                </>
              ) : (
                <div style={{ color: "#fca5a5" }}>Element not found on screen</div>
              )}
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
