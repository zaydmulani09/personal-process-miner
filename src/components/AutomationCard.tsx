import { useRef, useState } from "react";
import { sendToSidecar } from "../lib/sidecar";
import { Automation } from "../lib/types";

interface Props {
  automation: Automation;
  onRun: (id: number) => void;
  onDelete: (id: number) => void;
  onRename: (id: number, name: string) => void;
}

type Frequency = "daily" | "weekly" | "hourly";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

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

function scheduleInfoLabel(frequency: Frequency, time: string, dayOfWeek: number): string {
  if (frequency === "hourly") return "Hourly";
  if (frequency === "weekly") return `Weekly on ${DAY_NAMES[dayOfWeek]} at ${time}`;
  return `Daily at ${time}`;
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
  const [showSchedule, setShowSchedule] = useState(false);
  const [frequency, setFrequency] = useState<Frequency>("daily");
  const [schedTime, setSchedTime] = useState("09:00");
  const [dayOfWeek, setDayOfWeek] = useState(0);
  const [schedMsg, setSchedMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [isScheduled, setIsScheduled] = useState(automation.scheduled ?? false);
  const [scheduleInfo, setScheduleInfo] = useState(automation.schedule_info ?? "");
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

  const handleSetSchedule = async () => {
    setSchedMsg(null);
    try {
      const resp = (await sendToSidecar({
        type: "schedule_automation",
        automation_id: automation.id,
        schedule: {
          frequency,
          time: schedTime,
          day_of_week: frequency === "weekly" ? dayOfWeek : null,
        },
      })) as { ok: boolean; error?: string };
      if (resp.ok) {
        const label = scheduleInfoLabel(frequency, schedTime, dayOfWeek);
        setIsScheduled(true);
        setScheduleInfo(label);
        setSchedMsg({ ok: true, text: `Scheduled: ${label}` });
      } else {
        setSchedMsg({ ok: false, text: resp.error ?? "Failed to schedule" });
      }
    } catch (e) {
      setSchedMsg({ ok: false, text: String(e) });
    }
  };

  const handleRemoveSchedule = async () => {
    setSchedMsg(null);
    try {
      const resp = (await sendToSidecar({
        type: "unschedule_automation",
        automation_id: automation.id,
      })) as { ok: boolean; error?: string };
      if (resp.ok) {
        setIsScheduled(false);
        setScheduleInfo("");
        setSchedMsg({ ok: true, text: "Schedule removed" });
      } else {
        setSchedMsg({ ok: false, text: resp.error ?? "Failed to remove schedule" });
      }
    } catch (e) {
      setSchedMsg({ ok: false, text: String(e) });
    }
  };

  const statusDot = () => {
    if (!automation.last_run_status) return { color: "#94a3b8", symbol: "—" };
    if (automation.last_run_status === "success")
      return { color: "#16a34a", symbol: "✓" };
    return { color: "#dc2626", symbol: "✗" };
  };
  const dot = statusDot();

  const selectStyle: React.CSSProperties = {
    fontSize: 13,
    padding: "5px 8px",
    borderRadius: 6,
    border: "1px solid #e2e8f0",
    background: "#fff",
    cursor: "pointer",
  };

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

        {/* Schedule badge */}
        {isScheduled && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 12,
              background: "#fef9c3",
              color: "#854d0e",
              flexShrink: 0,
            }}
            title={scheduleInfo}
          >
            ⏰ {scheduleInfo || "Scheduled"}
          </span>
        )}
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
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
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
          onClick={() => { setShowSchedule((v) => !v); setSchedMsg(null); }}
          style={{
            padding: "6px 14px",
            fontSize: 13,
            borderRadius: 6,
            border: `1px solid ${showSchedule ? "#f59e0b" : "#fde68a"}`,
            background: showSchedule ? "#fef3c7" : "#fffbeb",
            color: "#92400e",
            cursor: "pointer",
            boxShadow: "none",
          }}
        >
          ⏰ Schedule
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

      {/* Inline schedule panel */}
      {showSchedule && (
        <div
          style={{
            marginTop: 14,
            padding: "14px 16px",
            border: "1px solid #fde68a",
            borderRadius: 8,
            background: "#fffbeb",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13, color: "#78350f", marginBottom: 10 }}>
            Schedule Automation
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 10 }}>
            {/* Frequency */}
            <label style={{ fontSize: 13, color: "#64748b" }}>
              Frequency{" "}
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as Frequency)}
                style={selectStyle}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="hourly">Hourly</option>
              </select>
            </label>

            {/* Time (hidden for hourly) */}
            {frequency !== "hourly" && (
              <label style={{ fontSize: 13, color: "#64748b" }}>
                Time{" "}
                <input
                  type="time"
                  value={schedTime}
                  onChange={(e) => setSchedTime(e.target.value)}
                  style={{ ...selectStyle, cursor: "default" }}
                />
              </label>
            )}

            {/* Day of week (weekly only) */}
            {frequency === "weekly" && (
              <label style={{ fontSize: 13, color: "#64748b" }}>
                Day{" "}
                <select
                  value={dayOfWeek}
                  onChange={(e) => setDayOfWeek(Number(e.target.value))}
                  style={selectStyle}
                >
                  {DAY_NAMES.map((d, i) => (
                    <option key={i} value={i}>{d}</option>
                  ))}
                </select>
              </label>
            )}
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={handleSetSchedule}
              style={{
                padding: "6px 14px",
                fontSize: 13,
                borderRadius: 6,
                border: "none",
                background: "#f59e0b",
                color: "#fff",
                cursor: "pointer",
                boxShadow: "none",
              }}
            >
              Set Schedule
            </button>
            {isScheduled && (
              <button
                onClick={handleRemoveSchedule}
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
                Remove Schedule
              </button>
            )}
          </div>

          {schedMsg && (
            <div
              style={{
                marginTop: 10,
                fontSize: 13,
                color: schedMsg.ok ? "#15803d" : "#dc2626",
                fontWeight: 500,
              }}
            >
              {schedMsg.ok ? "✓ " : "✗ "}
              {schedMsg.text}
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
