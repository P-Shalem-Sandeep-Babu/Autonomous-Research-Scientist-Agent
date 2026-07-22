const API_BASE = "http://127.0.0.1:8000/api/v1";
const WS_BASE = "ws://127.0.0.1:8000/ws";

export function getToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("arsa_token");
  }
  return null;
}

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("arsa_token", token);
  }
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("arsa_token");
  }
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
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
  async login(formData: FormData) {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }
    const data = await response.json();
    setToken(data.access_token);
    return data;
  },

  async register(userData: any) {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  },

  async getMe() {
    return request("/auth/me");
  },

  // Projects
  async getProjects() {
    return request("/projects");
  },

  async createProject(projectData: any) {
    return request("/projects", {
      method: "POST",
      body: JSON.stringify(projectData),
    });
  },

  async getProject(id: string | number) {
    return request(`/projects/${id}`);
  },

  async deleteProject(id: string | number) {
    return request(`/projects/${id}`, {
      method: "DELETE",
    });
  },

  async getCodeFile(projectId: string | number, fileId: string | number) {
    return request(`/projects/${projectId}/code/${fileId}`);
  },

  async getProjectGraph(projectId: string | number) {
    return request(`/projects/${projectId}/graph`);
  },

  // Analytics
  async getAnalytics() {
    return request("/analytics");
  },

  // WS URL Helper
  getWsUrl(projectId: string | number): string {
    const token = getToken();
    return `${WS_BASE}/projects/${projectId}?token=${token || ""}`;
  }
};
