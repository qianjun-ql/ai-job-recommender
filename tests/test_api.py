"""Tests for FR-07 — REST API layer.

Uses FastAPI TestClient (HTTPX under the hood).  The lifespan warmup and
heavy service calls are mocked so tests run without a GPU or Gemini key.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.models import (
    AnalyzeResponse,
    ChatResponse,
    GapResult,
    JobMatchResponse,
    ProjectResponse,
    SkillDemand,
)

# ── Patch warmup at import time so FAISS is not loaded during test collection ─

_WARMUP = "api.services.matcher.warmup"


@pytest.fixture(scope="module")
def client():
    with patch(_WARMUP):
        from api.main import app

        with TestClient(app) as c:
            yield c


# ── Shared mock data ──────────────────────────────────────────────────────────

_JOB = JobMatchResponse(
    job_id="job_001",
    title="ML Engineer",
    role="ML Engineer",
    location="Calgary, AB",
    match_score=0.92,
    skills=["Python", "PyTorch"],
    snippet="Build production ML systems.",
)

_GAP = GapResult(
    matched_skills=["Python"],
    missing_skills=["PyTorch", "Docker"],
    match_score=33.3,
    total_required=3,
    top_role_skills=[SkillDemand(skill="Python", demand_count=500, pct_of_jobs=0.75)],
    target_role="ML Engineer",
)

_PROJECT = ProjectResponse(
    title="PyTorch Image Classifier",
    description="Train a CNN on CIFAR-10 using PyTorch.",
    skills_addressed=["PyTorch"],
    difficulty="Intermediate",
    estimated_hours=20,
)


# ── GET /health ───────────────────────────────────────────────────────────────


class TestHealth:
    def test_returns_200(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200

    def test_status_ok(self, client: TestClient):
        body = client.get("/health").json()
        assert body["status"] == "ok"

    def test_response_schema(self, client: TestClient):
        body = client.get("/health").json()
        assert "status" in body
        assert "version" in body
        assert "dataset_rows" in body
        assert "index_size" in body

    def test_dataset_rows_positive(self, client: TestClient):
        body = client.get("/health").json()
        assert body["dataset_rows"] > 0


# ── GET /top_skills ───────────────────────────────────────────────────────────


class TestTopSkills:
    def test_valid_role_returns_200(self, client: TestClient):
        r = client.get("/top_skills", params={"role": "ML Engineer"})
        assert r.status_code == 200

    def test_invalid_role_returns_422(self, client: TestClient):
        r = client.get("/top_skills", params={"role": "Rocket Scientist"})
        assert r.status_code == 422

    def test_422_uses_error_envelope(self, client: TestClient):
        r = client.get("/top_skills", params={"role": "Rocket Scientist"})
        body = r.json()
        assert "error" in body
        assert "message" in body
        assert "request_id" in body

    def test_response_has_skills_list(self, client: TestClient):
        body = client.get("/top_skills", params={"role": "ML Engineer"}).json()
        assert "skills" in body
        assert isinstance(body["skills"], list)

    def test_limit_param_respected(self, client: TestClient):
        body = client.get("/top_skills", params={"role": "ML Engineer", "limit": 3}).json()
        assert len(body["skills"]) <= 3

    def test_role_echoed_in_response(self, client: TestClient):
        body = client.get("/top_skills", params={"role": "Data Scientist"}).json()
        assert body["role"] == "Data Scientist"

    def test_skill_fields_present(self, client: TestClient):
        body = client.get("/top_skills", params={"role": "ML Engineer", "limit": 1}).json()
        if body["skills"]:
            skill = body["skills"][0]
            assert "skill" in skill
            assert "demand_count" in skill
            assert "pct_of_jobs" in skill


# ── POST /analyze ─────────────────────────────────────────────────────────────


class TestAnalyze:
    @pytest.fixture
    def mocked_analyze(self, client: TestClient):
        """Patch all three service calls so /analyze never touches FAISS or Gemini."""
        with (
            patch("api.main.match_jobs", return_value=[_JOB]),
            patch("api.main.compute_gap", return_value=_GAP),
            patch("api.main.recommend_projects", return_value=[_PROJECT]),
        ):
            yield client

    def test_valid_request_returns_200(self, mocked_analyze: TestClient):
        r = mocked_analyze.post(
            "/analyze",
            json={"skills": ["Python"], "target_role": "ML Engineer"},
        )
        assert r.status_code == 200

    def test_response_schema(self, mocked_analyze: TestClient):
        body = mocked_analyze.post(
            "/analyze",
            json={"skills": ["Python"], "target_role": "ML Engineer"},
        ).json()
        assert "top_jobs" in body
        assert "matched_skills" in body
        assert "missing_skills" in body
        assert "match_score" in body
        assert "projects" in body

    def test_missing_skills_returns_422(self, client: TestClient):
        r = client.post("/analyze", json={"target_role": "ML Engineer"})
        assert r.status_code == 422

    def test_missing_role_returns_422(self, client: TestClient):
        r = client.post("/analyze", json={"skills": ["Python"]})
        assert r.status_code == 422

    def test_invalid_role_returns_422(self, client: TestClient):
        r = client.post("/analyze", json={"skills": ["Python"], "target_role": "Wizard"})
        assert r.status_code == 422

    def test_422_uses_error_envelope(self, client: TestClient):
        r = client.post("/analyze", json={})
        body = r.json()
        assert body["error"] == "VALIDATION_ERROR"
        assert "request_id" in body

    def test_empty_skills_list_returns_422(self, client: TestClient):
        r = client.post("/analyze", json={"skills": [], "target_role": "ML Engineer"})
        assert r.status_code == 422

    def test_top_jobs_contains_job_id(self, mocked_analyze: TestClient):
        body = mocked_analyze.post(
            "/analyze",
            json={"skills": ["Python"], "target_role": "ML Engineer"},
        ).json()
        assert body["top_jobs"][0]["job_id"] == "job_001"

    def test_projects_contains_skills_addressed(self, mocked_analyze: TestClient):
        body = mocked_analyze.post(
            "/analyze",
            json={"skills": ["Python"], "target_role": "ML Engineer"},
        ).json()
        assert "PyTorch" in body["projects"][0]["skills_addressed"]


# ── POST /chat ────────────────────────────────────────────────────────────────


class TestChat:
    _CHAT_RESPONSE = ChatResponse(
        answer="You need PyTorch and Docker for ML Engineer roles.",
        sources=["job_001", "job_002"],
        tool_calls_made=["search_jobs", "get_skill_gap"],
        session_id="test-session",
    )

    @pytest.fixture
    def mocked_chat(self, client: TestClient):
        with patch("api.main.agent_chat", return_value=self._CHAT_RESPONSE):
            yield client

    def test_valid_request_returns_200(self, mocked_chat: TestClient):
        r = mocked_chat.post(
            "/chat",
            json={
                "message": "What skills do I need?",
                "session_id": "test-session",
                "user_skills": ["Python"],
            },
        )
        assert r.status_code == 200

    def test_response_schema(self, mocked_chat: TestClient):
        body = mocked_chat.post(
            "/chat",
            json={"message": "What skills do I need?", "session_id": "abc"},
        ).json()
        assert "answer" in body
        assert "sources" in body
        assert "tool_calls_made" in body
        assert "session_id" in body

    def test_missing_message_returns_422(self, client: TestClient):
        r = client.post("/chat", json={"session_id": "abc"})
        assert r.status_code == 422

    def test_missing_session_id_returns_422(self, client: TestClient):
        r = client.post("/chat", json={"message": "hello"})
        assert r.status_code == 422

    def test_sources_is_list(self, mocked_chat: TestClient):
        body = mocked_chat.post(
            "/chat",
            json={"message": "hello", "session_id": "abc"},
        ).json()
        assert isinstance(body["sources"], list)

    def test_session_id_echoed(self, client: TestClient):
        # Use side_effect so the mock reflects the session_id from each request
        def _echo(message: str, session_id: str, user_skills: list) -> ChatResponse:
            return ChatResponse(answer="ok", sources=[], tool_calls_made=[], session_id=session_id)

        with patch("api.main.agent_chat", side_effect=_echo):
            body = client.post(
                "/chat",
                json={"message": "hello", "session_id": "my-session-42"},
            ).json()
        assert body["session_id"] == "my-session-42"
