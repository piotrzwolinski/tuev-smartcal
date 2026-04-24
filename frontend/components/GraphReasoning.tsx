"use client";

import { useState } from "react";
import {
  Building2,
  ArrowDown,
  Search,
  GitBranch,
  Calculator,
  Zap,
  Percent,
  Lightbulb,
  HelpCircle,
  CheckCircle2,
  ChevronDown,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ReasoningStep {
  id: string;
  icon: React.ReactNode;
  color: string;       // bg color for icon
  title: string;
  subtitle: string;
  nodes: Array<{
    label: string;
    type: "node" | "edge" | "value" | "formula" | "result";
    color?: string;
  }>;
  detail?: string;
  graphPath?: string;  // cypher-like path
}

const STEPS: ReasoningStep[] = [
  {
    id: "input",
    icon: <MessageSquare className="w-4 h-4" />,
    color: "bg-slate-700",
    title: "Kundenanfrage",
    subtitle: "Freitext wird analysiert",
    nodes: [
      { label: "\"Krankenhaus, 20.000m², 8 Etagen, 5 Aufzüge, Notstromaggregat\"", type: "value", color: "bg-slate-600" },
    ],
    detail: "Der Coordinator-LLM extrahiert strukturierte Parameter aus dem Freitext.",
  },
  {
    id: "params",
    icon: <Search className="w-4 h-4" />,
    color: "bg-blue-600",
    title: "Parameter-Extraktion",
    subtitle: "LLM → strukturierte Daten",
    nodes: [
      { label: "gebaeudetyp: Krankenhaus", type: "value", color: "bg-blue-500" },
      { label: "bgf_m2: 20.000", type: "value", color: "bg-blue-500" },
      { label: "etagen: 8", type: "value", color: "bg-blue-500" },
      { label: "aufzuege: 5", type: "value", color: "bg-blue-500" },
    ],
  },
  {
    id: "gebaeude",
    icon: <Building2 className="w-4 h-4" />,
    color: "bg-emerald-600",
    title: "Schritt 1: Gebäudetyp identifizieren",
    subtitle: "Graph-Lookup nach Gebäudetyp",
    nodes: [
      { label: "Krankenhaus / Klinik", type: "node", color: "bg-emerald-500" },
    ],
    graphPath: "MATCH (g:Gebaeudetyp) WHERE g.name CONTAINS 'Krankenhaus'",
  },
  {
    id: "pflicht",
    icon: <GitBranch className="w-4 h-4" />,
    color: "bg-emerald-600",
    title: "Schritt 2: Pflichtprüfungen ermitteln",
    subtitle: "ERFORDERT_PRUEFUNG-Kanten vom Gebäudetyp",
    nodes: [
      { label: "Krankenhaus / Klinik", type: "node", color: "bg-emerald-500" },
      { label: "ERFORDERT_PRUEFUNG", type: "edge", color: "bg-emerald-400" },
      { label: "Prüfung Blitzschutzanlage", type: "node", color: "bg-blue-500" },
      { label: "Prüfung Brandmeldeanlage (BMA)", type: "node", color: "bg-blue-500" },
    ],
    detail: "Zusätzlich: Aufzüge im Input → DL_AUFZUG_HP automatisch hinzugefügt",
    graphPath: "MATCH (g:Gebaeudetyp)-[r:ERFORDERT_PRUEFUNG]->(d:Dienstleistung)",
  },
  {
    id: "preise",
    icon: <Calculator className="w-4 h-4" />,
    color: "bg-amber-600",
    title: "Schritt 3: Preispositionen laden",
    subtitle: "HAT_PREISPOSITION + HAT_STAFFEL für jede Dienstleistung",
    nodes: [
      { label: "Aufzug Hauptprüfung", type: "node", color: "bg-blue-500" },
      { label: "→ Hauptprüfung pro Aufzug (385 €)", type: "value", color: "bg-amber-500" },
      { label: "→ Zuschlag pro Haltestelle über 5 (35 €)", type: "value", color: "bg-amber-500" },
      { label: "→ Staffel: ab 5 Aufzüge → 350 €", type: "value", color: "bg-orange-400" },
      { label: "Blitzschutzanlage", type: "node", color: "bg-blue-500" },
      { label: "→ Prüfung pro Anlage (280 €)", type: "value", color: "bg-amber-500" },
      { label: "→ Zusatz pro Ableitung über 8 (18 €)", type: "value", color: "bg-amber-500" },
      { label: "BMA", type: "node", color: "bg-blue-500" },
      { label: "→ Grundpauschale (450 €)", type: "value", color: "bg-amber-500" },
      { label: "→ Prüfung pro Melder (8,50 €)", type: "value", color: "bg-amber-500" },
      { label: "→ Staffel: ab 200 Melder → 7,20 €", type: "value", color: "bg-orange-400" },
      { label: "→ Staffel: ab 500 Melder → 6,00 €", type: "value", color: "bg-orange-400" },
    ],
    graphPath: "MATCH (d:Dienstleistung)-[:HAT_PREISPOSITION]->(p)-[:HAT_STAFFEL]->(s)",
  },
  {
    id: "schaetzung",
    icon: <Zap className="w-4 h-4" />,
    color: "bg-violet-600",
    title: "Schritt 4: Fehlende Mengen schätzen",
    subtitle: "SCHAETZT-Kanten mit Formeln + Sicherheitsfaktoren",
    nodes: [
      { label: "BGF (20.000m²)", type: "node", color: "bg-violet-500" },
      { label: "SCHAETZT: etagen + 1", type: "formula" },
      { label: "→ Haltestellen ≈ 9 (×1.0)", type: "result" },
      { label: "SCHAETZT: (bgf / etagen) / 200", type: "formula" },
      { label: "→ Ableitungen ≈ 17 (×1.3)", type: "result" },
      { label: "SCHAETZT: bgf / 30", type: "formula" },
      { label: "→ Brandmelder ≈ 800 (×1.2)", type: "result" },
      { label: "SCHAETZT: bgf / 25", type: "formula" },
      { label: "→ Stromkreise ≈ 1.040 (×1.3)", type: "result" },
      { label: "SCHAETZT: bgf / 8", type: "formula" },
      { label: "→ Geräte ≈ 3.500 (×1.4)", type: "result" },
    ],
    detail: "Sicherheitsfaktoren (×1.2 bis ×1.4) sorgen dafür, dass die Schätzung eher zu hoch als zu niedrig ausfällt.",
    graphPath: "MATCH (m:Merkmal)-[r:SCHAETZT]->(t:Merkmal) // r.formel, r.sicherheitsfaktor",
  },
  {
    id: "berechnung",
    icon: <Calculator className="w-4 h-4" />,
    color: "bg-blue-700",
    title: "Schritt 5: Preise berechnen",
    subtitle: "Mengen × Staffelpreise + Schwellwert-Logik",
    nodes: [
      { label: "Aufzug HP: 5 × 350 € = 1.750 €", type: "result" },
      { label: "Aufzug Haltestellen: (9−5) × 35 € = 140 €", type: "result" },
      { label: "Blitzschutz: 1 × 280 € = 280 €", type: "result" },
      { label: "Blitz Ableitungen: (17−8) × 18 € = 162 €", type: "result" },
      { label: "BMA Grundpauschale: 1 × 450 € = 450 €", type: "result" },
      { label: "BMA Melder: 800 × 6,00 € = 4.800 €", type: "result" },
    ],
    detail: "Staffellogik: 5 Aufzüge → 350 € statt 385 €. 800 Melder → 6,00 € statt 8,50 € (Staffel ab 500). Haltestellen: nur über Schwellwert 5 berechnet (9−5=4). Ableitungen: nur über Schwellwert 8 (17−8=9).",
  },
  {
    id: "buendel",
    icon: <Percent className="w-4 h-4" />,
    color: "bg-emerald-700",
    title: "Schritt 6: Bündelrabatte prüfen",
    subtitle: "GLEICHE_BEGEHUNG zwischen gebuchten Dienstleistungen",
    nodes: [
      { label: "BMA", type: "node", color: "bg-blue-500" },
      { label: "GLEICHE_BEGEHUNG (5%)", type: "edge", color: "bg-emerald-400" },
      { label: "Blitzschutz", type: "node", color: "bg-blue-500" },
      { label: "→ 5% auf kleinere Position (442 €) = −22,10 €", type: "result" },
    ],
    detail: "Rabatt wird auf die kleinere der beiden Positionen (Blitzschutz: 442 €) angewendet.",
    graphPath: "MATCH (a:DL)-[:GLEICHE_BEGEHUNG]->(b:DL) WHERE a.id IN $ids AND b.id IN $ids",
  },
  {
    id: "empfehlungen",
    icon: <Lightbulb className="w-4 h-4" />,
    color: "bg-amber-600",
    title: "Schritt 7: Empfehlungen generieren",
    subtitle: "EMPFIEHLT-Kanten von gebuchten zu nicht-gebuchten Services",
    nodes: [
      { label: "Aufzug HP", type: "node", color: "bg-blue-500" },
      { label: "EMPFIEHLT", type: "edge", color: "bg-amber-400" },
      { label: "DGUV V3 ortsfest (~12.480 €)", type: "node", color: "bg-amber-500" },
      { label: "BMA", type: "node", color: "bg-blue-500" },
      { label: "EMPFIEHLT", type: "edge", color: "bg-amber-400" },
      { label: "RLT-Prüfung (~520 €)", type: "node", color: "bg-amber-500" },
      { label: "BMA", type: "node", color: "bg-blue-500" },
      { label: "EMPFIEHLT", type: "edge", color: "bg-amber-400" },
      { label: "Sprinkleranlage (~8.570 €)", type: "node", color: "bg-amber-500" },
    ],
    graphPath: "MATCH (a:DL)-[r:EMPFIEHLT]->(b:DL) WHERE a.id IN $ids AND NOT b.id IN $ids",
  },
  {
    id: "rueckfragen",
    icon: <HelpCircle className="w-4 h-4" />,
    color: "bg-amber-500",
    title: "Schritt 8: Rückfragen identifizieren",
    subtitle: "Geschätzte Werte + fehlende ERFORDERT_MERKMAL",
    nodes: [
      { label: "Haltestellen: geschätzt ~9 — stimmt das?", type: "value", color: "bg-amber-400" },
      { label: "Ableitungen: geschätzt ~17 — stimmt das?", type: "value", color: "bg-amber-400" },
      { label: "Brandmelder: geschätzt ~800 — stimmt das?", type: "value", color: "bg-amber-400" },
      { label: "Sprachalarmanlage (SAA) vorhanden?", type: "value", color: "bg-amber-400" },
      { label: "Aufzugstyp?", type: "value", color: "bg-amber-400" },
      { label: "Entfernung zum Standort?", type: "value", color: "bg-amber-400" },
    ],
  },
  {
    id: "ergebnis",
    icon: <CheckCircle2 className="w-4 h-4" />,
    color: "bg-blue-700",
    title: "Ergebnis: Kalkulation",
    subtitle: "6 Positionen, 1 Rabatt, 3 Empfehlungen, 6 Rückfragen",
    nodes: [
      { label: "Aufzugsprüfung HP: 1.890,00 €", type: "result" },
      { label: "Blitzschutzanlage: 442,00 €", type: "result" },
      { label: "Brandmeldeanlage: 5.250,00 €", type: "result" },
      { label: "Bündelrabatt BMA+Blitz: −22,10 €", type: "result" },
      { label: "GESAMTBETRAG: 7.559,90 €", type: "value", color: "bg-blue-700" },
    ],
    detail: "19 Fakten mit Herkunftsnachweis (GRAPH / ESTIMATED / CALCULATED). Alle Preise aus dem Wissensgraph, keine LLM-Halluzination.",
  },
];

export default function GraphReasoning() {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900 mb-1">
          Graph Reasoning: Krankenhaus-Kalkulation
        </h3>
        <p className="text-xs text-slate-500">
          Vollständiger Traversierungspfad durch 154 Knoten und 183 Kanten — vom Freitext bis zur Kalkulation.
          Jeder Preis ist durch den Graphen belegt, kein LLM-Halluzinationsrisiko.
        </p>
      </div>

      {/* Steps */}
      <div className="relative">
        {STEPS.map((step, i) => {
          const isExpanded = expandedStep === step.id;
          const isLast = i === STEPS.length - 1;

          return (
            <div key={step.id} className="flex gap-4">
              {/* Timeline */}
              <div className="flex flex-col items-center">
                <div className={cn(
                  "w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-white shadow-lg",
                  step.color,
                )}>
                  {step.icon}
                </div>
                {!isLast && (
                  <div className="w-px flex-1 bg-gradient-to-b from-slate-300 to-slate-200 min-h-[20px]" />
                )}
              </div>

              {/* Content */}
              <div className={cn("flex-1 pb-6", isLast && "pb-0")}>
                <button
                  onClick={() => setExpandedStep(isExpanded ? null : step.id)}
                  className="w-full text-left bg-white rounded-xl border border-slate-200/60 shadow-sm hover:shadow-md hover:border-slate-300 transition-all overflow-hidden"
                >
                  <div className="px-4 py-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-slate-900">{step.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{step.subtitle}</div>
                    </div>
                    <ChevronDown className={cn(
                      "w-4 h-4 text-slate-400 transition-transform flex-shrink-0",
                      isExpanded && "rotate-180",
                    )} />
                  </div>

                  {/* Always show nodes preview */}
                  <div className="px-4 pb-3 flex flex-wrap gap-1.5">
                    {step.nodes.slice(0, isExpanded ? undefined : 4).map((node, j) => (
                      <span
                        key={j}
                        className={cn(
                          "inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium",
                          node.type === "node" && (node.color || "bg-blue-100 text-blue-700") + " text-white",
                          node.type === "edge" && "bg-slate-100 text-slate-600 border border-slate-200 italic",
                          node.type === "value" && (node.color || "bg-slate-100") + " text-white",
                          node.type === "formula" && "bg-violet-100 text-violet-700 font-mono border border-violet-200",
                          node.type === "result" && "bg-blue-50 text-blue-800 border border-blue-200 tabular-nums",
                        )}
                      >
                        {node.label}
                      </span>
                    ))}
                    {!isExpanded && step.nodes.length > 4 && (
                      <span className="text-[11px] text-slate-400 px-1 py-0.5">
                        +{step.nodes.length - 4} mehr
                      </span>
                    )}
                  </div>
                </button>

                {/* Expanded detail */}
                {isExpanded && (step.detail || step.graphPath) && (
                  <div className="mt-2 px-4 py-3 bg-slate-50 rounded-xl border border-slate-200/60 text-xs space-y-2 animate-fade-in">
                    {step.detail && (
                      <p className="text-slate-600 leading-relaxed">{step.detail}</p>
                    )}
                    {step.graphPath && (
                      <div className="bg-slate-900 text-emerald-400 px-3 py-2 rounded-lg font-mono text-[11px] overflow-x-auto">
                        {step.graphPath}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Traversierte Knoten", value: "38", sub: "von 154" },
          { label: "Traversierte Kanten", value: "47", sub: "von 183" },
          { label: "SCHAETZT-Formeln", value: "9", sub: "angewendet" },
          { label: "Herkunftsfakten", value: "19", sub: "dokumentiert" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-slate-200/60 p-3 shadow-sm text-center">
            <div className="text-xl font-bold text-slate-900">{s.value}</div>
            <div className="text-[10px] text-slate-400">{s.label}</div>
            <div className="text-[10px] text-slate-300">{s.sub}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
