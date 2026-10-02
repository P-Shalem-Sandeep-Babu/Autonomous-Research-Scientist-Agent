"use client";

import React from "react";
import ResearchChart from "@/components/ResearchChart";
import { WorkspaceStage } from "../StageSidebar";
import { ExperimentRun } from "@/types";

interface ExecutionEvaluationStageViewProps {
  activeStage: "execution" | "evaluation";
  runs: ExperimentRun[];
  stages: WorkspaceStage[];
}

export default function ExecutionEvaluationStageView({
  activeStage,
  runs,
  stages,
}: ExecutionEvaluationStageViewProps) {
  if (activeStage === "execution") {
    return (
      <div className="space-y-6">
        {runs.length === 0 ? (
          <div className="text-center p-12 text-slate-500 text-sm glass-card rounded-2xl border border-card-border/60">
            No active experiment runs recorded. Run pipeline to trigger model execution.
          </div>
        ) : (
          runs.map((run) => {
            const history = (run.metrics_history || []) as Array<{ train_acc?: number; val_acc?: number }>;

            return (
              <div key={run.id} className="space-y-6">
                <div className="glass-card rounded-xl p-5 border border-card-border">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3">
                    Live Training Accuracy Convergence
                  </h3>
                  {history.length > 1 ? (
                    <div className="relative w-full h-[180px] bg-slate-950/20 rounded border border-card-border/40 p-2">
                      <ResearchChart
                        title="Training Accuracy Convergence"
                        data={{
                          labels: history.map((_, idx: number) => `Epoch ${idx + 1}`),
                          datasets: [
                            {
                              label: "Train Accuracy",
                              data: history.map((h) => Number(h.train_acc || 0)),
                              borderColor: "#10b981",
                              backgroundColor: "rgba(16, 185, 129, 0.1)",
                              tension: 0.4,
                            },
                            {
                              label: "Validation Accuracy",
                              data: history.map((h) => Number(h.val_acc || 0)),
                              borderColor: "#06b6d4",
                              backgroundColor: "rgba(6, 182, 212, 0.1)",
                              tension: 0.4,
                            },
                          ],
                        }}
                      />
                    </div>
                  ) : (
                    <div className="h-[180px] border border-card-border/40 bg-slate-950/20 flex items-center justify-center text-xs text-slate-500 font-mono">
                      Building metrics curve history...
                    </div>
                  )}
                </div>

                <div className="glass-card rounded-xl border border-card-border p-5 bg-slate-950/60 font-mono text-[10px] text-slate-400 h-64 overflow-y-auto leading-normal select-text">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3 font-sans">
                    Stdout Run Logs
                  </h3>
                  <pre className="whitespace-pre-wrap">{run.logs}</pre>
                </div>
              </div>
            );
          })
        )}
      </div>
    );
  }

  // Evaluation View
  const evalStage = stages.find((s) => s.stage_name === "evaluation");
  const evalData = evalStage?.output_data;

  return (
    <div className="space-y-6">
      {!evalData ? (
        <div className="text-center p-12 text-slate-500 text-sm glass-card rounded-2xl border border-card-border/60">
          No evaluation report compiled yet.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4">
            {Object.entries((evalData.performance_report as Record<string, string | number>) || {}).map(([name, val]) => (
              <div
                key={name}
                className="p-4 rounded-xl bg-card/30 border border-card-border text-center"
              >
                <span className="text-[10px] block uppercase text-slate-500 font-mono truncate">
                  {name}
                </span>
                <span className="text-sm sm:text-base font-bold text-slate-200 mt-1 block">
                  {val}
                </span>
              </div>
            ))}
          </div>

          <div className="glass-card rounded-xl p-5 border border-card-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3">
              Model Baseline Comparisons
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-card-border/60 text-slate-400">
                    <th className="py-2">Model</th>
                    <th className="py-2">Accuracy</th>
                    <th className="py-2">F1-Score</th>
                    <th className="py-2 font-mono">FLOPs</th>
                  </tr>
                </thead>
                <tbody>
                  {((evalData.baseline_comparison as Array<{ Model: string; Accuracy: string | number; "F1-Score": string | number; FLOPs: string }>) || []).map((row, i: number) => (
                    <tr
                      key={i}
                      className={`border-b border-card-border/20 text-slate-300 ${
                        row.Model.includes("Ours") ? "bg-primary/5 text-primary" : ""
                      }`}
                    >
                      <td className="py-2.5 font-semibold text-slate-200">{row.Model}</td>
                      <td className="py-2.5">{row.Accuracy}</td>
                      <td className="py-2.5">{row["F1-Score"]}</td>
                      <td className="py-2.5 font-mono">{row.FLOPs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="glass-card rounded-xl p-5 border border-card-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">
              Improvement Analysis
            </h3>
            <div className="text-xs text-slate-300 leading-relaxed">
              {evalData.improvement_analysis}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
