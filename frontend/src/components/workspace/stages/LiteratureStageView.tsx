"use client";

import React from "react";
import { Upload, FileText, Trash2, RefreshCw } from "lucide-react";
import { WorkspaceStage } from "../StageSidebar";
import { LiteraturePaper, UploadedPaper } from "@/types";

interface LiteratureStageViewProps {
  litPapers: LiteraturePaper[];
  stages: WorkspaceStage[];
  uploadedPapers: UploadedPaper[];
  isUploading: boolean;
  deletingPaperId: number | null;
  onUploadPdf: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDeletePaper: (id: number, filename: string) => void;
}

export default function LiteratureStageView({
  litPapers,
  stages,
  uploadedPapers,
  isUploading,
  deletingPaperId,
  onUploadPdf,
  onDeletePaper,
}: LiteratureStageViewProps) {
  const litStage = stages.find((s) => s.stage_name === "literature");
  const summary = litStage?.output_data?.summary || "Compiling summary...";
  const comparisonTable = litStage?.output_data?.comparison_table || [];

  return (
    <div className="space-y-6">
      {/* RAG PDF Upload Panel */}
      <div className="p-4 sm:p-5 rounded-xl border border-card-border bg-card/25 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-2">
            <Upload className="w-3.5 h-3.5" />
            <span>RAG Document Manager</span>
            {uploadedPapers.length > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-[10px] font-mono">
                {uploadedPapers.length} indexed
              </span>
            )}
          </h3>
        </div>
        <p className="text-[11px] text-slate-400">
          Uploaded papers are chunked and indexed into the vector RAG database. They guide literature analysis when arXiv returns no results.
        </p>
        <div className="flex items-center gap-3">
          <input
            type="file"
            accept=".pdf"
            id="ref-pdf-upload"
            className="hidden"
            onChange={onUploadPdf}
            disabled={isUploading}
          />
          <label
            htmlFor="ref-pdf-upload"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary hover:bg-primary/95 text-background text-xs font-bold cursor-pointer transition-all min-h-[38px]"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{isUploading ? "Uploading PDF..." : "Upload Reference PDF"}</span>
          </label>
        </div>

        {/* Uploaded Papers List */}
        {uploadedPapers.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-card-border/30">
            <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
              Indexed Documents
            </p>
            {uploadedPapers.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-slate-900/60 border border-card-border/40 hover:border-primary/20 transition-all group min-h-[44px]"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-200 truncate">{p.filename}</p>
                    <p className="text-[10px] text-slate-500 font-mono">
                      {((p.char_count || 0) / 1000).toFixed(1)}k chars ·{" "}
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : ""}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onDeletePaper(p.id, p.filename)}
                  disabled={deletingPaperId === p.id}
                  title="Remove from RAG index"
                  className="flex-shrink-0 p-2 rounded-md text-slate-500 hover:text-error hover:bg-error/10 border border-transparent hover:border-error/20 transition-all disabled:opacity-40 min-h-[36px] min-w-[36px] flex items-center justify-center"
                >
                  {deletingPaperId === p.id ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {litPapers.length === 0 ? (
        <div className="text-center p-12 text-slate-500 text-sm glass-card rounded-2xl border border-card-border/60">
          No literature parsed yet. Run pipeline to extract domain papers.
        </div>
      ) : (
        <>
          <div className="glass-card rounded-xl p-5 border border-card-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">
              Synthesis Report
            </h3>
            <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
              {summary}
            </div>
          </div>

          <div className="glass-card rounded-xl p-5 border border-card-border">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-primary">
                Methods & Architecture Comparison
              </h3>
              <span className="text-[10px] font-mono text-slate-400">
                {comparisonTable.length} Papers Evaluated
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-card-border/60 text-slate-400">
                    <th className="py-2.5 pr-4 font-semibold">Paper & Architecture</th>
                    <th className="py-2.5 px-3 font-semibold whitespace-nowrap">
                      Reported Metric / Accuracy
                    </th>
                    <th className="py-2.5 pl-4 font-semibold">Key Limitations & Failure Modes</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonTable.map((row: Record<string, string>, i: number) => (
                    <tr
                      key={i}
                      className="border-b border-card-border/20 text-slate-300 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3 pr-4 align-top">
                        <div className="font-semibold text-slate-100">
                          {row.Method || row.method || "Architecture"}
                        </div>
                        {row.Paper && (
                          <div className="text-[11px] text-slate-400 mt-1 font-mono leading-tight">
                            {row.Paper}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3 align-top whitespace-nowrap">
                        <span className="inline-block px-2.5 py-1 rounded-md bg-primary/10 border border-primary/25 text-primary font-mono font-semibold text-[11px]">
                          {row.Accuracy ||
                            row.accuracy ||
                            row.Metric ||
                            row.metric ||
                            row["Key Finding"] ||
                            "Reported in Paper"}
                        </span>
                      </td>
                      <td className="py-3 pl-4 align-top text-slate-300 leading-relaxed text-[11px]">
                        {row.Limitations || row.limitations || "Not specified"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Extracted Literature ({litPapers.length} Papers)
              </h3>
            </div>
            {litPapers.map((paper) => (
              <div
                key={paper.id}
                className="p-4 rounded-xl bg-card/30 border border-card-border/50 hover:border-primary/20 transition-all"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-1.5">
                      {paper.source && (
                        <span className="px-2 py-0.5 rounded text-[9px] uppercase font-mono tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                          {paper.source}
                        </span>
                      )}
                      <span className="px-2 py-0.5 rounded text-[9px] font-mono tracking-wider bg-primary/10 text-primary border border-primary/20">
                        Relevance:{" "}
                        {paper.relevance_score
                          ? Number(paper.relevance_score).toFixed(1)
                          : "8.0"}
                        /10.0
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-slate-200 leading-snug">
                      {paper.url ? (
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-primary transition-colors inline-flex items-center gap-1.5"
                        >
                          {paper.title}
                          <svg
                            className="w-3 h-3 inline-block opacity-70 flex-shrink-0"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                            />
                          </svg>
                        </a>
                      ) : (
                        paper.title
                      )}
                    </h4>
                    <p className="text-[10px] text-slate-400 mt-1 font-mono">{paper.authors}</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3 text-[11px] border-t border-card-border/30 pt-3 text-slate-300">
                  <div>
                    <span className="font-bold block text-[9px] uppercase text-primary mb-1 tracking-wider">
                      Methodology
                    </span>
                    <div className="text-slate-300 leading-relaxed whitespace-pre-line text-[11px]">
                      {paper.methodology}
                    </div>
                  </div>
                  <div>
                    <span className="font-bold block text-[9px] uppercase text-emerald-400 mb-1 tracking-wider">
                      Findings & Metrics
                    </span>
                    <div className="text-slate-300 leading-relaxed whitespace-pre-line text-[11px]">
                      {paper.findings}
                    </div>
                  </div>
                  <div>
                    <span className="font-bold block text-[9px] uppercase text-amber-400 mb-1 tracking-wider">
                      Limitations
                    </span>
                    <div className="text-slate-300 leading-relaxed whitespace-pre-line text-[11px]">
                      {paper.limitations}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
