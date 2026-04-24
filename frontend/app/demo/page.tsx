"use client";

import { useState, useRef } from "react";
import {
  Calculator,
  Database,
  ChevronLeft,
  ChevronRight,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ChatPanel from "@/components/ChatPanel";
import KalkulationPanel from "@/components/KalkulationPanel";
import AgentTrace from "@/components/AgentTrace";
import GraphExplorer from "@/components/GraphExplorer";
import LoginScreen from "@/components/LoginScreen";

import type { ChatMessage, TraceStep, Kalkulation } from "@/lib/types";

type TabType = "chat" | "graph";

export default function DemoPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [kalkulation, setKalkulation] = useState<Kalkulation | null>(null);
  const [loading, setLoading] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("chat");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const describeStep = (step: TraceStep): string => {
    const p = step.params || {};
    switch (step.action) {
      case "get_schema":
        return "Lese Graph-Struktur...";
      case "find_nodes":
        return `Suche ${p.label || "Knoten"}${p.filters ? ` (${Object.values(p.filters).join(", ")})` : ""}...`;
      case "follow_edges":
        return `Erkunde ${p.rel_type || "Verbindungen"} von ${p.node_id || "Knoten"}...`;
      case "find_paths":
        return `Suche Pfade von ${p.from_id || "?"}...`;
      case "find_internal_edges":
        return "Prüfe Querverbindungen...";
      case "evaluate":
        return `Berechne: ${p.expression || "..."}`;
      case "check_completeness":
        return "Prüfe Vollständigkeit...";
      case "FINISH":
        return "Erstelle Kalkulation...";
      case "FORCED_FINISH":
        return "Erstelle Kalkulation mit bisherigen Daten...";
      default:
        return `${step.action}...`;
    }
  };

  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setTrace([]);

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionRef.current,
          message: text,
        }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.trim()) continue;

          let eventType = "message";
          let data = "";

          for (const line of part.split(/\r?\n/)) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              data += line.slice(6);
            } else if (line.startsWith("data:")) {
              data += line.slice(5);
            }
          }

          if (!data) continue;

          try {
            const parsed = JSON.parse(data);

            switch (eventType) {
              case "session":
                if (parsed.session_id) {
                  sessionRef.current = parsed.session_id;
                }
                break;
              case "message":
                setMessages((prev) => [
                  ...prev,
                  { role: "assistant", content: parsed.content },
                ]);
                break;
              case "status":
                setMessages((prev) => [
                  ...prev,
                  { role: "status", content: parsed.message },
                ]);
                break;
              case "trace":
                setTrace((prev) => [...prev, parsed]);
                {
                  const desc = describeStep(parsed);
                  const stepLabel = `Schritt ${parsed.step}/${15}`;
                  setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (last?.role === "status") {
                      return [...prev.slice(0, -1), { role: "status", content: `${stepLabel}: ${desc}` }];
                    }
                    return [...prev, { role: "status", content: `${stepLabel}: ${desc}` }];
                  });
                }
                break;
              case "kalkulation":
                setKalkulation(parsed);
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last?.role === "status") {
                    return prev.slice(0, -1);
                  }
                  return prev;
                });
                break;
              case "done":
                break;
            }
          } catch {
            // Skip unparseable events
          }
        }
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Verbindungsfehler: ${e instanceof Error ? e.message : "Unbekannt"}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    setMessages([]);
    setTrace([]);
    setKalkulation(null);
    sessionRef.current = null;
  };

  if (!authenticated) {
    return <LoginScreen onLogin={() => setAuthenticated(true)} />;
  }

  return (
    <div className="h-screen bg-gradient-to-br from-stone-50 via-blue-50/20 to-stone-50 flex flex-col overflow-hidden">
      <div className="flex-1 flex min-h-0">
      {/* Sidebar */}
      <aside
        className={cn(
          "h-full bg-white/70 backdrop-blur-xl border-r border-slate-200/60 flex flex-col transition-all duration-300",
          sidebarCollapsed ? "w-[72px]" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 border-b border-slate-200/60">
          <div className="flex items-center gap-3 min-w-0">
            {sidebarCollapsed ? (
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center shadow-lg shadow-blue-800/25">
                <span className="text-white font-bold text-xs">SC</span>
              </div>
            ) : (
              <div className="flex items-center gap-3 animate-fade-in">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center shadow-lg shadow-blue-800/25">
                  <span className="text-white font-bold text-xs">SC</span>
                </div>
                <div>
                  <h1 className="text-sm font-bold text-slate-900 leading-tight">SmartCal@EG</h1>
                  <p className="text-[10px] text-slate-400 font-medium">TÜV SÜD</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {!sidebarCollapsed && (
            <div className="px-3 py-2">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Main
              </span>
            </div>
          )}
          <button
            onClick={() => setActiveTab("chat")}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
              activeTab === "chat"
                ? "bg-[#0046ad] text-white shadow-lg shadow-blue-800/25"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            <Calculator className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>Kalkulation</span>}
          </button>

          <button
            onClick={() => setActiveTab("graph")}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
              activeTab === "graph"
                ? "bg-[#0046ad] text-white shadow-lg shadow-blue-800/25"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            <Database className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>Wissensgraph</span>}
          </button>
        </nav>

        {/* Collapse Toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="mx-3 mb-3 p-2 rounded-lg border border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4 mx-auto" />
          ) : (
            <ChevronLeft className="w-4 h-4 mx-auto" />
          )}
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b border-slate-200/60 bg-white backdrop-blur-xl sticky top-0 z-10 flex items-center justify-between px-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {activeTab === "chat" ? "Prüfkosten-Kalkulator" : "Wissensgraph"}
            </h2>
            <p className="text-xs text-slate-500">
              {activeTab === "chat"
                ? "Elektro- & Gebäudetechnik"
                : "Regeln, Preislogik & Graphstruktur"}
            </p>
          </div>
          {activeTab === "chat" && (
            <button
              onClick={handleNewSession}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Neue Sitzung starten"
            >
              <Trash2 className="h-4 w-4" />
              <span>New Session</span>
            </button>
          )}
        </header>

        {/* Content Area — fill remaining viewport height */}
        <div className="flex-1 min-h-0 p-6">
          {activeTab === "chat" ? (
            <div className="h-full flex gap-4">
              {/* Chat Panel — independent scroll, input sticky at bottom */}
              <div className={cn(
                "bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden flex flex-col transition-all duration-300 min-h-0",
                kalkulation || trace.length > 0 ? "w-1/2" : "w-full"
              )}>
                <ChatPanel
                  messages={messages}
                  onSend={handleSend}
                  loading={loading}
                />
              </div>

              {/* Right: Kalkulation + Trace — independent scroll */}
              {(kalkulation || trace.length > 0) && (
                <div className="w-1/2 overflow-y-auto min-h-0 space-y-4 animate-slide-in-right">
                  {trace.length > 0 && <AgentTrace steps={trace} loading={loading} />}
                  {kalkulation && <KalkulationPanel kalkulation={kalkulation} />}
                </div>
              )}
            </div>
          ) : (
            <div className="h-full overflow-y-auto">
              <div className="max-w-6xl mx-auto">
                <GraphExplorer />
              </div>
            </div>
          )}
        </div>
      </main>
      </div>

      {/* Footer */}
      <footer className="h-10 flex items-center justify-center border-t border-slate-200/60 bg-white/70 backdrop-blur-xl">
        <p className="text-xs text-slate-400 font-medium">Synapse OS for TÜV Süd</p>
      </footer>
    </div>
  );
}
