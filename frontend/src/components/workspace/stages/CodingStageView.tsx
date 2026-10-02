"use client";

import React from "react";
import { Terminal } from "lucide-react";
import { GeneratedFile, SandboxFile, TerminalHistoryItem } from "@/types";

interface CodingStageViewProps {
  projectId: string;
  codeFiles: GeneratedFile[];
  selectedCodeFileId: number | null;
  viewingSandboxFile: boolean;
  activeCodeTab: "db" | "sandbox";
  setActiveCodeTab: (tab: "db" | "sandbox") => void;
  setViewingSandboxFile: (viewing: boolean) => void;
  onSelectCodeFile: (id: number) => void;
  onSelectSandboxFile: (filepath: string) => void;
  sandboxFiles: SandboxFile[];
  selectedSandboxFile: string;
  codeContent: string;
  setCodeContent: (val: string) => void;
  onSaveCode: () => void;
  terminalHistory: TerminalHistoryItem[];
  setTerminalHistory: (hist: TerminalHistoryItem[] | ((prev: TerminalHistoryItem[]) => TerminalHistoryItem[])) => void;
  terminalLoading: boolean;
  terminalInput: string;
  setTerminalInput: (val: string) => void;
  onRunCommand: (e: React.FormEvent) => void;
}

export default function CodingStageView({
  projectId,
  codeFiles,
  selectedCodeFileId,
  viewingSandboxFile,
  activeCodeTab,
  setActiveCodeTab,
  setViewingSandboxFile,
  onSelectCodeFile,
  onSelectSandboxFile,
  sandboxFiles,
  selectedSandboxFile,
  codeContent,
  setCodeContent,
  onSaveCode,
  terminalHistory,
  setTerminalHistory,
  terminalLoading,
  terminalInput,
  setTerminalInput,
  onRunCommand,
}: CodingStageViewProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Sandbox Path Info Bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-card-border/60 bg-slate-900/60 font-mono text-[11px]">
        <div className="flex items-center gap-2 text-slate-400 flex-shrink-0">
          <svg
            className="w-3.5 h-3.5 text-primary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 7a2 2 0 012-2h3.586a1 1 0 01.707.293L11 7h10a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
            />
          </svg>
          <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">
            Sandbox Path
          </span>
        </div>
        <span className="flex-1 text-emerald-400/90 truncate select-all">
          sandbox_{projectId}/
        </span>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(`sandbox_${projectId}/`);
            const btn = document.getElementById("copy-path-btn");
            if (btn) {
              btn.textContent = "Copied!";
              setTimeout(() => {
                btn.textContent = "Copy";
              }, 1500);
            }
          }}
          id="copy-path-btn"
          className="flex-shrink-0 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-card-border/40 text-slate-300 text-[10px] font-bold transition-all min-h-[30px]"
        >
          Copy
        </button>
      </div>

      <div className="flex flex-col md:flex-row gap-4 min-h-[360px] md:h-[400px]">
        {codeFiles.length === 0 ? (
          <div className="text-center p-12 text-slate-500 text-sm my-auto w-full glass-card rounded-xl border border-card-border/60">
            No code structures compiled yet. Run pipeline to synthesize repository.
          </div>
        ) : (
          <>
            {/* Sidebar panel */}
            <div className="w-full md:w-56 bg-card/30 border border-card-border/60 rounded-xl p-3 flex flex-col gap-3 flex-shrink-0 font-mono">
              <div className="flex bg-slate-900/60 p-0.5 rounded border border-card-border/40 text-[10px] font-sans">
                <button
                  type="button"
                  onClick={() => {
                    setActiveCodeTab("db");
                    setViewingSandboxFile(false);
                  }}
                  className={`flex-1 py-1 rounded text-center font-semibold transition-all ${
                    activeCodeTab === "db"
                      ? "bg-primary text-background"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  DB Source
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveCodeTab("sandbox");
                    setViewingSandboxFile(true);
                  }}
                  className={`flex-1 py-1 rounded text-center font-semibold transition-all ${
                    activeCodeTab === "sandbox"
                      ? "bg-primary text-background"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Sandbox Files
                </button>
              </div>

              <div className="flex-1 flex flex-col gap-1 overflow-y-auto max-h-[160px] md:max-h-none">
                {activeCodeTab === "db" ? (
                  codeFiles.map((file) => (
                    <button
                      key={file.id}
                      type="button"
                      onClick={() => {
                        onSelectCodeFile(file.id);
                        setViewingSandboxFile(false);
                      }}
                      className={`w-full text-left px-3 py-1.5 rounded-lg text-[10px] font-semibold break-all border transition-colors min-h-[32px] ${
                        selectedCodeFileId === file.id && !viewingSandboxFile
                          ? "bg-primary/10 text-primary border-primary/20"
                          : "text-slate-400 hover:bg-slate-800/40 border-transparent"
                      }`}
                    >
                      {file.filepath}
                    </button>
                  ))
                ) : sandboxFiles.length === 0 ? (
                  <div className="text-[10px] text-slate-500 text-center py-4">
                    Sandbox is empty.
                  </div>
                ) : (
                  sandboxFiles.map((file) => {
                    const fPath = file.filepath || file.path || file.name;
                    return (
                      <button
                        key={fPath}
                        type="button"
                        onClick={() => onSelectSandboxFile(fPath)}
                        className={`w-full text-left px-3 py-1.5 rounded-lg text-[10px] font-semibold break-all border transition-colors min-h-[32px] ${
                          selectedSandboxFile === fPath && viewingSandboxFile
                            ? "bg-primary/10 text-primary border-primary/20"
                            : "text-slate-400 hover:bg-slate-800/40 border-transparent"
                        }`}
                      >
                        {fPath}
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Code Editor */}
            <div className="flex-1 min-w-0 flex flex-col border border-card-border/60 rounded-xl overflow-hidden bg-slate-950/40">
              <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>Interactive Sandbox Code Editor</span>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={onSaveCode}
                    className="px-2.5 py-1 rounded bg-success hover:bg-success/95 text-background font-bold text-[10px] min-h-[28px]"
                  >
                    Save Changes
                  </button>
                  <span>Python</span>
                </div>
              </div>
              <textarea
                value={codeContent}
                onChange={(e) => setCodeContent(e.target.value)}
                aria-label="Code File Content"
                className="flex-1 p-4 font-mono text-[11px] text-emerald-400/90 bg-transparent resize-none focus:outline-none leading-normal selection:bg-slate-800 animate-fade-in min-h-[220px]"
              />
            </div>
          </>
        )}
      </div>

      {/* Interactive Terminal Drawer */}
      <div className="border border-card-border/60 rounded-xl overflow-hidden bg-slate-950/50 flex flex-col h-[200px]">
        <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1.5 min-w-0">
            <Terminal className="w-3.5 h-3.5 text-primary flex-shrink-0" />
            <span className="flex-shrink-0">Sandbox Shell</span>
            <span className="text-slate-600 mx-1">·</span>
            <span className="text-emerald-400/70 text-[9px] truncate max-w-[200px] sm:max-w-[300px]">
              cwd: backend\sandbox_{projectId}
            </span>
          </span>
          <button
            type="button"
            onClick={() => setTerminalHistory([])}
            className="text-[9px] hover:text-slate-200 transition-colors flex-shrink-0"
          >
            Clear Console
          </button>
        </div>

        <div className="flex-1 p-3 overflow-y-auto font-mono text-[10px] leading-relaxed space-y-1 select-text">
          {terminalHistory.length === 0 ? (
            <div className="text-slate-600">
              Terminal ready. Run non-destructive sandbox diagnostics...
            </div>
          ) : (
            terminalHistory.map((item, idx) => (
              <div
                key={idx}
                className={
                  item.type === "command"
                    ? "text-primary"
                    : item.type === "error"
                    ? "text-error"
                    : "text-slate-300 whitespace-pre-wrap font-bold"
                }
              >
                {item.text}
              </div>
            ))
          )}
          {terminalLoading && (
            <div className="text-slate-500 animate-pulse">Running command...</div>
          )}
        </div>

        <form
          onSubmit={onRunCommand}
          className="border-t border-card-border/40 flex items-center bg-slate-900/30"
        >
          <span className="text-primary font-mono text-xs px-3 select-none">$</span>
          <input
            type="text"
            value={terminalInput}
            onChange={(e) => setTerminalInput(e.target.value)}
            placeholder="Type diagnostic command (e.g. dir, python train.py --help, cat requirements.txt)..."
            aria-label="Diagnostic command input"
            className="flex-1 bg-transparent py-2 text-slate-200 font-mono text-[10px] focus:outline-none min-h-[36px]"
          />
          <button
            type="submit"
            disabled={terminalLoading}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 font-bold font-mono text-[9px] text-slate-300 disabled:opacity-50 min-h-[36px]"
          >
            Execute
          </button>
        </form>
      </div>
    </div>
  );
}
