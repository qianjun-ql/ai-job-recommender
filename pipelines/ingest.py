"""
FR-01: Job Data Ingestion
Merges 3 datasets into one clean normalized CSV.

Input:
    data/raw/job_details/job_postings.csv
    data/raw/job_details/ai_ml_jobs_linkedin.csv
    data/raw/job_details/clean_jobs.csv

Output:
    data/processed/jobs_cleaned.csv
    data/processed/ingestion_report.json
"""

import hashlib
import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

# ── Make project root importable ──────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Role normalization map ────────────────────────────────────────────────────
ROLE_KEYWORDS: dict[str, list[str]] = {
    "ML Engineer": [
        "machine learning",
        "ml engineer",
        "mlops",
        "ml ops",
        "model engineer",
    ],
    "Data Scientist": [
        "data scientist",
        "data science",
        "data analyst",
        "business analyst",
        "analytics engineer",
        "quantitative",
        "research scientist",
    ],
    "AI Engineer": [
        "ai engineer",
        "artificial intelligence",
        "llm",
        "nlp",
        "computer vision",
        "deep learning",
        "generative ai",
        "prompt engineer",
    ],
    "Data Engineer": [
        "data engineer",
        "data pipeline",
        "etl",
        "data platform",
        "databricks",
        "spark",
        "data architect",
        "data infrastructure",
    ],
    "SWE": [
        "software engineer",
        "software developer",
        "backend",
        "frontend",
        "fullstack",
        "full stack",
        "full-stack",
        "web developer",
        "devops",
        "platform engineer",
        "cloud engineer",
        "site reliability",
        "sre",
        "python developer",
        "java developer",
        "engineer",
        "developer",
        "programmer",
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize_role(title: str) -> str | None:
    """Map a raw job title to a canonical role enum. Returns None if no match."""
    t = title.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return role
    return None


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", str(text))
    return re.sub(r"\s+", " ", text).strip()


def file_hash(path: Path) -> str:
    """Return MD5 hash of a file for change detection."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def dataset_changed(path: Path) -> bool:
    """Return True if file has changed since last ingest run."""
    hash_file = settings.HASH_DIR / f"{path.stem}.md5"
    settings.HASH_DIR.mkdir(parents=True, exist_ok=True)
    current = file_hash(path)
    if hash_file.exists() and hash_file.read_text() == current:
        logger.info(f"No changes detected in {path.name} — skipping")
        return False
    hash_file.write_text(current)
    return True


# ── Loaders ───────────────────────────────────────────────────────────────────
def load_job_postings() -> pd.DataFrame:
    """Load and normalize dataset 1 — LinkedIn job postings."""
    path = settings.JOB_POSTINGS_CSV
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    df = df[["job_id", "title", "description", "location"]].copy()
    df["source"] = "linkedin_postings"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_ai_ml_jobs() -> pd.DataFrame:
    """Load and normalize dataset 2 — AI/ML focused LinkedIn jobs."""
    path = settings.AI_ML_JOBS_CSV
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    df = df[["title", "description", "location"]].copy()
    df["job_id"] = "aiml_" + df.index.astype(str)
    df["source"] = "ai_ml_linkedin"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_clean_jobs() -> pd.DataFrame:
    """Load and normalize dataset 3 — general tech jobs."""
    path = settings.CLEAN_JOBS_CSV
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(columns={"id": "job_id"})
    df = df[["job_id", "title", "description", "location"]].copy()
    df["job_id"] = "clean_" + df["job_id"].astype(str)
    df["source"] = "clean_jobs"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


# ── Main pipeline ─────────────────────────────────────────────────────────────
def ingest() -> pd.DataFrame:
    """
    Run the full ingestion pipeline.
    Returns the cleaned DataFrame.
    """
    logger.info("═" * 60)
    logger.info("FR-01: Starting ingestion pipeline")
    logger.info("═" * 60)

    sources_changed = any(
        [
            dataset_changed(settings.JOB_POSTINGS_CSV),
            dataset_changed(settings.AI_ML_JOBS_CSV),
            dataset_changed(settings.CLEAN_JOBS_CSV),
        ]
    )
    if not sources_changed and settings.JOBS_CLEANED_CSV.exists():
        logger.info("No dataset changes detected — returning cached output ✅")
        return pd.read_csv(settings.JOBS_CLEANED_CSV)

    # ── 1. Load all 3 datasets ────────────────────────────────────────────────
    try:
        df1 = load_job_postings()
        df2 = load_ai_ml_jobs()
        df3 = load_clean_jobs()
    except FileNotFoundError as e:
        logger.error(str(e))
        raise

    # ── 2. Merge ──────────────────────────────────────────────────────────────
    df = pd.concat([df1, df2, df3], ignore_index=True)
    raw_count = len(df)
    logger.info(f"Combined total: {raw_count:,} rows")

    # ── 3. Drop nulls ─────────────────────────────────────────────────────────
    df.dropna(subset=["description", "title"], inplace=True)
    logger.info(f"After null drop: {len(df):,} rows")

    # ── 4. Deduplicate ────────────────────────────────────────────────────────
    before_dedup = len(df)
    df.drop_duplicates(subset=["job_id"], inplace=True)
    dupe_count = before_dedup - len(df)
    logger.info(f"Removed {dupe_count:,} duplicates — {len(df):,} remain")

    # ── 5. Strip HTML ─────────────────────────────────────────────────────────
    df["description"] = df["description"].apply(strip_html)

    # ── 6. Normalize roles ────────────────────────────────────────────────────
    df["job_text"] = df["title"] + " " + df["description"].str[:300]
    df["role"] = df["job_text"].apply(normalize_role)
    df.drop(columns=["job_text"], inplace=True)
    unmatched = df["role"].isna().sum()
    df.dropna(subset=["role"], inplace=True)
    logger.info(f"Unmatched roles dropped: {unmatched:,} — {len(df):,} remain")

    # ── 7. Balance dataset ────────────────────────────────────────────────────
    df = (
        df.groupby("role")
        .apply(
            lambda x: x.sample(min(len(x), settings.ROLE_CAP), random_state=42),
            include_groups=False,
        )
        .reset_index(level=0)  # brings 'role' back as a column
        .reset_index(drop=True)
    )

    # ── 8. Save output ────────────────────────────────────────────────────────
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.JOBS_CLEANED_CSV, index=False)
    logger.info(f"Saved → {settings.JOBS_CLEANED_CSV}")

    # ── 9. Write report ───────────────────────────────────────────────────────
    report = {
        "raw_rows": raw_count,
        "final_rows": len(df),
        "dupe_count": dupe_count,
        "role_counts": df["role"].value_counts().to_dict(),
        "source_counts": df["source"].value_counts().to_dict(),
    }
    settings.INGESTION_REPORT.write_text(json.dumps(report, indent=2))
    logger.info(f"Report → {settings.INGESTION_REPORT}")

    logger.info("Role breakdown:")
    for role, count in report["role_counts"].items():
        logger.info(f"  {role:25} {count:,}")

    logger.info("Source breakdown:")
    for source, count in report["source_counts"].items():
        logger.info(f"  {source:25} {count:,}")

    logger.info("FR-01: Ingestion complete ✅")
    return df


if __name__ == "__main__":
    ingest()
