"use client";

import React from "react";
import { Database, CheckCircle2, Globe, ExternalLink, Link2 } from "lucide-react";
import { WorkspaceStage } from "../StageSidebar";
import { DatasetRecommendation } from "@/types";

interface DatasetStageViewProps {
  datasets: DatasetRecommendation[];
  stages: WorkspaceStage[];
}

export default function DatasetStageView({ datasets, stages }: DatasetStageViewProps) {
  const datasetStage = stages.find((s) => s.stage_name === "dataset");
  const stageCataloged = (datasetStage?.output_data?.cataloged_datasets as DatasetRecommendation[]) || [];
  const effectiveDatasets: DatasetRecommendation[] = datasets.length > 0 ? datasets : stageCataloged;

  if (effectiveDatasets.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center border border-card-border/60">
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-3 text-amber-400">
          <Database className="w-6 h-6 animate-pulse" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">No Datasets Cataloged</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Run the dataset discovery stage or trigger the autonomous research pipeline to catalog verified benchmark repositories.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-slate-900/60 border border-card-border/60">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400 font-mono flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5" /> Stage 5 · Verified Benchmark Datasets
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
              {effectiveDatasets.length} Repositories Cataloged
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Curated scientific cohorts providing training, validation, and out-of-distribution evaluation targets with direct access links.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-center">
          <span className="text-[11px] px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> Direct Access Verified
          </span>
        </div>
      </div>

      {/* Dataset Cards Grid */}
      <div className="space-y-4">
        {effectiveDatasets.map((dataset, idx) => {
          const meta = dataset.metadata_fields || dataset.metadata || {};
          const directUrl = dataset.url || meta.direct_link || meta.url || "";
          const hfId = meta.huggingface_id || "";
          const scoreVal =
            dataset.quality_score != null
              ? dataset.quality_score > 1
                ? Math.round(dataset.quality_score)
                : Math.round(dataset.quality_score * 100)
              : 95;

          return (
            <div
              key={dataset.id || idx}
              className="glass-card rounded-xl p-4 sm:p-5 border border-card-border/80 hover:border-slate-700/80 transition-all space-y-4 shadow-sm"
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono uppercase">
                      {dataset.source || "Scientific Repository"}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                      Quality Score: {scoreVal}% · {scoreVal >= 95 ? "Gold Standard" : "High Fidelity"}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-100 mt-1">{dataset.name}</h3>
                </div>

                {/* Direct Action Link Button */}
                {directUrl && (
                  <a
                    href={directUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/15 hover:bg-primary/25 text-primary border border-primary/30 text-xs font-semibold transition-all hover:scale-[1.02] shadow-sm flex-shrink-0 self-start min-h-[36px]"
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>Access Direct Dataset</span>
                    <ExternalLink className="w-3.5 h-3.5 ml-0.5" />
                  </a>
                )}
              </div>

              {/* Description */}
              <p className="text-xs text-slate-300 leading-relaxed">{dataset.description}</p>

              {/* Metadata Grid */}
              {meta && Object.keys(meta).length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 pt-3 border-t border-card-border/30">
                  {meta.instances && (
                    <div className="p-2.5 rounded-lg bg-slate-900/40 border border-card-border/30">
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                        📦 Sample / Cohort Size
                      </span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block truncate">
                        {meta.instances}
                      </span>
                    </div>
                  )}
                  {meta.modalities && (
                    <div className="p-2.5 rounded-lg bg-slate-900/40 border border-card-border/30">
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                        🔬 Modalities / Channels
                      </span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block truncate">
                        {meta.modalities}
                      </span>
                    </div>
                  )}
                  {meta.annotations && (
                    <div className="p-2.5 rounded-lg bg-slate-900/40 border border-card-border/30">
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                        🏷️ Ground Truth Annotations
                      </span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block truncate">
                        {meta.annotations}
                      </span>
                    </div>
                  )}
                  {meta.license && (
                    <div className="p-2.5 rounded-lg bg-slate-900/40 border border-card-border/30">
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block font-mono">
                        📜 License & Access
                      </span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block truncate">
                        {meta.license}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Quick Loading Snippet (if HuggingFace) */}
              {hfId && (
                <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between gap-2 text-[11px] font-mono">
                  <span className="text-slate-400 truncate">
                    <span className="text-purple-400">from</span> datasets{" "}
                    <span className="text-purple-400">import</span> load_dataset; ds =
                    load_dataset(<span className="text-emerald-300">"{hfId}"</span>)
                  </span>
                  <span className="text-[9px] text-slate-500 uppercase px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 flex-shrink-0">
                    Python API
                  </span>
                </div>
              )}

              {/* Direct Link Anchor Footer */}
              {directUrl && (
                <div className="pt-2 border-t border-card-border/20 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-1.5 text-slate-400 font-mono min-w-0">
                    <Link2 className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                    <span className="text-[10px] text-slate-500 uppercase font-bold flex-shrink-0">
                      Direct URL:
                    </span>
                    <a
                      href={directUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline truncate max-w-xs sm:max-w-md"
                    >
                      {directUrl}
                    </a>
                  </div>
                  <a
                    href={directUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-primary/80 hover:text-primary font-semibold flex items-center gap-1 flex-shrink-0"
                  >
                    <span>Open Direct Repository</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
