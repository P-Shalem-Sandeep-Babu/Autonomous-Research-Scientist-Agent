"use strict";

"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api, getToken } from "@/lib/api";
import { 
  ArrowLeft, Play, Terminal, BookOpen, GitMerge, Brain, MessageSquare, 
  Database, FileCode, CheckCircle2, AlertTriangle, HelpCircle, FileText, 
  Activity, Award, RefreshCw, BarChart2, Layers, ShieldAlert, Cpu, Trash2, Upload
} from "lucide-react";
import ResearchChart from "@/components/ResearchChart";

type Stage = {
  id: number;
  stage_name: string;
  status: string;
  output_data?: any;
  started_at?: string;
  completed_at?: string;
  is_approved: boolean;
  user_feedback?: string;
};

export default function ProjectWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  
  const [project, setProject] = useState<any>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [activeStage, setActiveStage] = useState<string>("literature");
  const [consoleLogs, setConsoleLogs] = useState<any[]>([]);
  
  // Detail results for active display
  const [litPapers, setLitPapers] = useState<any[]>([]);
  const [gaps, setGaps] = useState<any[]>([]);
  const [hypotheses, setHypotheses] = useState<any[]>([]);
  const [debate, setDebate] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [plan, setPlan] = useState<any>(null);
  const [codeFiles, setCodeFiles] = useState<any[]>([]);
  const [selectedCodeFileId, setSelectedCodeFileId] = useState<number | null>(null);
  const [codeContent, setCodeContent] = useState<string>("");
  const [runs, setRuns] = useState<any[]>([]);
  const [paper, setPaper] = useState<any>(null);
  const [review, setReview] = useState<any>(null);
  const [reach, setReach] = useState<any[]>([]);
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [selectedGraphNode, setSelectedGraphNode] = useState<any>(null);

  // HITL States
  const [supervisorFeedback, setSupervisorFeedback] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [paperMode, setPaperMode] = useState<"preview" | "latex">("preview");
  const [latexSource, setLatexSource] = useState<string>("");
  const [loadingLatex, setLoadingLatex] = useState<boolean>(false);
  const [selectedReviewerTab, setSelectedReviewerTab] = useState<string>("reviewer_1");
  const [activeCodeTab, setActiveCodeTab] = useState<"db" | "sandbox">("db");
  const [sandboxFiles, setSandboxFiles] = useState<any[]>([]);
  const [selectedSandboxFile, setSelectedSandboxFile] = useState<string>("");
  const [viewingSandboxFile, setViewingSandboxFile] = useState<boolean>(false);
  const [terminalInput, setTerminalInput] = useState<string>("");
  const [terminalHistory, setTerminalHistory] = useState<any[]>([]);
  const [terminalLoading, setTerminalLoading] = useState<boolean>(false);
  const [sidebarTab, setSidebarTab] = useState<"console" | "reasoning">("console");
  const [liveReasoning, setLiveReasoning] = useState<Record<string, any[]>>({});
  const [showHFModal, setShowHFModal] = useState(false);
  const [hfPublishing, setHfPublishing] = useState(false);
  const [hfRepoUrl, setHfRepoUrl] = useState("");
  const [uploadedPapers, setUploadedPapers] = useState<any[]>([]);
  const [deletingPaperId, setDeletingPaperId] = useState<number | null>(null);

  const [isRunning, setIsRunning] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const wsRef = useRef<WebSocket | null>(null);
  const consoleBottomRef = useRef<HTMLDivElement | null>(null);

  // Load project details initially
  const loadProjectDetails = async () => {
    try {
      const data = await api.getProject(projectId);
      setProject(data.project);
      
      // Sort stages chronologically: lit -> gap -> hypo -> debate -> dataset -> planning -> coding -> execution -> evaluation -> writing -> review -> memory -> graph
      const order = ["literature", "gap", "hypothesis", "debate", "dataset", "planning", "coding", "execution", "evaluation", "writing", "review", "memory", "graph"];
      const sortedStages = [...data.stages].sort(
        (a, b) => order.indexOf(a.stage_name) - order.indexOf(b.stage_name)
      );
      setStages(sortedStages);

      const historicalCoT: Record<string, any[]> = {};
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
      setReach(data.reach_evidence || []);
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
        const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/sandbox/files/write`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ path: selectedSandboxFile, content: codeContent }),
        });
        if (!response.ok) throw new Error("Save sandbox file failed");
        alert("Sandbox file updated successfully!");
        loadSandboxFiles();
      } catch (err: any) {
        alert("Error saving sandbox file: " + err.message);
      }
    } else {
      if (selectedCodeFileId === null) return;
      try {
        const token = getToken();
        const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/code/${selectedCodeFileId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: codeContent }),
        });
        if (!response.ok) throw new Error("Save code failed");
        alert("Source code updated successfully inside sandbox!");
        loadProjectDetails();
      } catch (err: any) {
        alert("Error saving code: " + err.message);
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
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/papers/upload`, {
        method: "POST",
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
    } catch (err: any) {
      alert("Error uploading reference: " + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  // Fetch list of uploaded reference papers for this project
  const fetchUploadedPapers = async () => {
    try {
      const token = getToken();
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/papers`, {
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
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/papers/${paperId}`, {
        method: "DELETE",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) throw new Error("Delete failed");
      setUploadedPapers(prev => prev.filter(p => p.id !== paperId));
    } catch (err: any) {
      alert("Error deleting paper: " + err.message);
    } finally {
      setDeletingPaperId(null);
    }
  };

  // Approve a paused stage and provide feedback
  const handleApproveStage = async (stageName: string, isApproved: boolean) => {
    try {
      const token = getToken();
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/stages/${stageName}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ is_approved: isApproved, feedback: supervisorFeedback }),
      });
      if (!response.ok) throw new Error("Approval submission failed");
      setSupervisorFeedback("");
      alert(isApproved ? "Stage approved. Pipeline resuming..." : "Feedback submitted.");
      loadProjectDetails();
    } catch (err: any) {
      alert("Error submitting approval: " + err.message);
    }
  };

  const loadPaperLatex = async () => {
    setLoadingLatex(true);
    try {
      const token = getToken();
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/paper/compile`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }
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
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/paper/compile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ latex_source: latexSource }),
      });
      if (!response.ok) throw new Error("Failed to save LaTeX manuscript");
      alert("LaTeX manuscript updated successfully!");
      loadProjectDetails();
    } catch (err: any) {
      alert("Error saving LaTeX: " + err.message);
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
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/sandbox/files`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }
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
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/sandbox/files/read?path=${filepath}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }
      });
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
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/sandbox/terminal`, {
        method: "POST",
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
        setTerminalHistory((prev) => [...prev, { type: "output", text: output, exitCode: data.exit_code }]);
      } else {
        setTerminalHistory((prev) => [...prev, { type: "error", text: data.detail || "Command failed." }]);
      }
    } catch (err: any) {
      setTerminalHistory((prev) => [...prev, { type: "error", text: `Connection error: ${err.message}` }]);
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
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    const init = async () => {
      await loadProjectDetails();
      await fetchUploadedPapers();
      setLoading(false);
      
      // Setup WebSockets
      const wsUrl = api.getWsUrl(projectId);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        console.log("WebSocket connected to workspace");
        
        // If run=true was specified in query, trigger run
        const shouldRun = searchParams.get("run") === "true";
        if (shouldRun && project && project.status !== "running") {
          router.replace(`/projects/${projectId}`);
          ws.send(JSON.stringify({ action: "start", topic: project.title }));
        }
      };

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        
        if (payload.type === "log") {
          setConsoleLogs((prev) => [...prev, payload.data]);
        } else if (payload.type === "reasoning") {
          const reasoningStep = payload.data;
          const stageName = reasoningStep.stage || "literature";
          setLiveReasoning((prev) => {
            const list = prev[stageName] || [];
            return {
              ...prev,
              [stageName]: [...list, reasoningStep]
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

  // Scroll console to bottom on logs update
  useEffect(() => {
    if (consoleBottomRef.current) {
      consoleBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [consoleLogs]);

  const handleStartResearch = () => {
    const sendStart = () => {
      setConsoleLogs([]);
      wsRef.current!.send(JSON.stringify({ action: "start", topic: project?.title }));
    };

    if (wsRef.current && wsConnected) {
      sendStart();
    } else if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      // Socket is still opening — wait for it then send
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

  const getStageIcon = (name: string) => {
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

  // Hierarchical SVG Knowledge Graph coordinates helper
  const renderInteractiveGraph = () => {
    if (!graphData.nodes || graphData.nodes.length === 0) {
      return (
        <div className="h-full flex items-center justify-center text-slate-500 text-sm">
          Execute research pipeline to construct Knowledge Graph.
        </div>
      );
    }

    const width = 800;
    const height = 400;
    const order = ["paper", "gap", "hypothesis", "debate", "dataset", "experiment", "code", "paper_draft", "peer_review"];
    
    const columns: Record<string, any[]> = {};
    order.forEach(o => { columns[o] = []; });
    
    graphData.nodes.forEach((node: any) => {
      const colType = columns[node.type] ? node.type : "paper";
      columns[colType].push(node);
    });

    const activeCols = order.filter(o => columns[o].length > 0);
    const colSpacing = width / (activeCols.length + 1);
    
    const nodeCoords: Record<string, { x: number; y: number }> = {};
    activeCols.forEach((colType, colIdx) => {
      const colNodes = columns[colType];
      const x = (colIdx + 1) * colSpacing;
      const rowSpacing = height / (colNodes.length + 1);
      
      colNodes.forEach((node, rowIdx) => {
        const y = (rowIdx + 1) * rowSpacing;
        nodeCoords[node.id] = { x, y };
      });
    });

    return (
      <div className="relative w-full h-full border border-card-border/60 bg-background/40 rounded-xl overflow-hidden flex flex-col md:flex-row">
        <div className="flex-1 min-h-[300px] relative">
          <svg className="w-full h-full min-h-[350px] bg-slate-950/20" viewBox={`0 0 ${width} ${height}`}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
              </marker>
            </defs>

            {graphData.edges.map((edge: any, idx: number) => {
              const start = nodeCoords[edge.source];
              const end = nodeCoords[edge.target];
              if (!start || !end) return null;
              
              return (
                <g key={idx}>
                  <line 
                    x1={start.x} y1={start.y} 
                    x2={end.x} y2={end.y} 
                    stroke="#222d44" strokeWidth="2" 
                    markerEnd="url(#arrow)" 
                    strokeDasharray="4 4"
                  />
                  <text 
                    x={(start.x + end.x) / 2} 
                    y={(start.y + end.y) / 2 - 5}
                    fill="#64748b" fontSize="8" textAnchor="middle" className="font-mono"
                  >
                    {edge.type}
                  </text>
                </g>
              );
            })}

            {graphData.nodes.map((node: any) => {
              const coords = nodeCoords[node.id];
              if (!coords) return null;

              const isSelected = selectedGraphNode?.id === node.id;
              let color = "#06b6d4";
              if (node.type === "gap") color = "#8b5cf6";
              if (node.type === "hypothesis") color = "#10b981";
              if (node.type === "dataset") color = "#f59e0b";
              if (node.type === "code") color = "#14b8a6";
              if (node.type === "paper_draft") color = "#ec4899";
              if (node.type === "peer_review") color = "#ef4444";

              return (
                <g 
                  key={node.id} 
                  transform={`translate(${coords.x}, ${coords.y})`}
                  className="cursor-pointer group"
                  onClick={() => setSelectedGraphNode(node)}
                >
                  <circle 
                    r={isSelected ? "14" : "10"} 
                    fill={color} 
                    opacity="0.15" 
                    stroke={color} 
                    strokeWidth={isSelected ? "3" : "1.5"}
                    className="transition-all duration-200 group-hover:scale-125"
                  />
                  <circle r="4" fill={color} />
                  
                  <text 
                    y="25" 
                    fill="#94a3b8" 
                    fontSize="9" 
                    fontWeight="bold" 
                    textAnchor="middle" 
                    className="select-none pointer-events-none drop-shadow-md"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        <div className="w-full md:w-64 border-t md:border-t-0 md:border-l border-card-border/80 bg-card/40 p-4 flex flex-col justify-between overflow-y-auto">
          {selectedGraphNode ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{
                    backgroundColor: 
                      selectedGraphNode.type === "gap" ? "#8b5cf6" :
                      selectedGraphNode.type === "hypothesis" ? "#10b981" :
                      selectedGraphNode.type === "dataset" ? "#f59e0b" :
                      selectedGraphNode.type === "code" ? "#14b8a6" :
                      selectedGraphNode.type === "paper_draft" ? "#ec4899" :
                      selectedGraphNode.type === "peer_review" ? "#ef4444" : "#06b6d4"
                  }} 
                />
                <span className="text-xs font-bold uppercase tracking-widest text-slate-400 font-mono">
                  {selectedGraphNode.type.replace("_", " ")}
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-200 mb-4">{selectedGraphNode.label}</h4>
              
              <div className="space-y-3 text-xs text-slate-400">
                {Object.entries(selectedGraphNode.properties || {}).map(([key, val]: any) => (
                  <div key={key} className="border-b border-card-border/30 pb-2">
                    <span className="font-semibold block capitalize text-slate-500 font-mono text-[10px]">{key.replace("_", " ")}</span>
                    <span className="text-slate-300 break-words block mt-0.5">{typeof val === "object" ? JSON.stringify(val) : val}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center text-xs text-slate-500 my-auto">
              Click a node on the canvas to inspect research lineages.
            </div>
          )}
        </div>
      </div>
    );
  };

  const pausedStage = stages.find(s => s.status === "paused");

  return (
    <div className="min-h-screen bg-background flex flex-col relative text-slate-200">
      
      {/* Workspace Header */}
      <header className="border-b border-card-border bg-card/60 backdrop-blur-md sticky top-0 z-20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push("/dashboard")}
            className="p-2 rounded-lg border border-card-border hover:bg-card text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-base font-bold text-slate-200 line-clamp-1">{project?.title}</h1>
            <p className="text-xs text-slate-500">Autonomous Scientist Sandbox Workspace</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
            pausedStage ? "bg-warning/10 text-warning border-warning/20 animate-pulse" :
            isRunning ? "bg-primary/10 text-primary border-primary/20 animate-pulse" :
            project?.status === "completed" ? "bg-success/10 text-success border-success/20" : "bg-slate-800 border-slate-700 text-slate-400"
          }`}>
            {pausedStage ? "Awaiting Verification" : isRunning ? "Executing Agents" : project?.status === "completed" ? "Research Completed" : "Pipeline Idle"}
          </span>

          {project?.status !== "running" && !pausedStage && (
            <button
              onClick={handleStartResearch}
              disabled={!wsConnected && wsRef.current?.readyState !== WebSocket.CONNECTING}
              title={!wsConnected ? "Connecting to server..." : "Launch research pipeline"}
              className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary/95 text-background font-semibold rounded-lg text-xs shadow-lg shadow-primary/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{wsConnected ? "Launch Pipeline" : "Connecting..."}</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden max-h-[calc(100vh-73px)]">
        
        {/* Left Sidebar: 13 Stages Timeline */}
        <aside className="w-full lg:w-64 border-b lg:border-b-0 lg:border-r border-card-border bg-card/40 flex flex-row lg:flex-col overflow-x-auto lg:overflow-x-visible lg:overflow-y-auto p-4 gap-2 flex-shrink-0">
          {stages.map((stage) => {
            const isActive = activeStage === stage.stage_name;
            const isCompleted = stage.status === "completed";
            const isWorking = stage.status === "active";
            const isFailed = stage.status === "failed";
            const isPaused = stage.status === "paused";
            
            return (
              <div
                key={stage.id}
                onClick={() => setActiveStage(stage.stage_name)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 flex-shrink-0 lg:flex-shrink ${
                  isActive ? "bg-primary/15 text-primary border border-primary/20" : "border border-transparent hover:bg-slate-800/40 text-slate-400"
                }`}
              >
                <div className={`p-1.5 rounded-lg ${
                  isCompleted ? "bg-success/10 text-success" : 
                  isWorking ? "bg-primary/10 text-primary animate-pulse" :
                  isPaused ? "bg-warning/10 text-warning animate-pulse" :
                  isFailed ? "bg-error/10 text-error" : "bg-slate-800 text-slate-500"
                }`}>
                  {getStageIcon(stage.stage_name)}
                </div>

                <div className="hidden lg:block text-left">
                  <p className="text-xs font-semibold capitalize text-slate-300">
                    {stage.stage_name.replace("_", " ")}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5 capitalize">
                    {stage.status}
                  </p>
                </div>
              </div>
            );
          })}
        </aside>

        {/* Center: Stage Outputs Board */}
        <section className="flex-1 p-6 overflow-y-auto flex flex-col gap-6">
          
          {/* HITL approval card */}
          {pausedStage && (
            <div className="p-4 rounded-xl border border-warning/40 bg-warning/5 mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex-1">
                <span className="text-[10px] px-2 py-0.5 rounded bg-warning/20 text-warning border border-warning/30 font-bold uppercase tracking-wider">Awaiting Supervisor Verification</span>
                <h4 className="text-sm font-bold text-slate-200 mt-2">
                  Pipeline paused on: '{pausedStage.stage_name.replace("_", " ")}' stage.
                </h4>
                <p className="text-xs text-slate-400 mt-1">Review the stage outputs below and click Approve to resume execution, or provide override feedback.</p>
              </div>
              <div className="flex flex-col gap-2 w-full md:w-64 flex-shrink-0">
                <input
                  type="text"
                  value={supervisorFeedback}
                  onChange={(e) => setSupervisorFeedback(e.target.value)}
                  placeholder="Provide direction/feedback (optional)..."
                  className="w-full px-3 py-1.5 rounded bg-slate-900 border border-card-border text-xs focus:outline-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApproveStage(pausedStage.stage_name, true)}
                    className="flex-1 py-1.5 rounded bg-success hover:bg-success/90 text-background font-bold text-xs"
                  >
                    Approve & Resume
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between border-b border-card-border/40 pb-3">
            <h2 className="text-base font-bold text-slate-200 capitalize flex items-center gap-2">
              {getStageIcon(activeStage)}
              <span>{activeStage.replace("_", " ")} Output</span>
            </h2>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Stage Workspace</span>
          </div>

          {/* Render Stage Specific Output */}
          <div className="flex-1">
            {/* 1. LITERATURE REVIEW VIEW */}
            {activeStage === "literature" && (
              <div className="space-y-6">
                {/* RAG PDF Upload Panel */}
                <div className="p-4 rounded-xl border border-card-border bg-card/25">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-2 flex items-center gap-2">
                    <Upload className="w-3.5 h-3.5" />
                    RAG Document Manager
                    {uploadedPapers.length > 0 && (
                      <span className="ml-auto px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-[10px] font-mono">
                        {uploadedPapers.length} indexed
                      </span>
                    )}
                  </h3>
                  <p className="text-[11px] text-slate-400 mb-3">Uploaded papers are chunked and indexed into the vector RAG database. They guide literature analysis when arXiv returns no results.</p>
                  <div className="flex items-center gap-3 mb-4">
                    <input
                      type="file"
                      accept=".pdf"
                      id="ref-pdf-upload"
                      className="hidden"
                      onChange={handleUploadPdf}
                      disabled={isUploading}
                    />
                    <label
                      htmlFor="ref-pdf-upload"
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary hover:bg-primary/95 text-background text-xs font-bold cursor-pointer transition-all"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      {isUploading ? "Uploading PDF..." : "Upload Reference PDF"}
                    </label>
                  </div>

                  {/* Uploaded Papers List */}
                  {uploadedPapers.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Indexed Documents</p>
                      {uploadedPapers.map((p) => (
                        <div key={p.id} className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-slate-900/60 border border-card-border/40 hover:border-primary/20 transition-all group">
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-slate-200 truncate">{p.filename}</p>
                              <p className="text-[10px] text-slate-500 font-mono">
                                {(p.char_count / 1000).toFixed(1)}k chars · {p.created_at ? new Date(p.created_at).toLocaleDateString() : ""}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeletePaper(p.id, p.filename)}
                            disabled={deletingPaperId === p.id}
                            title="Remove from RAG index"
                            className="flex-shrink-0 p-1.5 rounded-md text-slate-500 hover:text-error hover:bg-error/10 border border-transparent hover:border-error/20 transition-all disabled:opacity-40"
                          >
                            {deletingPaperId === p.id
                              ? <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              : <Trash2 className="w-3.5 h-3.5" />
                            }
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {litPapers.length === 0 ? (
                  <div className="text-center p-12 text-slate-500 text-sm">No literature parsed yet. Run pipeline.</div>
                ) : (
                  <>
                    <div className="glass-card rounded-xl p-5 border border-card-border">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">Synthesis Report</h3>
                      <div className="text-sm text-slate-300 leading-relaxed">
                        {stages.find(s => s.stage_name === "literature")?.output_data?.summary || "Compiling summary..."}
                      </div>
                    </div>

                    <div className="glass-card rounded-xl p-5 border border-card-border">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3">Methods Comparison</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left border-collapse">
                          <thead>
                            <tr className="border-b border-card-border/60 text-slate-400">
                              <th className="py-2">Method</th>
                              <th className="py-2">Accuracy</th>
                              <th className="py-2">Limitations</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(stages.find(s => s.stage_name === "literature")?.output_data?.comparison_table || []).map((row: any, i: number) => (
                              <tr key={i} className="border-b border-card-border/20 text-slate-300">
                                <td className="py-2.5 font-semibold text-slate-200">{row.Method}</td>
                                <td className="py-2.5 text-primary">{row.Accuracy}</td>
                                <td className="py-2.5">{row.Limitations}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Extracted Paper Metadata</h3>
                      {litPapers.map((paper) => (
                        <div key={paper.id} className="p-4 rounded-xl bg-card/30 border border-card-border/50 hover:border-primary/20 transition-all">
                          <h4 className="text-xs font-bold text-slate-200">{paper.title}</h4>
                          <p className="text-[10px] text-slate-400 mt-1">{paper.authors} | Relevance: {paper.relevance_score}/10.0</p>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3 text-[11px] border-t border-card-border/30 pt-3 text-slate-300">
                            <div>
                              <span className="font-bold block text-[9px] uppercase text-slate-500">Methodology</span>
                              {paper.methodology}
                            </div>
                            <div>
                              <span className="font-bold block text-[9px] uppercase text-slate-500">Findings</span>
                              {paper.findings}
                            </div>
                            <div>
                              <span className="font-bold block text-[9px] uppercase text-slate-500">Limitations</span>
                              {paper.limitations}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 2. RESEARCH GAP VIEW */}
            {activeStage === "gap" && (
              <div className="space-y-4">
                {gaps.length === 0 ? (
                  <div className="text-center p-12 text-slate-500 text-sm">No research gaps detected yet.</div>
                ) : (
                  gaps.map((gap) => (
                    <div key={gap.id} className="glass-card rounded-xl p-5 border border-card-border flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div className="flex-1">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-primary mb-2 font-mono">Unexplored Gap</h3>
                        <p className="text-sm text-slate-300 leading-relaxed">{gap.description}</p>
                      </div>
                      <div className="flex gap-4 border-l border-card-border/60 pl-4 flex-shrink-0">
                        <div className="text-center">
                          <span className="text-[9px] block uppercase text-slate-500 font-mono">Novelty</span>
                          <span className="text-base font-bold text-slate-200">{gap.novelty_score}%</span>
                        </div>
                        <div className="text-center">
                          <span className="text-[9px] block uppercase text-slate-500 font-mono">Opportunity</span>
                          <span className="text-base font-bold text-primary">{gap.opportunity_score}%</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 3. HYPOTHESIS VIEW */}
            {activeStage === "hypothesis" && (
              <div className="space-y-4">
                {hypotheses.length === 0 ? (
                  <div className="text-center p-12 text-slate-500 text-sm">No hypotheses generated yet.</div>
                ) : (
                  hypotheses.map((hypo) => (
                    <div key={hypo.id} className="glass-card rounded-xl p-5 border border-card-border">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-primary font-mono">Scientific Hypothesis</h3>
                        <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 text-[10px] font-mono">
                          Confidence: {Math.round(hypo.confidence_level * 100)}%
                        </span>
                      </div>
                      <p className="text-sm font-bold text-slate-200 leading-relaxed mb-3">
                        {hypo.statement}
                      </p>
                      <div className="text-xs text-slate-400 bg-background/40 p-3.5 rounded-lg border border-card-border/40">
                        <span className="font-bold block text-[9px] uppercase text-slate-500 mb-1">Scientific Reasoning</span>
                        {hypo.reasoning}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 4. DEBATE VIEW */}
            {activeStage === "debate" && (
              <div className="space-y-6">
                {!debate ? (
                  <div className="text-center p-12 text-slate-500 text-sm">Debate panels are offline. Run pipeline to initiate debate.</div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="p-4 rounded-xl bg-card/20 border border-card-border">
                        <h4 className="text-xs font-bold text-slate-400 uppercase font-mono mb-2">Proposal A (CNN)</h4>
                        <p className="text-xs text-slate-300 leading-relaxed">{debate.proposal_a}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-card/20 border border-card-border">
                        <h4 className="text-xs font-bold text-slate-400 uppercase font-mono mb-2">Proposal B (ViT)</h4>
                        <p className="text-xs text-slate-300 leading-relaxed">{debate.proposal_b}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-card/20 border border-card-border">
                        <h4 className="text-xs font-bold text-slate-400 uppercase font-mono mb-2">Proposal C (RL Hybrid)</h4>
                        <p className="text-xs text-slate-300 leading-relaxed">{debate.proposal_c || "RL-guided Vision Transformer Hybrid"}</p>
                      </div>
                    </div>

                    <div className="glass-card rounded-xl border border-card-border p-5 space-y-4">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3">Debate Arena Log</h3>
                      <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
                        {(debate.debate_rounds || []).map((round: any, i: number) => (
                          <div key={i} className="flex gap-3 text-xs bg-slate-900/30 p-3 rounded-lg border border-card-border/30">
                            <span className="font-bold text-primary flex-shrink-0 w-24 font-mono">{round.agent}:</span>
                            <span className="text-slate-300 leading-relaxed">{round.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-5 rounded-xl border border-success/30 bg-success/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-success/20 text-success border border-success/30 font-bold uppercase tracking-wider">Winning Proposal Selected</span>
                        <h4 className="text-sm font-bold text-slate-200 mt-2">{debate.winner_proposal}</h4>
                        <p className="text-xs text-slate-400 mt-1">{debate.rationale}</p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 5. DATASET VIEW */}
            {activeStage === "dataset" && (
              <div className="space-y-4">
                {datasets.length === 0 ? (
                  <div className="text-center p-12 text-slate-500 text-sm">No datasets cataloged.</div>
                ) : (
                  datasets.map((dataset) => (
                    <div key={dataset.id} className="glass-card rounded-xl p-5 border border-card-border">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-xs font-bold text-slate-200">{dataset.name}</h3>
                        <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px] font-mono">
                          Quality Score: {dataset.quality_score}%
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed mb-4">{dataset.description}</p>
                      
                      {dataset.metadata_fields && (
                        <div className="grid grid-cols-3 gap-4 border-t border-card-border/30 pt-3 text-[10px] font-mono text-slate-400">
                          {Object.entries(dataset.metadata_fields).map(([k, v]: any) => (
                            <div key={k}>
                              <span className="text-slate-500 block uppercase font-bold text-[8px]">{k}</span>
                              <span className="text-slate-300">{v}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 6. EXPERIMENT PLANNING VIEW */}
            {activeStage === "planning" && (
              <div className="space-y-6">
                {!plan ? (
                  <div className="text-center p-12 text-slate-500 text-sm">Experimental roadmaps are empty.</div>
                ) : (
                  <>
                    <div className="glass-card rounded-xl p-5 border border-card-border">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-4">Milestone Roadmap</h3>
                      <div className="space-y-4 relative pl-4 border-l border-card-border">
                        {(plan.roadmap || []).map((step: any, i: number) => (
                          <div key={i} className="relative">
                            <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-primary" />
                            <h4 className="text-xs font-bold text-slate-200">{step.step}</h4>
                            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{step.details}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-card/20 border border-card-border">
                        <h4 className="text-xs font-bold text-slate-400 uppercase font-mono mb-3">Target Metrics</h4>
                        <div className="flex flex-wrap gap-2">
                          {(plan.metrics || []).map((metric: string, i: number) => (
                            <span key={i} className="px-2 py-1 rounded bg-slate-800 border border-card-border/80 text-[10px] text-slate-300">
                              {metric}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-card/20 border border-card-border">
                        <h4 className="text-xs font-bold text-slate-400 uppercase font-mono mb-3">Resource Allocation</h4>
                        {plan.hardware_requirements && (
                          <div className="space-y-2 text-xs text-slate-400 font-mono">
                            <div className="flex justify-between"><span className="text-slate-500">GPU:</span><span className="text-slate-300">{plan.hardware_requirements.GPU}</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">RAM:</span><span className="text-slate-300">{plan.hardware_requirements.RAM}</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">Run-time:</span><span className="text-slate-300">{plan.hardware_requirements.expected_runtime}</span></div>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 7. CODE VIEWER VIEW (INTERACTIVE EDITOR) */}
            {activeStage === "coding" && (
              <div className="flex flex-col gap-4">

                {/* Sandbox Path Info Bar */}
                <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-card-border/60 bg-slate-900/60 font-mono text-[11px]">
                  <div className="flex items-center gap-2 text-slate-400 flex-shrink-0">
                    <svg className="w-3.5 h-3.5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7a2 2 0 012-2h3.586a1 1 0 01.707.293L11 7h10a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Sandbox Path</span>
                  </div>
                  <span className="flex-1 text-emerald-400/90 truncate select-all">
                    D:\Minor_Project\Research Agent\backend\sandbox_{projectId}\
                  </span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(`D:\\Minor_Project\\Research Agent\\backend\\sandbox_${projectId}\\`);
                      const btn = document.getElementById("copy-path-btn");
                      if (btn) { btn.textContent = "Copied!"; setTimeout(() => { btn.textContent = "Copy"; }, 1500); }
                    }}
                    id="copy-path-btn"
                    className="flex-shrink-0 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-card-border/40 text-slate-300 text-[10px] font-bold transition-all"
                  >
                    Copy
                  </button>
                </div>

                <div className="flex flex-col md:flex-row gap-4 h-[350px]">
                  {codeFiles.length === 0 ? (
                    <div className="text-center p-12 text-slate-500 text-sm my-auto w-full">No code structures compiled.</div>
                  ) : (
                    <>
                      {/* Sidebar panel */}
                      <div className="w-full md:w-56 bg-card/30 border border-card-border/60 rounded-xl p-3 flex flex-col gap-3 flex-shrink-0 font-mono">
                        <div className="flex bg-slate-900/60 p-0.5 rounded border border-card-border/40 text-[10px] font-sans">
                          <button
                            onClick={() => { setActiveCodeTab("db"); setViewingSandboxFile(false); }}
                            className={`flex-1 py-1 rounded text-center font-semibold transition-all ${
                              activeCodeTab === "db" ? "bg-primary text-background" : "text-slate-400 hover:text-slate-200"
                            }`}
                          >
                            DB Source
                          </button>
                          <button
                            onClick={() => { setActiveCodeTab("sandbox"); setViewingSandboxFile(true); }}
                            className={`flex-1 py-1 rounded text-center font-semibold transition-all ${
                              activeCodeTab === "sandbox" ? "bg-primary text-background" : "text-slate-400 hover:text-slate-200"
                            }`}
                          >
                            Sandbox Files
                          </button>
                        </div>

                        <div className="flex-1 flex flex-col gap-1 overflow-y-auto max-h-[300px]">
                          {activeCodeTab === "db" ? (
                            codeFiles.map((file) => (
                              <button
                                key={file.id}
                                onClick={() => { handleSelectCodeFile(file.id); setViewingSandboxFile(false); }}
                                className={`w-full text-left px-3 py-1.5 rounded-lg text-[10px] font-semibold break-all border ${
                                  selectedCodeFileId === file.id && !viewingSandboxFile ? "bg-primary/10 text-primary border border-primary/20" : "text-slate-400 hover:bg-slate-800/40 border-transparent"
                                }`}
                              >
                                {file.filepath}
                              </button>
                            ))
                          ) : (
                            sandboxFiles.length === 0 ? (
                              <div className="text-[10px] text-slate-500 text-center py-4">Sandbox is empty.</div>
                            ) : (
                              sandboxFiles.map((file) => (
                                <button
                                  key={file.filepath}
                                  onClick={() => handleSelectSandboxFile(file.filepath)}
                                  className={`w-full text-left px-3 py-1.5 rounded-lg text-[10px] font-semibold break-all border ${
                                    selectedSandboxFile === file.filepath && viewingSandboxFile ? "bg-primary/10 text-primary border border-primary/20" : "text-slate-400 hover:bg-slate-800/40 border-transparent"
                                  }`}
                                >
                                  {file.filepath}
                                </button>
                              ))
                            )
                          )}
                        </div>
                      </div>

                      {/* Code Editor */}
                      <div className="flex-1 flex flex-col border border-card-border/60 rounded-xl overflow-hidden bg-slate-950/40">
                        <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                          <span>Interactive Sandbox Code Editor</span>
                          <div className="flex items-center gap-3">
                            <button
                              onClick={handleSaveCode}
                              className="px-2.5 py-1 rounded bg-success hover:bg-success/95 text-background font-bold text-[10px]"
                            >
                              Save Changes
                            </button>
                            <span>Python</span>
                          </div>
                        </div>
                        <textarea
                          value={codeContent}
                          onChange={(e) => setCodeContent(e.target.value)}
                          className="flex-1 p-4 font-mono text-[11px] text-emerald-400/90 bg-transparent resize-none focus:outline-none leading-normal selection:bg-slate-800 animate-fade-in"
                        />
                      </div>
                    </>
                  )}
                </div>

                {/* Interactive Terminal Drawer */}
                <div className="border border-card-border/60 rounded-xl overflow-hidden bg-slate-950/50 flex flex-col h-[180px]">
                  <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-primary" />
                      <span>Sandbox Shell</span>
                      <span className="text-slate-600 mx-1">·</span>
                      <span className="text-emerald-400/70 text-[9px] truncate max-w-[300px]">cwd: backend\sandbox_{projectId}</span>
                    </span>
                    <button 
                      onClick={() => setTerminalHistory([])}
                      className="text-[9px] hover:text-slate-200 transition-colors"
                    >
                      Clear Console
                    </button>
                  </div>
                  
                  <div className="flex-1 p-3 overflow-y-auto font-mono text-[10px] leading-relaxed space-y-1">
                    {terminalHistory.length === 0 ? (
                      <div className="text-slate-600">Terminal ready. Run non-destructive sandbox diagnostics...</div>
                    ) : (
                      terminalHistory.map((item, idx) => (
                        <div key={idx} className={item.type === "command" ? "text-primary" : item.type === "error" ? "text-error" : "text-slate-300 whitespace-pre-wrap font-bold"}>
                          {item.text}
                        </div>
                      ))
                    )}
                    {terminalLoading && <div className="text-slate-500 animate-pulse">Running command...</div>}
                  </div>

                  <form onSubmit={handleRunCommand} className="border-t border-card-border/40 flex items-center bg-slate-900/30">
                    <span className="text-primary font-mono text-xs px-3 select-none">$</span>
                    <input
                      type="text"
                      value={terminalInput}
                      onChange={(e) => setTerminalInput(e.target.value)}
                      placeholder="Type diagnostic command (e.g. dir, python train.py --help, cat requirements.txt)..."
                      className="flex-1 bg-transparent py-2 text-slate-200 font-mono text-[10px] focus:outline-none"
                    />
                    <button
                      type="submit"
                      disabled={terminalLoading}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 font-bold font-mono text-[9px] text-slate-300 disabled:opacity-50"
                    >
                      Execute
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* 8. EXPERIMENT EXECUTION & PLOTS VIEW */}
            {activeStage === "execution" && (
              <div className="space-y-6">
                {runs.length === 0 ? (
                  <div className="text-center p-12 text-slate-500 text-sm">No active experiment runs recorded.</div>
                ) : (
                  runs.map((run) => {
                    const history = run.metrics_history || [];
                    const maxEpoch = history.length;
                    
                    return (
                      <div key={run.id} className="space-y-6">
                        <div className="glass-card rounded-xl p-5 border border-card-border">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3">Live Training Accuracy Convergence</h3>
                          {history.length > 1 ? (
                            <div className="relative w-full h-[180px] bg-slate-950/20 rounded border border-card-border/40 p-2">
                              <ResearchChart
                                title="Training Accuracy Convergence"
                                data={
                                  {
                                    labels: history.map((_: any, idx: number) => `Epoch ${idx + 1}`),
                                    datasets: [
                                      {
                                        label: "Train Accuracy",
                                        data: history.map((h: any) => h.train_acc),
                                        borderColor: "#10b981",
                                        backgroundColor: "rgba(16, 185, 129, 0.1)",
                                        tension: 0.4,
                                      },
                                      {
                                        label: "Validation Accuracy",
                                        data: history.map((h: any) => h.val_acc),
                                        borderColor: "#06b6d4",
                                        backgroundColor: "rgba(6, 182, 212, 0.1)",
                                        tension: 0.4,
                                      },
                                    ],
                                  }
                                }
                              />
                            </div>
                          ) : (
                            <div className="h-[180px] border border-card-border/40 bg-slate-950/20 flex items-center justify-center text-xs text-slate-500 font-mono">
                              Building metrics curve history...
                            </div>
                          )}
                        </div>

                        <div className="glass-card rounded-xl border border-card-border p-5 bg-slate-950/60 font-mono text-[10px] text-slate-400 h-64 overflow-y-auto leading-normal">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3 font-sans">Stdout Run Logs</h3>
                          <pre className="whitespace-pre-wrap">{run.logs}</pre>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* 9. EVALUATION STATS VIEW */}
            {activeStage === "evaluation" && (
              <div className="space-y-6">
                {stages.find(s => s.stage_name === "evaluation")?.output_data === undefined ? (
                  <div className="text-center p-12 text-slate-500 text-sm">No evaluation report compiled.</div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      {Object.entries(stages.find(s => s.stage_name === "evaluation")?.output_data?.performance_report || {}).map(([name, val]: any) => (
                        <div key={name} className="p-4 rounded-xl bg-card/30 border border-card-border text-center">
                          <span className="text-[10px] block uppercase text-slate-500 font-mono">{name}</span>
                          <span className="text-base font-bold text-slate-200 mt-1 block">{val}</span>
                        </div>
                      ))}
                    </div>

                    <div className="glass-card rounded-xl p-5 border border-card-border">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-3">Model Baseline Comparisons</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left border-collapse">
                          <thead>
                            <tr className="border-b border-card-border/60 text-slate-400">
                              <th className="py-2">Model</th>
                              <th className="py-2">Accuracy</th>
                              <th className="py-2">F1-Score</th>
                              <th className="py-2">FLOPs</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(stages.find(s => s.stage_name === "evaluation")?.output_data?.baseline_comparison || []).map((row: any, i: number) => (
                              <tr key={i} className={`border-b border-card-border/20 text-slate-300 ${
                                row.Model.includes("Ours") ? "bg-primary/5 text-primary" : ""
                              }`}>
                                <td className="py-2.5 font-semibold text-slate-200">{row.Model}</td>
                                <td className="py-2.5">{row.Accuracy}</td>
                                <td className="py-2.5">{row["F1-Score"]}</td>
                                <td className="py-2.5 font-mono">{row.FLOPs}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="glass-card rounded-xl p-5 border border-card-border">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">Improvement Analysis</h3>
                      <div className="text-xs text-slate-300 leading-relaxed">
                        {stages.find(s => s.stage_name === "evaluation")?.output_data?.improvement_analysis}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 10. SCIENTIFIC WRITER VIEW */}
            {activeStage === "writing" && (
              <div className="space-y-6">
                {!paper ? (
                  <div className="text-center p-12 text-slate-500 text-sm">Manuscript draft is empty. Run pipeline.</div>
                ) : (
                  <div className="flex flex-col gap-4">
                    {/* Dual Mode View Selector */}
                    <div className="flex items-center gap-2 bg-slate-900/60 p-1 rounded-lg border border-card-border/40 w-fit">
                      <button
                        onClick={() => setPaperMode("preview")}
                        className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                          paperMode === "preview"
                            ? "bg-primary text-background"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Manuscript Preview
                      </button>
                      <button
                        onClick={() => setPaperMode("latex")}
                        className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                          paperMode === "latex"
                            ? "bg-primary text-background"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        LaTeX Source
                      </button>
                    </div>

                    <div className="flex flex-col lg:flex-row gap-6">
                      {paperMode === "preview" ? (
                        <div className="flex-1 glass-card rounded-xl border border-card-border p-6 overflow-y-auto max-h-[500px] text-xs text-slate-300 font-serif leading-relaxed">
                          <div className="text-center mb-8 font-sans">
                            <span className="text-[9px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 uppercase tracking-widest font-bold font-mono">
                              Publication Draft
                            </span>
                            <h2 className="text-base font-extrabold text-slate-100 tracking-tight mt-3">{paper.title}</h2>
                            <p className="text-[10px] text-slate-400 mt-1">Authors: ARSA Multi-Agent Intelligence Core</p>
                          </div>

                          <div className="border-t border-card-border/60 pt-4 mb-6">
                            <h4 className="font-sans font-bold text-slate-200 mb-1 uppercase tracking-wide text-[10px]">Abstract</h4>
                            <p className="text-slate-400 italic text-[11px] leading-relaxed">{paper.abstract}</p>
                          </div>

                          {Object.entries(paper.sections || {}).map(([secTitle, secText]: any) => (
                            <div key={secTitle} className="mb-6">
                              <h4 className="font-sans font-bold text-slate-200 mb-2">{secTitle}</h4>
                              <p className="whitespace-pre-line leading-relaxed text-slate-300">{secText}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex-1 flex flex-col md:flex-row gap-4 min-h-[500px]">
                          {/* LaTeX Editor */}
                          <div className="flex-1 flex flex-col border border-card-border/60 rounded-xl overflow-hidden bg-slate-950/40">
                            <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                              <span>Interactive LaTeX Editor</span>
                              <div className="flex items-center gap-3">
                                <button
                                  onClick={handleSaveLatex}
                                  disabled={loadingLatex}
                                  className="px-2.5 py-1 rounded bg-success hover:bg-success/90 text-background font-bold text-[10px] disabled:opacity-50"
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
                                className="flex-1 p-4 font-mono text-[11px] text-emerald-400/90 bg-transparent resize-none focus:outline-none leading-normal selection:bg-slate-800 min-h-[450px]"
                              />
                            )}
                          </div>

                          {/* Live Compiled PDF Preview Panel */}
                          <div className="flex-1 flex flex-col border border-card-border/60 rounded-xl overflow-hidden bg-slate-900/10">
                            <div className="bg-card/40 border-b border-card-border/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                              <span>Live Compiled PDF Preview</span>
                              <span>PDF Frame</span>
                            </div>
                            <iframe
                              src={`http://127.0.0.1:8000/static/papers/arsa_paper_${projectId}.pdf`}
                              className="flex-1 w-full bg-slate-950/20 border-none min-h-[450px]"
                              title="LaTeX compiled PDF preview"
                            />
                          </div>
                        </div>
                      )}

                      <div className="w-full lg:w-60 flex flex-col gap-4 flex-shrink-0">
                        <div className="p-4 rounded-xl border border-card-border bg-card/40">
                          <span className="text-[9px] block uppercase text-slate-500 font-mono">Publication Readiness</span>
                          <div className="flex items-baseline gap-1 mt-1">
                            <span className="text-2xl font-extrabold text-slate-200">{paper.publication_readiness_score}%</span>
                            <span className="text-[10px] text-success">Passed threshold</span>
                          </div>
                        </div>

                        <button 
                          onClick={() => alert("LaTeX paper compiled. PDF Download initiated!")}
                          className="w-full py-3 rounded-lg bg-primary hover:bg-primary/95 text-background font-bold text-xs shadow-lg shadow-primary/20 transition-all text-center"
                        >
                          Compile & Export (PDF)
                        </button>

                        <button 
                          onClick={() => setShowHFModal(true)}
                          className="w-full py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-500/20 transition-all text-center"
                        >
                          Publish to Hugging Face Hub
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 11. PEER REVIEW VIEW */}
            {activeStage === "review" && (
              <div className="space-y-6">
                {!review ? (
                  <div className="text-center p-12 text-slate-500 text-sm">Manuscript has not been reviewed yet.</div>
                ) : (
                  <>
                    <div className="flex items-center justify-between border border-card-border bg-card/20 rounded-xl p-5">
                      <div>
                        <span className="text-[9px] block uppercase text-slate-500 font-mono">Blind Review Summary</span>
                        <h4 className="text-sm font-bold text-slate-200 mt-1">Publication Readiness Score</h4>
                      </div>
                      <div className="text-right">
                        <span className="text-3xl font-extrabold text-slate-200">{review.score}</span>
                        <span className="text-[10px] text-slate-500 block">out of 10.0</span>
                      </div>
                    </div>

                    {review.comments && review.comments.reviewer_1 ? (
                      <div className="space-y-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Review Board Critiques</h3>
                        <div className="flex flex-wrap gap-2 bg-slate-900/60 p-1 rounded-lg border border-card-border/40 w-fit">
                          {["reviewer_1", "reviewer_2", "reviewer_3"].map((tab) => {
                            const label = tab === "reviewer_1" ? "Reviewer 1 (Skeptical)" :
                                          tab === "reviewer_2" ? "Reviewer 2 (Methodological)" :
                                          "Reviewer 3 (Editor consensus)";
                            const active = selectedReviewerTab === tab;
                            return (
                              <button
                                key={tab}
                                onClick={() => setSelectedReviewerTab(tab)}
                                className={`px-3 py-1 rounded-md text-[10px] font-mono font-semibold transition-all ${
                                  active ? "bg-primary text-background" : "text-slate-400 hover:text-slate-200"
                                }`}
                              >
                                {label}
                              </button>
                            );
                          })}
                        </div>
                        
                        {(() => {
                          const activeReview = review.comments[selectedReviewerTab];
                          if (!activeReview) return <div className="text-xs text-slate-500">No review content loaded.</div>;
                          return (
                            <div className="p-4 rounded-xl bg-card/30 border border-card-border/60 text-xs">
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
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Review Comments</h3>
                        {Object.entries(review.comments || {}).map(([name, critique]: any) => (
                          <div key={name} className="p-4 rounded-xl bg-card/30 border border-card-border/50 text-xs">
                            <span className="font-bold text-slate-300 block mb-1 font-mono uppercase text-[9px]">{name}</span>
                            <p className="text-slate-400 leading-relaxed">{critique}</p>
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
                  </>
                )}
              </div>
            )}

            {/* 12. RESEARCH MEMORY VIEW */}
            {activeStage === "memory" && (
              <div className="space-y-4">
                {stages.find(s => s.stage_name === "memory")?.output_data === undefined ? (
                  <div className="text-center p-12 text-slate-500 text-sm">Memory consolidation is pending.</div>
                ) : (
                  <>
                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 text-xs text-slate-300 leading-relaxed mb-4">
                      Insights from this project have been cataloged in the system memory index. These will be retrieved automatically to guide and optimize future research designs.
                    </div>
                    
                    <div className="space-y-3">
                      <div className="p-4 rounded-xl border border-card-border bg-slate-900/20">
                        <span className="text-[9px] font-mono text-success uppercase block">Successful Method</span>
                        <h4 className="text-xs font-bold text-slate-200 mt-1">Domain-Adversarial Representation Alignment</h4>
                        <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                          Applying a gradient reversal layer against scanner domains aligned features, resulting in +2.4% validation generalization boost on Philips scanner MRIs.
                        </p>
                      </div>

                      <div className="p-4 rounded-xl border border-card-border bg-slate-900/20">
                        <span className="text-[9px] font-mono text-error uppercase block">Failed Method / Constraint</span>
                        <h4 className="text-xs font-bold text-slate-200 mt-1">Raw Vision Transformer Cross-Scanner Training</h4>
                        <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                          Training standard ViT architectures on multi-scanner datasets yielded model biases towards boundary intensity shapes, triggering -5.1% accuracy drop.
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 13. KNOWLEDGE GRAPH VIEW */}
            {activeStage === "graph" && (
              <div className="h-[400px]">
                {renderInteractiveGraph()}
              </div>
            )}
          </div>
        </section>

        {/* Right Panel: Live Console Logs & CoT Trace */}
        <section className="w-full lg:w-[360px] border-t lg:border-t-0 lg:border-l border-card-border bg-card/20 flex flex-col flex-shrink-0 max-h-[400px] lg:max-h-full">
          <div className="border-b border-card-border/60 px-4 py-3 flex items-center justify-between bg-card/40 flex-shrink-0">
            <div className="flex bg-slate-900/60 p-0.5 rounded border border-card-border/40 text-[10px] font-sans">
              <button
                onClick={() => setSidebarTab("console")}
                className={`px-3 py-1 rounded text-center font-semibold transition-all ${
                  sidebarTab === "console" ? "bg-primary text-background" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Logs
              </button>
              <button
                onClick={() => setSidebarTab("reasoning")}
                className={`px-3 py-1 rounded text-center font-semibold transition-all ${
                  sidebarTab === "reasoning" ? "bg-primary text-background" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                CoT Trace
              </button>
            </div>
            <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-success" : "bg-error animate-ping"}`} />
          </div>

          {sidebarTab === "console" ? (
            <div className="flex-1 p-4 overflow-y-auto font-mono text-[10px] text-slate-400 leading-relaxed bg-slate-950/40 space-y-2">
              {consoleLogs.length === 0 ? (
                <div className="text-slate-600 text-center py-12">Console stream is idle. Launch research pipeline to read logs.</div>
              ) : (
                consoleLogs.map((log, idx) => {
                  let color = "text-slate-400";
                  if (log.level === "ERROR") color = "text-error font-bold";
                  if (log.level === "WARNING") color = "text-warning";
                  if (log.message.startsWith("===")) color = "text-primary font-bold";

                  return (
                    <div key={idx} className={color}>
                      <span className="text-slate-600 select-none mr-1.5 font-mono">[{new Date(log.timestamp || Date.now()).toLocaleTimeString()}]</span>
                      {log.message}
                    </div>
                  );
                })
              )}
              <div ref={consoleBottomRef} />
            </div>
          ) : (
            <div className="flex-1 p-4 overflow-y-auto bg-slate-950/40 space-y-4">
              <div className="text-[11px] font-sans border-b border-card-border/30 pb-2 flex items-center justify-between text-slate-300 font-semibold">
                <span>Active Agent: {activeStage.replace("_", " ").toUpperCase()}</span>
                <span className="text-[9px] text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">Reasoning Chain</span>
              </div>
              
              {!liveReasoning[activeStage] || liveReasoning[activeStage].length === 0 ? (
                <div className="text-slate-600 text-center py-12 text-[10px] font-mono">No reasoning steps logged for this stage yet. Run pipeline.</div>
              ) : (
                <div className="space-y-4 relative pl-3 border-l border-card-border/40 ml-2 mt-2">
                  {liveReasoning[activeStage].map((step, idx) => (
                    <div key={idx} className="relative group">
                      <div className="absolute -left-[16px] top-1.5 w-1.5 h-1.5 rounded-full bg-primary ring-4 ring-primary/10 group-hover:scale-125 transition-transform" />
                      <div className="bg-slate-900/40 p-2.5 rounded-lg border border-card-border/40 text-[10px]">
                        <div className="flex items-center justify-between text-slate-500 mb-1 font-mono text-[8px]">
                          <span className="font-semibold text-primary/80 uppercase">Step {idx + 1}</span>
                          <span>{new Date(step.timestamp || Date.now()).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-300 leading-normal whitespace-pre-wrap font-sans">{step.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

      </div>

      {/* Hugging Face Publish Modal */}
      {showHFModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-card-border/85 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4 animate-scale-up">
            <div className="flex items-center justify-between border-b border-card-border/50 pb-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Brain className="w-5 h-5 text-indigo-400" />
                <span>Publish to Hugging Face Hub</span>
              </h3>
              <button 
                onClick={() => { setShowHFModal(false); setHfRepoUrl(""); }}
                className="text-slate-500 hover:text-slate-300 text-sm font-bold font-mono"
              >
                ✕
              </button>
            </div>
            
            {!hfRepoUrl ? (
              <>
                <p className="text-xs text-slate-400 leading-relaxed">
                  You are about to export and publish this project's research outputs to Hugging Face.
                  This will upload the following artifacts:
                </p>
                <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-300">
                  <li>Model Card (README.md) containing the summary and evaluations</li>
                  <li>Hyperparameter configurations (config.yaml)</li>
                  <li>Training metrics histories and logs</li>
                  <li>Mock/Fine-tuned PyTorch Model Weights</li>
                </ul>
                <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-lg p-3 text-[10px] text-indigo-300 leading-normal">
                  Note: Models will be published under the <strong>arsa-ai</strong> community organization.
                </div>
                <div className="flex gap-3 justify-end pt-2">
                  <button
                    onClick={() => { setShowHFModal(false); }}
                    className="px-4 py-2 rounded-lg border border-card-border hover:bg-slate-800 text-xs font-semibold text-slate-400"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      setHfPublishing(true);
                      try {
                        const token = getToken();
                        const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/publish/hf`, {
                          method: "POST",
                          headers: {
                            ...(token ? { Authorization: `Bearer ${token}` } : {}),
                          }
                        });
                        if (!response.ok) throw new Error("Hugging Face upload failed");
                        const data = await response.json();
                        setHfRepoUrl(data.repository_url);
                        alert("Repository successfully created and populated on Hugging Face!");
                      } catch (err: any) {
                        alert("Error publishing: " + err.message);
                      } finally {
                        setHfPublishing(false);
                      }
                    }}
                    disabled={hfPublishing}
                    className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {hfPublishing ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Uploading...</span>
                      </>
                    ) : (
                      <span>Publish Now</span>
                    )}
                  </button>
                </div>
              </>
            ) : (
              <div className="space-y-4 text-center py-4">
                <div className="w-12 h-12 bg-success/15 rounded-full flex items-center justify-center mx-auto border border-success/30">
                  <CheckCircle2 className="w-6 h-6 text-success" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-200">Upload Complete!</h4>
                  <p className="text-xs text-slate-400 mt-1">Your research project has been successfully published.</p>
                </div>
                <a 
                  href={hfRepoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-colors"
                >
                  View Repository on Hugging Face
                </a>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
