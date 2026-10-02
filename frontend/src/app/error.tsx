"use client";

import React, { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global application error caught by ErrorBoundary:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background text-slate-200 flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-card p-8 rounded-2xl border border-red-500/30 text-center space-y-6">
        <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 mx-auto flex items-center justify-center">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100">Something went wrong</h2>
          <p className="text-xs text-slate-400 mt-2">
            An unexpected error occurred in the research scientist workspace.
          </p>
          {error?.message && (
            <div className="mt-3 p-3 rounded-lg bg-slate-950/80 border border-card-border/60 text-[11px] font-mono text-red-300 text-left overflow-x-auto max-h-32">
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
            <span>Try Again</span>
          </button>
          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-card-border/60 transition-all"
          >
            <Home className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
