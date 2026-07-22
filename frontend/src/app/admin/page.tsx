"use strict";

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import { 
  ArrowLeft, Cpu, Key, Users, Settings, Database, 
  CheckCircle, Plus, Trash2, Edit2, ShieldAlert
} from "lucide-react";

export default function AdminPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  // Mock Admin Settings
  const [keys, setKeys] = useState([
    { provider: "Gemini Pro", model: "gemini-1.5-pro", key: "••••••••••••••••" },
    { provider: "OpenAI GPT-4o", model: "gpt-4o", key: "••••••••••••••••" },
    { provider: "LM Studio Local", model: "qwen-2.5-7b", key: "http://localhost:1234/v1" }
  ]);
  
  const [compute, setCompute] = useState({
    activeGpus: "1x NVIDIA A100 (80GB)",
    utilization: 45,
    memoryLimit: 64, // GB
    cpuCores: 16
  });

  const [users, setUsers] = useState([
    { id: 1, name: "Dr. Alice Researcher", email: "researcher@arsa.ai", role: "researcher" },
    { id: 2, name: "Prof. Bob Supervisor", email: "supervisor@arsa.ai", role: "supervisor" },
    { id: 3, name: "Admin Charlie", email: "admin@arsa.ai", role: "administrator" }
  ]);

  useEffect(() => {
    const fetchAdmin = async () => {
      const token = getToken();
      if (!token) {
        router.push("/login");
        return;
      }
      try {
        const user = await api.getMe();
        if (user.role !== "administrator") {
          alert("Access denied: Admin permissions required.");
          router.push("/dashboard");
          return;
        }
        setCurrentUser(user);
      } catch (err) {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    fetchAdmin();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col relative text-slate-200">
      <div className="absolute inset-0 tech-grid opacity-15 pointer-events-none" />

      {/* Header */}
      <header className="border-b border-card-border bg-card/60 backdrop-blur-md px-6 py-4 flex items-center gap-4 z-10">
        <button 
          onClick={() => router.push("/dashboard")}
          className="p-2 rounded-lg border border-card-border hover:bg-card text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-base font-bold text-slate-200">System Admin Control Center</h1>
          <p className="text-xs text-slate-500">Resource quotas, LLM orchestration, and user privileges</p>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto p-6 md:p-8 space-y-8 z-10">
        
        {/* Row 1: LLM Key Management & Compute quotas */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LLM configs */}
          <div className="glass-card rounded-2xl p-6 border border-card-border">
            <h2 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider font-mono">
              <Key className="w-4 h-4 text-primary" />
              <span>Orchestrated Model API Keys</span>
            </h2>
            <div className="space-y-4">
              {keys.map((k, i) => (
                <div key={i} className="flex justify-between items-center p-3 bg-background/40 rounded-xl border border-card-border/60">
                  <div>
                    <h4 className="text-xs font-bold text-slate-300">{k.provider}</h4>
                    <span className="text-[10px] text-slate-500 font-mono mt-0.5 block">{k.model}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 font-mono bg-slate-900/60 px-2 py-0.5 rounded border border-card-border">{k.key}</span>
                    <button className="text-slate-400 hover:text-primary p-1"><Edit2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
              <button className="w-full py-2.5 rounded-lg border border-dashed border-primary/20 hover:border-primary bg-primary/5 hover:bg-primary/10 text-primary font-bold text-xs transition-all flex items-center justify-center gap-1.5">
                <Plus className="w-4 h-4" />
                <span>Link API Credentials</span>
              </button>
            </div>
          </div>

          {/* Compute node quotas */}
          <div className="glass-card rounded-2xl p-6 border border-card-border flex flex-col justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider font-mono">
                <Cpu className="w-4 h-4 text-primary" />
                <span>GPU Sandbox Engine Allocation</span>
              </h2>
              <div className="space-y-3 text-xs text-slate-400 font-mono">
                <div className="flex justify-between border-b border-card-border/40 pb-2">
                  <span className="text-slate-500">Node Hardware:</span>
                  <span className="text-slate-300 font-semibold">{compute.activeGpus}</span>
                </div>
                <div className="flex justify-between border-b border-card-border/40 pb-2">
                  <span className="text-slate-500">Allocated CPU Cores:</span>
                  <span className="text-slate-300 font-semibold">{compute.cpuCores} Cores</span>
                </div>
                <div className="flex justify-between border-b border-card-border/40 pb-2">
                  <span className="text-slate-500">Shared Sandbox RAM:</span>
                  <span className="text-slate-300 font-semibold">{compute.memoryLimit} GB</span>
                </div>
                <div className="flex justify-between pb-2">
                  <span className="text-slate-500">Virtual GPU Load:</span>
                  <span className="text-primary font-semibold">{compute.utilization}% load</span>
                </div>
              </div>
            </div>
            
            <div className="pt-6 border-t border-card-border/40 flex items-center gap-2 text-[10px] text-slate-500">
              <CheckCircle className="w-3.5 h-3.5 text-success" />
              <span>GPU scheduler online. Sandboxed executions are active.</span>
            </div>
          </div>
        </div>

        {/* Row 2: User management */}
        <div className="glass-card rounded-2xl p-6 border border-card-border">
          <h2 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider font-mono">
            <Users className="w-4 h-4 text-primary" />
            <span>Platform User Directory</span>
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-card-border/60 text-slate-500 uppercase tracking-widest text-[9px] font-mono">
                  <th className="py-2">Researcher Name</th>
                  <th className="py-2">Email</th>
                  <th className="py-2">System Role</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-card-border/20 text-slate-300">
                    <td className="py-3 font-semibold text-slate-200">{u.name}</td>
                    <td className="py-3">{u.email}</td>
                    <td className="py-3 capitalize">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold font-mono ${
                        u.role === "administrator" ? "bg-error/10 text-error border border-error/20" :
                        u.role === "supervisor" ? "bg-warning/10 text-warning border border-warning/20" : "bg-primary/10 text-primary border border-primary/20"
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 text-right space-x-2">
                      <button className="text-slate-400 hover:text-primary"><Edit2 className="w-3.5 h-3.5" /></button>
                      <button className="text-slate-400 hover:text-error"><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </main>
    </div>
  );
}
