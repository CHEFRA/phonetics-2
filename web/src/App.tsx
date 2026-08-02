import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Models from "./pages/Models";
import Settings from "./pages/Settings";
import Stats from "./pages/Stats";

const TABS = [
  { id: "dashboard", label: "概览" },
  { id: "history", label: "历史" },
  { id: "stats", label: "统计" },
  { id: "models", label: "模型" },
  { id: "settings", label: "设置" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("dashboard");

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center gap-1 border-b border-neutral-200 bg-white px-4 py-2">
        <span className="mr-4 text-sm font-semibold text-neutral-800">
          Phonetics-2
        </span>
        {TABS.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={
              tab === item.id
                ? "rounded-md bg-green-600 px-3 py-1 text-sm font-medium text-white"
                : "rounded-md px-3 py-1 text-sm font-medium text-neutral-600 hover:bg-neutral-100"
            }
          >
            {item.label}
          </button>
        ))}
      </header>
      <main className="flex-1 overflow-auto p-4">
        {tab === "dashboard" && <Dashboard />}
        {tab === "history" && <History />}
        {tab === "stats" && <Stats />}
        {tab === "models" && <Models />}
        {tab === "settings" && <Settings />}
      </main>
    </div>
  );
}
