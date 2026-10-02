"use client";

import React, { useRef, useEffect, useState } from "react";
import { Terminal, Brain, ChevronDown, ChevronUp, Maximize2, Minimize2 } from "lucide-react";
import { ConsoleLogEntry, ReasoningStep } from "@/types";

interface ConsoleTraceDrawerProps {
  consoleLogs: ConsoleLogEntry[];
  liveReasoning: Record<string, ReasoningStep[]>;
  activeStage: string;
  wsConnected: boolean;
  sidebarTab: "console" | "reasoning";
  setSidebarTab: (tab: "console" | "reasoning") => void;
}

export default function ConsoleTraceDrawer({
  consoleLogs,
  liveReasoning,
  activeStage,
  wsConnected,
  sidebarTab,
  setSidebarTab,
}: ConsoleTraceDrawerProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const consoleBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isCollapsed && sidebarTab === "console" && consoleBottomRef.current) {
      consoleBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [consoleLogs.length, isCollapsed, sidebarTab]);

  return (
    <aside
      aria-label="Real-time Execution Logs and Reasoning Chain"
      className={`border-t xl:border-t-0 xl:border-l border-card-border bg-card/20 flex flex-col flex-shrink-0 transition-all duration-200 ${
        isCollapsed
          ? "h-11 xl:h-full xl:w-14 overflow-hidden"
          : "w-full xl:w-[340px] max-h-[360px] xl:max-h-full h-full"
      }`}
    >
      {/* Header bar */}
      <div className="border-b border-card-border/60 px-3 py-2 flex items-center justify-between bg-card/40 flex-shrink-0">
        <div className="flex items-center gap-2">
          {!isCollapsed && (
            <div className="flex bg-slate-900/60 p-0.5 rounded border border-card-border/40 text-[10px] font-sans">
              <button
                type="button"
                onClick={() => setSidebarTab("console")}
                className={`px-2.5 py-1 rounded text-center font-semibold transition-all ${
                  sidebarTab === "console"
                    ? "bg-primary text-background"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Logs ({consoleLogs.length})
              </button>
              <button
                type="button"
                onClick={() => setSidebarTab("reasoning")}
                className={`px-2.5 py-1 rounded text-center font-semibold transition-all ${
                  sidebarTab === "reasoning"
                    ? "bg-primary text-background"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                CoT Trace
              </button>
            </div>
          )}

          {isCollapsed && (
            <span className="text-[10px] font-mono text-slate-400 font-bold xl:hidden">
              Telemetry & Logs ({consoleLogs.length})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* WS Status Dot */}
          <span
            title={wsConnected ? "WebSocket Connected" : "Connecting to telemetry stream..."}
            className={`w-2 h-2 rounded-full ${
              wsConnected ? "bg-success" : "bg-error animate-ping"
            }`}
          />

          {/* Toggle Expand / Collapse */}
          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title={isCollapsed ? "Expand Telemetry Panel" : "Collapse Telemetry Panel"}
            aria-label={isCollapsed ? "Expand Telemetry Panel" : "Collapse Telemetry Panel"}
          >
            {isCollapsed ? (
              <ChevronUp className="w-4 h-4 xl:rotate-90" />
            ) : (
              <ChevronDown className="w-4 h-4 xl:-rotate-90" />
            )}
          </button>
        </div>
      </div>

      {/* Main Drawer Body */}
      {!isCollapsed && (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {sidebarTab === "console" ? (
            <div
              tabIndex={0}
              role="log"
              aria-label="Console log output"
              className="flex-1 p-3.5 overflow-y-auto font-mono text-[10px] text-slate-400 leading-relaxed bg-slate-950/40 space-y-2 select-text"
            >
              {consoleLogs.length === 0 ? (
                <div className="text-slate-600 text-center py-12">
                  Console stream is idle. Launch research pipeline to read logs.
                </div>
              ) : (
                consoleLogs.map((log, idx) => {
                  let color = "text-slate-400";
                  if (log.level === "ERROR") color = "text-error font-bold";
                  if (log.level === "WARNING") color = "text-warning";
                  if (typeof log.message === "string" && log.message.startsWith("===")) {
                    color = "text-primary font-bold";
                  }

                  return (
                    <div key={idx} className={color}>
                      <span className="text-slate-600 select-none mr-1.5 font-mono">
                        [{new Date(log.timestamp || Date.now()).toLocaleTimeString()}]
                      </span>
                      {log.message}
                    </div>
                  );
                })
              )}
              <div ref={consoleBottomRef} />
            </div>
          ) : (
            <div
              tabIndex={0}
              role="region"
              aria-label="Agent reasoning chain steps"
              className="flex-1 p-3.5 overflow-y-auto bg-slate-950/40 space-y-4"
            >
              <div className="text-[11px] font-sans border-b border-card-border/30 pb-2 flex items-center justify-between text-slate-300 font-semibold">
                <span>Active Agent: {activeStage.replace("_", " ").toUpperCase()}</span>
                <span className="text-[9px] text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                  Chain-of-Thought
                </span>
              </div>

              {!liveReasoning[activeStage] || liveReasoning[activeStage].length === 0 ? (
                <div className="text-slate-600 text-center py-12 text-[10px] font-mono">
                  No reasoning steps logged for this stage yet. Run pipeline.
                </div>
              ) : (
                <div className="space-y-4 relative pl-3 border-l border-card-border/40 ml-2 mt-2">
                  {liveReasoning[activeStage].map((step, idx) => (
                    <div key={idx} className="relative group">
                      <div className="absolute -left-[16px] top-1.5 w-1.5 h-1.5 rounded-full bg-primary ring-4 ring-primary/10 group-hover:scale-125 transition-transform" />
                      <div className="bg-slate-900/40 p-2.5 rounded-lg border border-card-border/40 text-[10px]">
                        <div className="flex items-center justify-between text-slate-500 mb-1 font-mono text-[8px]">
                          <span className="font-semibold text-primary/80 uppercase">
                            Step {idx + 1}
                          </span>
                          <span>{new Date(step.timestamp || Date.now()).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-300 leading-normal whitespace-pre-wrap font-sans">
                          {step.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
