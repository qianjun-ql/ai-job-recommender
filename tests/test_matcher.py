"""Tests for FR-04 — Semantic Job Matching (api/services/matcher.py).

All tests that touch _load_resources (FAISS index + encoder) mock that
function so no GPU, no disk index, and no SentenceTransformer download
are required.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from api.models import JobMatchResponse
from api.services.matcher import (
    _build_query_text,
    _location_matches,
    match_jobs,
    search_by_query,
    warmup,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

_SAMPLE_JOB_MAP: list[dict[str, Any]] = [
    {
        "job_id": "job_001",
        "title": "ML Engineer",
        "role": "ML Engineer",
        "location": "Calgary, AB",
        "skills": ["Python", "PyTorch"],
        "snippet": "Train production models.",
    },
    {
        "job_id": "job_002",
        "title": "AI Engineer",
        "role": "AI Engineer",
        "location": "Toronto, ON",
        "skills": ["Python", "TensorFlow"],
        "snippet": "Build AI pipelines.",
    },
    {
        "job_id": "job_003",
        "title": "Data Scientist",
        "role": "Data Scientist",
        "location": "Vancouver, BC",
        "skills": ["Python", "SQL"],
        "snippet": "Analyse datasets.",
    },
]


def _make_resources(
    scores: list[float] | None = None,
    indices: list[int] | None = None,
    n_jobs: int = 3,
) -> tuple[MagicMock, list[dict[str, Any]], MagicMock]:
    """
    Return (mock_index, job_id_map, mock_model) suitable for patching
    _load_resources.

    scores / indices default to returning all 3 sample jobs in order.
    The mock index.search respects the k argument (truncates results to k).
    """
    if scores is None:
        scores = [0.95, 0.88, 0.70]
    if indices is None:
        indices = list(range(len(_SAMPLE_JOB_MAP)))

    _scores = scores
    _indices = indices

    def _search(vec: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        s = _scores[:k]
        i = _indices[:k]
        return np.array([s], dtype=np.float32), np.array([i], dtype=np.int64)

    mock_index = MagicMock()
    mock_index.ntotal = n_jobs
    mock_index.search.side_effect = _search

    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((1, 384), dtype=np.float32)

    return mock_index, _SAMPLE_JOB_MAP[:n_jobs], mock_model


_PATCH = "api.services.matcher._load_resources"


# ── TestBuildQueryText ─────────────────────────────────────────────────────────


class TestBuildQueryText:
    def test_with_role_and_skills(self) -> None:
        text = _build_query_text(["Python", "SQL"], "ML Engineer")
        assert "ML Engineer" in text
        assert "Python" in text
        assert "SQL" in text

    def test_no_role_defaults_to_job_candidate(self) -> None:
        text = _build_query_text(["Python"], None)
        assert "job candidate" in text

    def test_empty_skills_shows_none(self) -> None:
        text = _build_query_text([], "ML Engineer")
        assert "none" in text

    def test_skills_are_sorted(self) -> None:
        text_ab = _build_query_text(["A", "B"], None)
        text_ba = _build_query_text(["B", "A"], None)
        assert text_ab == text_ba

    def test_long_skill_list_capped_at_60(self) -> None:
        skills = [f"Skill{i}" for i in range(100)]
        text = _build_query_text(skills, None)
        # Sort and take first 60, the rest should be absent
        sorted_skills = sorted(skills)
        for s in sorted_skills[:60]:
            assert s in text
        # At least one skill from the tail should be absent
        missing = [s for s in sorted_skills[60:] if s not in text]
        assert len(missing) > 0

    def test_query_format_prefix(self) -> None:
        """Query must start with '<role>: job candidate.' or 'job candidate:'."""
        text = _build_query_text(["Python"], "AI Engineer")
        assert text.startswith("AI Engineer:")


# ── TestLocationMatches ────────────────────────────────────────────────────────


class TestLocationMatches:
    def test_exact_match(self) -> None:
        assert _location_matches("Calgary", "Calgary")

    def test_case_insensitive(self) -> None:
        assert _location_matches("Calgary, AB", "calgary")
        assert _location_matches("CALGARY", "Calgary")

    def test_substring_match(self) -> None:
        assert _location_matches("Greater Calgary Area", "calgary")

    def test_no_match(self) -> None:
        assert not _location_matches("Toronto, ON", "calgary")

    def test_empty_filter_always_matches(self) -> None:
        # _location_matches is only called when location is not None/empty,
        # but defensive check: empty string is a substring of everything.
        assert _location_matches("Anywhere", "")

    def test_partial_city(self) -> None:
        assert _location_matches("San Francisco, CA", "san francisco")


# ── TestMatchJobs ──────────────────────────────────────────────────────────────


class TestMatchJobs:
    def test_returns_list_of_job_match_response(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"])
        assert isinstance(results, list)
        assert all(isinstance(r, JobMatchResponse) for r in results)

    def test_k_limits_results(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"], k=2)
        assert len(results) <= 2

    def test_k_negative_raises(self) -> None:
        """k=0 is falsy so silently converts to default; k=-1 is not."""
        with pytest.raises(ValueError, match="k must be between"):
            match_jobs(["Python"], k=-1)

    def test_k_above_20_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be between"):
            match_jobs(["Python"], k=21)

    def test_role_filter_excludes_non_matching_roles(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"], role_filter="ML Engineer")
        assert all(r.role == "ML Engineer" for r in results)

    def test_location_filter_applied(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"], location="Calgary")
        assert all("calgary" in r.location.lower() for r in results)

    def test_scores_in_valid_range(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"])
        for r in results:
            assert 0.0 <= r.match_score <= 1.0

    def test_scores_sorted_descending(self) -> None:
        resources = _make_resources(scores=[0.95, 0.70, 0.50])
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"])
        scores = [r.match_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_negative_faiss_index_skipped(self) -> None:
        """FAISS returns idx=-1 for empty slots; those must be skipped."""
        resources = _make_resources(scores=[0.9, 0.8, 0.7], indices=[0, -1, 2])
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"])
        assert all(r.job_id != "" for r in results)
        # idx -1 was skipped, so no invalid entry in results
        job_ids = {r.job_id for r in results}
        assert "job_001" in job_ids
        assert "job_003" in job_ids

    def test_empty_skills_still_returns_results(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs([])
        assert isinstance(results, list)

    def test_no_location_match_returns_empty(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"], location="Nowhere City")
        assert results == []

    def test_result_fields_populated(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = match_jobs(["Python"])
        r = results[0]
        assert r.job_id
        assert r.title
        assert r.role
        assert r.location
        assert isinstance(r.skills, list)
        assert isinstance(r.snippet, str)


# ── TestSearchByQuery ──────────────────────────────────────────────────────────


class TestSearchByQuery:
    def test_returns_list_of_job_match_response(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = search_by_query("machine learning engineer")
        assert isinstance(results, list)
        assert all(isinstance(r, JobMatchResponse) for r in results)

    def test_top_k_respected(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = search_by_query("ML jobs", top_k=2)
        assert len(results) <= 2

    def test_top_k_clamped_below_1(self) -> None:
        """top_k=0 should be clamped to 1, not raise."""
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = search_by_query("anything", top_k=0)
        assert isinstance(results, list)

    def test_top_k_clamped_above_20(self) -> None:
        """top_k=100 should be clamped to 20."""
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            # Mock index.search called with min(100, 20)=20
            results = search_by_query("anything", top_k=100)
        mock_index = resources[0]
        called_k = mock_index.search.call_args[0][1]
        assert called_k <= 20

    def test_negative_faiss_index_skipped(self) -> None:
        resources = _make_resources(scores=[0.9, 0.5], indices=[-1, 1])
        with patch(_PATCH, return_value=resources):
            results = search_by_query("test query")
        # idx=-1 skipped; only idx=1 (job_002) returned
        assert all(r.job_id != "" for r in results)

    def test_scores_in_valid_range(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = search_by_query("data science")
        for r in results:
            assert 0.0 <= r.match_score <= 1.0

    def test_empty_query_still_works(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            results = search_by_query("")
        assert isinstance(results, list)


# ── TestWarmup ─────────────────────────────────────────────────────────────────


class TestWarmup:
    def test_warmup_calls_load_resources(self) -> None:
        resources = _make_resources()
        with patch(_PATCH, return_value=resources) as mock_load:
            warmup()
        mock_load.assert_called_once()

    def test_warmup_is_idempotent(self) -> None:
        """Calling warmup() twice should not raise."""
        resources = _make_resources()
        with patch(_PATCH, return_value=resources):
            warmup()
            warmup()
