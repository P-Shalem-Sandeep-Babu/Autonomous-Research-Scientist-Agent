"use client";

import React from "react";
import { Cpu, CheckCircle2 } from "lucide-react";
import { WorkspaceStage } from "../StageSidebar";
import { ResearchMemory } from "@/types";

interface MemoryStageViewProps {
  memories: ResearchMemory[];
  stages: WorkspaceStage[];
}

export default function MemoryStageView({ memories, stages }: MemoryStageViewProps) {
  const memoryStage = stages.find((s) => s.stage_name === "memory");
  const stageMemories = (memoryStage?.output_data?.memories as ResearchMemory[]) || [];
  const rawMemories = memories.length > 0 ? memories : stageMemories;

  const parsedMemories = rawMemories.map((m: ResearchMemory | Record<string, unknown>) => {
    const rawVal = "value" in m ? m.value : undefined;
    let val: Record<string, unknown> = typeof rawVal === "object" && rawVal !== null ? (rawVal as Record<string, unknown>) : {};
    if (typeof rawVal === "string") {
      try {
        val = JSON.parse(rawVal);
      } catch {
        val = { description: rawVal };
      }
    }
    const memType = "memory_type" in m ? String(m.memory_type) : "";
    const memKey = "key" in m ? String(m.key) : "";
    const category = memType || (m as Record<string, unknown>)?.category || val?.category || "key_insight";
    const title = val?.title || memKey.replace(/_/g, " ").toUpperCase() || "Research Memory";
    const description = String(val?.description || (m as Record<string, unknown>)?.description || "");
    const metrics = String(val?.metrics || (m as Record<string, unknown>)?.metrics || "");
    const sourcePaper = String(val?.source_paper || (m as Record<string, unknown>)?.source_paper || "");
    const transferability = String(val?.transferability || (m as Record<string, unknown>)?.transferability || "");

    return {
      id: "id" in m ? String(m.id) : String(Math.random()),
      category: String(category),
      title: String(title),
      description,
      metrics,
      sourcePaper,
      transferability,
    };
  });

  if (parsedMemories.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center border border-card-border/60">
        <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3 text-primary">
          <Cpu className="w-6 h-6 animate-pulse" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">Memory Consolidation Pending</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Run the research pipeline to synthesize long-term memory patterns, negative constraints, and transferrable algorithmic principles.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-card-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-primary font-mono flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5" /> Stage 12 · Long-Term Research Memory & AgentDB Store
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-mono">
              {parsedMemories.length} Verified Insights Cataloged
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Empirical findings, successful architectural motifs, and negative constraints indexed for cross-project autonomous reasoning.
          </p>
        </div>
        <div className="flex items-center gap-1.5 self-start sm:self-center">
          <span className="text-[10px] px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Vector Index Synced
          </span>
        </div>
      </div>

      {/* Memory Cards Grid */}
      <div className="space-y-3.5">
        {parsedMemories.map((mem, idx: number) => {
          const isSuccess = mem.category === "successful_method";
          const isFailed = mem.category === "failed_method";
          const badgeBg = isSuccess
            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            : isFailed
            ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
            : "bg-violet-500/10 text-violet-400 border-violet-500/20";

          const categoryLabel = isSuccess
            ? "Successful Method"
            : isFailed
            ? "Negative Constraint / Failed Method"
            : "Key Insight / Discovery";

          return (
            <div
              key={mem.id || String(idx)}
              className="glass-card rounded-xl p-4 sm:p-5 border border-card-border/80 hover:border-slate-700/80 transition-all space-y-3 shadow-sm"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-[9px] font-bold px-2 py-0.5 rounded border font-mono uppercase tracking-wider ${badgeBg}`}
                  >
                    {categoryLabel}
                  </span>
                  {mem.sourcePaper && (
                    <span className="text-[10px] text-slate-500 font-mono truncate max-w-[280px]">
                      Source: {mem.sourcePaper}
                    </span>
                  )}
                </div>
                {mem.metrics && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800/80 text-cyan-300 font-mono font-semibold border border-card-border/40 self-start sm:self-center">
                    {mem.metrics}
                  </span>
                )}
              </div>

              <div>
                <h4 className="text-xs font-bold text-slate-100">{mem.title}</h4>
                <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                  {mem.description}
                </p>
              </div>

              {mem.transferability && (
                <div className="p-2.5 rounded-lg bg-slate-900/40 border border-card-border/40 flex items-start gap-2 text-[11px] text-slate-400">
                  <span className="text-primary font-bold text-[10px] uppercase tracking-wider font-mono flex-shrink-0 mt-0.5">
                    Cross-Project Transfer:
                  </span>
                  <span className="text-slate-300 leading-normal">{mem.transferability}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
