import { useEffect, useState } from "react";
import Automations from "./pages/Automations";
import Dashboard from "./pages/Dashboard";
import Onboarding from "./pages/Onboarding";
import Settings from "./pages/Settings";
import ShareInsights from "./pages/ShareInsights";
import ScreenInspector from "./components/ScreenInspector";
import NLBuilder from "./components/NLBuilder";
import { sendToSidecar } from "./lib/sidecar";

type Page = "dashboard" | "automations" | "build" | "settings" | "share";

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
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);

  useEffect(() => {
    sendToSidecar({ type: "get_onboarding_state" })
      .then((resp) => {
        const r = resp as { complete: boolean };
        setOnboardingDone(r.complete);
      })
      .catch(() => setOnboardingDone(true)); // fail-open: show main app
  }, []);

  const handleOnboardingComplete = () => {
    setOnboardingDone(true);
    setPage("dashboard");
  };

  if (onboardingDone === null) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          color: "#94a3b8",
          fontSize: 14,
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 24,
            height: 24,
            border: "3px solid #e2e8f0",
            borderTopColor: "#3b82f6",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!onboardingDone) {
    return <Onboarding onComplete={handleOnboardingComplete} />;
  }

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
          label="✨ Build"
          active={page === "build"}
          onClick={() => setPage("build")}
        />
        <NavItem
          label="⚙ Settings"
          active={page === "settings"}
          onClick={() => setPage("settings")}
        />
        <NavItem
          label="↗ Share"
          active={page === "share"}
          onClick={() => setPage("share")}
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
        ) : page === "build" ? (
          <NLBuilder onNavigate={(p) => setPage(p as Page)} />
        ) : page === "settings" ? (
          <Settings onNavigate={(p) => setPage(p as Page)} />
        ) : (
          <ShareInsights />
        )}
      </main>
      <ScreenInspector />
    </div>
  );
}
