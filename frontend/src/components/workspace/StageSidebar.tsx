"use client";

import React from "react";
import {
  BookOpen, GitMerge, Brain, MessageSquare, Database, FileCode,
  Activity, BarChart2, FileText, Award, Cpu, Layers, HelpCircle,
  CheckCircle2, AlertTriangle, Clock, ChevronRight
} from "lucide-react";

import { ReasoningStep } from "@/types";

export type WorkspaceStage = {
  id: number;
  stage_name: string;
  status: string;
  output_data?: Record<string, any> | null;
  started_at?: string | null;
  completed_at?: string | null;
  is_approved: boolean;
  user_feedback?: string | null;
  reasoning_chain?: ReasoningStep[] | null;
};

interface StageSidebarProps {
  stages: WorkspaceStage[];
  activeStage: string;
  onSelectStage: (stageName: string) => void;
}

export const getStageIcon = (name: string) => {
  switch (name) {
    case "literature": return <BookOpen className="w-4 h-4" />;
    case "gap": return <GitMerge className="w-4 h-4" />;
    case "hypothesis": return <Brain className="w-4 h-4" />;
    case "debate": return <MessageSquare className="w-4 h-4" />;
    case "dataset": return <Database className="w-4 h-4" />;
    case "planning": return <Layers className="w-4 h-4" />;
    case "coding": return <FileCode className="w-4 h-4" />;
    case "execution": return <Activity className="w-4 h-4" />;
    case "evaluation": return <BarChart2 className="w-4 h-4" />;
    case "writing": return <FileText className="w-4 h-4" />;
    case "review": return <Award className="w-4 h-4" />;
    case "memory": return <Cpu className="w-4 h-4" />;
    case "graph": return <Layers className="w-4 h-4" />;
    default: return <HelpCircle className="w-4 h-4" />;
  }
};

export default function StageSidebar({
  stages,
  activeStage,
  onSelectStage,
}: StageSidebarProps) {
  return (
    <nav
      role="navigation"
      aria-label="Research Pipeline Stages"
      className="w-full md:w-56 lg:w-64 border-b md:border-b-0 md:border-r border-card-border bg-card/40 flex flex-row md:flex-col overflow-x-auto md:overflow-x-visible md:overflow-y-auto p-3 sm:p-4 gap-2 flex-shrink-0 scrollbar-thin"
    >
      <div className="hidden md:flex items-center justify-between pb-2 mb-1 border-b border-card-border/40 px-1">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">
          Pipeline Stages
        </span>
        <span className="text-[10px] text-slate-500 font-mono">
          {stages.filter((s) => s.status === "completed").length}/{stages.length} Done
        </span>
      </div>

      {stages.map((stage, idx) => {
        const isActive = activeStage === stage.stage_name;
        const isCompleted = stage.status === "completed";
        const isWorking = stage.status === "active";
        const isFailed = stage.status === "failed";
        const isPaused = stage.status === "paused";

        return (
          <button
            key={stage.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-label={`Stage ${idx + 1}: ${stage.stage_name.replace("_", " ")}, status: ${stage.status}`}
            onClick={() => onSelectStage(stage.stage_name)}
            className={`flex items-center gap-2.5 sm:gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 flex-shrink-0 md:flex-shrink text-left min-h-[44px] min-w-[130px] md:min-w-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              isActive
                ? "bg-primary/15 text-primary border border-primary/30 shadow-sm"
                : "border border-transparent hover:bg-slate-800/40 text-slate-400 hover:text-slate-200"
            }`}
          >
            {/* Status Icon Indicator */}
            <div
              className={`p-1.5 rounded-lg flex-shrink-0 transition-colors ${
                isCompleted
                  ? "bg-success/10 text-success"
                  : isWorking
                  ? "bg-primary/10 text-primary animate-pulse"
                  : isPaused
                  ? "bg-warning/10 text-warning animate-pulse"
                  : isFailed
                  ? "bg-error/10 text-error"
                  : "bg-slate-800/80 text-slate-500"
              }`}
            >
              {getStageIcon(stage.stage_name)}
            </div>

            {/* Stage Title and Status - Visible on Tablet and Desktop */}
            <div className="flex-1 min-w-0">
              <p
                className={`text-xs font-semibold capitalize truncate ${
                  isActive ? "text-primary" : "text-slate-300"
                }`}
              >
                {stage.stage_name.replace("_", " ")}
              </p>
              <p className="text-[10px] text-slate-500 capitalize leading-none mt-0.5 truncate">
                {stage.status}
              </p>
            </div>

            {/* Trailing Badges */}
            {isCompleted && (
              <CheckCircle2 className="w-3.5 h-3.5 text-success ml-auto flex-shrink-0 hidden md:block" />
            )}
            {isPaused && (
              <AlertTriangle className="w-3.5 h-3.5 text-warning ml-auto flex-shrink-0 animate-pulse hidden md:block" />
            )}
            {isActive && (
              <ChevronRight className="w-3 h-3 text-primary/60 ml-auto flex-shrink-0 md:hidden" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
