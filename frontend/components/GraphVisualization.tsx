"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import { Loader2, Maximize2, Minimize2 } from "lucide-react";
import { cn } from "@/lib/utils";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

interface GraphNode {
  id: string;
  label: string;
  name: string;
}

interface GraphEdge {
  source: string;
  target: string;
  rel: string;
}

const LABEL_COLORS: Record<string, string> = {
  Dienstleistung: "#3b82f6",
  Gebaeudetyp: "#10b981",
  Preisposition: "#f59e0b",
  Staffel: "#fb923c",
  Merkmal: "#8b5cf6",
  Zuschlag: "#ef4444",
  Norm: "#64748b",
  Qualifikation: "#06b6d4",
  Pruefintervall: "#2dd4bf",
  Nutzungsart: "#84cc16",
  Stressor: "#f43f5e",
  Trait: "#ec4899",
  Gefahrenzone: "#dc2626",
  Region: "#38bdf8",
};

const LABEL_SIZES: Record<string, number> = {
  Dienstleistung: 8,
  Gebaeudetyp: 7,
  Preisposition: 5,
  Staffel: 4,
  Merkmal: 6,
  Zuschlag: 5,
  Norm: 4,
  Qualifikation: 4,
};

const LABEL_DISPLAY: Record<string, string> = {
  Dienstleistung: "Prüfung",
  Gebaeudetyp: "Gebäude",
  Preisposition: "Preis",
  Staffel: "Staffel",
  Merkmal: "Merkmal",
  Zuschlag: "Zuschlag",
  Norm: "Norm",
  Qualifikation: "Qualif.",
  Pruefintervall: "Intervall",
  Nutzungsart: "Nutzung",
  Stressor: "Stressor",
  Trait: "Trait",
  Gefahrenzone: "Gefahr",
  Region: "Region",
};

const REL_COLORS: Record<string, string> = {
  ERFORDERT_PRUEFUNG: "#10b981",
  HAT_PREISPOSITION: "#f59e0b",
  HAT_STAFFEL: "#fb923c",
  ERFORDERT_MERKMAL: "#8b5cf6",
  SCHAETZT: "#a78bfa",
  GLEICHE_BEGEHUNG: "#34d399",
  EMPFIEHLT: "#fbbf24",
  LOEST_AUS: "#ef4444",
  BASIERT_AUF: "#94a3b8",
  ERFORDERT_QUALIFIKATION: "#06b6d4",
};

export default function GraphVisualization() {
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const fgRef = useRef<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("http://localhost:8010/api/graph/visual")
      .then((r) => r.json())
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleNodeClick = useCallback((node: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 500);
      fgRef.current.zoom(3, 500);
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-white rounded-xl border border-slate-200/60">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="text-center text-slate-500 py-12">
        Verbindung zum Backend fehlgeschlagen.
      </div>
    );
  }

  // Build force graph data
  const fgNodes = graphData.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    name: n.name,
    color: LABEL_COLORS[n.label] || "#94a3b8",
    size: LABEL_SIZES[n.label] || 4,
  }));

  const fgLinks = graphData.edges.map((e) => ({
    source: e.source,
    target: e.target,
    rel: e.rel,
    color: REL_COLORS[e.rel] || "#cbd5e1",
  }));

  // Get unique labels for legend
  const labels = [...new Set(graphData.nodes.map((n) => n.label))].sort();

  // Filter if label selected
  const visibleNodeIds = selectedLabel
    ? new Set(fgNodes.filter((n) => n.label === selectedLabel).map((n) => n.id))
    : null;

  const filteredLinks = visibleNodeIds
    ? fgLinks.filter((l) => {
        const src = typeof l.source === "object" ? (l.source as any).id : l.source;
        const tgt = typeof l.target === "object" ? (l.target as any).id : l.target;
        return visibleNodeIds.has(src) || visibleNodeIds.has(tgt);
      })
    : fgLinks;

  const connectedIds = visibleNodeIds
    ? new Set([
        ...visibleNodeIds,
        ...filteredLinks.map((l) => (typeof l.source === "object" ? (l.source as any).id : l.source)),
        ...filteredLinks.map((l) => (typeof l.target === "object" ? (l.target as any).id : l.target)),
      ])
    : null;

  const height = fullscreen ? window.innerHeight - 60 : 600;

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="bg-white rounded-xl border border-slate-200/60 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm text-slate-900">
            Wissensgraph — {graphData.nodes.length} Knoten, {graphData.edges.length} Kanten
          </h3>
          <button
            onClick={() => setFullscreen(!fullscreen)}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition"
          >
            {fullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setSelectedLabel(null)}
            className={cn(
              "px-2.5 py-1 rounded-full text-[11px] font-medium transition-all border",
              !selectedLabel
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-white text-slate-500 border-slate-200 hover:border-slate-400"
            )}
          >
            Alle
          </button>
          {labels.map((label) => (
            <button
              key={label}
              onClick={() => setSelectedLabel(selectedLabel === label ? null : label)}
              className={cn(
                "px-2.5 py-1 rounded-full text-[11px] font-medium transition-all border flex items-center gap-1.5",
                selectedLabel === label
                  ? "text-white border-transparent"
                  : "bg-white border-slate-200 hover:border-slate-400"
              )}
              style={
                selectedLabel === label
                  ? { backgroundColor: LABEL_COLORS[label], borderColor: LABEL_COLORS[label] }
                  : {}
              }
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: LABEL_COLORS[label] || "#94a3b8" }}
              />
              {LABEL_DISPLAY[label] || label}
              <span className={cn("tabular-nums", selectedLabel === label ? "text-white/70" : "text-slate-400")}>
                {graphData.nodes.filter((n) => n.label === label).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Graph */}
      <div
        ref={containerRef}
        className={cn(
          "bg-slate-950 rounded-xl border border-slate-200/60 overflow-hidden shadow-sm",
          fullscreen && "fixed inset-0 z-50 rounded-none"
        )}
      >
        {hoveredNode && (
          <div className="absolute top-3 left-3 z-10 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-lg border border-slate-200 text-xs">
            <div className="font-semibold text-slate-800">{hoveredNode}</div>
          </div>
        )}
        {fullscreen && (
          <button
            onClick={() => setFullscreen(false)}
            className="absolute top-3 right-3 z-10 bg-white/90 backdrop-blur-sm rounded-lg p-2 shadow-lg border border-slate-200 hover:bg-white transition"
          >
            <Minimize2 className="w-4 h-4 text-slate-600" />
          </button>
        )}
        <ForceGraph2D
          ref={fgRef}
          graphData={{
            nodes: fgNodes,
            links: filteredLinks,
          }}
          width={containerRef.current?.clientWidth || 800}
          height={height}
          backgroundColor="#0f172a"
          nodeRelSize={1}
          nodeVal={(node: any) => {
            if (connectedIds && !connectedIds.has(node.id)) return 1;
            return node.size || 4;
          }}
          nodeColor={(node: any) => {
            if (connectedIds && !connectedIds.has(node.id)) return "#334155";
            return node.color;
          }}
          nodeLabel={(node: any) => `${LABEL_DISPLAY[node.label] || node.label}: ${node.name}`}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const size = connectedIds && !connectedIds.has(node.id)
              ? 2
              : (node.size || 4);
            const color = connectedIds && !connectedIds.has(node.id)
              ? "#334155"
              : node.color;

            // Node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            // Glow for important nodes
            if (size >= 6 && (!connectedIds || connectedIds.has(node.id))) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, size + 2, 0, 2 * Math.PI);
              ctx.fillStyle = color + "30";
              ctx.fill();
            }

            // Label for zoomed-in or large nodes
            if (globalScale > 1.5 || size >= 7) {
              const label = node.name.length > 25 ? node.name.slice(0, 22) + "..." : node.name;
              const fontSize = Math.max(10 / globalScale, 2);
              ctx.font = `${fontSize}px Inter, sans-serif`;
              ctx.textAlign = "center";
              ctx.textBaseline = "top";
              ctx.fillStyle = "#e2e8f0";
              ctx.fillText(label, node.x, node.y + size + 2);
            }
          }}
          linkColor={(link: any) => {
            if (connectedIds) {
              const src = typeof link.source === "object" ? link.source.id : link.source;
              const tgt = typeof link.target === "object" ? link.target.id : link.target;
              if (!connectedIds.has(src) || !connectedIds.has(tgt)) return "#1e293b";
            }
            return (link.color || "#475569") + "60";
          }}
          linkWidth={(link: any) => {
            if (connectedIds) {
              const src = typeof link.source === "object" ? link.source.id : link.source;
              const tgt = typeof link.target === "object" ? link.target.id : link.target;
              if (!connectedIds.has(src) || !connectedIds.has(tgt)) return 0.2;
            }
            return 0.8;
          }}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={0.9}
          onNodeClick={handleNodeClick}
          onNodeHover={(node: any) => setHoveredNode(node ? node.name : null)}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      </div>
    </div>
  );
}
