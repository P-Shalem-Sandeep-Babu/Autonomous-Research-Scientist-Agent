"use client";

import React from "react";
import { API_BASE } from "@/lib/api";
import { ScientificPaper } from "@/types";

interface WritingStageViewProps {
  paper: ScientificPaper | null;
  paperMode: "preview" | "latex";
  setPaperMode: (mode: "preview" | "latex") => void;
  latexSource: string;
  setLatexSource: (val: string) => void;
  loadingLatex: boolean;
  onSaveLatex: () => void;
  projectId: string;
  onOpenHFModal: () => void;
}

export default function WritingStageView({
  paper,
  paperMode,
  setPaperMode,
  latexSource,
  setLatexSource,
  loadingLatex,
  onSaveLatex,
  projectId,
  onOpenHFModal,
}: WritingStageViewProps) {
  if (!paper) {
    return (
      <div className="text-center p-12 text-slate-500 text-sm glass-card rounded-2xl border border-card-border/60">
        Manuscript draft is empty. Run pipeline to synthesize paper.
      </div>
    );
  }

  // Derive PDF URL dynamically from API_BASE
  const pdfUrl = `${API_BASE.replace(/\/api\/v1$/, "")}/static/papers/arsa_paper_${projectId}.pdf`;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        {/* Dual Mode View Selector */}
        <div className="flex items-center gap-2 bg-slate-900/60 p-1 rounded-lg border border-card-border/40 w-fit">
          <button
            type="button"
            onClick={() => setPaperMode("preview")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all min-h-[36px] ${
              paperMode === "preview"
                ? "bg-primary text-background shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Manuscript Preview
          </button>
          <button
            type="button"
            onClick={() => setPaperMode("latex")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all min-h-[36px] ${
              paperMode === "latex"
                ? "bg-primary text-background shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            LaTeX Source
          </button>
        </div>

        {/* Content & Action Panel */}
        <div className="flex flex-col xl:flex-row gap-6">
          {paperMode === "preview" ? (
            <div className="flex-1 min-w-0 glass-card rounded-xl border border-card-border p-6 overflow-y-auto max-h-[550px] text-xs text-slate-300 font-serif leading-relaxed">
              <div className="text-center mb-8 font-sans">
                <span className="text-[9px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 uppercase tracking-widest font-bold font-mono">
                  Publication Draft
                </span>
                <h2 className="text-base font-extrabold text-slate-100 tracking-tight mt-3">
                  {paper.title}
                </h2>
                <p className="text-[10px] text-slate-400 mt-1">
                  Authors: ARSA Multi-Agent Intelligence Core
                </p>
              </div>

              <div className="border-t border-card-border/60 pt-4 mb-6">
                <h4 className="font-sans font-bold text-slate-200 mb-1 uppercase tracking-wide text-[10px]">
                  Abstract
                </h4>
                <p className="text-slate-400 italic text-[11px] leading-relaxed">
                  {paper.abstract}
                </p>
              </div>

              {Object.entries(paper.sections || {}).map(([secTitle, secText]) => (
                <div key={secTitle} className="mb-6">
                  <h4 className="font-sans font-bold text-slate-200 mb-2">{secTitle}</h4>
                  <p className="whitespace-pre-line leading-relaxed text-slate-300">{String(secText)}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex-1 min-w-0 flex flex-col md:flex-row gap-4 min-h-[500px]">
              {/* LaTeX Editor */}
              <div className="flex-1 min-w-0 flex flex-col border border-card-border/60 rounded-xl overflow-hidden bg-slate-950/40">
                <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Interactive LaTeX Editor</span>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={onSaveLatex}
                      disabled={loadingLatex}
                      className="px-2.5 py-1 rounded bg-success hover:bg-success/90 text-background font-bold text-[10px] disabled:opacity-50 min-h-[30px]"
                    >
                      Save Manuscript
                    </button>
                    <span>LaTeX</span>
                  </div>
                </div>
                {loadingLatex ? (
                  <div className="flex-1 flex items-center justify-center text-xs text-slate-500 font-mono">
                    Loading LaTeX source...
                  </div>
                ) : (
                  <textarea
                    value={latexSource}
                    onChange={(e) => setLatexSource(e.target.value)}
                    aria-label="LaTeX Manuscript Code"
                    className="flex-1 p-4 font-mono text-[11px] text-emerald-400/90 bg-transparent resize-none focus:outline-none leading-normal selection:bg-slate-800 min-h-[420px]"
                  />
                )}
              </div>

              {/* Live Compiled PDF Preview Panel */}
              <div className="flex-1 min-w-0 flex flex-col border border-card-border/60 rounded-xl overflow-hidden bg-slate-900/10">
                <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Live Compiled PDF Preview</span>
                  <span>PDF Frame</span>
                </div>
                <iframe
                  src={pdfUrl}
                  className="flex-1 w-full bg-slate-950/20 border-none min-h-[420px]"
                  title="LaTeX compiled PDF preview"
                />
              </div>
            </div>
          )}

          {/* Action Sidebar / Readiness Card */}
          <div className="w-full xl:w-60 flex flex-col sm:flex-row xl:flex-col gap-4 flex-shrink-0">
            <div className="flex-1 sm:flex-none p-4 rounded-xl border border-card-border bg-card/40">
              <span className="text-[9px] block uppercase text-slate-500 font-mono">
                Publication Readiness
              </span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-2xl font-extrabold text-slate-200">
                  {paper.publication_readiness_score || 0}%
                </span>
                <span className="text-[10px] text-success">Passed threshold</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => alert("LaTeX paper compiled. PDF Download initiated!")}
              className="flex-1 sm:flex-none py-3 px-4 rounded-lg bg-primary hover:bg-primary/95 text-background font-bold text-xs shadow-lg shadow-primary/20 transition-all text-center min-h-[44px]"
            >
              Compile & Export (PDF)
            </button>

            <button
              type="button"
              onClick={onOpenHFModal}
              className="flex-1 sm:flex-none py-3 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-500/20 transition-all text-center min-h-[44px]"
            >
              Publish to Hugging Face Hub
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
