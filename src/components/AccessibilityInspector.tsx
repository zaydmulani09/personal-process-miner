import { useState } from "react";
import { sendToSidecar } from "../lib/sidecar";

export default function AccessibilityInspector() {
  const [minimized, setMinimized] = useState(true);
  const [treeText, setTreeText] = useState<string | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inspectScreen = async () => {
    setLoadingTree(true);
    setError(null);
    setTreeText(null);
    setAnswer(null);
    try {
      const resp = await sendToSidecar({ type: "get_tree_as_text" }) as { text: string };
      setTreeText(resp.text || "(empty tree)");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingTree(false);
    }
  };

  const askQuestion = async () => {
    if (!question.trim()) return;
    setLoadingAnswer(true);
    setAnswer(null);
    setError(null);
    try {
      const resp = await sendToSidecar({
        type: "answer_screen_question",
        question,
        tree_text: treeText || "",
      }) as { text: string };
      setAnswer(resp.text || "(no answer)");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingAnswer(false);
    }
  };

  const panelStyle: React.CSSProperties = {
    position: "fixed",
    bottom: 16,
    right: 16,
    width: minimized ? "auto" : 340,
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
        <span style={{ fontWeight: 600 }}>🔍 Screen Inspector</span>
        {!minimized && <span style={{ color: "#94a3b8", fontSize: 16 }}>−</span>}
      </div>

      {!minimized && (
        <div style={{ padding: "12px 14px 14px" }}>
          <button
            onClick={inspectScreen}
            disabled={loadingTree}
            style={{
              width: "100%",
              padding: "8px 0",
              borderRadius: 7,
              border: "none",
              background: loadingTree ? "#334155" : "#3b82f6",
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              cursor: loadingTree ? "not-allowed" : "pointer",
              marginBottom: 10,
            }}
          >
            {loadingTree ? (
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
                Reading accessibility tree...
              </span>
            ) : "🔍 Inspect Screen"}
          </button>

          {error && (
            <div style={{ color: "#f87171", fontSize: 12, marginBottom: 8 }}>{error}</div>
          )}

          {treeText && (
            <div style={{ marginBottom: 10 }}>
              <div style={{
                fontSize: 11, color: "#64748b", marginBottom: 4,
                fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5
              }}>
                Accessibility Tree
              </div>
              <pre style={{
                background: "#0f172a",
                color: "#94a3b8",
                borderRadius: 6,
                padding: "8px 10px",
                fontSize: 10,
                overflowY: "auto",
                maxHeight: 160,
                margin: 0,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}>
                {treeText}
              </pre>
            </div>
          )}

          <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && askQuestion()}
              placeholder="Ask about this screen..."
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
              onClick={askQuestion}
              disabled={loadingAnswer || !question.trim()}
              style={{
                padding: "6px 10px",
                borderRadius: 6,
                border: "none",
                background: "#3b82f6",
                color: "#fff",
                fontSize: 12,
                cursor: (loadingAnswer || !question.trim()) ? "not-allowed" : "pointer",
                opacity: (loadingAnswer || !question.trim()) ? 0.5 : 1,
              }}
            >
              {loadingAnswer ? "…" : "Ask"}
            </button>
          </div>

          {answer && (
            <div style={{
              marginTop: 6,
              padding: "8px 10px",
              borderRadius: 7,
              background: "#0f172a",
              fontSize: 12,
              color: "#cbd5e1",
              lineHeight: 1.5,
            }}>
              {answer}
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
