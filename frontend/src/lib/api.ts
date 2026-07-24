// Cliente da API do spec-monitor. Substitui o antigo mock-data.ts: os tipos são
// os mesmos, só que agora os dados vêm do backend FastAPI (/api/*).
//
// Base da URL:
//   - vazio (default) → chamadas relativas "/api/...". Em dev o proxy do Vite
//     (vite.config.ts) repassa para o backend; em prod funciona se o frontend
//     e a API estiverem no mesmo host (reverse proxy roteando /api).
//   - VITE_API_URL definido → chamadas absolutas para lá (frontend e API em
//     hosts diferentes). Nesse caso o backend precisa de CORS liberado para a
//     origem do frontend e cookie SameSite=None/Secure (ver .env do backend).
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export type SyncStatus = "ok" | "failed" | "never";

// STATUS defasado: STATUS.md ficou para trás da atividade recente das specs.
// Derivado no backend (não persistido) a partir das datas de commit.
export interface Staleness {
  stale: boolean;
  daysBehind: number | null;
  thresholdDays: number;
  lastStatusUpdate: string | null;
  lastActivityAt: string | null;
}

export interface Project {
  id: string;
  name: string;
  repo: string;
  branch: string;
  specsDir: string;
  statusPath: string;
  lastSyncAt: string | null;
  lastSyncOk: SyncStatus;
  specsCount: number;
  staleness: Staleness;
}

export interface SpecFile {
  id: string;
  projectId: string;
  path: string;
  title: string;
  lastUpdated: string | null;
  versionsCount: number;
}

export interface SpecVersion {
  id: string;
  specFileId: string;
  commitSha: string;
  commitDate: string;
  commitMessage: string;
  author: string;
  content: string;
}

export interface StatusSnapshot {
  id: string;
  projectId: string;
  commitSha: string;
  commitDate: string;
  commitMessage: string;
  content: string;
}

export interface ActivityItem {
  date: string;
  specId: string;
  specTitle: string;
  commitSha: string;
  commitMessage: string;
  author: string;
}

export interface AdminUser {
  id: string;
  email: string;
  role: "admin" | "viewer";
  createdAt: string;
}

export interface Checkpoint {
  id: string;
  projectId: string;
  path: string;
  number: number;
  title: string;
  date: string | null;
  commitSha: string;
  commitDate: string | null;
  content: string;
}

export interface ProjectDetail {
  project: Project;
  latestStatus: StatusSnapshot | null;
  specs: SpecFile[];
  checkpoints: Checkpoint[];
  recentActivity: ActivityItem[];
  lastSync: { startedAt: string | null; ok: boolean; message: string } | null;
}

export interface SpecDetail {
  spec: SpecFile;
  project: Project;
  versions: SpecVersion[];
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  // 401 → sessão ausente/expirada: manda pro login (client-side).
  if (res.status === 401) {
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Não autenticado");
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* corpo não-JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- Auth ---
export const login = (email: string, password: string) =>
  apiFetch<AdminUser>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const logout = () => apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" });

export const getMe = () => apiFetch<AdminUser>("/auth/me");

// --- Projetos ---
export const listProjects = () => apiFetch<Project[]>("/projects");

export const getProjectDetail = (projectId: string) =>
  apiFetch<ProjectDetail>(`/projects/${projectId}`);

export interface CreateProjectInput {
  name: string;
  repo: string;
  branch: string;
  specsDir: string;
  statusPath: string;
  token?: string;
}

export const createProject = (input: CreateProjectInput) =>
  apiFetch<Project>("/projects", { method: "POST", body: JSON.stringify(input) });

export const syncProject = (projectId: string) =>
  apiFetch<Project>(`/projects/${projectId}/sync`, { method: "POST" });

export const deleteProject = (projectId: string) =>
  apiFetch<void>(`/projects/${projectId}`, { method: "DELETE" });

// --- Specs ---
export const getSpecDetail = (projectId: string, specId: string) =>
  apiFetch<SpecDetail>(`/projects/${projectId}/specs/${specId}`);

// --- Membros do projeto (admin) ---
export const listMembers = (projectId: string) =>
  apiFetch<AdminUser[]>(`/projects/${projectId}/members`);

export const addMember = (projectId: string, userId: string) =>
  apiFetch<AdminUser>(`/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ userId }),
  });

export const removeMember = (projectId: string, userId: string) =>
  apiFetch<void>(`/projects/${projectId}/members/${userId}`, { method: "DELETE" });

// --- Usuários ---
export const listUsers = () => apiFetch<AdminUser[]>("/users");

export const createUser = (email: string, password: string, isAdmin: boolean) =>
  apiFetch<AdminUser>("/users", {
    method: "POST",
    body: JSON.stringify({ email, password, isAdmin }),
  });
