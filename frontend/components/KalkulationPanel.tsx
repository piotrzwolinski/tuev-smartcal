"use client";

import { Calculator, HelpCircle, Lightbulb, FileText } from "lucide-react";
import type { Kalkulation } from "@/lib/types";

interface Props {
  kalkulation: Kalkulation;
}

function formatEuro(n: number): string {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  }).format(n);
}

export default function KalkulationPanel({ kalkulation }: Props) {
  if (kalkulation.raw_response) {
    return (
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 p-4 animate-fade-in">
        <h3 className="font-semibold text-sm text-slate-900 mb-2">Agent Response</h3>
        <pre className="text-xs text-slate-500 whitespace-pre-wrap overflow-auto max-h-96">
          {kalkulation.raw_response}
        </pre>
      </div>
    );
  }

  const positionen = kalkulation.positionen || [];
  const zuschlaege = kalkulation.zuschlaege || [];
  const rabatte = kalkulation.rabatte || [];
  const gesamt = kalkulation.gesamtbetrag || 0;
  const rueckfragen = kalkulation.rueckfragen || [];
  const empfehlungen = kalkulation.empfehlungen || [];

  return (
    <div className="space-y-4 animate-slide-in-right">
      {/* Main table */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center">
            <Calculator className="w-3.5 h-3.5 text-white" />
          </div>
          <h3 className="font-semibold text-sm text-slate-900">Kalkulation</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50/80">
              <th className="text-left px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Position</th>
              <th className="text-left px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Beschreibung</th>
              <th className="text-right px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Menge</th>
              <th className="text-right px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">EP</th>
              <th className="text-right px-4 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {positionen.map((pos, i) => (
              <tr key={i} className="border-t border-slate-100 hover:bg-slate-50/50 transition">
                <td className="px-4 py-2.5 font-medium text-slate-800 text-[13px]">
                  {pos.dienstleistung}
                </td>
                <td className="px-4 py-2.5 text-slate-400 text-xs">
                  {pos.beschreibung || "\u2014"}
                </td>
                <td className="px-4 py-2.5 text-right text-slate-500 tabular-nums">
                  {pos.menge ?? "\u2014"}
                </td>
                <td className="px-4 py-2.5 text-right text-slate-500 tabular-nums">
                  {pos.einheitspreis ? formatEuro(pos.einheitspreis) : "\u2014"}
                </td>
                <td className="px-4 py-2.5 text-right font-semibold text-slate-800 tabular-nums">
                  {formatEuro(pos.betrag)}
                </td>
              </tr>
            ))}

            {zuschlaege.map((z, i) => (
              <tr key={`z-${i}`} className="border-t border-red-100 bg-red-50/50">
                <td className="px-4 py-2 font-medium text-red-700 text-[13px]">
                  + {z.name}
                </td>
                <td className="px-4 py-2 text-red-400 text-xs" colSpan={3}>
                  {z.grund || ""}
                </td>
                <td className="px-4 py-2 text-right font-semibold text-red-700 tabular-nums">
                  {formatEuro(z.betrag)}
                </td>
              </tr>
            ))}

            {rabatte.map((r, i) => (
              <tr key={`r-${i}`} className="border-t border-emerald-100 bg-emerald-50/50">
                <td className="px-4 py-2 font-medium text-emerald-700 text-[13px]">
                  &minus; {r.name}
                </td>
                <td className="px-4 py-2 text-emerald-400 text-xs" colSpan={3}>
                  {r.grund || ""}
                </td>
                <td className="px-4 py-2 text-right font-semibold text-emerald-700 tabular-nums">
                  &minus;{formatEuro(Math.abs(r.betrag))}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-slate-200 bg-slate-50/80">
              <td className="px-4 py-3 font-bold text-base text-slate-800" colSpan={4}>
                Gesamtbetrag (netto)
              </td>
              <td className="px-4 py-3 text-right font-bold text-base text-gradient tabular-nums">
                {formatEuro(gesamt)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Rueckfragen */}
      {rueckfragen.length > 0 && (
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-amber-200/60 p-4 animate-fade-in">
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-5 h-5 rounded-md bg-amber-100 flex items-center justify-center">
              <HelpCircle className="w-3 h-3 text-amber-600" />
            </div>
            <h4 className="font-semibold text-amber-800 text-sm">
              Rückfragen an den Kunden
            </h4>
          </div>
          <ul className="list-disc list-inside text-[13px] text-amber-700 space-y-1 ml-1">
            {rueckfragen.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Empfehlungen */}
      {empfehlungen.length > 0 && (
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-blue-200/60 p-4 animate-fade-in">
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-5 h-5 rounded-md bg-blue-100 flex items-center justify-center">
              <Lightbulb className="w-3 h-3 text-blue-600" />
            </div>
            <h4 className="font-semibold text-blue-800 text-sm">
              Empfehlungen
            </h4>
          </div>
          <div className="space-y-2">
            {empfehlungen.map((emp, i) => (
              <div key={i} className="text-[13px]">
                <span className="font-semibold text-blue-700">
                  {emp.dienstleistung}
                </span>
                <span className="text-blue-600"> &mdash; {emp.grund}</span>
                {typeof emp.geschaetzter_preis === "number" && !isNaN(emp.geschaetzter_preis) && (
                  <span className="text-blue-400 ml-1 tabular-nums">
                    (~{formatEuro(emp.geschaetzter_preis)})
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Facts / Provenance */}
      {kalkulation.facts && kalkulation.facts.length > 0 && (
        <details className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden animate-fade-in">
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Herkunft der Daten ({kalkulation.facts.length} Fakten)
          </summary>
          <div className="px-4 pb-4 space-y-1.5 border-t border-slate-100">
            {kalkulation.facts.map((f, i) => (
              <div key={i} className="text-xs flex items-start gap-2 mt-1.5">
                <span
                  className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium flex-shrink-0 border ${
                    f.source.includes("GRAPH") || f.source.includes("Beziehung") || f.source.includes("\u2192")
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : f.source.includes("CALCULATED") || f.source.includes("Formel")
                        ? "bg-blue-50 text-blue-700 border-blue-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                  }`}
                >
                  {f.source.includes("GRAPH") || f.source.includes("Beziehung") || f.source.includes("\u2192") ? "GRAPH" : f.source.includes("Formel") ? "CALC" : "EST"}
                </span>
                <span className="text-slate-500">{f.claim}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
