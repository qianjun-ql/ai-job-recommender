"""
API request/response schemas — Pydantic v2.
All FR-07 endpoints use these models for validation and serialisation.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    AI_ENGINEER = "AI Engineer"
    DATA_ENGINEER = "Data Engineer"
    DATA_SCIENTIST = "Data Scientist"
    ML_ENGINEER = "ML Engineer"
    SWE = "SWE"


# ── Shared sub-models ─────────────────────────────────────────────────────────


class JobMatchResponse(BaseModel):
    job_id: str
    title: str
    role: str
    location: str
    match_score: float
    skills: list[str]
    snippet: str


class ProjectResponse(BaseModel):
    title: str
    description: str
    skills_addressed: list[str]
    difficulty: str  # Beginner | Intermediate | Advanced
    estimated_hours: int


class SkillDemand(BaseModel):
    skill: str
    demand_count: int
    pct_of_jobs: float


class GapResult(BaseModel):
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: float  # 0–100 (% of required skills the user already has)
    total_required: int
    top_role_skills: list[SkillDemand]  # top skills by demand, for UI display
    target_role: str = ""  # echoed back so callers don't need to re-pass it


# ── POST /analyze ─────────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    skills: list[str] = Field(..., min_length=1)
    target_role: Role | None = None  # optional — analyze across all roles if omitted
    location: str | None = None


class AnalyzeResponse(BaseModel):
    top_jobs: list[JobMatchResponse]
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: float
    projects: list[ProjectResponse]


# ── POST /chat ────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = ""  # empty string → new session
    user_skills: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]  # job_ids cited
    tool_calls_made: list[str]
    session_id: str


# ── GET /top_skills ───────────────────────────────────────────────────────────


class TopSkillsResponse(BaseModel):
    role: str
    skills: list[SkillDemand]


# ── GET /market_stats ────────────────────────────────────────────────────────


class MarketStatsResponse(BaseModel):
    total_jobs: int
    total_skills: int
    roles: dict[str, int]  # role_name -> job count
    top_skills: list[SkillDemand]


# ── GET /skills_by_role ───────────────────────────────────────────────────────


class RoleSkillsItem(BaseModel):
    role: str
    skills: list[SkillDemand]


class SkillsByRoleResponse(BaseModel):
    roles: list[RoleSkillsItem]


# ── POST /extract_jd ─────────────────────────────────────────────────────────


class ExtractJDRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Raw job description text")


class ExtractJDResponse(BaseModel):
    skills: list[str]
    method: str  # "hybrid" | "dictionary"
    count: int


# ── GET /health ───────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str
    dataset_rows: int
    index_size: int
