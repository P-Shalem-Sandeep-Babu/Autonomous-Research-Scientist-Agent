"use client";

import React from "react";
import {
  MessageSquare, Brain, CheckCircle2, Layers, BookOpen, AlertTriangle,
  Cpu, Award
} from "lucide-react";
import { DebateData } from "@/types";

interface DebateStageViewProps {
  debate: DebateData | null;
}

export default function DebateStageView({ debate }: DebateStageViewProps) {
  if (!debate) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center border border-card-border/60">
        <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3 text-primary">
          <MessageSquare className="w-6 h-6 animate-pulse" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">Multi-Agent Debate Panel Offline</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Initiate the autonomous research pipeline or advance past Hypothesis Generation to trigger the 4-expert peer review debate.
        </p>
      </div>
    );
  }

  // Extract detailed proposals or parse text strings
  const det = debate.proposals_detailed || {};

  const parseProposal = (key: "a" | "b" | "c", rawText?: string, detObj?: Record<string, unknown>) => {
    if (detObj && detObj.title) {
      return {
        title: String(detObj.title),
        tag: String(
          detObj.tag ||
          (key === "a"
            ? "Surveyed Literature Baseline"
            : key === "b"
            ? "Incremental SOTA Extension"
            : "Target Hypothesis Synthesis (Winner)")
        ),
        citation: String(detObj.citation || ""),
        architecture: String(detObj.architecture || rawText || ""),
        strengths: String(detObj.strengths || ""),
        limitations: String(detObj.limitations || ""),
        complexity: String(detObj.complexity || ""),
        metric: String(detObj.reported_metric || detObj.expected_gain || ""),
      };
    }

    // Parse raw text fallback
    let title =
      key === "a"
        ? "Proposal A: Literature Baseline"
        : key === "b"
        ? "Proposal B: Incremental SOTA"
        : "Proposal C: Novel Hypothesis Synthesis";
    let tag =
      key === "a"
        ? "Surveyed Literature Baseline"
        : key === "b"
        ? "Incremental Extension"
        : "Target Hypothesis Synthesis (Winner)";
    let citation = "";
    let architecture = rawText || "";
    let limitations = "";
    let strengths = "";
    let complexity = "";

    if (rawText) {
      const boldMatch = rawText.match(/^\*\*([^*]+)\*\*(?:\s*\[([^\]]+)\])?:\s*([\s\S]*)/);
      if (boldMatch) {
        title = boldMatch[1].trim();
        if (boldMatch[2]) citation = boldMatch[2].trim();
        architecture = boldMatch[3].trim();
      } else {
        const colonIdx = rawText.indexOf(":");
        if (colonIdx > 0 && colonIdx < 60) {
          title = rawText.slice(0, colonIdx).trim();
          architecture = rawText.slice(colonIdx + 1).trim();
        }
      }
    }

    return { title, tag, citation, architecture, strengths, limitations, complexity, metric: "" };
  };

  const propA = parseProposal("a", debate.proposal_a, det.a);
  const propB = parseProposal("b", debate.proposal_b, det.b);
  const propC = parseProposal("c", debate.proposal_c, det.c);

  const getAgentBadge = (name: string) => {
    const lower = (name || "").toLowerCase();
    if (lower.includes("mod") || lower.includes("chair")) {
      return { role: "Lead Session Chair", color: "text-blue-400 bg-blue-500/10 border-blue-500/30", icon: "🎙️" };
    }
    if (lower.includes("neuro") || lower.includes("domain") || lower.includes("specialist") || lower.includes("bio")) {
      return { role: "Domain & Clinical Specialist", color: "text-purple-400 bg-purple-500/10 border-purple-500/30", icon: "🔬" };
    }
    if (lower.includes("hard") || lower.includes("opt") || lower.includes("compute")) {
      return { role: "Hardware & Compute Architect", color: "text-amber-400 bg-amber-500/10 border-amber-500/30", icon: "⚡" };
    }
    if (lower.includes("stat") || lower.includes("method")) {
      return { role: "Biostatistician & Methodologist", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30", icon: "📊" };
    }
    return { role: "Panelist", color: "text-slate-400 bg-slate-500/10 border-slate-500/30", icon: "💬" };
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-slate-900/60 border border-card-border/60">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-primary font-mono flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5" /> Stage 4 · Multi-Agent Scientific Debate
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-mono">
              4-Expert Swarm Panel
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Rigorous cross-examination of competing architectures grounded in surveyed papers, compute budgets, and statistical validity.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-center">
          <span className="text-[11px] px-2.5 py-1 rounded-lg bg-success/15 text-success border border-success/30 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> Unanimous Consensus Reached
          </span>
        </div>
      </div>

      {/* 3 Competing Technical Proposals - Responsive for Tablet & Desktop */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-primary" /> Competing Architectural Proposals
          </h3>
          <span className="text-[11px] text-slate-400">Evaluated across 4 peer review rounds</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {/* Proposal A: Literature Baseline */}
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 hover:border-slate-700/80 transition-all flex flex-col justify-between space-y-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono uppercase">
                  Proposal A · Baseline
                </span>
                <span className="text-[9px] text-slate-400 font-mono">Prior Literature</span>
              </div>
              <h4 className="text-sm font-bold text-slate-200 leading-snug">
                {propA.title}
              </h4>
              {propA.citation && (
                <p className="text-[11px] font-mono text-blue-300/80 flex items-center gap-1">
                  <BookOpen className="w-3 h-3 flex-shrink-0" /> {propA.citation}
                </p>
              )}
              <p className="text-xs text-slate-300 leading-relaxed pt-1 border-t border-card-border/30">
                {propA.architecture}
              </p>
            </div>

            <div className="space-y-2 pt-2 border-t border-card-border/30 text-[11px]">
              {propA.limitations && (
                <div className="p-2 rounded-lg bg-amber-950/20 border border-amber-900/30 text-amber-200/90 text-[10px] leading-relaxed flex items-start gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Critical Limitation:</strong> {propA.limitations}</span>
                </div>
              )}
              {propA.complexity && (
                <div className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
                  <Cpu className="w-3 h-3 text-slate-500" />
                  <span>{propA.complexity}</span>
                </div>
              )}
            </div>
          </div>

          {/* Proposal B: Incremental SOTA Extension */}
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 hover:border-slate-700/80 transition-all flex flex-col justify-between space-y-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono uppercase">
                  Proposal B · Extension
                </span>
                <span className="text-[9px] text-slate-400 font-mono">Incremental SOTA</span>
              </div>
              <h4 className="text-sm font-bold text-slate-200 leading-snug">
                {propB.title}
              </h4>
              {propB.citation && (
                <p className="text-[11px] font-mono text-purple-300/80 flex items-center gap-1">
                  <BookOpen className="w-3 h-3 flex-shrink-0" /> {propB.citation}
                </p>
              )}
              <p className="text-xs text-slate-300 leading-relaxed pt-1 border-t border-card-border/30">
                {propB.architecture}
              </p>
            </div>

            <div className="space-y-2 pt-2 border-t border-card-border/30 text-[11px]">
              {propB.limitations && (
                <div className="p-2 rounded-lg bg-amber-950/20 border border-amber-900/30 text-amber-200/90 text-[10px] leading-relaxed flex items-start gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Key Bottleneck:</strong> {propB.limitations}</span>
                </div>
              )}
              {propB.complexity && (
                <div className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
                  <Cpu className="w-3 h-3 text-slate-500" />
                  <span>{propB.complexity}</span>
                </div>
              )}
            </div>
          </div>

          {/* Proposal C: Target Hypothesis Synthesis (WINNER) - Spans across on tablet */}
          <div className="p-4 rounded-xl bg-gradient-to-b from-emerald-950/30 via-slate-900/50 to-slate-950 border-2 border-emerald-500/50 shadow-lg shadow-emerald-950/30 flex flex-col justify-between space-y-3 relative overflow-hidden md:col-span-2 xl:col-span-1">
            <div className="absolute -top-6 -right-6 w-20 h-20 bg-emerald-500/10 rounded-full blur-xl pointer-events-none"></div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono uppercase flex items-center gap-1">
                  <Award className="w-3 h-3 text-emerald-400" /> Proposal C · Selected Winner
                </span>
                <span className="text-[9px] font-bold text-emerald-400 font-mono">Consensus Pick</span>
              </div>
              <h4 className="text-sm font-bold text-slate-100 leading-snug">
                {propC.title}
              </h4>
              {propC.citation && (
                <p className="text-[11px] font-mono text-emerald-400/90 flex items-center gap-1">
                  <BookOpen className="w-3 h-3 flex-shrink-0" /> {propC.citation}
                </p>
              )}
              <p className="text-xs text-slate-200 leading-relaxed pt-1 border-t border-emerald-500/20 font-medium">
                {propC.architecture}
              </p>
            </div>

            <div className="space-y-2 pt-2 border-t border-emerald-500/20 text-[11px]">
              {(propC.strengths || propC.metric) && (
                <div className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-200 text-[10px] leading-relaxed flex items-start gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Decisive Advantage:</strong> {propC.strengths || propC.metric}</span>
                </div>
              )}
              {propC.complexity && (
                <div className="text-[10px] font-mono text-emerald-300/80 flex items-center gap-1.5">
                  <Cpu className="w-3 h-3 text-emerald-400" />
                  <span>{propC.complexity}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Agent Dialogue Log */}
      <div className="glass-card rounded-xl border border-card-border/70 p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-card-border/40 pb-3">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-mono">
              Swarm Panel Transcripts & Peer Cross-Examination
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            {debate.debate_rounds?.length || 0} Dialogue Rounds
          </span>
        </div>

        <div className="space-y-3 max-h-[380px] overflow-y-auto pr-2 custom-scrollbar">
          {(debate.debate_rounds || []).map((round: { agent?: string; persona?: string; argument?: string; content?: string; role?: string; message?: string }, i: number) => {
            const badge = getAgentBadge(round.agent || "");
            return (
              <div key={i} className="p-3.5 rounded-xl bg-slate-900/40 border border-card-border/40 hover:border-card-border transition-colors space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm">{badge.icon}</span>
                    <span className="text-xs font-bold text-slate-200 font-mono">{round.agent}</span>
                    <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${badge.color}`}>
                      {badge.role}
                    </span>
                  </div>
                  <span className="text-[9px] font-mono text-slate-500">Round {i + 1}</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed pl-6">
                  {round.message || round.argument || round.content || ""}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Consensus Selection & Rationale Footer */}
      <div className="p-4 sm:p-5 rounded-xl border-2 border-emerald-500/40 bg-gradient-to-r from-emerald-950/30 via-slate-900/50 to-slate-950 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-lg shadow-emerald-950/20">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold uppercase tracking-wider font-mono flex items-center gap-1">
              <Award className="w-3 h-3 text-emerald-400" /> Consensus Winning Architecture
            </span>
          </div>
          <h4 className="text-base font-bold text-slate-100">{debate.winner_proposal}</h4>
          <p className="text-xs text-slate-300 leading-relaxed max-w-4xl pt-1">
            <strong>Scientific Selection Rationale:</strong> {debate.rationale}
          </p>
        </div>
        <div className="flex-shrink-0 self-start md:self-center">
          <div className="px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-left md:text-right">
            <span className="text-[9px] text-emerald-400 font-mono block uppercase">Pipeline Status</span>
            <span className="text-xs font-bold text-slate-200">Ready for Dataset Stage</span>
          </div>
        </div>
      </div>
    </div>
  );
}
