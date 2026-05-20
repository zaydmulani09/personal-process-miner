import { useState } from "react";
import Automations from "./pages/Automations";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";

type Page = "dashboard" | "automations" | "settings";

function NavItem({
  label,
  active,
  onClick,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: "8px 12px",
        fontSize: 14,
        fontWeight: active ? 600 : 400,
        color: active ? "#f8fafc" : "#94a3b8",
        background: active ? "rgba(255,255,255,0.1)" : "transparent",
        borderRadius: 6,
        margin: "0 8px",
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      {label}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <aside
        style={{
          width: 200,
          background: "#1e293b",
          color: "#f8fafc",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
          paddingTop: 20,
        }}
      >
        <div
          style={{
            padding: "0 20px 20px",
            fontWeight: 700,
            fontSize: 15,
            display: "flex",
            alignItems: "center",
            gap: 8,
            color: "#f8fafc",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            marginBottom: 8,
          }}
        >
          <span>⚙</span>
          <span>Process Miner</span>
        </div>

        <NavItem
          label="Dashboard"
          active={page === "dashboard"}
          onClick={() => setPage("dashboard")}
        />
        <NavItem
          label="Automations"
          active={page === "automations"}
          onClick={() => setPage("automations")}
        />
        <NavItem
          label="⚙ Settings"
          active={page === "settings"}
          onClick={() => setPage("settings")}
        />
      </aside>

      <main
        style={{
          flex: 1,
          overflowY: "auto",
          background: "#ffffff",
        }}
      >
        {page === "dashboard" ? (
          <Dashboard />
        ) : page === "automations" ? (
          <Automations />
        ) : (
          <Settings onNavigate={(p) => setPage(p as Page)} />
        )}
      </main>
    </div>
  );
}
