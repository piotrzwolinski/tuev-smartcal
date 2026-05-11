"use client";

import { useState, useRef, useEffect } from "react";
import {
  Zap,
  ChevronLeft,
  ChevronRight,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ChatPanel from "@/components/ChatPanel";
import AgentTrace from "@/components/AgentTrace";
import BlitzschutzAngebotPanel from "@/components/BlitzschutzAngebotPanel";
import type { BlitzschutzAngebot } from "@/components/BlitzschutzAngebotPanel";
import LoginScreen from "@/components/LoginScreen";
import type { ChatMessage, TraceStep } from "@/lib/types";
import { PRODUCTS, DEFAULT_PRODUCT, type ProductConfig } from "@/lib/products";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function Home() {
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem("smartcal_auth") === "1") setAuthenticated(true);
  }, []);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [angebot, setAngebot] = useState<BlitzschutzAngebot | null>(null);
  const [loading, setLoading] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [pricingMode, setPricingMode] = useState<"graph" | "python">("graph");
  const [provenance, setProvenance] = useState<Array<{step:string;source:string;value:unknown;node_id:string}>>([]);
  const [activeProduct, setActiveProduct] = useState<ProductConfig>(DEFAULT_PRODUCT);

  const switchProduct = (product: ProductConfig) => {
    if (product.id === activeProduct.id) return;
    setActiveProduct(product);
    setMessages([]);
    setTrace([]);
    setAngebot(null);
    setProvenance([]);
    sessionRef.current = null;
  };

  if (!authenticated) {
    return <LoginScreen onLogin={() => { sessionStorage.setItem("smartcal_auth", "1"); setAuthenticated(true); }} />;
  }

  const describeStep = (step: TraceStep): string => {
    // Graph provenance steps have result_summary with full description
    if (step.result_summary?.startsWith("Graph →")) {
      return step.result_summary;
    }
    switch (step.action) {
      case "extract": return "Merkmale aus Anfrage extrahiert";
      case "validate": return "Pydantic Schema-Validation ✓";
      case "grundkosten": return step.result_summary || "Grundkosten aus Graph laden...";
      case "prueftage": return step.result_summary || "Prüftage-Schätzung...";
      case "tagegeld": return step.result_summary || "Tagegeld berechnen...";
      case "pruefkosten": return step.result_summary || "Prüfkosten-Staffeln anwenden...";
      case "reisekosten": return step.result_summary || "Reisekosten berechnen...";
      case "bericht": return step.result_summary || "Berichtstyp zuordnen...";
      case "zuschlag": return step.result_summary || "Zuschläge prüfen...";
      case "confidence": return step.result_summary || "Confidence Score berechnen...";
      case "cross_sell": return step.result_summary || "Empfehlungen prüfen...";
      case "pricing": return step.result_summary || "Preislogik anwenden...";
      default: return step.result_summary || step.action || "...";
    }
  };

  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setTrace([]);

    try {
      const resp = await fetch(`${API}${activeProduct.apiPrefix}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionRef.current,
          message: text,
          mode: pricingMode,
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
            if (line.startsWith("event: ")) eventType = line.slice(7).trim();
            else if (line.startsWith("data: ")) data += line.slice(6);
            else if (line.startsWith("data:")) data += line.slice(5);
          }
          if (!data) continue;
          try {
            const parsed = JSON.parse(data);
            switch (eventType) {
              case "session":
                if (parsed.session_id) sessionRef.current = parsed.session_id;
                break;
              case "message": {
                let content = parsed.content || "";
                if (typeof content === "string" && content.trimStart().startsWith("{")) {
                  try {
                    const inner = JSON.parse(content);
                    if (inner.message) content = inner.message;
                  } catch { /* not JSON, keep as-is */ }
                }
                setMessages((prev) => [...prev, { role: "assistant", content }]);
              }
                break;
              case "trace": {
                const traceStep: TraceStep = {
                  step: trace.length + 1,
                  action: parsed.step || "step",
                  result_summary: parsed.label,
                  params: parsed.payload,
                };
                setTrace((prev) => [...prev, traceStep]);
                const desc = describeStep(traceStep);
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last?.role === "status") return [...prev.slice(0, -1), { role: "status", content: desc }];
                  return [...prev, { role: "status", content: desc }];
                });
                break;
              }
              case "angebot":
                setAngebot(parsed);
                setProvenance(parsed.provenance || []);
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last?.role === "status") return prev.slice(0, -1);
                  return prev;
                });
                break;
              case "done":
                break;
            }
          } catch { /* skip */ }
        }
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Verbindungsfehler: ${e instanceof Error ? e.message : "Unbekannt"}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    setMessages([]);
    setTrace([]);
    setAngebot(null);
    sessionRef.current = null;
  };

  return (
    <div className="h-screen bg-gradient-to-br from-stone-50 via-blue-50/20 to-stone-50 flex flex-col overflow-hidden">
      <div className="flex-1 flex min-h-0">
        {/* Sidebar */}
        <aside className={cn(
          "h-full bg-white/70 backdrop-blur-xl border-r border-slate-200/60 flex flex-col transition-all duration-300",
          sidebarCollapsed ? "w-[72px]" : "w-64"
        )}>
          <div className="h-16 flex items-center px-4 border-b border-slate-200/60">
            <div className="flex items-center gap-3 min-w-0">
              {sidebarCollapsed ? (
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center shadow-lg shadow-blue-800/25">
                  <Zap className="w-5 h-5 text-white" />
                </div>
              ) : (
                <div className="flex items-center gap-3 animate-fade-in">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center shadow-lg shadow-blue-800/25">
                    <Zap className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-sm font-bold text-slate-900 leading-tight">SmartCal@EG</h1>
                    <p className="text-[10px] text-slate-400 font-medium">{activeProduct.name} · {activeProduct.lpvRef}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {!sidebarCollapsed && (
              <div className="px-3 py-2">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Phase 1</span>
              </div>
            )}
            {PRODUCTS.map((p) => (
              <button
                key={p.id}
                onClick={() => switchProduct(p)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
                  activeProduct.id === p.id
                    ? "bg-[#0046ad] text-white shadow-lg shadow-blue-800/25"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                )}
              >
                <span className="w-5 h-5 text-center text-xs flex-shrink-0">{p.shortLabel}</span>
                {!sidebarCollapsed && <span>{p.name}</span>}
              </button>
            ))}
          </nav>

          {!sidebarCollapsed && (
            <div className="mx-3 mb-2 space-y-1">
              <a href="/status.html" target="_blank" rel="noopener noreferrer"
                className="block px-3 py-2 text-xs text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                📋 PoC → MVP Status
              </a>
              <a href="/audit-kalkulationsnachweise.html" target="_blank" rel="noopener noreferrer"
                className="block px-3 py-2 text-xs text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                📊 Kalkulationsnachweise
              </a>
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="mx-3 mb-3 p-2 rounded-lg border border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4 mx-auto" /> : <ChevronLeft className="w-4 h-4 mx-auto" />}
          </button>
        </aside>

        {/* Main */}
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
          <header className="h-16 border-b border-slate-200/60 bg-white backdrop-blur-xl sticky top-0 z-10 flex items-center justify-between px-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{activeProduct.name}-Kalkulator</h2>
              <p className="text-xs text-slate-500">{activeProduct.subtitle}</p>
            </div>
            <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
              <span className="px-3 py-1.5 rounded-md text-xs font-semibold bg-[#0046ad] text-white shadow">
                Wissensgraph
              </span>
            </div>
            <button
              onClick={handleNewSession}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Neue Sitzung starten"
            >
              <Trash2 className="h-4 w-4" />
              <span>Neue Anfrage</span>
            </button>
          </header>

          <div className="flex-1 min-h-0 p-6">
            <div className="h-full flex gap-4">
              {/* Chat */}
              <div className={cn(
                "bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden flex flex-col transition-all duration-300 min-h-0",
                angebot || trace.length > 0 ? "w-1/2" : "w-full"
              )}>
                <ChatPanel
                  messages={messages}
                  onSend={handleSend}
                  loading={loading}
                  placeholder={activeProduct.placeholder}
                  suggestions={activeProduct.suggestions}
                />
              </div>

              {/* Angebot + Trace */}
              {(angebot || trace.length > 0) && (
                <div className="w-1/2 overflow-y-auto min-h-0 space-y-4 animate-slide-in-right">
                  {trace.length > 0 && <AgentTrace steps={trace} loading={loading} />}
                  {angebot && <BlitzschutzAngebotPanel angebot={angebot} />}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      <footer className="h-10 flex items-center justify-center border-t border-slate-200/60 bg-white/70 backdrop-blur-xl">
        <p className="text-xs text-slate-400 font-medium">Synapse OS for TÜV Süd · {activeProduct.name} {activeProduct.lpvRef}</p>
      </footer>
    </div>
  );
}
