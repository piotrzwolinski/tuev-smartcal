"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Database,
  GitBranch,
  ArrowRight,
  Loader2,
  CircleDot,
  Link2,
  Zap,
  Calculator,
  Percent,
  Lightbulb,
  Building2,
  Shield,
  ChevronRight,
} from "lucide-react";
import GraphReasoning from "./GraphReasoning";
import { cn } from "@/lib/utils";

interface GraphSchema {
  nodes: Array<{ label: string; count: number }>;
  relationships: Array<{ rel: string; from_label: string; to_label: string; count: number }>;
  schaetzt_rules: Array<{ from_label: string; to_label: string; props: Record<string, unknown> }>;
  bundles: Array<{ a_name: string; b_name: string; rabatt: number; grund: string }>;
  services: Array<{ id: string; name: string; kategorie: string; preispositionen: number; merkmale: number }>;
  gt_services: Array<{ gt_name: string; dl_name: string; grund: string }>;
  empfiehlt: Array<{ from_name: string; to_name: string; grund: string; relevanz: string }>;
  totals: { nodes: number; edges: number; node_types: number; rel_types: number };
}

const NODE_COLORS: Record<string, string> = {
  Dienstleistung: "bg-blue-500",
  Gebaeudetyp: "bg-emerald-500",
  Preisposition: "bg-amber-500",
  Staffel: "bg-orange-400",
  Merkmal: "bg-violet-500",
  Zuschlag: "bg-red-500",
  Norm: "bg-slate-500",
  Qualifikation: "bg-cyan-500",
  Pruefintervall: "bg-teal-400",
  Nutzungsart: "bg-lime-500",
  Stressor: "bg-rose-500",
  Trait: "bg-pink-400",
  Gefahrenzone: "bg-red-600",
  Region: "bg-sky-400",
};

const NODE_LABELS: Record<string, string> = {
  Dienstleistung: "Prüfdienstleistungen",
  Gebaeudetyp: "Gebäudetypen",
  Preisposition: "Preispositionen",
  Staffel: "Mengenstaffeln",
  Merkmal: "Gebäudemerkmale",
  Zuschlag: "Zuschläge",
  Norm: "Normen & Vorschriften",
  Qualifikation: "Qualifikationen",
  Pruefintervall: "Prüfintervalle",
  Nutzungsart: "Nutzungsarten",
  Stressor: "Stressoren",
  Trait: "Traits",
  Gefahrenzone: "Gefahrenzonen",
  Region: "Regionen",
};

const REL_LABELS: Record<string, string> = {
  ERFORDERT_PRUEFUNG: "erfordert Prüfung",
  HAT_PREISPOSITION: "hat Preisposition",
  HAT_STAFFEL: "hat Mengenstaffel",
  ERFORDERT_MERKMAL: "erfordert Merkmal",
  SCHAETZT: "schätzt",
  GLEICHE_BEGEHUNG: "gleiche Begehung",
  EMPFIEHLT: "empfiehlt",
  LOEST_AUS: "löst aus",
  BASIERT_AUF: "basiert auf",
  ERFORDERT_QUALIFIKATION: "erfordert Qualifikation",
  HAT_NUTZUNGSART: "hat Nutzungsart",
  BESTIMMT_INTERVALL: "bestimmt Intervall",
  SCHLIESST_EIN: "schließt ein",
  BEWIRKT_ZUSCHLAG: "bewirkt Zuschlag",
  DEMANDS_TRAIT: "erfordert Eigenschaft",
  EXPOSES_TO: "exponiert an",
};

/* eslint-disable @typescript-eslint/no-explicit-any */

interface EdgeDetail {
  a_id: string; a_name: string; a_label: string;
  b_id: string; b_name: string; b_label: string;
  props: Record<string, any>;
}

interface NodeDetail {
  id: string;
  props: Record<string, any>;
}

export default function GraphExplorer() {
  const [schema, setSchema] = useState<GraphSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string>("reasoning");

  // Expandable detail state
  const [expandedRel, setExpandedRel] = useState<string | null>(null);
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [relDetails, setRelDetails] = useState<Record<string, EdgeDetail[]>>({});
  const [nodeDetails, setNodeDetails] = useState<Record<string, NodeDetail[]>>({});
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchRelDetails = useCallback(async (relType: string) => {
    if (relDetails[relType]) return;
    setDetailLoading(true);
    try {
      const r = await fetch(`http://localhost:8010/api/graph/edges/${relType}`);
      const data = await r.json();
      setRelDetails((prev) => ({ ...prev, [relType]: data.edges }));
    } catch { /* ignore */ }
    setDetailLoading(false);
  }, [relDetails]);

  const fetchNodeDetails = useCallback(async (label: string) => {
    if (nodeDetails[label]) return;
    setDetailLoading(true);
    try {
      const r = await fetch(`http://localhost:8010/api/graph/nodes/${label}`);
      const data = await r.json();
      setNodeDetails((prev) => ({ ...prev, [label]: data.nodes }));
    } catch { /* ignore */ }
    setDetailLoading(false);
  }, [nodeDetails]);

  const toggleRel = (relType: string) => {
    if (expandedRel === relType) {
      setExpandedRel(null);
    } else {
      setExpandedRel(relType);
      fetchRelDetails(relType);
    }
  };

  const toggleNode = (label: string) => {
    if (expandedNode === label) {
      setExpandedNode(null);
    } else {
      setExpandedNode(label);
      fetchNodeDetails(label);
    }
  };

  useEffect(() => {
    fetch("http://localhost:8010/api/graph/schema")
      .then((r) => r.json())
      .then((data) => {
        setSchema(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="text-center text-slate-500 py-12">
        Verbindung zum Backend fehlgeschlagen.
      </div>
    );
  }

  const sections = [
    { id: "reasoning", label: "Reasoning-Beispiel", icon: Zap },
    { id: "overview", label: "Übersicht", icon: Database },
    { id: "services", label: "Prüfungen", icon: Shield },
    { id: "buildings", label: "Gebäudetypen", icon: Building2 },
    { id: "pricing", label: "Preisregeln", icon: Calculator },
    { id: "estimation", label: "Schätzformeln", icon: Zap },
    { id: "bundles", label: "Bündelrabatte", icon: Percent },
    { id: "recommendations", label: "Empfehlungen", icon: Lightbulb },
  ];

  return (
    <div className="space-y-6">
      {/* Section tabs */}
      <div className="flex gap-2 flex-wrap">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              activeSection === s.id
                ? "bg-[#0046ad] text-white shadow-md shadow-blue-800/25"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            )}
          >
            <s.icon className="w-3.5 h-3.5" />
            {s.label}
          </button>
        ))}
      </div>

      {/* Reasoning Example */}
      {activeSection === "reasoning" && <GraphReasoning />}

      {/* Overview */}
      {activeSection === "overview" && (
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Knoten", value: schema.totals.nodes, icon: CircleDot, color: "text-blue-600 bg-blue-50" },
              { label: "Kanten", value: schema.totals.edges, icon: Link2, color: "text-emerald-600 bg-emerald-50" },
              { label: "Knotentypen", value: schema.totals.node_types, icon: Database, color: "text-violet-600 bg-violet-50" },
              { label: "Kantentypen", value: schema.totals.rel_types, icon: GitBranch, color: "text-amber-600 bg-amber-50" },
            ].map((stat) => (
              <div key={stat.label} className="bg-white rounded-xl border border-slate-200/60 p-4 shadow-sm">
                <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center mb-2", stat.color)}>
                  <stat.icon className="w-4 h-4" />
                </div>
                <div className="text-2xl font-bold text-slate-900">{stat.value}</div>
                <div className="text-xs text-slate-400">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Node types */}
          <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="font-semibold text-sm text-slate-900">Knotentypen im Wissensgraph</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {schema.nodes.map((n) => (
                <div key={n.label}>
                  <button
                    onClick={() => toggleNode(n.label)}
                    className="w-full flex items-center gap-2.5 px-5 py-2.5 hover:bg-slate-50 transition text-left"
                  >
                    <ChevronRight className={cn(
                      "w-3.5 h-3.5 text-slate-300 transition-transform",
                      expandedNode === n.label && "rotate-90"
                    )} />
                    <div className={cn("w-3 h-3 rounded-full flex-shrink-0", NODE_COLORS[n.label] || "bg-slate-400")} />
                    <span className="text-sm text-slate-700 flex-1">{NODE_LABELS[n.label] || n.label}</span>
                    <span className="text-xs font-mono text-slate-400 tabular-nums">{n.count}</span>
                  </button>
                  {expandedNode === n.label && (
                    <div className="px-5 pb-3 bg-slate-50/50">
                      {detailLoading && !nodeDetails[n.label] ? (
                        <div className="flex items-center gap-2 py-2 text-xs text-slate-400">
                          <Loader2 className="w-3 h-3 animate-spin" /> Laden...
                        </div>
                      ) : (
                        <div className="space-y-1 pt-1">
                          {(nodeDetails[n.label] || []).map((node) => {
                            const props = node.props || {};
                            const name = props.name || props.label || props.key || node.id;
                            const importantProps = Object.entries(props).filter(
                              ([k]) => !["id", "name", "label"].includes(k)
                            );
                            return (
                              <div key={node.id} className="text-xs py-1.5 px-3 bg-white rounded-lg border border-slate-100">
                                <div className="font-medium text-slate-800">{name}</div>
                                {importantProps.length > 0 && (
                                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                                    {importantProps.slice(0, 6).map(([k, v]) => (
                                      <span key={k} className="text-slate-400">
                                        <span className="text-slate-500">{k}:</span> {String(v).slice(0, 50)}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Relationships */}
          <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="font-semibold text-sm text-slate-900">Beziehungstypen</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {schema.relationships.map((r, i) => {
                const relKey = `${r.rel}__${r.from_label}__${r.to_label}`;
                const isExpanded = expandedRel === r.rel;
                return (
                  <div key={i}>
                    <button
                      onClick={() => toggleRel(r.rel)}
                      className="w-full flex items-center gap-2 px-5 py-2.5 text-xs hover:bg-slate-50 transition text-left"
                    >
                      <ChevronRight className={cn(
                        "w-3.5 h-3.5 text-slate-300 transition-transform flex-shrink-0",
                        isExpanded && "rotate-90"
                      )} />
                      <span className={cn("px-1.5 py-0.5 rounded font-medium text-white text-[10px] flex-shrink-0", NODE_COLORS[r.from_label] || "bg-slate-400")}>
                        {NODE_LABELS[r.from_label]?.split(" ")[0] || r.from_label}
                      </span>
                      <span className="text-slate-400 flex items-center gap-1">
                        <ArrowRight className="w-3 h-3" />
                        <span className="font-medium text-slate-600">{REL_LABELS[r.rel] || r.rel}</span>
                        <ArrowRight className="w-3 h-3" />
                      </span>
                      <span className={cn("px-1.5 py-0.5 rounded font-medium text-white text-[10px] flex-shrink-0", NODE_COLORS[r.to_label] || "bg-slate-400")}>
                        {NODE_LABELS[r.to_label]?.split(" ")[0] || r.to_label}
                      </span>
                      <span className="text-slate-300 ml-auto tabular-nums flex-shrink-0">{r.count}x</span>
                    </button>
                    {isExpanded && (
                      <div className="px-5 pb-3 bg-slate-50/50">
                        {detailLoading && !relDetails[r.rel] ? (
                          <div className="flex items-center gap-2 py-2 text-xs text-slate-400">
                            <Loader2 className="w-3 h-3 animate-spin" /> Laden...
                          </div>
                        ) : (
                          <div className="space-y-1 pt-1">
                            {(relDetails[r.rel] || []).map((edge, j) => {
                              const props = edge.props || {};
                              const propEntries = Object.entries(props).filter(
                                ([, v]) => v !== null && v !== undefined && v !== ""
                              );
                              return (
                                <div key={j} className="text-xs py-2 px-3 bg-white rounded-lg border border-slate-100">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-slate-700">{edge.a_name || edge.a_id}</span>
                                    <ArrowRight className="w-3 h-3 text-slate-300" />
                                    <span className="font-medium text-blue-700">{edge.b_name || edge.b_id}</span>
                                  </div>
                                  {propEntries.length > 0 && (
                                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                                      {propEntries.map(([k, v]) => (
                                        <span key={k} className="text-slate-400">
                                          <span className="text-slate-500">{k}:</span>{" "}
                                          <span className="text-slate-600">{String(v).slice(0, 80)}</span>
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Services */}
      {activeSection === "services" && (
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <h3 className="font-semibold text-sm text-slate-900">
              {schema.services.length} Prüfdienstleistungen
            </h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50/80">
                <th className="text-left px-5 py-2 text-[11px] font-semibold text-slate-400 uppercase">Dienstleistung</th>
                <th className="text-left px-5 py-2 text-[11px] font-semibold text-slate-400 uppercase">Kategorie</th>
                <th className="text-center px-5 py-2 text-[11px] font-semibold text-slate-400 uppercase">Preispositionen</th>
                <th className="text-center px-5 py-2 text-[11px] font-semibold text-slate-400 uppercase">Merkmale</th>
              </tr>
            </thead>
            <tbody>
              {schema.services.map((s) => (
                <tr key={s.id} className="border-t border-slate-100 hover:bg-slate-50/50">
                  <td className="px-5 py-2.5 font-medium text-slate-800">{s.name}</td>
                  <td className="px-5 py-2.5">
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200/50">
                      {s.kategorie}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-center tabular-nums text-slate-600">{s.preispositionen}</td>
                  <td className="px-5 py-2.5 text-center tabular-nums text-slate-600">{s.merkmale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Buildings */}
      {activeSection === "buildings" && (
        <div className="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm">
          <h3 className="font-semibold text-sm text-slate-900 mb-4">
            Gebäudetypen &amp; Pflichtprüfungen
          </h3>
          {(() => {
            const grouped: Record<string, Array<{ dl_name: string; grund: string }>> = {};
            for (const gs of schema.gt_services) {
              if (!grouped[gs.gt_name]) grouped[gs.gt_name] = [];
              grouped[gs.gt_name].push({ dl_name: gs.dl_name, grund: gs.grund });
            }
            return Object.entries(grouped).map(([gt, services]) => (
              <div key={gt} className="mb-4 last:mb-0">
                <div className="flex items-center gap-2 mb-2">
                  <Building2 className="w-4 h-4 text-emerald-600" />
                  <span className="font-semibold text-sm text-slate-800">{gt}</span>
                  <span className="text-[10px] font-medium text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">
                    {services.length} Pflichtprüfungen
                  </span>
                </div>
                <div className="ml-6 space-y-1">
                  {services.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <ArrowRight className="w-3 h-3 text-slate-300 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="font-medium text-blue-700">{s.dl_name}</span>
                        <span className="text-slate-400 ml-1">— {s.grund}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ));
          })()}
        </div>
      )}

      {/* Pricing rules */}
      {activeSection === "pricing" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm">
            <h3 className="font-semibold text-sm text-slate-900 mb-3">Preislogik</h3>
            <div className="space-y-3 text-xs text-slate-600">
              <div className="flex gap-3 items-start p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-blue-700 font-bold text-[10px]">1</span>
                </div>
                <div>
                  <div className="font-semibold text-slate-800">Gebäudetyp → Pflichtprüfungen</div>
                  <div className="text-slate-500 mt-0.5">ERFORDERT_PRUEFUNG-Kanten bestimmen, welche Prüfungen Pflicht sind</div>
                </div>
              </div>
              <div className="flex gap-3 items-start p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-blue-700 font-bold text-[10px]">2</span>
                </div>
                <div>
                  <div className="font-semibold text-slate-800">Dienstleistung → Preispositionen</div>
                  <div className="text-slate-500 mt-0.5">Jede Prüfung hat Grundpauschalen + mengenabhängige Positionen (pro Gerät, pro m², ...)</div>
                </div>
              </div>
              <div className="flex gap-3 items-start p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-blue-700 font-bold text-[10px]">3</span>
                </div>
                <div>
                  <div className="font-semibold text-slate-800">Mengenstaffeln</div>
                  <div className="text-slate-500 mt-0.5">Ab bestimmten Mengen gelten günstigere Stückpreise (z.B. ab 10 Wallboxen: 125 € statt 145 €)</div>
                </div>
              </div>
              <div className="flex gap-3 items-start p-3 bg-violet-50/50 rounded-lg border border-violet-100">
                <div className="w-6 h-6 rounded bg-violet-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-violet-700 font-bold text-[10px]">4</span>
                </div>
                <div>
                  <div className="font-semibold text-slate-800">SCHAETZT-Formeln</div>
                  <div className="text-slate-500 mt-0.5">Fehlende Mengen (Melder, Stromkreise, ...) werden aus BGF/Etagen geschätzt</div>
                </div>
              </div>
              <div className="flex gap-3 items-start p-3 bg-emerald-50/50 rounded-lg border border-emerald-100">
                <div className="w-6 h-6 rounded bg-emerald-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-emerald-700 font-bold text-[10px]">5</span>
                </div>
                <div>
                  <div className="font-semibold text-slate-800">GLEICHE_BEGEHUNG → Bündelrabatte</div>
                  <div className="text-slate-500 mt-0.5">Prüfungen, die zusammen durchgeführt werden, erhalten 5–15% Rabatt</div>
                </div>
              </div>
              <div className="flex gap-3 items-start p-3 bg-amber-50/50 rounded-lg border border-amber-100">
                <div className="w-6 h-6 rounded bg-amber-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-amber-700 font-bold text-[10px]">6</span>
                </div>
                <div>
                  <div className="font-semibold text-slate-800">EMPFIEHLT → Cross-Selling</div>
                  <div className="text-slate-500 mt-0.5">Jede Prüfung kann weitere sinnvolle Prüfungen empfehlen</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Estimation formulas */}
      {activeSection === "estimation" && (
        <div className="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm">
          <h3 className="font-semibold text-sm text-slate-900 mb-3">
            Schätzformeln (SCHAETZT-Kanten)
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Fehlende Gebäudemerkmale werden aus bekannten Werten (BGF, Etagen) geschätzt.
          </p>
          <div className="space-y-2">
            {schema.schaetzt_rules.map((r, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-violet-50/50 rounded-lg border border-violet-100">
                <Zap className="w-4 h-4 text-violet-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-violet-800">{r.from_label || "?"}</span>
                    <ArrowRight className="w-3 h-3 text-violet-400" />
                    <span className="font-semibold text-violet-800">{r.to_label || "?"}</span>
                  </div>
                  <code className="text-[11px] bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded font-mono">
                    {String(r.props?.formel || "")}
                  </code>
                  <div className="text-slate-500 mt-1">{String(r.props?.beschreibung || "")}</div>
                  {Boolean(r.props?.sicherheitsfaktor) && Number(r.props?.sicherheitsfaktor) !== 1.0 && (
                    <div className="text-amber-600 mt-0.5">
                      Sicherheitsfaktor: ×{String(r.props.sicherheitsfaktor)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bundles */}
      {activeSection === "bundles" && (
        <div className="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm">
          <h3 className="font-semibold text-sm text-slate-900 mb-3">
            Bündelrabatte (GLEICHE_BEGEHUNG)
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Wenn diese Prüfungen zusammen gebucht werden, entfallen separate Anfahrten.
          </p>
          <div className="space-y-2">
            {schema.bundles.map((b, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-emerald-50/50 rounded-lg border border-emerald-100">
                <Percent className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-emerald-800">{b.a_name}</span>
                    <span className="text-emerald-400">+</span>
                    <span className="font-semibold text-emerald-800">{b.b_name}</span>
                    <span className="ml-auto font-bold text-emerald-700 tabular-nums">−{b.rabatt}%</span>
                  </div>
                  <div className="text-slate-500">{b.grund}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {activeSection === "recommendations" && (
        <div className="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm">
          <h3 className="font-semibold text-sm text-slate-900 mb-3">
            Empfehlungsregeln (EMPFIEHLT)
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Wenn eine Prüfung gebucht wird, empfehlen wir automatisch ergänzende Prüfungen.
          </p>
          <div className="space-y-2">
            {schema.empfiehlt.map((e, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-amber-50/50 rounded-lg border border-amber-100">
                <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-slate-700">{e.from_name}</span>
                    <ArrowRight className="w-3 h-3 text-amber-400" />
                    <span className="font-semibold text-amber-800">{e.to_name}</span>
                    {e.relevanz && (
                      <span className={cn(
                        "ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-medium",
                        e.relevanz === "hoch"
                          ? "bg-red-50 text-red-600 border border-red-200"
                          : "bg-slate-50 text-slate-500 border border-slate-200"
                      )}>
                        {e.relevanz}
                      </span>
                    )}
                  </div>
                  <div className="text-slate-500">{e.grund}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
