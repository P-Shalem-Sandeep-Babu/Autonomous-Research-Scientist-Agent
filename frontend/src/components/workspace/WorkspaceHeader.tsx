"use client";

import React from "react";
import { ArrowLeft, Play } from "lucide-react";
import { WorkspaceStage } from "./StageSidebar";

interface WorkspaceHeaderProps {
  projectTitle?: string;
  projectStatus?: string;
  pausedStage?: WorkspaceStage;
  isRunning: boolean;
  isStarting: boolean;
  wsConnected: boolean;
  canLaunch: boolean;
  onBack: () => void;
  onLaunch: () => void;
}

export default function WorkspaceHeader({
  projectTitle,
  projectStatus,
  pausedStage,
  isRunning,
  isStarting,
  wsConnected,
  canLaunch,
  onBack,
  onLaunch,
}: WorkspaceHeaderProps) {
  return (
    <header className="border-b border-card-border bg-card/60 backdrop-blur-md sticky top-0 z-20 px-4 sm:px-6 py-3.5 flex flex-wrap sm:flex-nowrap items-center justify-between gap-3">
      {/* Title & Back Navigation */}
      <div className="flex items-center gap-3 sm:gap-4 min-w-0">
        <button
          type="button"
          onClick={onBack}
          aria-label="Back to Projects Dashboard"
          className="p-2 rounded-lg border border-card-border hover:bg-card text-slate-400 hover:text-slate-200 transition-colors flex-shrink-0 min-h-[40px] min-w-[40px] flex items-center justify-center"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="min-w-0">
          <h1 className="text-sm sm:text-base font-bold text-slate-200 truncate">
            {projectTitle || "Research Workspace"}
          </h1>
          <p className="text-[11px] sm:text-xs text-slate-500 hidden sm:block truncate">
            Autonomous Scientist Sandbox Workspace
          </p>
        </div>
      </div>

      {/* Status & Pipeline Launch Button */}
      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0 ml-auto">
        <span
          className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
            pausedStage
              ? "bg-warning/10 text-warning border-warning/20 animate-pulse"
              : isRunning
              ? "bg-primary/10 text-primary border-primary/20 animate-pulse"
              : projectStatus === "completed"
              ? "bg-success/10 text-success border-success/20"
              : "bg-slate-800 border-slate-700 text-slate-400"
          }`}
        >
          {pausedStage
            ? "Awaiting Verification"
            : isRunning
            ? "Executing Agents"
            : projectStatus === "completed"
            ? "Research Completed"
            : "Pipeline Idle"}
        </span>

        {projectStatus !== "running" && !pausedStage && (
          <button
            type="button"
            onClick={onLaunch}
            disabled={!canLaunch}
            title={
              isStarting
                ? "Initializing..."
                : !wsConnected
                ? "Connecting to server..."
                : "Launch research pipeline"
            }
            className="flex items-center gap-1.5 px-3.5 sm:px-4 py-2 bg-primary hover:bg-primary/95 text-background font-semibold rounded-lg text-xs shadow-lg shadow-primary/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed min-h-[40px]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>
              {isStarting
                ? "Launching..."
                : wsConnected
                ? "Launch Pipeline"
                : "Connecting..."}
            </span>
          </button>
        )}
      </div>
    </header>
  );
}
