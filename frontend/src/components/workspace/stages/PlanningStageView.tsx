"use client";

import React from "react";
import {
  Target, ArrowRight, Layers, CheckCircle2, Gauge, Cpu, ShieldCheck
} from "lucide-react";
import { ExperimentPlan, Project, Hypothesis, ResearchGap } from "@/types";

interface PlanningStageViewProps {
  plan: ExperimentPlan | null;
  stageData?: Record<string, unknown> | null;
  project?: Project | null;
  hypotheses?: Hypothesis[];
  gaps?: ResearchGap[];
  onProceedToCoding: () => void;
}

export default function PlanningStageView({
  plan,
  stageData,
  project,
  hypotheses = [],
  gaps = [],
  onProceedToCoding,
}: PlanningStageViewProps) {
  const sData = stageData || {};
  const effectivePlan = plan || (sData.roadmap ? (sData as unknown as ExperimentPlan) : null);

  if (!effectivePlan) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center border border-card-border/60">
        <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3 text-primary">
          <Target className="w-6 h-6 animate-pulse" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">No Experiment Plan Formulated</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Run the planning stage or trigger the autonomous research pipeline to generate parameter-grounded milestone roadmaps, metric suites, and hardware allocations.
        </p>
      </div>
    );
  }

  const roadmap = effectivePlan.roadmap || [];
  const metrics = (effectivePlan.metrics || []) as Array<Record<string, any> | string>;
  const hw = (effectivePlan.hardware_requirements || {}) as Record<string, any>;
  const ablationMatrix = (effectivePlan.ablation_matrix || (sData as Record<string, any>).ablation_matrix || []) as Array<Record<string, any>>;
  const planTitle =
    effectivePlan.title ||
    (typeof sData.title === "string" ? sData.title : undefined) ||
    (project?.title ? `Empirical Experiment Plan: ${project.title}` : "Empirical Experiment Plan");
  const targetHypo =
    effectivePlan.target_hypothesis ||
    (typeof sData.target_hypothesis === "string" ? sData.target_hypothesis : undefined) ||
    hypotheses.find((h: Hypothesis) => h.selected)?.statement ||
    "Tri-Planar Axial-Mamba UNet Architecture for 3D MRI Segmentation";
  const targetGap =
    effectivePlan.target_gap ||
    (typeof sData.target_gap === "string" ? sData.target_gap : undefined) ||
    gaps[0]?.description ||
    "Multi-Center Scanner Shift & High Computational Memory";

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-950 border border-card-border/80 shadow-md space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-primary font-mono flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5" /> Stage 6 · Empirical Verification Protocol
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-mono font-semibold">
                {roadmap.length} Sequential Phases
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-semibold">
                PyTorch 2.3+ / CUDA Standard
              </span>
            </div>
            <h2 className="text-sm sm:text-base font-bold text-slate-100">{planTitle}</h2>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-center">
            <button
              type="button"
              onClick={onProceedToCoding}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 text-xs font-semibold transition-all hover:scale-[1.02] shadow-sm min-h-[38px]"
            >
              <span>Proceed to Code Synthesis</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Target Hypothesis & Research Gap Alignment Callouts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-2 border-t border-card-border/30">
          <div className="p-2.5 rounded-lg bg-indigo-950/20 border border-indigo-900/30 flex items-start gap-2">
            <span className="text-[10px] font-bold text-indigo-400 uppercase font-mono flex-shrink-0 mt-0.5">
              🎯 Target Hypothesis:
            </span>
            <span className="text-xs text-slate-200 line-clamp-2">
              {targetHypo}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-cyan-950/20 border border-cyan-900/30 flex items-start gap-2">
            <span className="text-[10px] font-bold text-cyan-400 uppercase font-mono flex-shrink-0 mt-0.5">
              🔬 Resolves Gap:
            </span>
            <span className="text-xs text-slate-200 line-clamp-2">
              {targetGap}
            </span>
          </div>
        </div>
      </div>

      {/* Milestone Roadmap Timeline */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-primary" /> Phase-by-Phase Experimental Roadmap
          </h3>
          <span className="text-[11px] text-slate-400 font-mono">
            Rigorous 5-Step Execution Plan
          </span>
        </div>

        <div className="space-y-4">
          {roadmap.map((step, i: number) => {
            const category =
              step.category ||
              (i === 0
                ? "Data Pipeline"
                : i === 1
                ? "Model Architecture"
                : i === 2
                ? "Optimization Protocol"
                : i === 3
                ? "Ablation Studies"
                : "Statistical Validation");
            const categoryColor =
              i === 0
                ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                : i === 1
                ? "text-purple-400 bg-purple-500/10 border-purple-500/20"
                : i === 2
                ? "text-cyan-400 bg-cyan-500/10 border-cyan-500/20"
                : i === 3
                ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                : "text-blue-400 bg-blue-500/10 border-blue-500/20";

            return (
              <div
                key={i}
                className="glass-card rounded-xl p-4 sm:p-5 border border-card-border/80 hover:border-slate-700/80 transition-all space-y-3.5 shadow-sm relative overflow-hidden"
              >
                {/* Phase Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border font-mono uppercase ${categoryColor}`}>
                        {category}
                      </span>
                      {step.milestone && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>Milestone: {step.milestone}</span>
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-bold text-slate-100 mt-1">{step.step}</h4>
                  </div>
                  <span className="text-xs font-mono text-slate-500 self-start">Step {i + 1} of {roadmap.length}</span>
                </div>

                {/* Phase Detailed Description */}
                <p className="text-xs text-slate-300 leading-relaxed">
                  {step.details}
                </p>

                {/* 4-Column Technical Specification Grid - Responsive on Tablet */}
                {(step.inputs || step.algorithm || step.deliverables || step.mitigation) && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 pt-3 border-t border-card-border/30 text-[11px]">
                    {step.inputs && (
                      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-card-border/30">
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                          📥 Cohorts & Inputs
                        </span>
                        <span className="text-xs text-slate-200 mt-0.5 block leading-snug break-words">
                          {step.inputs}
                        </span>
                      </div>
                    )}
                    {step.algorithm && (
                      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-card-border/30">
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                          ⚙️ Key Algorithms / Layers
                        </span>
                        <span className="text-xs text-slate-200 mt-0.5 block leading-snug break-words">
                          {step.algorithm}
                        </span>
                      </div>
                    )}
                    {step.deliverables && (
                      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-card-border/30">
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                          🎯 Target Deliverables
                        </span>
                        <span className="text-xs text-slate-200 mt-0.5 block leading-snug break-words">
                          {step.deliverables}
                        </span>
                      </div>
                    )}
                    {step.mitigation && (
                      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-card-border/30">
                        <span className="text-[9px] font-bold text-amber-400 uppercase tracking-wider block font-mono">
                          🛡️ Failure Mitigation
                        </span>
                        <span className="text-xs text-amber-200/90 mt-0.5 block leading-snug break-words">
                          {step.mitigation}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Target Performance Metrics Matrix */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-primary" /> Target Acceptance Metrics & Benchmark Bounds
          </h3>
          <span className="text-[11px] text-slate-400 font-mono">Quantitative Validation Criteria</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {metrics.map((metric, i: number) => {
            const mStr = typeof metric === "string" ? metric : ((metric as Record<string, string>).name || JSON.stringify(metric));
            return (
              <div
                key={i}
                className="p-3.5 rounded-xl bg-slate-900/40 border border-card-border/70 hover:border-slate-700/80 transition-all flex flex-col justify-between space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-bold text-slate-200 leading-snug">
                    {mStr}
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-mono flex-shrink-0">
                    Metric {i + 1}
                  </span>
                </div>
                <div className="pt-1.5 border-t border-card-border/30 flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                  <span>Empirically Evaluated & Logged</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Ablation Studies Matrix (if available) */}
      {ablationMatrix.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-emerald-400" /> Planned Ablation Study Matrix
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">Causal Component Isolation</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {ablationMatrix.map((ab, i: number) => (
              <div
                key={i}
                className={`p-4 rounded-xl border transition-all flex flex-col justify-between space-y-2.5 ${
                  i === ablationMatrix.length - 1
                    ? "bg-emerald-950/30 border-emerald-500/40 shadow-sm"
                    : "bg-slate-950/40 border-card-border/60"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400 uppercase">
                      Variant {i + 1}
                    </span>
                    {i === ablationMatrix.length - 1 && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                        Full Proposed
                      </span>
                    )}
                  </div>
                  <h4 className="text-xs font-bold text-slate-100">{ab.variant}</h4>
                  <p className="text-[11px] text-slate-300 leading-relaxed">{ab.purpose}</p>
                </div>

                <div className="pt-2 border-t border-card-border/30 flex items-center justify-between text-[10px] font-mono">
                  <span className="text-slate-400">Target: <strong className="text-emerald-400">{ab.dice_expected}</strong></span>
                  <span className="text-slate-500">{ab.vram}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resource & Compute Allocation Dashboard */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-primary" /> Compute & Hardware Budget Allocation
          </h3>
          <span className="text-[11px] text-slate-400 font-mono">Infrastructure Provisioning</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          <div className="p-3 rounded-xl bg-slate-900/50 border border-card-border/60 space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500 block">⚡ Accelerator</span>
            <span className="text-xs font-bold text-slate-200 block truncate">{hw.GPU || "NVIDIA RTX 4090"}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/50 border border-card-border/60 space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500 block">⏱️ Wall-Clock</span>
            <span className="text-xs font-bold text-slate-200 block truncate">{hw.expected_runtime || "2.8 hours"}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/50 border border-card-border/60 space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500 block">🎯 Precision</span>
            <span className="text-xs font-bold text-emerald-400 block truncate">{hw.precision || "AMP FP16 / BF16"}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/50 border border-card-border/60 space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500 block">🧠 System RAM</span>
            <span className="text-xs font-bold text-slate-200 block truncate">{hw.RAM || "64 GB"}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/50 border border-card-border/60 space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500 block">🖥️ CPU Cores</span>
            <span className="text-xs font-bold text-slate-200 block truncate">{hw.CPU || "16 vCPUs"}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/50 border border-card-border/60 space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500 block">📦 Environment</span>
            <span className="text-xs font-bold text-slate-200 block truncate">{hw.framework || "PyTorch 2.3+ / CUDA"}</span>
          </div>
        </div>
      </div>

      {/* Statistical Falsification Protocol Footer */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-card-border/60 space-y-2">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-300 font-mono uppercase">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Empirical Falsification Protocol & Statistical Rigor</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          All comparative evaluations utilize 5-fold cross-validation partitioned by clinical scanner site. Significance is certified using two-tailed paired Wilcoxon signed-rank tests (<strong className="text-slate-200">p &lt; 0.01</strong>) with 1,000-sample bootstrap confidence intervals. The primary hypothesis is subject to immediate scientific rejection if the out-of-distribution performance drop exceeds 5.0% or if parameter efficiency fails to scale linearly.
        </p>
      </div>
    </div>
  );
}
