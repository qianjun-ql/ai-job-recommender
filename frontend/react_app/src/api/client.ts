/**
 * Typed Axios client for the Django proxy layer.
 * All requests go to Vite dev server → /api/* → Django :8001 → FastAPI :8000
 */
import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true, // include session cookie for auth
  headers: { "Content-Type": "application/json" },
});

// ─── Types matching FastAPI Pydantic models ───────────────────────────────────

export interface JobMatchResponse {
  job_id: string;
  title: string;
  role: string;
  location: string;
  match_score: number;
  skills: string[];
  snippet: string;
}

export interface GapResult {
  matched_skills: string[];
  missing_skills: string[];
  match_score: number;
  total_required: number;
  target_role: string;
}

export interface ProjectRecommendation {
  title: string;
  description: string;
  skills_addressed: string[]; // matches ProjectResponse.skills_addressed in FastAPI
  difficulty: string;
  estimated_hours: number;
  github_template?: string;
}

export interface AnalyzeRequest {
  skills: string[];
  target_role?: string; // optional — matches AnalyzeRequest.target_role (Role | None)
}

export interface AnalyzeResponse {
  top_jobs: JobMatchResponse[];
  matched_skills: string[];
  missing_skills: string[];
  match_score: number;
  projects: ProjectRecommendation[];
}

export interface ChatRequest {
  message: string;
  session_id?: string; // omit on first message; backend assigns empty string default
  user_skills?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  tool_calls_made: string[];
  session_id: string;
}

export interface SkillDemand {
  skill: string;
  demand_count: number;
  pct_of_jobs: number;
}

/** GET /market_stats response — landing page data */
export interface MarketStats {
  total_jobs: number;
  total_skills: number;
  roles: Record<string, number>;
  top_skills: SkillDemand[];
}

/** GET /skills_by_role response item */
export interface RoleSkillsItem {
  role: string;
  skills: SkillDemand[];
}

export interface SkillsByRoleResponse {
  roles: RoleSkillsItem[];
}

export interface ExtractJDResponse {
  skills: string[];
  method: "hybrid" | "dictionary";
  count: number;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
}

// ─── ML endpoints (Django → FastAPI proxy) ────────────────────────────────────

export const mlApi = {
  analyze: (data: AnalyzeRequest) =>
    api.post<AnalyzeResponse>("/ml/analyze/", data).then((r) => r.data),

  chat: (data: ChatRequest) =>
    api.post<ChatResponse>("/ml/chat/", data).then((r) => r.data),

  /** Top N skills for a specific role. */
  topSkills: (role: string, limit = 20) =>
    api
      .get<{ role: string; skills: SkillDemand[] }>("/ml/top_skills/", {
        params: { role, limit },
      })
      .then((r) => r.data.skills),

  /** Cross-role market stats for landing page (no role required). */
  marketStats: (limit = 15) =>
    api
      .get<MarketStats>("/ml/market_stats/", { params: { limit } })
      .then((r) => r.data),

  /** Top N skills per role for the role comparison chart. */
  skillsByRole: (limit = 8) =>
    api
      .get<SkillsByRoleResponse>("/ml/skills_by_role/", { params: { limit } })
      .then((r) => r.data.roles),

  /** Extract skills from a raw job description text (no auth required). */
  extractJD: (text: string) =>
    api
      .post<ExtractJDResponse>("/ml/extract_jd/", { text })
      .then((r) => r.data),

  health: () => api.get<{ status: string }>("/ml/health/").then((r) => r.data),
};

// ─── Auth endpoints (Django session auth) ─────────────────────────────────────

export const authApi = {
  register: (data: RegisterRequest) =>
    api.post<UserProfile>("/auth/register/", data).then((r) => r.data),

  login: (data: LoginRequest) =>
    api.post<UserProfile>("/auth/login/", data).then((r) => r.data),

  logout: () => api.post<void>("/auth/logout/").then((r) => r.data),

  me: () => api.get<UserProfile>("/auth/me/").then((r) => r.data),
};

export default api;
