import Dashboard from "./pages/Dashboard";

function NavItem({ label, active }: { label: string; active?: boolean }) {
  return (
    <div
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

        <NavItem label="Dashboard" active />
      </aside>

      <main
        style={{
          flex: 1,
          overflowY: "auto",
          background: "#ffffff",
        }}
      >
        <Dashboard />
      </main>
    </div>
  );
}
