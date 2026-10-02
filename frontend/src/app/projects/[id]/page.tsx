"use strict";

"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api, getToken, API_BASE } from "@/lib/api";
import {
  Project,
  LiteraturePaper,
  ResearchGap,
  Hypothesis,
  DebateData,
  DatasetRecommendation,
  ExperimentPlan,
  GeneratedFile,
  ExperimentRun,
  ScientificPaper,
  PeerReview,
  ResearchMemory,
  KnowledgeGraphData,
  KnowledgeGraphNode,
  ConsoleLogEntry,
  ReasoningStep,
  TerminalHistoryItem,
  UploadedPaper,
  SandboxFile
} from "@/types";

import StageSidebar, { WorkspaceStage, getStageIcon } from "@/components/workspace/StageSidebar";
import WorkspaceHeader from "@/components/workspace/WorkspaceHeader";
import ConsoleTraceDrawer from "@/components/workspace/ConsoleTraceDrawer";
import PublishModal from "@/components/workspace/PublishModal";
import InteractiveKnowledgeGraph from "@/components/workspace/InteractiveKnowledgeGraph";

import LiteratureStageView from "@/components/workspace/stages/LiteratureStageView";
import GapStageView from "@/components/workspace/stages/GapStageView";
import HypothesisStageView from "@/components/workspace/stages/HypothesisStageView";
import DebateStageView from "@/components/workspace/stages/DebateStageView";
import DatasetStageView from "@/components/workspace/stages/DatasetStageView";
import PlanningStageView from "@/components/workspace/stages/PlanningStageView";
import CodingStageView from "@/components/workspace/stages/CodingStageView";
import ExecutionEvaluationStageView from "@/components/workspace/stages/ExecutionEvaluationStageView";
import WritingStageView from "@/components/workspace/stages/WritingStageView";
import ReviewStageView from "@/components/workspace/stages/ReviewStageView";
import MemoryStageView from "@/components/workspace/stages/MemoryStageView";

export default function ProjectWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [stages, setStages] = useState<WorkspaceStage[]>([]);
  const [activeStage, setActiveStage] = useState<string>("literature");
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLogEntry[]>([]);
  const [isStarting, setIsStarting] = useState<boolean>(false);

  // Detail results for active display
  const [litPapers, setLitPapers] = useState<LiteraturePaper[]>([]);
  const [gaps, setGaps] = useState<ResearchGap[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [debate, setDebate] = useState<DebateData | null>(null);
  const [datasets, setDatasets] = useState<DatasetRecommendation[]>([]);
  const [plan, setPlan] = useState<ExperimentPlan | null>(null);
  const [codeFiles, setCodeFiles] = useState<GeneratedFile[]>([]);
  const [selectedCodeFileId, setSelectedCodeFileId] = useState<number | null>(null);
  const [codeContent, setCodeContent] = useState<string>("");
  const [runs, setRuns] = useState<ExperimentRun[]>([]);
  const [paper, setPaper] = useState<ScientificPaper | null>(null);
  const [review, setReview] = useState<PeerReview | null>(null);
  const [memories, setMemories] = useState<ResearchMemory[]>([]);
  const [graphData, setGraphData] = useState<KnowledgeGraphData>({ nodes: [], edges: [] });
  const [selectedGraphNode, setSelectedGraphNode] = useState<KnowledgeGraphNode | null>(null);

  // HITL States
  const [supervisorFeedback, setSupervisorFeedback] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [paperMode, setPaperMode] = useState<"preview" | "latex">("preview");
  const [latexSource, setLatexSource] = useState<string>("");
  const [loadingLatex, setLoadingLatex] = useState<boolean>(false);
  const [selectedReviewerTab, setSelectedReviewerTab] = useState<string>("reviewer_1");
  const [activeCodeTab, setActiveCodeTab] = useState<"db" | "sandbox">("db");
  const [sandboxFiles, setSandboxFiles] = useState<SandboxFile[]>([]);
  const [selectedSandboxFile, setSelectedSandboxFile] = useState<string>("");
  const [viewingSandboxFile, setViewingSandboxFile] = useState<boolean>(false);
  const [terminalInput, setTerminalInput] = useState<string>("");
  const [terminalHistory, setTerminalHistory] = useState<TerminalHistoryItem[]>([]);
  const [terminalLoading, setTerminalLoading] = useState<boolean>(false);
  const [sidebarTab, setSidebarTab] = useState<"console" | "reasoning">("console");
  const [liveReasoning, setLiveReasoning] = useState<Record<string, ReasoningStep[]>>({});
  const [showHFModal, setShowHFModal] = useState(false);
  const [uploadedPapers, setUploadedPapers] = useState<UploadedPaper[]>([]);
  const [deletingPaperId, setDeletingPaperId] = useState<number | null>(null);

  const [isRunning, setIsRunning] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [, setLoading] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);

  // Load project details initially
  const loadProjectDetails = async () => {
    try {
      const data = await api.getProject(projectId);
      setProject(data.project);

      // Sort stages chronologically: lit -> gap -> hypo -> debate -> dataset -> planning -> coding -> execution -> evaluation -> writing -> review -> memory -> graph
      const order = [
        "literature",
        "gap",
        "hypothesis",
        "debate",
        "dataset",
        "planning",
        "coding",
        "execution",
        "evaluation",
        "writing",
        "review",
        "memory",
        "graph",
      ];
      const sortedStages = [...data.stages].sort(
        (a, b) => order.indexOf(a.stage_name) - order.indexOf(b.stage_name)
      );
      setStages(sortedStages);

      const historicalCoT: Record<string, ReasoningStep[]> = {};
      sortedStages.forEach((s) => {
        historicalCoT[s.stage_name] = s.reasoning_chain || [];
      });
      setLiveReasoning(historicalCoT);

      setLitPapers(data.literature || []);
      setGaps(data.gaps || []);
      setHypotheses(data.hypotheses || []);
      setDebate(data.debate);
      setDatasets(data.datasets || []);
      setPlan(data.plan);
      setCodeFiles(data.code_files || []);
      setRuns(data.experiment_runs || []);
      setPaper(data.scientific_paper);
      setReview(data.peer_review);
      setMemories(data.memories || []);
      setIsRunning(data.project.status === "running");

      // Select first file if code exists
      if (data.code_files && data.code_files.length > 0 && selectedCodeFileId === null) {
        handleSelectCodeFile(data.code_files[0].id);
      }

      // Fetch knowledge graph
      const graph = await api.getProjectGraph(projectId);
      setGraphData(graph);
    } catch (err) {
      console.error("Error loading project details", err);
    }
  };

  // Select code file to view content
  const handleSelectCodeFile = async (fileId: number) => {
    setSelectedCodeFileId(fileId);
    try {
      const data = await api.getCodeFile(projectId, fileId);
      setCodeContent(data.content);
    } catch (err) {
      setCodeContent("# Error loading file content.");
    }
  };

  // Save modified code back to sandbox
  const handleSaveCode = async () => {
    if (activeCodeTab === "sandbox") {
      if (!selectedSandboxFile) return;
      try {
        const token = getToken();
        const response = await fetch(
          `${API_BASE}/projects/${projectId}/sandbox/files/write`,
          {
            method: "PUT",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ path: selectedSandboxFile, content: codeContent }),
          }
        );
        if (!response.ok) throw new Error("Save sandbox file failed");
        alert("Sandbox file updated successfully!");
        loadSandboxFiles();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        alert("Error saving sandbox file: " + msg);
      }
    } else {
      if (selectedCodeFileId === null) return;
      try {
        const token = getToken();
        const response = await fetch(
          `${API_BASE}/projects/${projectId}/code/${selectedCodeFileId}`,
          {
            method: "PUT",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ content: codeContent }),
          }
        );
        if (!response.ok) throw new Error("Save code failed");
        alert("Source code updated successfully inside sandbox!");
        loadProjectDetails();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        alert("Error saving code: " + msg);
      }
    }
  };

  // Upload custom PDF reference paper
  const handleUploadPdf = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/papers/upload`, {
        method: "POST",
        credentials: "include",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Upload failed");
      }
      alert("PDF reference uploaded and indexed successfully into project RAG database!");
      loadProjectDetails();
      fetchUploadedPapers();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert("Error uploading reference: " + msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Fetch list of uploaded reference papers for this project
  const fetchUploadedPapers = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/papers`, {
        credentials: "include",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (response.ok) {
        const data = await response.json();
        setUploadedPapers(data.papers || []);
      }
    } catch (err) {
      console.error("Error fetching uploaded papers:", err);
    }
  };

  // Delete an uploaded reference paper
  const handleDeletePaper = async (paperId: number, filename: string) => {
    if (!confirm(`Delete "${filename}" from the RAG index? This cannot be undone.`)) return;
    setDeletingPaperId(paperId);
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/papers/${paperId}`, {
        method: "DELETE",
        credentials: "include",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) throw new Error("Delete failed");
      setUploadedPapers((prev) => prev.filter((p) => p.id !== paperId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert("Error deleting paper: " + msg);
    } finally {
      setDeletingPaperId(null);
    }
  };

  // Approve a paused stage and provide feedback
  const handleApproveStage = async (stageName: string, isApproved: boolean) => {
    try {
      const token = getToken();
      const response = await fetch(
        `${API_BASE}/projects/${projectId}/stages/${stageName}/approve`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ is_approved: isApproved, feedback: supervisorFeedback }),
        }
      );
      if (!response.ok) throw new Error("Approval submission failed");
      setSupervisorFeedback("");
      alert(isApproved ? "Stage approved. Pipeline resuming..." : "Feedback submitted.");
      loadProjectDetails();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert("Error submitting approval: " + msg);
    }
  };

  const loadPaperLatex = async () => {
    setLoadingLatex(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/paper/compile`, {
        credentials: "include",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!response.ok) throw new Error("Failed to load LaTeX source");
      const data = await response.json();
      setLatexSource(data.latex_source);
    } catch (err) {
      console.error(err);
      setLatexSource("% Error loading LaTeX source.");
    } finally {
      setLoadingLatex(false);
    }
  };

  const handleSaveLatex = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/paper/compile`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ latex_source: latexSource }),
      });
      if (!response.ok) throw new Error("Failed to save LaTeX manuscript");
      alert("LaTeX manuscript updated successfully!");
      loadProjectDetails();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert("Error saving LaTeX: " + msg);
    }
  };

  useEffect(() => {
    if (paperMode === "latex") {
      loadPaperLatex();
    }
  }, [paperMode]);

  const loadSandboxFiles = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/sandbox/files`, {
        credentials: "include",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (response.ok) {
        const data = await response.json();
        setSandboxFiles(data.files || []);
      }
    } catch (err) {
      console.error("Error loading sandbox files", err);
    }
  };

  const handleSelectSandboxFile = async (filepath: string) => {
    setSelectedSandboxFile(filepath);
    setViewingSandboxFile(true);
    try {
      const token = getToken();
      const response = await fetch(
        `${API_BASE}/projects/${projectId}/sandbox/files/read?path=${filepath}`,
        {
          credentials: "include",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        }
      );
      if (response.ok) {
        const data = await response.json();
        setCodeContent(data.content);
      }
    } catch (err) {
      setCodeContent("# Error loading sandbox file.");
    }
  };

  const handleRunCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!terminalInput.trim()) return;

    const cmd = terminalInput;
    setTerminalInput("");
    setTerminalHistory((prev) => [...prev, { type: "command", text: `$ ${cmd}` }]);
    setTerminalLoading(true);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/sandbox/terminal`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ command: cmd }),
      });
      const data = await response.json();
      if (response.ok) {
        let output = "";
        if (data.stdout) output += data.stdout;
        if (data.stderr) output += data.stderr;
        if (!output) output = "[Command completed with no output]";
        setTerminalHistory((prev) => [
          ...prev,
          { type: "output", text: output, exitCode: data.exit_code },
        ]);
      } else {
        setTerminalHistory((prev) => [
          ...prev,
          { type: "error", text: data.detail || "Command failed." },
        ]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTerminalHistory((prev) => [
        ...prev,
        { type: "error", text: `Connection error: ${msg}` },
      ]);
    } finally {
      setTerminalLoading(false);
      loadSandboxFiles();
    }
  };

  useEffect(() => {
    if (activeStage === "coding") {
      loadSandboxFiles();
    }
  }, [activeStage, activeCodeTab]);

  // Connect to websocket
  useEffect(() => {
    const init = async () => {
      try {
        await api.getMe();
      } catch {
        router.push("/login");
        return;
      }

      await loadProjectDetails();
      await fetchUploadedPapers();
      setLoading(false);

      // Setup WebSockets (OWASP compliant: clean URL with in-band credential handshake or HttpOnly cookie)
      const wsUrl = api.getWsUrl(projectId);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      const token = getToken();

      ws.onopen = () => {
        setWsConnected(true);
        console.log("WebSocket connected to workspace, transmitting in-band auth handshake...");
        // Send in-band authentication frame over TLS/WS socket
        ws.send(JSON.stringify({ type: "auth", token: token || "cookie_session" }));
      };

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);

        if (payload.type === "authenticated") {
          console.log("WebSocket secure session confirmed by server:", payload.message);
          // If run=true was specified in query, trigger run now that session is authenticated
          const shouldRun = searchParams.get("run") === "true";
          if (shouldRun && project && project.status !== "running") {
            router.replace(`/projects/${projectId}`);
            ws.send(JSON.stringify({ action: "start", topic: project.title }));
          }
        } else if (payload.type === "log") {
          setConsoleLogs((prev) => [...prev, payload.data]);
        } else if (payload.type === "reasoning") {
          const reasoningStep = payload.data;
          const stageName = reasoningStep.stage || "literature";
          setLiveReasoning((prev) => {
            const list = prev[stageName] || [];
            return {
              ...prev,
              [stageName]: [...list, reasoningStep],
            };
          });
        } else if (payload.type === "status") {
          const newStatus = payload.data;
          setIsRunning(newStatus === "running");
          loadProjectDetails(); // Reload data on status transitions
        } else if (payload.type === "info") {
          setConsoleLogs((prev) => [...prev, { level: "INFO", message: payload.message }]);
        } else if (payload.type === "error") {
          setConsoleLogs((prev) => [...prev, { level: "ERROR", message: payload.message }]);
          setIsRunning(false);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log("WebSocket disconnected from workspace");
      };
    };

    init();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [projectId]);

  const handleStartResearch = () => {
    if (isStarting || isRunning) return;
    setIsStarting(true);
    setTimeout(() => setIsStarting(false), 3000);

    const sendStart = () => {
      setConsoleLogs([]);
      wsRef.current!.send(JSON.stringify({ action: "start", topic: project?.title }));
    };

    if (wsRef.current && wsConnected) {
      sendStart();
    } else if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      const onOpen = () => {
        setWsConnected(true);
        sendStart();
        wsRef.current?.removeEventListener("open", onOpen);
        wsRef.current?.removeEventListener("error", onError);
      };
      const onError = () => {
        wsRef.current?.removeEventListener("open", onOpen);
        wsRef.current?.removeEventListener("error", onError);
        setConsoleLogs((prev) => [
          ...prev,
          { level: "ERROR", message: "WebSocket connection failed. Please refresh and try again." },
        ]);
      };
      wsRef.current.addEventListener("open", onOpen);
      wsRef.current.addEventListener("error", onError);
    } else {
      setConsoleLogs((prev) => [
        ...prev,
        { level: "ERROR", message: "WebSocket disconnected. Please refresh the page." },
      ]);
    }
  };

  const pausedStage = stages.find((s) => s.status === "paused");

  return (
    <div className="min-h-screen bg-background flex flex-col relative text-slate-200">
      {/* Workspace Header */}
      <WorkspaceHeader
        projectTitle={project?.title}
        projectStatus={project?.status}
        pausedStage={pausedStage}
        isRunning={isRunning}
        isStarting={isStarting}
        wsConnected={wsConnected}
        canLaunch={
          !isStarting &&
          !isRunning &&
          (wsConnected || wsRef.current?.readyState === WebSocket.CONNECTING)
        }
        onBack={() => router.push("/dashboard")}
        onLaunch={handleStartResearch}
      />

      {/* Main Workspace Layout - Responsive for Tablet & Desktop */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden max-h-[calc(100vh-73px)]">
        {/* Left Sidebar: 13 Stages Timeline */}
        <StageSidebar
          stages={stages}
          activeStage={activeStage}
          onSelectStage={setActiveStage}
        />

        {/* Center: Stage Outputs Board */}
        <section className="flex-1 p-4 sm:p-6 overflow-y-auto flex flex-col gap-6 min-w-0">
          {/* HITL approval card */}
          {pausedStage && (
            <div className="p-4 rounded-xl border border-warning/40 bg-warning/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex-1 min-w-0">
                <span className="text-[10px] px-2 py-0.5 rounded bg-warning/20 text-warning border border-warning/30 font-bold uppercase tracking-wider">
                  Awaiting Supervisor Verification
                </span>
                <h4 className="text-sm font-bold text-slate-200 mt-2">
                  Pipeline paused on: '{pausedStage.stage_name.replace("_", " ")}' stage.
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Review stage outputs below and click Approve to resume execution, or provide override feedback.
                </p>
              </div>
              <div className="flex flex-col gap-2 w-full md:w-64 flex-shrink-0">
                <input
                  type="text"
                  value={supervisorFeedback}
                  onChange={(e) => setSupervisorFeedback(e.target.value)}
                  placeholder="Provide direction/feedback (optional)..."
                  aria-label="Supervisor Feedback"
                  className="w-full px-3 py-1.5 rounded bg-slate-900 border border-card-border text-xs focus:outline-none min-h-[38px]"
                />
                <button
                  type="button"
                  onClick={() => handleApproveStage(pausedStage.stage_name, true)}
                  className="w-full py-1.5 rounded bg-success hover:bg-success/90 text-background font-bold text-xs min-h-[38px]"
                >
                  Approve & Resume
                </button>
              </div>
            </div>
          )}

          {/* Active Stage Heading */}
          <div className="flex items-center justify-between border-b border-card-border/40 pb-3 flex-shrink-0">
            <h2 className="text-sm sm:text-base font-bold text-slate-200 capitalize flex items-center gap-2">
              {getStageIcon(activeStage)}
              <span>{activeStage.replace("_", " ")} Output</span>
            </h2>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
              Stage Workspace
            </span>
          </div>

          {/* Render Stage Specific Output Subcomponent */}
          <div className="flex-1 min-w-0">
            {/* 1. LITERATURE REVIEW VIEW */}
            {activeStage === "literature" && (
              <LiteratureStageView
                litPapers={litPapers}
                stages={stages}
                uploadedPapers={uploadedPapers}
                isUploading={isUploading}
                deletingPaperId={deletingPaperId}
                onUploadPdf={handleUploadPdf}
                onDeletePaper={handleDeletePaper}
              />
            )}

            {/* 2. RESEARCH GAP VIEW */}
            {activeStage === "gap" && (
              <GapStageView gaps={gaps} stages={stages} />
            )}

            {/* 3. HYPOTHESIS VIEW */}
            {activeStage === "hypothesis" && (
              <HypothesisStageView hypotheses={hypotheses} stages={stages} />
            )}

            {/* 4. DEBATE VIEW */}
            {activeStage === "debate" && (
              <DebateStageView debate={debate} />
            )}

            {/* 5. DATASET VIEW */}
            {activeStage === "dataset" && (
              <DatasetStageView datasets={datasets} stages={stages} />
            )}

            {/* 6. EXPERIMENT PLANNING VIEW */}
            {activeStage === "planning" && (
              <PlanningStageView
                plan={plan}
                stageData={stages.find((s) => s.stage_name === "planning")?.output_data}
                project={project}
                hypotheses={hypotheses}
                gaps={gaps}
                onProceedToCoding={() => setActiveStage("coding")}
              />
            )}

            {/* 7. CODE VIEWER VIEW */}
            {activeStage === "coding" && (
              <CodingStageView
                projectId={projectId}
                codeFiles={codeFiles}
                selectedCodeFileId={selectedCodeFileId}
                viewingSandboxFile={viewingSandboxFile}
                activeCodeTab={activeCodeTab}
                setActiveCodeTab={setActiveCodeTab}
                setViewingSandboxFile={setViewingSandboxFile}
                onSelectCodeFile={handleSelectCodeFile}
                onSelectSandboxFile={handleSelectSandboxFile}
                sandboxFiles={sandboxFiles}
                selectedSandboxFile={selectedSandboxFile}
                codeContent={codeContent}
                setCodeContent={setCodeContent}
                onSaveCode={handleSaveCode}
                terminalHistory={terminalHistory}
                setTerminalHistory={setTerminalHistory}
                terminalLoading={terminalLoading}
                terminalInput={terminalInput}
                setTerminalInput={setTerminalInput}
                onRunCommand={handleRunCommand}
              />
            )}

            {/* 8. EXPERIMENT EXECUTION VIEW */}
            {activeStage === "execution" && (
              <ExecutionEvaluationStageView
                activeStage="execution"
                runs={runs}
                stages={stages}
              />
            )}

            {/* 9. EVALUATION STATS VIEW */}
            {activeStage === "evaluation" && (
              <ExecutionEvaluationStageView
                activeStage="evaluation"
                runs={runs}
                stages={stages}
              />
            )}

            {/* 10. SCIENTIFIC WRITER VIEW */}
            {activeStage === "writing" && (
              <WritingStageView
                paper={paper}
                paperMode={paperMode}
                setPaperMode={setPaperMode}
                latexSource={latexSource}
                setLatexSource={setLatexSource}
                loadingLatex={loadingLatex}
                onSaveLatex={handleSaveLatex}
                projectId={projectId}
                onOpenHFModal={() => setShowHFModal(true)}
              />
            )}

            {/* 11. PEER REVIEW VIEW */}
            {activeStage === "review" && (
              <ReviewStageView
                review={review}
                selectedReviewerTab={selectedReviewerTab}
                setSelectedReviewerTab={setSelectedReviewerTab}
              />
            )}

            {/* 12. RESEARCH MEMORY VIEW */}
            {activeStage === "memory" && (
              <MemoryStageView memories={memories} stages={stages} />
            )}

            {/* 13. KNOWLEDGE GRAPH VIEW */}
            {activeStage === "graph" && (
              <div className="h-[450px]">
                <InteractiveKnowledgeGraph
                  graphData={graphData}
                  selectedGraphNode={selectedGraphNode}
                  onSelectNode={setSelectedGraphNode}
                />
              </div>
            )}
          </div>
        </section>

        {/* Right Panel: Live Console Logs & CoT Trace (Collapsible on Tablet/Mobile) */}
        <ConsoleTraceDrawer
          consoleLogs={consoleLogs}
          liveReasoning={liveReasoning}
          activeStage={activeStage}
          wsConnected={wsConnected}
          sidebarTab={sidebarTab}
          setSidebarTab={setSidebarTab}
        />
      </div>

      {/* Hugging Face Hub Modal */}
      <PublishModal
        isOpen={showHFModal}
        onClose={() => setShowHFModal(false)}
        projectId={projectId}
      />
    </div>
  );
}
