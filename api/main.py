"""
FR-07: REST API Layer

Endpoints:
    POST /analyze          — FR-04 + FR-05 + FR-06 combined pipeline
    GET  /top_skills       — top N skills for a role (?role=&limit=)
    GET  /health           — liveness + dataset stats
    POST /chat             — FR-08 agentic RAG chatbot (LangChain + Gemini)

Cross-cutting:
    - Every request gets a UUID request_id (logged + returned in errors)
    - Optional API key auth via X-API-Key header (disabled when API_KEY unset)
    - Rate limiting: 100 requests/day per IP (slowapi)
    - Consistent error envelope: { "error": str, "message": str, "request_id": str }
    - All 422 Pydantic validation errors follow the same envelope
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    Role,
    TopSkillsResponse,
)
from api.services.chatbot import agent_chat
from api.services.gap import compute_gap, get_top_skills
from api.services.matcher import match_jobs
from api.services.matcher import warmup as warmup_matcher
from api.services.recommender import recommend_projects
from config.settings import settings

logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["100/day"])


# ── Lifespan: warm up FAISS index + role index on startup ────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up FAISS index and role skill index …")
    try:
        warmup_matcher()  # loads FAISS + sentence encoder
    except Exception as exc:
        logger.warning(f"Matcher warm-up failed (will lazy-load on first request): {exc}")
    yield
    logger.info("API shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Job Skills Recommender",
    version=settings.API_VERSION,
    description=(
        "Semantic job matching, skill gap analysis, and LLM project "
        "recommendations for AI/ML job seekers."
    ),
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Middleware: inject request_id ─────────────────────────────────────────────


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Auth dependency ───────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)):
    """
    If settings.API_KEY is set, require a matching X-API-Key header.
    If not set (empty string), auth is disabled — all requests pass through.
    """
    if settings.API_KEY and api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Error envelope ────────────────────────────────────────────────────────────


def _error_response(
    status_code: int,
    error: str,
    message: str,
    request: Request | None = None,
) -> JSONResponse:
    request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "message": message, "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors())
    return _error_response(422, "VALIDATION_ERROR", msg, request)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return _error_response(exc.status_code, "HTTP_ERROR", exc.detail, request)


# ── POST /analyze ─────────────────────────────────────────────────────────────


@app.post("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("100/day")
async def analyze(request: Request, body: AnalyzeRequest) -> AnalyzeResponse:
    """
    Full pipeline: embed skills → match jobs (FR-04) → gap analysis (FR-05)
    → LLM project recommendations (FR-06).

    Returns top matching jobs, skill gap vs target role, and project ideas
    to close that gap.
    """
    # FR-04: semantic job matching
    top_jobs = match_jobs(
        user_skills=body.skills,
        role_filter=body.target_role,
        location=body.location,
        k=5,
    )

    # FR-05: skill gap analysis
    gap = compute_gap(user_skills=body.skills, target_role=body.target_role)

    # FR-06: LLM project recommendations
    projects = recommend_projects(
        missing_skills=gap.missing_skills,
        user_skills=body.skills,
        target_role=body.target_role,
        n=3,
    )

    return AnalyzeResponse(
        top_jobs=top_jobs,
        matched_skills=gap.matched_skills,
        missing_skills=gap.missing_skills,
        match_score=gap.match_score,
        projects=projects,
    )


# ── GET /top_skills ───────────────────────────────────────────────────────────


@app.get(
    "/top_skills",
    response_model=TopSkillsResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("100/day")
async def top_skills(
    request: Request,
    role: Role,
    limit: int = 20,
) -> TopSkillsResponse:
    """
    Return the top N most demanded skills for a role, ordered by frequency.
    Useful for displaying "what ML Engineers need" without a user profile.
    """
    limit = max(1, min(limit, 50))
    skills = get_top_skills(role, n=limit)
    return TopSkillsResponse(role=role, skills=skills)


# ── GET /health ───────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — no auth required."""
    # Dataset rows from CSV (fast: just count lines)
    dataset_rows = 0
    try:
        with open(settings.JOBS_CLEANED_CSV) as f:
            dataset_rows = sum(1 for _ in f) - 1  # subtract header
    except Exception:
        pass

    # Index size from job_id_map — avoids loading the full FAISS index
    index_size = 0
    try:
        import json

        index_size = len(json.loads(settings.JOB_ID_MAP.read_text()))
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version=settings.API_VERSION,
        dataset_rows=dataset_rows,
        index_size=index_size,
    )


# ── POST /chat ────────────────────────────────────────────────────────────────


@app.post("/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit("100/day")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """FR-08 — Agentic RAG chatbot.

    Passes the message and user skills to a LangChain tool-calling agent
    (Gemini 2.0 Flash) with 4 tools: search_jobs, get_skill_gap,
    get_trending_skills, recommend_projects. Conversation history is
    maintained per session_id (last 10 turns).
    """
    return agent_chat(
        message=body.message,
        session_id=body.session_id,
        user_skills=body.user_skills,
    )
