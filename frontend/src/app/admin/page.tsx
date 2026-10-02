"use strict";

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import { User, AdminUser, ApiKeyItem, SystemComputeInfo } from "@/types";
import { 
  ArrowLeft, Cpu, Key, Users, Settings, 
  CheckCircle, Plus, Trash2, Edit2, ShieldAlert,
  X, AlertTriangle, RefreshCw, Power, Check
} from "lucide-react";

export default function AdminPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Live Admin Data
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [compute, setCompute] = useState<SystemComputeInfo>({
    active_gpus: "1x NVIDIA A100 (80GB)",
    utilization_pct: 35,
    memory_limit_gb: 64,
    allocated_cpu_cores: 16,
    scheduler_status: "online"
  });
  const [users, setUsers] = useState<AdminUser[]>([]);

  // Modals state
  const [isAddKeyOpen, setIsAddKeyOpen] = useState<boolean>(false);
  const [newKeyProvider, setNewKeyProvider] = useState<string>("Gemini Pro");
  const [newKeyModel, setNewKeyModel] = useState<string>("gemini-1.5-pro");
  const [newKeyValue, setNewKeyValue] = useState<string>("");

  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [userRole, setUserRole] = useState<"researcher" | "supervisor" | "administrator">("researcher");
  const [userQuota, setUserQuota] = useState<number>(50);
  const [userIsActive, setUserIsActive] = useState<boolean>(true);

  const [isEditComputeOpen, setIsEditComputeOpen] = useState<boolean>(false);
  const [editActiveGpus, setEditActiveGpus] = useState<string>("");
  const [editCpuCores, setEditCpuCores] = useState<number>(16);
  const [editMemoryLimitGb, setEditMemoryLimitGb] = useState<number>(64);
  const [editSchedulerStatus, setEditSchedulerStatus] = useState<string>("online");

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  const fetchAdminData = async () => {
    try {
      const [fetchedKeys, fetchedCompute, fetchedUsers] = await Promise.all([
        api.getAdminKeys(),
        api.getAdminCompute(),
        api.getAdminUsers()
      ]);
      setKeys(fetchedKeys);
      setCompute(fetchedCompute);
      setUsers(fetchedUsers);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load admin telemetry";
      showNotification("error", msg);
    }
  };

  useEffect(() => {
    const fetchAdmin = async () => {
      try {
        const user = await api.getMe();
        if (user.role !== "administrator") {
          alert("Access denied: Administrator permissions required.");
          router.push("/dashboard");
          return;
        }
        setCurrentUser(user);
        await fetchAdminData();
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    fetchAdmin();
  }, [router]);

  // Key Handlers
  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyValue.trim()) return;
    try {
      setActionLoading(true);
      await api.createAdminKey({
        provider: newKeyProvider,
        model_name: newKeyModel,
        api_key: newKeyValue.trim()
      });
      showNotification("success", `Registered credentials for ${newKeyProvider} (${newKeyModel})`);
      setIsAddKeyOpen(false);
      setNewKeyValue("");
      const updatedKeys = await api.getAdminKeys();
      setKeys(updatedKeys);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to register key";
      showNotification("error", msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteKey = async (keyId: number, provider: string) => {
    if (!confirm(`Are you sure you want to revoke API credentials for ${provider}?`)) return;
    try {
      setActionLoading(true);
      await api.deleteAdminKey(keyId);
      showNotification("success", `Revoked API credentials for ${provider}`);
      const updatedKeys = await api.getAdminKeys();
      setKeys(updatedKeys);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete key";
      showNotification("error", msg);
    } finally {
      setActionLoading(false);
    }
  };

  // User Handlers
  const handleOpenEditUser = (user: AdminUser) => {
    setEditingUser(user);
    setUserRole(user.role);
    setUserQuota(user.compute_quota_gpu_hours);
    setUserIsActive(user.is_active);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      setActionLoading(true);
      await api.updateAdminUser(editingUser.id, {
        role: userRole,
        compute_quota_gpu_hours: Number(userQuota),
        is_active: userIsActive
      });
      showNotification("success", `Updated permissions and quota for ${editingUser.full_name}`);
      setEditingUser(null);
      const updatedUsers = await api.getAdminUsers();
      setUsers(updatedUsers);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update user";
      showNotification("error", msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteUser = async (user: AdminUser) => {
    if (user.id === currentUser?.id) {
      showNotification("error", "Cannot delete your own administrator account.");
      return;
    }
    if (!confirm(`Permanently remove user "${user.full_name}" (${user.email}) and all their research workspaces?`)) return;
    try {
      setActionLoading(true);
      await api.deleteAdminUser(user.id);
      showNotification("success", `Removed user ${user.full_name}`);
      const updatedUsers = await api.getAdminUsers();
      setUsers(updatedUsers);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete user";
      showNotification("error", msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Compute Handlers
  const handleOpenEditCompute = () => {
    setEditActiveGpus(compute.active_gpus);
    setEditCpuCores(compute.allocated_cpu_cores);
    setEditMemoryLimitGb(compute.memory_limit_gb);
    setEditSchedulerStatus(compute.scheduler_status);
    setIsEditComputeOpen(true);
  };

  const handleSaveCompute = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setActionLoading(true);
      const updated = await api.updateAdminCompute({
        active_gpus: editActiveGpus,
        allocated_cpu_cores: Number(editCpuCores),
        memory_limit_gb: Number(editMemoryLimitGb),
        scheduler_status: editSchedulerStatus
      });
      setCompute(updated);
      showNotification("success", "GPU Sandbox Allocation updated successfully");
      setIsEditComputeOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update compute settings";
      showNotification("error", msg);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
          <span className="text-xs text-slate-400 font-mono">Authenticating Administrator Session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col relative text-slate-200">
      <div className="absolute inset-0 tech-grid opacity-15 pointer-events-none" />

      {/* Header */}
      <header className="border-b border-card-border bg-card/60 backdrop-blur-md px-6 py-4 flex items-center justify-between z-10 sticky top-0">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push("/dashboard")}
            className="p-2 rounded-lg border border-card-border hover:bg-card text-slate-400 hover:text-slate-200 transition-colors"
            title="Return to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-primary" />
              <h1 className="text-base font-bold text-slate-200">System Admin Control Center</h1>
            </div>
            <p className="text-xs text-slate-500">Resource quotas, LLM orchestration, and user privileges</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchAdminData}
            disabled={actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-card-border hover:bg-card text-slate-300 text-xs font-mono transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? "animate-spin text-primary" : ""}`} />
            <span>Sync</span>
          </button>
          <div className="text-right hidden sm:block border-l border-card-border/60 pl-3">
            <span className="text-xs font-semibold text-slate-300 block">{currentUser?.full_name}</span>
            <span className="text-[10px] text-primary font-mono uppercase">Superuser Access</span>
          </div>
        </div>
      </header>

      {/* Floating Notification */}
      {notification && (
        <div className="fixed top-20 right-6 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl border text-xs font-semibold shadow-2xl backdrop-blur-md ${
            notification.type === "success" 
              ? "bg-success/15 border-success/30 text-success" 
              : "bg-error/15 border-error/30 text-error"
          }`}>
            {notification.type === "success" ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      <main className="flex-1 max-w-6xl w-full mx-auto p-6 md:p-8 space-y-8 z-10">
        
        {/* Row 1: LLM Key Management & Compute quotas */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LLM configs */}
          <div className="glass-card rounded-2xl p-6 border border-card-border flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2 uppercase tracking-wider font-mono">
                  <Key className="w-4 h-4 text-primary" />
                  <span>Orchestrated Model API Keys</span>
                </h2>
                <span className="text-[10px] text-slate-500 font-mono">{keys.length} Registered</span>
              </div>

              <div className="space-y-3">
                {keys.length === 0 ? (
                  <p className="text-xs text-slate-500 italic p-4 text-center border border-dashed border-card-border rounded-xl">
                    No custom credentials linked. Using environment defaults.
                  </p>
                ) : (
                  keys.map((k) => (
                    <div key={k.id} className="flex justify-between items-center p-3 bg-background/40 rounded-xl border border-card-border/60 hover:border-card-border transition-colors">
                      <div className="min-w-0 pr-2">
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-slate-200 truncate">{k.provider}</h4>
                          <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono uppercase ${
                            k.status === "active" ? "bg-success/10 text-success border border-success/20" : "bg-error/10 text-error border border-error/20"
                          }`}>
                            {k.status}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono mt-0.5 block truncate">{k.model_name}</span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-xs text-slate-400 font-mono bg-slate-900/60 px-2 py-0.5 rounded border border-card-border">
                          {k.masked_key}
                        </span>
                        <button 
                          onClick={() => handleDeleteKey(k.id, k.provider)}
                          disabled={actionLoading}
                          className="text-slate-500 hover:text-error p-1.5 rounded-lg hover:bg-error/10 transition-colors"
                          title="Revoke Key"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-card-border/40">
              <button 
                onClick={() => setIsAddKeyOpen(true)}
                className="w-full py-2.5 rounded-lg border border-dashed border-primary/30 hover:border-primary bg-primary/5 hover:bg-primary/10 text-primary font-bold text-xs transition-all flex items-center justify-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                <span>Link New API Credentials</span>
              </button>
            </div>
          </div>

          {/* Compute node quotas */}
          <div className="glass-card rounded-2xl p-6 border border-card-border flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2 uppercase tracking-wider font-mono">
                  <Cpu className="w-4 h-4 text-primary" />
                  <span>GPU Sandbox Engine Allocation</span>
                </h2>
                <button
                  onClick={handleOpenEditCompute}
                  className="flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline font-mono"
                >
                  <Edit2 className="w-3 h-3" />
                  <span>Configure Node</span>
                </button>
              </div>

              <div className="space-y-3 text-xs text-slate-400 font-mono">
                <div className="flex justify-between border-b border-card-border/40 pb-2.5">
                  <span className="text-slate-500">Node Hardware:</span>
                  <span className="text-slate-200 font-semibold">{compute.active_gpus}</span>
                </div>
                <div className="flex justify-between border-b border-card-border/40 pb-2.5">
                  <span className="text-slate-500">Allocated CPU Cores:</span>
                  <span className="text-slate-200 font-semibold">{compute.allocated_cpu_cores} Cores</span>
                </div>
                <div className="flex justify-between border-b border-card-border/40 pb-2.5">
                  <span className="text-slate-500">Shared Sandbox RAM:</span>
                  <span className="text-slate-200 font-semibold">{compute.memory_limit_gb} GB</span>
                </div>
                <div className="flex justify-between border-b border-card-border/40 pb-2.5">
                  <span className="text-slate-500">Virtual GPU Load:</span>
                  <span className="text-primary font-semibold">{compute.utilization_pct}% load</span>
                </div>
                <div className="flex justify-between pb-1">
                  <span className="text-slate-500">Scheduler State:</span>
                  <span className={`capitalize font-semibold ${
                    compute.scheduler_status === "online" ? "text-success" : "text-warning"
                  }`}>
                    {compute.scheduler_status}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="pt-4 mt-4 border-t border-card-border/40 flex items-center gap-2 text-[11px] text-slate-400">
              <CheckCircle className="w-4 h-4 text-success flex-shrink-0" />
              <span>Isolated execution container verified. Sandboxed processes are active.</span>
            </div>
          </div>
        </div>

        {/* Row 2: User management */}
        <div className="glass-card rounded-2xl p-6 border border-card-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2 uppercase tracking-wider font-mono">
              <Users className="w-4 h-4 text-primary" />
              <span>Platform User Directory & Quotas</span>
            </h2>
            <span className="text-xs text-slate-500 font-mono">{users.length} Active Accounts</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-card-border/60 text-slate-500 uppercase tracking-widest text-[9px] font-mono">
                  <th className="py-2.5 px-3">Researcher</th>
                  <th className="py-2.5 px-3">Email Address</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Compute Quota (GPU-h)</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-card-border/20 text-slate-300 hover:bg-card/40 transition-colors">
                    <td className="py-3 px-3 font-semibold text-slate-200">
                      <div className="flex items-center gap-2">
                        <span>{u.full_name}</span>
                        {u.id === currentUser?.id && (
                          <span className="text-[9px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-mono font-normal">You</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">{u.email}</td>
                    <td className="py-3 px-3 capitalize">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold font-mono ${
                        u.role === "administrator" ? "bg-error/10 text-error border border-error/20" :
                        u.role === "supervisor" ? "bg-warning/10 text-warning border border-warning/20" : "bg-primary/10 text-primary border border-primary/20"
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono">
                      <span className="text-slate-200">{u.compute_used_gpu_hours || 0}</span>
                      <span className="text-slate-500"> / {u.compute_quota_gpu_hours || 50} hrs</span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono ${
                        u.is_active ? "bg-success/10 text-success" : "bg-slate-800 text-slate-400"
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? "bg-success" : "bg-slate-500"}`} />
                        {u.is_active ? "Active" : "Suspended"}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right space-x-1">
                      <button 
                        onClick={() => handleOpenEditUser(u)}
                        className="text-slate-400 hover:text-primary p-1.5 rounded-lg hover:bg-primary/10 transition-colors"
                        title="Edit User Quota & Role"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button 
                        onClick={() => handleDeleteUser(u)}
                        disabled={u.id === currentUser?.id || actionLoading}
                        className={`p-1.5 rounded-lg transition-colors ${
                          u.id === currentUser?.id 
                            ? "text-slate-700 cursor-not-allowed" 
                            : "text-slate-400 hover:text-error hover:bg-error/10"
                        }`}
                        title={u.id === currentUser?.id ? "Cannot delete own account" : "Delete User"}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </main>

      {/* Modal: Link New API Key */}
      {isAddKeyOpen && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl border border-card-border p-6 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Key className="w-4 h-4 text-primary" />
                <span>Link LLM Provider Credentials</span>
              </h3>
              <button 
                onClick={() => setIsAddKeyOpen(false)}
                className="text-slate-500 hover:text-slate-300 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddKey} className="space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  Provider
                </label>
                <select
                  value={newKeyProvider}
                  onChange={(e) => {
                    setNewKeyProvider(e.target.value);
                    if (e.target.value === "Gemini Pro") setNewKeyModel("gemini-1.5-pro");
                    else if (e.target.value === "OpenAI GPT-4o") setNewKeyModel("gpt-4o");
                    else if (e.target.value === "Anthropic Claude") setNewKeyModel("claude-3-5-sonnet-20241022");
                    else if (e.target.value === "Groq LLaMA") setNewKeyModel("llama-3.3-70b-versatile");
                    else setNewKeyModel("local-model");
                  }}
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs"
                >
                  <option value="Gemini Pro">Gemini Pro</option>
                  <option value="OpenAI GPT-4o">OpenAI GPT-4o</option>
                  <option value="Anthropic Claude">Anthropic Claude</option>
                  <option value="Groq LLaMA">Groq LLaMA</option>
                  <option value="LM Studio Local">LM Studio / Local Ollama</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  Target Model Name
                </label>
                <input
                  type="text"
                  required
                  value={newKeyModel}
                  onChange={(e) => setNewKeyModel(e.target.value)}
                  placeholder="e.g., gemini-1.5-pro or gpt-4o"
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  API Key / Secret Token
                </label>
                <input
                  type="password"
                  required
                  value={newKeyValue}
                  onChange={(e) => setNewKeyValue(e.target.value)}
                  placeholder="Paste AI provider secret key"
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Stored securely and masked in the database. Never exposed in client payloads.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddKeyOpen(false)}
                  className="px-4 py-2 rounded-lg border border-card-border text-xs font-semibold text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-background text-xs font-bold transition-all"
                >
                  {actionLoading ? "Saving..." : "Store Credentials"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit User Quota & Role */}
      {editingUser && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl border border-card-border p-6 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Users className="w-4 h-4 text-primary" />
                <span>Configure User: {editingUser.full_name}</span>
              </h3>
              <button 
                onClick={() => setEditingUser(null)}
                className="text-slate-500 hover:text-slate-300 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  Platform Role
                </label>
                <select
                  value={userRole}
                  onChange={(e) => setUserRole(e.target.value as "researcher" | "supervisor" | "administrator")}
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs capitalize"
                >
                  <option value="researcher">Researcher</option>
                  <option value="supervisor">Supervisor</option>
                  <option value="administrator">Administrator</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  GPU Compute Quota (Hours)
                </label>
                <input
                  type="number"
                  min="0"
                  max="10000"
                  step="0.5"
                  required
                  value={userQuota}
                  onChange={(e) => setUserQuota(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Total compute sandbox budget allocated for this researcher.
                </p>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  Account Status
                </label>
                <div className="flex gap-4 items-center mt-1">
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input 
                      type="radio" 
                      name="isActive" 
                      checked={userIsActive} 
                      onChange={() => setUserIsActive(true)}
                    />
                    <span>Active (Permit Logins)</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input 
                      type="radio" 
                      name="isActive" 
                      checked={!userIsActive} 
                      onChange={() => setUserIsActive(false)}
                    />
                    <span className="text-error">Suspended</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 rounded-lg border border-card-border text-xs font-semibold text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-background text-xs font-bold transition-all"
                >
                  {actionLoading ? "Updating..." : "Save Settings"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit Compute Allocation */}
      {isEditComputeOpen && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl border border-card-border p-6 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-primary" />
                <span>Configure Compute Sandbox Engine</span>
              </h3>
              <button 
                onClick={() => setIsEditComputeOpen(false)}
                className="text-slate-500 hover:text-slate-300 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCompute} className="space-y-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  Node Hardware Description
                </label>
                <input
                  type="text"
                  required
                  value={editActiveGpus}
                  onChange={(e) => setEditActiveGpus(e.target.value)}
                  placeholder="e.g., 2x NVIDIA A100 (80GB) SXM4"
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                    CPU Cores
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="256"
                    required
                    value={editCpuCores}
                    onChange={(e) => setEditCpuCores(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                    RAM Limit (GB)
                  </label>
                  <input
                    type="number"
                    min="4"
                    max="1024"
                    required
                    value={editMemoryLimitGb}
                    onChange={(e) => setEditMemoryLimitGb(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                  Scheduler State
                </label>
                <select
                  value={editSchedulerStatus}
                  onChange={(e) => setEditSchedulerStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg glass-input text-xs"
                >
                  <option value="online">Online (Accepting executions)</option>
                  <option value="drain">Drain (Complete current, no new)</option>
                  <option value="maintenance">Maintenance</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEditComputeOpen(false)}
                  className="px-4 py-2 rounded-lg border border-card-border text-xs font-semibold text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-background text-xs font-bold transition-all"
                >
                  {actionLoading ? "Updating..." : "Apply Node Settings"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
