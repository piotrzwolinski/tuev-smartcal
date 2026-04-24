"use client";

import { Calculator, AlertTriangle, CheckCircle, Lightbulb, Shield, Database, Code, FileText } from "lucide-react";

export interface ProvenanceStep {
  step: string;
  source: string;
  value: unknown;
  node_id: string;
}

export interface BlitzschutzAngebot {
  gewerk: string;
  total: number;
  breakdown: { grund: number; pruef: number; reise: number; bericht: number; subtotal: number };
  zuschlaege: { name: string; percent: number; amount: number }[];
  confidence: number;
  confidence_reason: string;
  similar: unknown[];
  lpv_referenz: string;
  warnings: string[];
  mode?: "graph" | "python";
  provenance?: ProvenanceStep[];
}

interface Props {
  angebot: BlitzschutzAngebot;
}

function formatEuro(n: number): string {
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(n);
}

export default function BlitzschutzAngebotPanel({ angebot }: Props) {
  const bd = angebot.breakdown;
  const confLevel = angebot.confidence >= 0.9 ? "high" : angebot.confidence >= 0.7 ? "med" : "low";

  return (
    <div className="space-y-4 animate-slide-in-right">
      {/* Total */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center">
              <Calculator className="w-3.5 h-3.5 text-white" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900">Blitzschutz-Kalkulation</h3>
          </div>
          <ConfidencePill level={confLevel} value={angebot.confidence} />
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50/80">
              <th className="text-left px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Position</th>
              <th className="text-left px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Beschreibung</th>
              <th className="text-right px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Betrag</th>
            </tr>
          </thead>
          <tbody>
            <Row label="Grundkosten" sub="Pauschale Auftragsverwaltung 256€ + Prüfmittel + Tagegeld" amount={bd.grund} />
            <Row label="Prüfkosten" sub="LPV B04 §8.1 · 33€/Messstelle + Staffeln" amount={bd.pruef} highlight />
            <Row label="Reisekosten" sub="1,10€/km PKW + Reisezeit × 180€/h" amount={bd.reise} />
            <Row label="Berichterstellung" sub="klein 119€ / standard 380€ / komplex 550€" amount={bd.bericht} />

            {angebot.zuschlaege.map((z, i) => (
              <tr key={i} className="border-t border-red-100 bg-red-50/50">
                <td className="px-4 py-2 font-medium text-red-700 text-[13px]">+ {z.name}</td>
                <td className="px-4 py-2 text-red-400 text-xs">+{(z.percent * 100).toFixed(0)}%</td>
                <td className="px-4 py-2 text-right font-semibold text-red-700 tabular-nums">{formatEuro(z.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-slate-200 bg-slate-50/80">
              <td className="px-4 py-3 font-bold text-base text-slate-800" colSpan={2}>
                Gesamtbetrag (netto)
              </td>
              <td className="px-4 py-3 text-right font-bold text-base tabular-nums" style={{ color: "#0046ad" }}>
                {formatEuro(angebot.total)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Confidence / Warning */}
      {angebot.confidence < 1.0 && angebot.confidence_reason && (
        <div className={`bg-white rounded-2xl shadow-xl shadow-slate-200/50 border p-4 animate-fade-in ${
          confLevel === "low" ? "border-red-200/60" : "border-amber-200/60"
        }`}>
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-5 h-5 rounded-md flex items-center justify-center ${
              confLevel === "low" ? "bg-red-100" : "bg-amber-100"
            }`}>
              <AlertTriangle className={`w-3 h-3 ${confLevel === "low" ? "text-red-600" : "text-amber-600"}`} />
            </div>
            <h4 className={`font-semibold text-sm ${confLevel === "low" ? "text-red-800" : "text-amber-800"}`}>
              Confidence-Hinweis
            </h4>
          </div>
          <p className={`text-[13px] ${confLevel === "low" ? "text-red-700" : "text-amber-700"}`}>
            {angebot.confidence_reason}
          </p>
        </div>
      )}

      {angebot.warnings.length > 0 && (
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 p-4 animate-fade-in">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-5 h-5 rounded-md bg-slate-100 flex items-center justify-center">
              <Lightbulb className="w-3 h-3 text-slate-600" />
            </div>
            <h4 className="font-semibold text-slate-800 text-sm">Hinweise</h4>
          </div>
          <ul className="list-disc list-inside text-[13px] text-slate-600 space-y-1 ml-1">
            {angebot.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* Mode + LPV Reference */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 p-4 animate-fade-in">
        <div className="flex items-center gap-2 mb-1">
          {angebot.mode === "graph" ? <Database className="w-4 h-4 text-[#0046ad]" /> : <Code className="w-4 h-4 text-slate-600" />}
          <span className={`text-xs font-semibold ${angebot.mode === "graph" ? "text-[#0046ad]" : "text-slate-600"}`}>
            {angebot.mode === "graph" ? "Wissensgraph-Engine" : "Python-Engine (hardcoded)"}
          </span>
        </div>
        <p className="text-[13px] text-slate-500">
          {angebot.gewerk} · {angebot.lpv_referenz} · LPV 2025/2026 TÜV SÜD Industrie Service GmbH
        </p>
      </div>

      {/* Provenance (only graph mode) */}
      {angebot.provenance && angebot.provenance.length > 0 && (
        <details className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden animate-fade-in">
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Herkunft der Werte — {angebot.provenance.length} Graph-Abfragen
          </summary>
          <div className="px-4 pb-4 space-y-1.5 border-t border-slate-100">
            {angebot.provenance.map((p, i) => (
              <div key={i} className="text-xs flex items-start gap-2 mt-1.5">
                <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium flex-shrink-0 border ${
                  p.step === "pruefkosten" ? "bg-blue-50 text-blue-700 border-blue-200" :
                  p.step === "grundkosten" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                  p.step === "zuschlag" ? "bg-red-50 text-red-700 border-red-200" :
                  p.step === "cross_sell" ? "bg-purple-50 text-purple-700 border-purple-200" :
                  "bg-amber-50 text-amber-700 border-amber-200"
                }`}>
                  {p.step.toUpperCase().slice(0,8)}
                </span>
                <span className="text-slate-500">{p.source}</span>
                <span className="text-slate-400 ml-auto font-mono">{typeof p.value === 'number' ? `${p.value}€` : String(p.value).slice(0,25)}</span>
                {p.node_id && <span className="text-[10px] text-slate-300 font-mono">{p.node_id}</span>}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function Row({ label, sub, amount, highlight }: { label: string; sub: string; amount: number; highlight?: boolean }) {
  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50/50 transition">
      <td className={`px-4 py-2.5 font-medium text-[13px] ${highlight ? "text-[#0046ad]" : "text-slate-800"}`}>{label}</td>
      <td className="px-4 py-2.5 text-slate-400 text-xs">{sub}</td>
      <td className={`px-4 py-2.5 text-right font-semibold tabular-nums ${highlight ? "text-[#0046ad]" : "text-slate-800"}`}>
        {formatEuro(amount)}
      </td>
    </tr>
  );
}

function ConfidencePill({ level, value }: { level: string; value: number }) {
  const cls = {
    high: "bg-emerald-50 text-emerald-700 border-emerald-200",
    med: "bg-amber-50 text-amber-700 border-amber-200",
    low: "bg-red-50 text-red-700 border-red-200",
  }[level] || "";
  const Icon = level === "high" ? CheckCircle : AlertTriangle;
  return (
    <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider border ${cls}`}>
      <Icon className="w-3 h-3" />
      {Math.round(value * 100)}%
    </div>
  );
}
