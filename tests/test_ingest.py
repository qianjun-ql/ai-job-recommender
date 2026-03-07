"""Tests for FR-01 — Job Data Ingestion."""

from pathlib import Path

import pandas as pd
import pytest

from config.settings import settings
from pipelines.ingest import ingest, normalize_role, strip_html


class TestStripHtml:
    def test_removes_bold_tags(self):
        assert strip_html("<b>Python</b>") == "Python"

    def test_removes_nested_tags(self):
        assert strip_html("<div><p>Hello</p></div>") == "Hello"

    def test_collapses_whitespace(self):
        assert strip_html("hello   world") == "hello world"

    def test_handles_empty_string(self):
        assert strip_html("") == ""

    def test_plain_text_unchanged(self):
        assert strip_html("Python Developer") == "Python Developer"


class TestNormalizeRole:
    def test_swe_match(self):
        assert normalize_role("Senior Software Engineer") == "SWE"

    def test_ml_engineer_match(self):
        assert normalize_role("Machine Learning Engineer") == "ML Engineer"

    def test_data_scientist_match(self):
        assert normalize_role("Data Scientist II") == "Data Scientist"

    def test_ai_engineer_match(self):
        assert normalize_role("AI Engineer - NLP") == "AI Engineer"

    def test_data_engineer_match(self):
        assert normalize_role("Senior Data Engineer") == "Data Engineer"

    def test_no_match_returns_none(self):
        assert normalize_role("Underwater Basket Weaver") is None

    def test_case_insensitive(self):
        assert normalize_role("MACHINE LEARNING ENGINEER") == "ML Engineer"


class TestIngestOutput:
    def test_output_file_exists(self):
        assert settings.JOBS_CLEANED_CSV.exists()

    def test_no_nulls_in_required_columns(self):
        df = pd.read_csv(settings.JOBS_CLEANED_CSV)
        assert df["description"].isna().sum() == 0
        assert df["title"].isna().sum() == 0
        assert df["role"].isna().sum() == 0

    def test_all_roles_valid(self):
        valid_roles = {
            "ML Engineer",
            "Data Scientist",
            "AI Engineer",
            "Data Engineer",
            "SWE",
        }
        df = pd.read_csv(settings.JOBS_CLEANED_CSV)
        assert set(df["role"].unique()).issubset(valid_roles)

    def test_minimum_row_count(self):
        df = pd.read_csv(settings.JOBS_CLEANED_CSV)
        assert len(df) >= 10000  # PRD requirement: ≥ 10,000 rows

    def test_no_duplicate_job_ids(self):
        df = pd.read_csv(settings.JOBS_CLEANED_CSV)
        assert df["job_id"].duplicated().sum() == 0
