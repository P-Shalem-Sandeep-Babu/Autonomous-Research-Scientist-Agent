"use strict";

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, clearToken } from "@/lib/api";
import { 
  FlaskConical, LogOut, Plus, Search, Calendar, Folder, User as UserIcon, 
  Trash2, Brain, ChevronRight, BookOpen, GitMerge, FileText, Cpu, Play
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>({
    papers_analyzed: 0,
    gaps_found: 0,
    hypotheses_generated: 0,
    experiments_executed: 0,
    publications_generated: 0,
    total_projects: 0,
    compute_allocated: { gpus_active: 0, gpu_utilization_pct: 0, vram_allocated_gb: 0, vram_total_gb: 0 }
  });
  
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(true);

  // Quick Launch Presets
  const presets = [
    {
      title: "Novel Domain Invariant Brain Tumor Detection using MRI scans",
      description: "Addresses multi-scanner generalization issues (Siemens vs. Philips) for Glioma classification."
    },
    {
      title: "Transformer-based classification of multi-class Chest X-Rays",
      description: "Focuses on identifying pneumonia and lesions with local attention explanations."
    },
    {
      title: "GNN-based drug discovery for Alzheimer's protein folding",
      description: "Generates molecular compound graphs and plans affinity simulation loops."
    }
  ];

  useEffect(() => {
    const fetchUserData = async () => {
      const token = getToken();
      if (!token) {
        router.push("/login");
        return;
      }
      try {
        const user = await api.getMe();
        setCurrentUser(user);
        
        const prj = await api.getProjects();
        setProjects(prj);
        
        const ana = await api.getAnalytics();
        setAnalytics(ana);
      } catch (err) {
        console.error("Dashboard init error", err);
        clearToken();
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    fetchUserData();
  }, [router]);

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  const handleLaunchPreset = async (presetTitle: string, presetDesc: string) => {
    try {
      setLoading(true);
      const prj = await api.createProject({
        title: presetTitle,
        description: presetDesc
      });
      // Redirect directly to the project page to run the websocket pipeline
      router.push(`/projects/${prj.id}?run=true`);
    } catch (err) {
      alert("Error starting preset: " + err);
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const prj = await api.createProject({
        title: newTitle,
        description: newDesc
      });
      setNewTitle("");
      setNewDesc("");
      setIsCreating(false);
      
      // Fetch updated projects
      const updated = await api.getProjects();
      setProjects(updated);
      const ana = await api.getAnalytics();
      setAnalytics(ana);
    } catch (err) {
      alert("Error creating project: " + err);
    }
  };

  const handleDeleteProject = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this research project?")) return;
    try {
      await api.deleteProject(id);
      setProjects(projects.filter(p => p.id !== id));
      const ana = await api.getAnalytics();
      setAnalytics(ana);
    } catch (err) {
      alert("Delete failed: " + err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
          <span className="text-sm text-slate-400">Loading AI Research Hub...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col relative">
      {/* Background Grids */}
      <div className="absolute inset-0 tech-grid opacity-20 pointer-events-none" />

      {/* Top Navbar */}
      <header className="border-b border-card-border bg-card/60 backdrop-blur-md sticky top-0 z-20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
            <FlaskConical className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-200">ARSA Scientist Hub</h1>
            <p className="text-xs text-slate-500">Autonomous Scientific Multi-Agent platform</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {currentUser && (
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-slate-300">{currentUser.full_name}</p>
              <p className="text-xs text-slate-500 capitalize">{currentUser.role} Account</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-error/20 hover:bg-error/10 text-error text-xs font-semibold transition-all duration-200"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-8 z-10">
        
        {/* Core Metrics Row */}
        <section className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="glass-card rounded-xl p-5">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Papers Analyzed</span>
              <BookOpen className="w-4 h-4 text-primary" />
            </div>
            <p className="text-2xl font-extrabold text-slate-200 glow-text-cyan">{analytics.papers_analyzed}</p>
            <p className="text-xs text-slate-500 mt-1">Cross-referencing PubMed & arXiv</p>
          </div>
          
          <div className="glass-card rounded-xl p-5">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Gaps Discovered</span>
              <GitMerge className="w-4 h-4 text-accent" />
            </div>
            <p className="text-2xl font-extrabold text-slate-200">{analytics.gaps_found}</p>
            <p className="text-xs text-slate-500 mt-1">Unexplored limitation points</p>
          </div>

          <div className="glass-card rounded-xl p-5">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Hypotheses Rated</span>
              <Brain className="w-4 h-4 text-success" />
            </div>
            <p className="text-2xl font-extrabold text-slate-200">{analytics.hypotheses_generated}</p>
            <p className="text-xs text-slate-500 mt-1">Formulated proposals</p>
          </div>

          <div className="glass-card rounded-xl p-5">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Papers Authored</span>
              <FileText className="w-4 h-4 text-warning" />
            </div>
            <p className="text-2xl font-extrabold text-slate-200">{analytics.publications_generated}</p>
            <p className="text-xs text-slate-500 mt-1">Academic LaTeX publications</p>
          </div>

          <div className="glass-card rounded-xl p-5 col-span-2 lg:col-span-1">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">GPU Compute active</span>
              <Cpu className="w-4 h-4 text-primary" />
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-extrabold text-slate-200">
                {analytics.compute_allocated?.gpu_utilization_pct || 0}%
              </p>
              <span className="text-xs text-slate-400 font-mono">
                ({analytics.compute_allocated?.vram_allocated_gb || 0}GB/{analytics.compute_allocated?.vram_total_gb || 0}GB)
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Mock A100 sandboxes running</p>
          </div>
        </section>

        {/* Action Panel: AI Scientist Mode */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-card rounded-2xl p-6 border border-card-border flex flex-col justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-200 mb-2 flex items-center gap-2">
                <Plus className="w-5 h-5 text-primary" />
                <span>Launch AI Scientist Mode</span>
              </h2>
              <p className="text-sm text-slate-400 mb-6">
                Define a research question or topic. The platform coordinates 13 specialized agents autonomously, producing literature reviews, compiling training loops, executing simulations, and generating a peer-reviewed research paper.
              </p>

              {isCreating ? (
                <form onSubmit={handleCreateProject} className="space-y-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400 block uppercase">Project Title</label>
                    <input
                      type="text"
                      required
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      placeholder="e.g., GNN-based drug discovery for Alzheimer's protein folding"
                      className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400 block uppercase">Context / Goal Description</label>
                    <textarea
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                      placeholder="e.g., Use pocket-aware equivariant message passing to predict binding affinity on the MoleculeNet BACE1 dataset..."
                      className="w-full px-4 py-2.5 rounded-lg glass-input text-sm h-24 resize-none"
                    />
                  </div>
                  <div className="flex gap-3 justify-end">
                    <button
                      type="button"
                      onClick={() => setIsCreating(false)}
                      className="px-4 py-2 rounded-lg border border-card-border text-xs font-semibold hover:bg-slate-800 text-slate-400"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/95 text-background text-xs font-semibold"
                    >
                      Initialize Workspace
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex flex-col gap-3">
                  <button
                    onClick={() => setIsCreating(true)}
                    className="w-full py-4 rounded-xl border border-dashed border-primary/30 hover:border-primary bg-primary/5 hover:bg-primary/10 text-primary font-bold flex items-center justify-center gap-2 transition-all duration-200"
                  >
                    <Plus className="w-5 h-5" />
                    <span>Create Custom Research Goal</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Quick Launch Preset Sidebar */}
          <div className="glass-card rounded-2xl p-6 border border-card-border flex flex-col">
            <h3 className="text-sm font-bold text-slate-300 mb-4 uppercase tracking-wider">Scientific Preset Templates</h3>
            <div className="space-y-3 flex-1 flex flex-col justify-between">
              {presets.map((preset, idx) => (
                <div 
                  key={idx} 
                  onClick={() => handleLaunchPreset(preset.title, preset.description)}
                  className="p-3.5 rounded-xl bg-background/50 hover:bg-background/90 border border-card-border hover:border-primary/40 cursor-pointer group transition-all duration-200 flex flex-col justify-between"
                >
                  <div>
                    <h4 className="text-xs font-bold text-slate-200 group-hover:text-primary transition-colors">{preset.title}</h4>
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{preset.description}</p>
                  </div>
                  <div className="flex items-center justify-end text-[10px] text-primary font-semibold gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Play className="w-2.5 h-2.5 fill-current" />
                    <span>Execute Pipeline</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Projects List Grid */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
            <Folder className="w-5 h-5 text-primary" />
            <span>Active Research Workspaces</span>
          </h2>

          {projects.length === 0 ? (
            <div className="glass-card rounded-2xl p-12 text-center border border-card-border">
              <Folder className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-base font-bold text-slate-400">No active research workspaces</h3>
              <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                Create a custom project or select an automated scientific template to activate the agent network.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((p) => (
                <div
                  key={p.id}
                  onClick={() => router.push(`/projects/${p.id}`)}
                  className="glass-card rounded-xl p-5 border border-card-border flex flex-col justify-between h-48 cursor-pointer relative overflow-hidden group"
                >
                  {/* Status Indicator Bar */}
                  <div className={`absolute top-0 left-0 w-full h-1 ${
                    p.status === "completed" ? "bg-success" : 
                    p.status === "running" ? "bg-primary animate-pulse" : 
                    p.status === "failed" ? "bg-error" : "bg-slate-600"
                  }`} />
                  
                  <div>
                    <div className="flex items-start justify-between">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        p.status === "completed" ? "bg-success/10 text-success border border-success/20" : 
                        p.status === "running" ? "bg-primary/10 text-primary border border-primary/20" : 
                        p.status === "failed" ? "bg-error/10 text-error border border-error/20" : "bg-slate-800 text-slate-400 border border-slate-700"
                      }`}>
                        {p.status}
                      </span>
                      <button
                        onClick={(e) => handleDeleteProject(p.id, e)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-error hover:bg-error/10 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <h3 className="text-sm font-bold text-slate-200 mt-3 group-hover:text-primary transition-colors line-clamp-2">
                      {p.title}
                    </h3>
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-400 border-t border-card-border/40 pt-3">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      <span>{new Date(p.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <UserIcon className="w-3.5 h-3.5 text-slate-500" />
                      <span className="capitalize">{p.user?.full_name || "Alice"}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
