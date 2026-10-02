"use client";

import React from "react";
import { ShieldAlert } from "lucide-react";
import { PeerReview } from "@/types";

interface ReviewStageViewProps {
  review: PeerReview | null;
  selectedReviewerTab: string;
  setSelectedReviewerTab: (tab: string) => void;
}

export default function ReviewStageView({
  review,
  selectedReviewerTab,
  setSelectedReviewerTab,
}: ReviewStageViewProps) {
  if (!review) {
    return (
      <div className="text-center p-12 text-slate-500 text-sm glass-card rounded-2xl border border-card-border/60">
        Manuscript has not been reviewed yet. Run pipeline to trigger peer review panel.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border border-card-border bg-card/20 rounded-xl p-5">
        <div>
          <span className="text-[9px] block uppercase text-slate-500 font-mono">
            Blind Review Summary
          </span>
          <h4 className="text-sm font-bold text-slate-200 mt-1">Publication Readiness Score</h4>
        </div>
        <div className="text-right">
          <span className="text-3xl font-extrabold text-slate-200">{review.score}</span>
          <span className="text-[10px] text-slate-500 block">out of 10.0</span>
        </div>
      </div>

      {review.comments && review.comments.reviewer_1 ? (
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Review Board Critiques
          </h3>
          <div className="flex flex-wrap gap-2 bg-slate-900/60 p-1 rounded-lg border border-card-border/40 w-fit">
            {["reviewer_1", "reviewer_2", "reviewer_3"].map((tab) => {
              const label =
                tab === "reviewer_1"
                  ? "Reviewer 1 (Skeptical)"
                  : tab === "reviewer_2"
                  ? "Reviewer 2 (Methodological)"
                  : "Reviewer 3 (Editor consensus)";
              const active = selectedReviewerTab === tab;
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setSelectedReviewerTab(tab)}
                  className={`px-3 py-1.5 rounded-md text-[10px] font-mono font-semibold transition-all min-h-[32px] ${
                    active
                      ? "bg-primary text-background"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {(() => {
            const activeReview = review.comments[selectedReviewerTab];
            if (!activeReview)
              return <div className="text-xs text-slate-500">No review content loaded.</div>;
            return (
              <div className="p-4 sm:p-5 rounded-xl bg-card/30 border border-card-border/60 text-xs">
                <div className="flex items-center justify-between border-b border-card-border/30 pb-2 mb-3">
                  <span className="font-bold text-slate-300 font-mono uppercase text-[9px]">
                    {selectedReviewerTab.replace("_", " ")} Assessment Sheet
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-primary/15 text-primary border border-primary/20 font-bold font-mono">
                    Score: {activeReview.score}/10.0
                  </span>
                </div>
                <p className="text-slate-300 leading-relaxed whitespace-pre-wrap font-serif italic">
                  "{activeReview.critique}"
                </p>
              </div>
            );
          })()}
        </div>
      ) : (
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Review Comments
          </h3>
          {Object.entries(review.comments || {}).map(([name, critique]) => (
            <div
              key={name}
              className="p-4 rounded-xl bg-card/30 border border-card-border/50 text-xs"
            >
              <span className="font-bold text-slate-300 block mb-1 font-mono uppercase text-[9px]">
                {name}
              </span>
              <p className="text-slate-400 leading-relaxed">
                {typeof critique === "object" ? JSON.stringify(critique) : String(critique)}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="p-5 rounded-xl border border-warning/30 bg-warning/5 space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-warning flex items-center gap-1.5">
          <ShieldAlert className="w-4 h-4" />
          <span>Recommended Improvements</span>
        </h3>
        <ul className="list-disc pl-4 space-y-1.5 text-xs text-slate-300 leading-relaxed">
          {(review.suggestions || []).map((sug: string, i: number) => (
            <li key={i}>{sug}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
