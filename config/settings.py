"""
Central configuration — all paths and env vars live here.
Never hardcode paths in pipeline files.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Project root ──────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent.parent

    # ── Raw data ──────────────────────────────────────────────────────────────
    RAW_DIR: Path = BASE_DIR / "data" / "raw" / "job_details"
    JOB_POSTINGS_CSV: Path = RAW_DIR / "job_postings.csv"
    AI_ML_JOBS_CSV: Path = RAW_DIR / "ai_ml_jobs_linkedin.csv"
    CLEAN_JOBS_CSV: Path = RAW_DIR / "clean_jobs.csv"

    # ── Processed data ────────────────────────────────────────────────────────
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    JOBS_CLEANED_CSV: Path = PROCESSED_DIR / "jobs_cleaned.csv"
    INGESTION_REPORT: Path = PROCESSED_DIR / "ingestion_report.json"
    HASH_DIR: Path = PROCESSED_DIR / ".hashes"

    # ── Models ────────────────────────────────────────────────────────────────
    MODELS_DIR: Path = BASE_DIR / "models"
    FAISS_INDEX: Path = MODELS_DIR / "faiss_jobs.index"
    JOB_ID_MAP: Path = MODELS_DIR / "job_id_map.json"
    SKILLS_DICT: Path = MODELS_DIR / "skills_dictionary.json"
    PROJECTS_CACHE: Path = MODELS_DIR / "projects_cache.json"
    JOB_SKILLS: Path = PROCESSED_DIR / "job_skills.json"
    SKILL_FREQUENCY: Path = PROCESSED_DIR / "skill_frequency.csv"

    # ── ML settings ───────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    TOP_K_JOBS: int = 5
    SKILL_FREQUENCY_THRESHOLD: float = 0.30
    ROLE_CAP: int = 2000

    # ── API settings ──────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LLM_TIMEOUT: int = 10

    # ── Secrets (from .env) ───────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
