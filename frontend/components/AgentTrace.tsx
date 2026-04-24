"use client";

import { useState } from "react";
import { Brain, ChevronDown, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceStep } from "@/lib/types";

interface Props {
  steps: TraceStep[];
  loading: boolean;
}

export default function AgentTrace({ steps, loading }: Props) {
  const [expanded, setExpanded] = useState(true);

  // Each pipeline step is already a clean, meaningful label — no grouping needed
  const totalMs = steps.reduce((s, st) => s + (st.duration_ms || 0), 0);

  return (
    <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden animate-fade-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 transition"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-100 to-blue-50 flex items-center justify-center">
            <Brain className="w-4 h-4 text-blue-700" />
          </div>
          <h3 className="font-semibold text-sm text-slate-900">Analyse-Fortschritt</h3>
          {loading ? (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200/60">
              <Loader2 className="w-3 h-3 animate-spin" />
              analysiert...
            </span>
          ) : (
            <span className="text-[11px] font-medium text-slate-400 bg-slate-50 px-2.5 py-0.5 rounded-full border border-slate-200/60">
              {steps.length} Schritte{totalMs > 0 ? ` · ${(totalMs / 1000).toFixed(1)}s` : ""}
            </span>
          )}
        </div>
        <ChevronDown className={cn(
          "w-4 h-4 text-slate-400 transition-transform",
          expanded ? "rotate-180" : ""
        )} />
      </button>

      {expanded && (
        <div className="border-t px-4 pb-4">
          <div className="mt-3 space-y-0">
            {steps.map((step, i) => {
              const isLast = i === steps.length - 1;
              const isDone = !loading || !isLast;

              return (
                <div key={i} className="flex gap-3 animate-fade-in">
                  {/* Timeline line + dot */}
                  <div className="flex flex-col items-center">
                    <div className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 border-2",
                      isDone
                        ? "bg-blue-50 border-blue-500 text-blue-600"
                        : "bg-white border-blue-400 text-blue-500"
                    )}>
                      {isDone ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      )}
                    </div>
                    {i < steps.length - 1 && (
                      <div className="w-px flex-1 bg-blue-200 min-h-[16px]" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="pb-3 -mt-0.5 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "text-[13px] font-medium",
                        isDone ? "text-slate-800" : "text-blue-700"
                      )}>
                        {step.action}
                      </span>
                      {isDone && (step.duration_ms || 0) > 0 && (
                        <span className="text-[10px] font-medium text-slate-300">
                          {(step.duration_ms || 0) >= 1000
                            ? `${((step.duration_ms || 0) / 1000).toFixed(1)}s`
                            : `${step.duration_ms}ms`}
                        </span>
                      )}
                      {Boolean(step.params?.ref) && (
                        <span className="relative group/tip inline-flex">
                          <span className="text-[10px] text-blue-400 cursor-help hover:text-blue-600 transition">ⓘ</span>
                          <div className="hidden group-hover/tip:block absolute left-4 bottom-full z-50 mb-1 w-[420px] max-w-[90vw] bg-slate-900 text-white text-xs p-3 rounded-xl shadow-2xl leading-relaxed pointer-events-none">
                            <div className="text-[10px] text-blue-300 font-semibold uppercase tracking-wider mb-1">Quellennachweis</div>
                            {String(step.params?.ref ?? "")}
                          </div>
                        </span>
                      )}
                    </div>
                    {step.result_summary && (
                      <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                        {step.result_summary}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
