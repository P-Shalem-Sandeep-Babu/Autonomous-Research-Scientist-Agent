import {
  User,
  Project,
  DashboardAnalytics,
  KnowledgeGraphData,
  AdminUser,
  ApiKeyItem,
  ApiKeyCreateInput,
  SystemComputeInfo,
  LoginResponse,
  MFASetupResponse
} from "@/types";

// Dynamically resolve API and WebSocket URLs from environment or window location
const getApiBase = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    const proto = window.location.protocol;
    const host = window.location.hostname;
    // Default to port 8000 on the same host if accessing over LAN or local IP
    return `${proto}//${host}:8000/api/v1`;
  }
  return "http://127.0.0.1:8000/api/v1";
};

const getWsBase = (): string => {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname;
    return `${wsProto}//${host}:8000/ws`;
  }
  return "ws://127.0.0.1:8000/ws";
};

export const API_BASE = getApiBase();
export const WS_BASE = getWsBase();

// Security Fix 5.1: Eliminate localStorage storage of sensitive JWT secrets.
// Tokens are maintained solely in closure memory during an active tab session,
// while primary session persistence is delegated to secure HttpOnly cookies.
let inMemoryToken: string | null = null;

export function getToken(): string | null {
  return inMemoryToken;
}

export function setToken(token: string) {
  inMemoryToken = token;
  // Proactively purge any residual tokens from legacy localStorage
  if (typeof window !== "undefined") {
    try {
      localStorage.removeItem("arsa_token");
    } catch {}
  }
}

export function clearToken() {
  inMemoryToken = null;
  if (typeof window !== "undefined") {
    try {
      localStorage.removeItem("arsa_token");
    } catch {}
  }
}

async function request<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include", // Pass secure HttpOnly cookies with every request
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    const err = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Request failed");
  }

  return response.json();
}

export const api = {
  // Auth
  async login(formData: FormData, mfaCode?: string): Promise<LoginResponse> {
    if (mfaCode) {
      formData.set("mfa_code", mfaCode);
    }
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }
    const data: LoginResponse = await response.json();
    if (data.access_token) {
      setToken(data.access_token);
    }
    return data;
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      clearToken();
    }
  },

  async forgotPassword(email: string): Promise<{ message: string; reset_token?: string }> {
    return request<{ message: string; reset_token?: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    return request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  },

  async setupMFA(): Promise<MFASetupResponse> {
    return request<MFASetupResponse>("/auth/mfa/setup", {
      method: "POST",
    });
  },

  async enableMFA(code: string): Promise<{ message: string }> {
    return request<{ message: string }>("/auth/mfa/enable", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  },

  async disableMFA(code: string, password: string): Promise<{ message: string }> {
    return request<{ message: string }>("/auth/mfa/disable", {
      method: "POST",
      body: JSON.stringify({ code, password }),
    });
  },

  async register(userData: { email: string; password: string; full_name: string; role?: string }): Promise<User> {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  },

  async getMe(): Promise<User> {
    return request<User>("/auth/me");
  },

  // Projects
  async getProjects(): Promise<Project[]> {
    return request<Project[]>("/projects");
  },

  async createProject(projectData: { title: string; description?: string }): Promise<Project> {
    return request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(projectData),
    });
  },

  async getProject(id: string | number): Promise<any> {
    return request(`/projects/${id}`);
  },

  async deleteProject(id: string | number): Promise<{ status: string }> {
    return request<{ status: string }>(`/projects/${id}`, {
      method: "DELETE",
    });
  },

  async getCodeFile(projectId: string | number, fileId: string | number): Promise<{ id: number; filepath: string; content: string }> {
    return request(`/projects/${projectId}/code/${fileId}`);
  },

  async getProjectGraph(projectId: string | number): Promise<KnowledgeGraphData> {
    return request<KnowledgeGraphData>(`/projects/${projectId}/graph`);
  },

  // Analytics
  async getAnalytics(): Promise<DashboardAnalytics> {
    return request<DashboardAnalytics>("/analytics");
  },

  // Admin APIs
  async getAdminUsers(): Promise<AdminUser[]> {
    return request<AdminUser[]>("/admin/users");
  },

  async updateAdminUser(userId: number, data: { role?: string; compute_quota_gpu_hours?: number; is_active?: boolean }): Promise<AdminUser> {
    return request<AdminUser>(`/admin/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async deleteAdminUser(userId: number): Promise<{ status: string; detail: string }> {
    return request<{ status: string; detail: string }>(`/admin/users/${userId}`, {
      method: "DELETE",
    });
  },

  async getAdminKeys(): Promise<ApiKeyItem[]> {
    return request<ApiKeyItem[]>("/admin/keys");
  },

  async createAdminKey(data: ApiKeyCreateInput): Promise<ApiKeyItem> {
    return request<ApiKeyItem>("/admin/keys", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async deleteAdminKey(keyId: number): Promise<{ status: string; detail: string }> {
    return request<{ status: string; detail: string }>(`/admin/keys/${keyId}`, {
      method: "DELETE",
    });
  },

  async getAdminCompute(): Promise<SystemComputeInfo> {
    return request<SystemComputeInfo>("/admin/compute");
  },

  async updateAdminCompute(data: Partial<SystemComputeInfo>): Promise<SystemComputeInfo> {
    return request<SystemComputeInfo>("/admin/compute", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  // WS URL Helper - OWASP compliant clean URL (no credentials leaked into access logs)
  getWsUrl(projectId: string | number): string {
    return `${WS_BASE}/projects/${projectId}`;
  }
};

