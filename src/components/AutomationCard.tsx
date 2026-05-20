import { useRef, useState } from "react";
import { Automation } from "../lib/types";

interface Props {
  automation: Automation;
  onRun: (id: number) => void;
  onDelete: (id: number) => void;
  onRename: (id: number, name: string) => void;
}

function timeAgo(isoString: string | null): string {
  if (!isoString) return "Never";
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)} days ago`;
}

function scriptPreview(body: string): string {
  const lines = body.split("\n").filter((l) => l.trim());
  const preview = lines.slice(0, 3).join("\n");
  return lines.length > 3 ? preview + "\n..." : preview;
}

export default function AutomationCard({
  automation,
  onRun,
  onDelete,
  onRename,
}: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(automation.name);
  const [isRunning, setIsRunning] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const isPlaywright = automation.script_type === "playwright";

  const handleNameClick = () => {
    setIsEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const commitRename = () => {
    const trimmed = editName.trim();
    if (trimmed && trimmed !== automation.name) {
      onRename(automation.id, trimmed);
    } else {
      setEditName(automation.name);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") commitRename();
    if (e.key === "Escape") {
      setEditName(automation.name);
      setIsEditing(false);
    }
  };

  const handleRun = async () => {
    setIsRunning(true);
    try {
      await onRun(automation.id);
    } finally {
      setIsRunning(false);
    }
  };

  const handleDelete = () => {
    if (window.confirm(`Delete "${automation.name}"?`)) {
      onDelete(automation.id);
    }
  };

  const statusDot = () => {
    if (!automation.last_run_status) return { color: "#94a3b8", symbol: "—" };
    if (automation.last_run_status === "success")
      return { color: "#16a34a", symbol: "✓" };
    return { color: "#dc2626", symbol: "✗" };
  };
  const dot = statusDot();

  return (
    <div
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: "16px 20px",
        marginBottom: 12,
        background: "#fff",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 8,
          flexWrap: "wrap",
        }}
      >
        {isEditing ? (
          <input
            ref={inputRef}
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={handleKeyDown}
            autoFocus
            style={{
              fontSize: 15,
              fontWeight: 600,
              border: "1px solid #3b82f6",
              borderRadius: 4,
              padding: "2px 6px",
              outline: "none",
              flexGrow: 1,
              minWidth: 120,
            }}
          />
        ) : (
          <span
            onClick={handleNameClick}
            title="Click to rename"
            style={{
              fontWeight: 600,
              fontSize: 15,
              cursor: "text",
              borderBottom: "1px dashed #cbd5e1",
            }}
          >
            {automation.name}
          </span>
        )}

        {/* Type badge */}
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 12,
            background: isPlaywright ? "#dcfce7" : "#dbeafe",
            color: isPlaywright ? "#15803d" : "#1d4ed8",
            flexShrink: 0,
          }}
        >
          {isPlaywright ? "Playwright" : "PyAutoGUI"}
        </span>
      </div>

      {/* Stats row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          fontSize: 13,
          color: "#64748b",
          marginBottom: 10,
        }}
      >
        <span>
          Runs: <strong>{automation.run_count}</strong>
        </span>
        <span>Last run: {timeAgo(automation.last_run_at)}</span>
        <span
          style={{ color: dot.color, fontWeight: 600, fontSize: 14 }}
          title={automation.last_run_status ?? "never run"}
        >
          {dot.symbol}
        </span>
      </div>

      {/* Script preview */}
      {automation.script_body && (
        <pre
          style={{
            background: "#0f172a",
            color: "#94a3b8",
            padding: "10px 14px",
            borderRadius: 6,
            fontSize: 11,
            lineHeight: 1.5,
            margin: "0 0 12px",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontFamily: "'Cascadia Code', 'Fira Mono', 'Consolas', monospace",
            maxHeight: 80,
            overflow: "hidden",
          }}
        >
          {scriptPreview(automation.script_body)}
        </pre>
      )}

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={handleRun}
          disabled={isRunning}
          style={{
            padding: "6px 14px",
            fontSize: 13,
            borderRadius: 6,
            border: "none",
            background: isRunning ? "#94a3b8" : "#3b82f6",
            color: "#fff",
            cursor: isRunning ? "not-allowed" : "pointer",
            boxShadow: "none",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          {isRunning ? (
            <>
              <span
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  border: "2px solid rgba(255,255,255,0.4)",
                  borderTopColor: "#fff",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              Running…
            </>
          ) : (
            "▶ Run"
          )}
        </button>
        <button
          onClick={handleDelete}
          style={{
            padding: "6px 14px",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid #fca5a5",
            background: "#fff5f5",
            color: "#dc2626",
            cursor: "pointer",
            boxShadow: "none",
          }}
        >
          🗑 Delete
        </button>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
