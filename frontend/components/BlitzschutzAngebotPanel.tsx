"use client";

import { Calculator, AlertTriangle, CheckCircle, Lightbulb, Shield, Database, Code } from "lucide-react";

export interface ProvenanceStep {
  step: string;
  source: string;
  value: unknown;
  node_id: string;
  ref?: string;
}

export interface BlitzschutzAngebot {
  gewerk: string;
  total: number;
  breakdown: { grund: number; pruef: number; reise: number; bericht: number; subtotal: number };
  zuschlaege: { name: string; percent: number; amount: number }[];
  zusatzleistungen?: { name: string; preis: number; positionen: { name: string; betrag: number }[]; quelle: string }[];
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
            <h3 className="font-semibold text-sm text-slate-900">{angebot.gewerk?.split(" ")[0] || "Kalkulation"}-Kalkulation</h3>
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

            {angebot.zusatzleistungen && angebot.zusatzleistungen.length > 0 && (
              <>
                <tr className="border-t-2 border-blue-200">
                  <td colSpan={3} className="px-4 py-2 text-[11px] font-semibold text-blue-600 uppercase tracking-wider bg-blue-50/40">
                    Zusatzleistungen
                  </td>
                </tr>
                {angebot.zusatzleistungen.map((zl, i) =>
                  zl.positionen.map((pos, j) => (
                    <tr key={`zl-${i}-${j}`} className="border-t border-blue-100 bg-blue-50/20">
                      <td className="px-4 py-2 font-medium text-blue-800 text-[13px]">{j === 0 ? zl.name : ""}</td>
                      <td className="px-4 py-2 text-blue-500 text-xs">{pos.name}</td>
                      <td className="px-4 py-2 text-right font-semibold text-blue-800 tabular-nums">{j === 0 && zl.preis > 0 ? formatEuro(zl.preis) : ""}</td>
                    </tr>
                  ))
                )}
              </>
            )}
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

      {/* Quellennachweis */}
      {angebot.provenance && angebot.provenance.length > 0 && (
        <Quellennachweis provenance={angebot.provenance} />
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

type SourceType = "regel" | "fachexperte" | "heuristik" | "statistik";

function classifySource(ref: string | undefined): SourceType {
  if (!ref) return "heuristik";
  const r = ref.toLowerCase();
  if (r.startsWith("lpv") || r.startsWith("kalkulationshilfen")) return "regel";
  if (r.includes("veit") || r.includes("pausch")) return "fachexperte";
  if (r.includes("batch") || r.includes("statistik")) return "statistik";
  if (r.includes("heuristik")) return "heuristik";
  return "regel";
}

function extractQuelle(ref: string | undefined): string {
  if (!ref) return "—";
  const colon = ref.indexOf(":");
  if (colon > 0 && colon < 40) return ref.slice(0, colon);
  return ref.length > 45 ? ref.slice(0, 42) + "…" : ref;
}

const SOURCE_BADGE: Record<SourceType, { label: string; cls: string }> = {
  regel:        { label: "REGEL",        cls: "bg-emerald-50 text-emerald-700 border-emerald-300" },
  fachexperte:  { label: "EXPERTE",      cls: "bg-blue-50 text-blue-700 border-blue-300" },
  heuristik:    { label: "HEURISTIK",    cls: "bg-amber-50 text-amber-700 border-amber-300" },
  statistik:    { label: "STATISTIK",    cls: "bg-purple-50 text-purple-700 border-purple-300" },
};

const SKIP_STEPS = new Set(["confidence", "cross_sell"]);

function formatProvValue(v: unknown): string {
  const s = String(v);
  if (s.includes("roundtrip")) return s;
  if (s.includes("Tage")) return s;
  if (s.includes("km")) return s;
  const m = s.match(/([\d.,]+)\s*\(war\s*([\d.,]+)\)/);
  if (m) return `${parseFloat(m[1]).toLocaleString("de-DE")}€`;
  const m2 = s.match(/^([\d.,]+)$/);
  if (m2) {
    const n = parseFloat(m2[1].replace(",", ""));
    if (!isNaN(n) && n >= 1) return `${n.toLocaleString("de-DE")}€`;
  }
  return s.length > 35 ? s.slice(0, 32) + "…" : s;
}

function deduplicateProvenance(entries: ProvenanceStep[]): ProvenanceStep[] {
  const seen = new Set<string>();
  return entries.filter(p => {
    const key = `${p.step}:${p.source}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function Quellennachweis({ provenance }: { provenance: ProvenanceStep[] }) {
  const entries = deduplicateProvenance(provenance.filter(p => !SKIP_STEPS.has(p.step)));
  if (entries.length === 0) return null;

  const regelCount = entries.filter(p => classifySource(p.ref) === "regel").length;
  const experteCount = entries.filter(p => classifySource(p.ref) === "fachexperte").length;
  const heuristikCount = entries.filter(p => classifySource(p.ref) === "heuristik").length;

  return (
    <details className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden animate-fade-in">
      <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-50 transition flex items-center gap-2">
        <Shield className="w-4 h-4 text-[#0046ad]" />
        <span>Quellennachweis</span>
        <span className="ml-auto flex items-center gap-1.5 text-[10px]">
          {regelCount > 0 && <span className="px-1.5 py-0.5 rounded border bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold">{regelCount} Regel</span>}
          {experteCount > 0 && <span className="px-1.5 py-0.5 rounded border bg-blue-50 text-blue-700 border-blue-300 font-semibold">{experteCount} Experte</span>}
          {heuristikCount > 0 && <span className="px-1.5 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-300 font-semibold">{heuristikCount} Heuristik</span>}
        </span>
      </summary>
      <div className="border-t border-slate-100">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="bg-slate-50/80">
              <th className="text-left px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Position</th>
              <th className="text-right px-3 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Wert</th>
              <th className="text-left px-3 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Quelle</th>
              <th className="text-center px-3 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Typ</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((p, i) => {
              const typ = classifySource(p.ref);
              const badge = SOURCE_BADGE[typ];
              return (
                <tr key={i} className="border-t border-slate-50 hover:bg-slate-50/50 transition">
                  <td className="px-4 py-1.5 text-slate-700 font-medium">{p.source}</td>
                  <td className="px-3 py-1.5 text-right text-slate-500 font-mono tabular-nums">{formatProvValue(p.value)}</td>
                  <td className="px-3 py-1.5 text-slate-400" title={p.ref}>{extractQuelle(p.ref)}</td>
                  <td className="px-3 py-1.5 text-center">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-bold border ${badge.cls}`}>
                      {badge.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
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
