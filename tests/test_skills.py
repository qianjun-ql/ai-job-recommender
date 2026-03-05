"""Tests for FR-02 — Skill Extraction."""

import json
from pathlib import Path

import pandas as pd
import pytest

from pipelines.extract_skills import compute_frequency, extract, extract_skills


class TestExtractSkills:
    def test_detects_python(self):
        assert "Python" in extract_skills("We need python developers")

    def test_detects_pytorch(self):
        assert "PyTorch" in extract_skills("Experience with PyTorch required")

    def test_detects_aws(self):
        assert "AWS" in extract_skills("Deploy to AWS SageMaker")

    def test_detects_docker(self):
        assert "Docker" in extract_skills("Must know Docker and Kubernetes")

    def test_detects_multiple_skills(self):
        skills = extract_skills("Python, PyTorch, Docker, AWS, SQL experience required")
        assert len(skills) >= 4

    def test_empty_description_returns_empty(self):
        assert extract_skills("") == []

    def test_case_insensitive(self):
        assert "Python" in extract_skills("PYTHON DEVELOPER NEEDED")

    def test_no_false_positives(self):
        skills = extract_skills("We sell handmade wooden furniture")
        assert skills == []


class TestComputeFrequency:
    def test_returns_dataframe(self):
        job_skills = {"j1": ["Python", "SQL"], "j2": ["Python", "Docker"]}
        df = compute_frequency(job_skills, total_jobs=2)
        assert isinstance(df, pd.DataFrame)

    def test_python_most_common(self):
        job_skills = {"j1": ["Python", "SQL"], "j2": ["Python", "Docker"]}
        df = compute_frequency(job_skills, total_jobs=2)
        assert df.iloc[0]["skill"] == "Python"

    def test_pct_correct(self):
        job_skills = {"j1": ["Python"], "j2": ["Python"], "j3": ["SQL"]}
        df = compute_frequency(job_skills, total_jobs=3)
        python_row = df[df["skill"] == "Python"].iloc[0]
        assert python_row["pct_of_jobs"] == round(2 / 3, 4)


class TestExtractOutput:
    def test_job_skills_file_exists(self):
        assert Path("data/processed/job_skills.json").exists()

    def test_skill_frequency_file_exists(self):
        assert Path("data/processed/skill_frequency.csv").exists()

    def test_job_skills_not_empty(self):
        data = json.loads(Path("data/processed/job_skills.json").read_text())
        assert len(data) > 0

    def test_minimum_unique_skills(self):
        df = pd.read_csv("data/processed/skill_frequency.csv")
        assert len(df) >= 20

    def test_pct_between_0_and_1(self):
        df = pd.read_csv("data/processed/skill_frequency.csv")
        assert df["pct_of_jobs"].between(0, 1).all()
