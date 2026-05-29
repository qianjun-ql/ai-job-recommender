"""
FR-09 — Proxy views: forward React requests to the FastAPI ML service.

React calls Django at /api/ml/*.
Django forwards to FastAPI (internal, not publicly exposed).
This shields FastAPI from the internet and allows adding auth middleware later.
"""

import logging

import httpx
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0  # seconds — chat can be slow due to LLM


def _fastapi_headers() -> dict[str, str]:
    """Headers forwarded to every FastAPI request."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.FASTAPI_API_KEY:
        headers["x-api-key"] = settings.FASTAPI_API_KEY
    return headers


def _proxy_post(path: str, data: dict) -> Response:
    """POST to FastAPI and return a DRF Response with the same status code."""
    url = f"{settings.FASTAPI_URL}{path}"
    try:
        r = httpx.post(url, json=data, headers=_fastapi_headers(), timeout=_TIMEOUT)
        return Response(r.json(), status=r.status_code)
    except httpx.TimeoutException:
        logger.error("FastAPI timeout: %s", url)
        return Response({"error": "ML service timed out. Please try again."}, status=504)
    except httpx.ConnectError:
        logger.error("FastAPI unreachable: %s", url)
        return Response({"error": "ML service unavailable. Is FastAPI running?"}, status=503)


def _proxy_get(path: str, params: dict | None = None) -> Response:
    """GET to FastAPI and return a DRF Response."""
    url = f"{settings.FASTAPI_URL}{path}"
    try:
        r = httpx.get(url, params=params, headers=_fastapi_headers(), timeout=_TIMEOUT)
        return Response(r.json(), status=r.status_code)
    except httpx.TimeoutException:
        return Response({"error": "ML service timed out."}, status=504)
    except httpx.ConnectError:
        return Response({"error": "ML service unavailable."}, status=503)


# ── Endpoints ─────────────────────────────────────────────────────────────────────


@api_view(["GET"])
def health(request: Request) -> Response:
    """Forward GET /health to FastAPI."""
    return _proxy_get("/health")


@api_view(["POST"])
def analyze(request: Request) -> Response:
    """Forward POST /analyze to FastAPI.

    Body: { skills: string[], target_role: string, location?: string }
    """
    return _proxy_post("/analyze", request.data)


@api_view(["POST"])
def chat(request: Request) -> Response:
    """Forward POST /chat to FastAPI.

    Body: { message: string, session_id: string, user_skills: string[] }
    """
    return _proxy_post("/chat", request.data)


@api_view(["GET"])
def top_skills(request: Request) -> Response:
    """Forward GET /top_skills to FastAPI.

    Params: role (required), limit (optional, default 20)
    """
    return _proxy_get("/top_skills", dict(request.query_params))


@api_view(["GET"])
def market_stats(request: Request) -> Response:
    """Forward GET /market_stats — landing page data, no auth required."""
    return _proxy_get("/market_stats", dict(request.query_params))


@api_view(["GET"])
def skills_by_role(request: Request) -> Response:
    """Forward GET /skills_by_role — top skills per role for compare chart."""
    return _proxy_get("/skills_by_role", dict(request.query_params))


@api_view(["POST"])
def extract_jd(request: Request) -> Response:
    """Forward POST /extract_jd — extract skills from raw job description text.

    Body: { text: string }
    Returns: { skills: string[], method: string, count: int }
    No auth required — used by the landing page.
    """
    return _proxy_post("/extract_jd", request.data)
