"use client";

import React, { useEffect } from "react";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function ProjectWorkspaceError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Project workspace error caught by ErrorBoundary:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background text-slate-200 flex items-center justify-center p-6">
      <div className="max-w-lg w-full glass-card p-8 rounded-2xl border border-red-500/30 text-center space-y-6">
        <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 mx-auto flex items-center justify-center">
          <AlertCircle className="w-7 h-7" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-100">Project Workspace Render Error</h2>
          <p className="text-xs text-slate-400 mt-2">
            The workspace encountered an unexpected property or formatting error while rendering active research stages.
          </p>
          {error?.message && (
            <div className="mt-4 p-3 rounded-lg bg-slate-950/80 border border-card-border/60 text-[11px] font-mono text-red-300 text-left overflow-x-auto max-h-36">
              {error.message}
            </div>
          )}
        </div>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => reset()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary/90 text-background font-semibold text-xs transition-all shadow-lg shadow-primary/20"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Workspace</span>
          </button>
          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-card-border/60 transition-all"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
