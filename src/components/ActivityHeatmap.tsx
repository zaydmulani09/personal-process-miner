import { addDays, format, parseISO, startOfWeek, subDays } from "date-fns";
import { useState } from "react";
import { Session } from "../lib/types";

const DAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"];

function cellColor(count: number): string {
  if (count === 0) return "var(--color-heatmap-empty)";
  if (count <= 2) return "#bbf7d0";
  if (count <= 5) return "#4ade80";
  return "#16a34a";
}

interface Props {
  sessions: Session[];
}

export default function ActivityHeatmap({ sessions }: Props) {
  const [tooltip, setTooltip] = useState<{
    date: string;
    count: number;
    x: number;
    y: number;
  } | null>(null);

  const countByDay: Record<string, number> = {};
  sessions.forEach((s) => {
    if (s.started_at) {
      try {
        const day = format(parseISO(s.started_at), "yyyy-MM-dd");
        countByDay[day] = (countByDay[day] ?? 0) + 1;
      } catch {
        // ignore unparseable dates
      }
    }
  });

  const today = new Date();
  const weekStart = startOfWeek(today); // Sunday of current week
  const gridStart = subDays(weekStart, 7 * 11); // 12 weeks total
  const days: Date[] = [];
  for (let i = 0; i < 84; i++) {
    days.push(addDays(gridStart, i));
  }
  const todayStr = format(today, "yyyy-MM-dd");

  return (
    <div style={{ marginBottom: 24, position: "relative" }}>
      <h3
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "#64748b",
          margin: "0 0 8px",
          textAlign: "left",
        }}
      >
        Activity — last 12 weeks
      </h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 14px)",
          gap: 3,
          marginBottom: 4,
        }}
      >
        {DAY_LABELS.map((d, i) => (
          <div
            key={i}
            style={{
              fontSize: 10,
              color: "#94a3b8",
              textAlign: "center",
              width: 14,
            }}
          >
            {d}
          </div>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 14px)",
          gridAutoRows: "14px",
          gap: 3,
        }}
        onMouseLeave={() => setTooltip(null)}
      >
        {days.map((day, i) => {
          const str = format(day, "yyyy-MM-dd");
          const count = countByDay[str] ?? 0;
          const isFuture = str > todayStr;
          return (
            <div
              key={i}
              style={{
                width: 14,
                height: 14,
                borderRadius: 3,
                background: isFuture ? "transparent" : cellColor(count),
                opacity: isFuture ? 0 : 1,
                cursor: "default",
              }}
              onMouseEnter={(e) => {
                if (!isFuture) {
                  setTooltip({ date: str, count, x: e.clientX, y: e.clientY });
                }
              }}
            />
          );
        })}
      </div>

      {tooltip && (
        <div
          style={{
            position: "fixed",
            left: tooltip.x + 12,
            top: tooltip.y - 8,
            background: "#0f172a",
            color: "#f8fafc",
            fontSize: 11,
            padding: "4px 8px",
            borderRadius: 4,
            pointerEvents: "none",
            zIndex: 200,
            whiteSpace: "nowrap",
          }}
        >
          {tooltip.date} — {tooltip.count} session
          {tooltip.count !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
