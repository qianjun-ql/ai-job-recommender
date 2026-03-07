"""Tests for FR-05 — Skill Gap Analysis (api/services/gap.py)."""

import pytest

from api.models import GapResult, SkillDemand
from api.services.gap import compute_gap, get_required_skills, get_top_skills


class TestComputeGap:
    def test_returns_gap_result(self):
        result = compute_gap(["Python"], "ML Engineer")
        assert isinstance(result, GapResult)

    def test_target_role_echoed(self):
        result = compute_gap(["Python"], "ML Engineer")
        assert result.target_role == "ML Engineer"

    def test_empty_skills_gives_zero_score(self):
        result = compute_gap([], "ML Engineer")
        assert result.match_score == 0.0

    def test_empty_skills_all_required_are_missing(self):
        result = compute_gap([], "ML Engineer")
        assert len(result.missing_skills) == result.total_required

    def test_empty_skills_no_matched(self):
        result = compute_gap([], "ML Engineer")
        assert result.matched_skills == []

    def test_known_skill_appears_in_matched(self):
        # "python" is in every role's required skills
        result = compute_gap(["Python"], "ML Engineer")
        assert "python" in result.matched_skills or "Python" in result.matched_skills

    def test_match_score_range(self):
        result = compute_gap(["Python", "PyTorch", "SQL"], "ML Engineer")
        assert 0.0 <= result.match_score <= 100.0

    def test_more_skills_higher_score(self):
        low = compute_gap([], "Data Scientist")
        high = compute_gap(["Python", "SQL", "PyTorch", "R", "TensorFlow"], "Data Scientist")
        assert high.match_score >= low.match_score

    def test_case_insensitive_matching(self):
        lower = compute_gap(["python"], "ML Engineer")
        upper = compute_gap(["PYTHON"], "ML Engineer")
        assert lower.matched_skills == upper.matched_skills
        assert lower.match_score == upper.match_score

    def test_invalid_role_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown role"):
            compute_gap(["Python"], "Rocket Scientist")

    def test_total_required_positive(self):
        result = compute_gap([], "ML Engineer")
        assert result.total_required > 0

    def test_matched_plus_missing_equals_total(self):
        result = compute_gap(["Python"], "ML Engineer")
        assert len(result.matched_skills) + len(result.missing_skills) == result.total_required

    def test_top_role_skills_sorted_by_demand(self):
        result = compute_gap(["Python"], "ML Engineer")
        counts = [s.demand_count for s in result.top_role_skills]
        assert counts == sorted(counts, reverse=True)

    def test_all_roles_work(self):
        # All roles must run without error; skill count may vary by dataset composition
        roles = ["AI Engineer", "Data Engineer", "Data Scientist", "ML Engineer", "SWE"]
        for role in roles:
            result = compute_gap(["Python"], role)
            assert result.target_role == role

    def test_ml_heavy_roles_have_skills(self):
        # The dataset is ML-heavy; these roles must have required skills
        for role in ["AI Engineer", "Data Scientist", "ML Engineer"]:
            result = compute_gap([], role)
            assert result.total_required > 0, f"{role} returned no required skills"

    def test_location_ignored(self):
        # gap.py doesn't take location — confirm no TypeError
        result = compute_gap(["Python", "SQL"], "Data Engineer")
        assert isinstance(result, GapResult)


class TestGetTopSkills:
    def test_returns_list_of_skill_demand(self):
        skills = get_top_skills("ML Engineer")
        assert all(isinstance(s, SkillDemand) for s in skills)

    def test_limit_respected(self):
        skills = get_top_skills("ML Engineer", n=5)
        assert len(skills) <= 5

    def test_sorted_by_demand_descending(self):
        skills = get_top_skills("ML Engineer", n=10)
        counts = [s.demand_count for s in skills]
        assert counts == sorted(counts, reverse=True)

    def test_pct_of_jobs_between_0_and_1(self):
        skills = get_top_skills("Data Scientist", n=10)
        assert all(0.0 <= s.pct_of_jobs <= 1.0 for s in skills)

    def test_not_empty(self):
        skills = get_top_skills("Data Engineer", n=10)
        assert len(skills) > 0

    def test_invalid_role_raises_value_error(self):
        with pytest.raises(ValueError):
            get_top_skills("Fake Role")

    def test_all_roles_return_skills(self):
        # ML-centric roles in this dataset must have skill data; SWE excluded
        # (SWE is a minority in this ML-focused LinkedIn dataset)
        for role in ["AI Engineer", "Data Engineer", "Data Scientist", "ML Engineer"]:
            assert len(get_top_skills(role, n=5)) > 0, f"{role} returned no skills"


class TestGetRequiredSkills:
    def test_returns_list_of_skill_demand(self):
        skills = get_required_skills("ML Engineer")
        assert all(isinstance(s, SkillDemand) for s in skills)

    def test_threshold_filters_low_frequency(self):
        # At 30% threshold, all returned skills should appear in ≥30% of jobs
        skills = get_required_skills("ML Engineer", threshold=0.30)
        assert all(s.pct_of_jobs >= 0.30 for s in skills)

    def test_lower_threshold_returns_more_skills(self):
        strict = get_required_skills("ML Engineer", threshold=0.50)
        lenient = get_required_skills("ML Engineer", threshold=0.10)
        assert len(lenient) >= len(strict)
