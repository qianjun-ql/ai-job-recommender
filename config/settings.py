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
    CSV_ALL_JOBS: Path = RAW_DIR / "all_jobs.csv"
    JOBS_DATASET_CSV: Path = RAW_DIR / "jobs_dataset.csv"
    FINAL_JOB_LIST_CSV: Path = RAW_DIR / "final_job_list.csv"
    DS_JOBS_INDEED_CSV: Path = RAW_DIR / "data_science_jobs_indeed_usa.csv"
    POSTINGS_CSV: Path = RAW_DIR / "postings.csv"
    ML_JOBS_US_CSV: Path = RAW_DIR / "1000_ml_jobs_us.csv"

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
    NER_STOPWORDS: Path = MODELS_DIR / "ner_stopwords.json"
    PROJECTS_CACHE: Path = MODELS_DIR / "projects_cache.json"
    JOB_SKILLS: Path = PROCESSED_DIR / "job_skills.json"
    SKILL_FREQUENCY: Path = PROCESSED_DIR / "skill_frequency.csv"

    # ── ML settings ───────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    TOP_K_JOBS: int = 5
    SKILL_FREQUENCY_THRESHOLD: float = 0.30
    ROLE_CAP: int = 2000
    JOBBERT_BATCH_SIZE: int = 8  # keep small to avoid MPS OOM during inference

    # Minimum number of jobs a novel (NER-detected) skill must appear in to be kept.
    # Filters low-frequency noise from the NER output.
    NOVEL_SKILL_MIN_FREQUENCY: int = 10

    # ── API settings ──────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_VERSION: str = "1.0.0"
    # Optional API key — if set, all endpoints require X-API-Key header.
    # Leave empty to disable auth (local dev / demo mode).
    API_KEY: str = ""
    LLM_TIMEOUT: int = 10

    # ── Secrets (from .env) ───────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    # Primary model — gemini-2.0-flash-lite has 1500 req/day on free tier.
    # Fallbacks tried in order on RESOURCE_EXHAUSTED (429).
    GEMINI_MODEL: str = "gemini-2.0-flash-lite"
    GEMINI_FALLBACK_MODELS: list[str] = [
        "gemini-1.5-flash",
        "gemini-2.0-flash",
    ]

    # Groq fallback — 14 400 req/day free, tried after all Gemini models fail.
    # Get a free key at https://console.groq.com
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Langfuse observability (optional; pipeline runs without these set)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
