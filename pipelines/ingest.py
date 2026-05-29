"""
FR-01: Job Data Ingestion
Merges 9 datasets into one clean normalized CSV.

Input:
    data/raw/job_details/job_postings.csv
    data/raw/job_details/ai_ml_jobs_linkedin.csv
    data/raw/job_details/clean_jobs.csv
    data/raw/job_details/all_jobs.csv
    data/raw/job_details/jobs_dataset.csv
    data/raw/job_details/final_job_list.csv
    data/raw/job_details/data_science_jobs_indeed_usa.csv
    data/raw/job_details/postings.csv
    data/raw/job_details/1000_ml_jobs_us.csv

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
        "applied scientist",
        "ai specialist",
        "ai architect",
        "ai researcher",
        "gen ai",
        "genai",
        "ai/ml",
        "ml scientist",
        "conversational ai",
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
        "analytics engineer",
        "big data",
        "data warehouse",
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
    """Return SHA-256 of a file (streaming, memory-safe for large CSVs)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _has_changed(path: Path) -> bool:
    """Check if a file's hash differs from the stored value. Read-only — no side effects."""
    hash_file = settings.HASH_DIR / f"{path.stem}.sha256"
    if not hash_file.exists():
        return True
    return hash_file.read_text().strip() != file_hash(path)


def _commit_hashes(paths: list[Path]) -> None:
    """Persist current file hashes after a successful rebuild."""
    settings.HASH_DIR.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            (settings.HASH_DIR / f"{path.stem}.sha256").write_text(file_hash(path))


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


def load_all_jobs_csv() -> pd.DataFrame:
    """Load and normalize dataset 4 — all_jobs.csv (94k tech jobs, pre-cleaned descriptions)."""
    path = settings.CSV_ALL_JOBS
    if not path.exists():
        logger.warning(f"Optional dataset not found, skipping: {path.name}")
        return pd.DataFrame(columns=["job_id", "title", "description", "location", "source"])
    df = pd.read_csv(path, low_memory=False, encoding="latin1")
    # Use cleaned_description (already HTML-stripped) when available, fall back to description
    df["description"] = df["cleaned_description"].fillna(df["description"])
    df = df.rename(columns={"id": "job_id"})
    df = df[["job_id", "title", "description", "location"]].copy()
    df["job_id"] = "csv_" + df["job_id"].astype(str)
    df["source"] = "all_jobs_csv"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_jobs_dataset() -> pd.DataFrame:
    """Load and normalize jobs_dataset.csv (735 curated US tech jobs w/ salary)."""
    path = settings.JOBS_DATASET_CSV
    if not path.exists():
        logger.warning(f"Optional dataset not found, skipping: {path.name}")
        return pd.DataFrame(columns=["job_id", "title", "description", "location", "source"])
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(
        columns={"positionName": "title", "description": "description", "location": "location"}
    )
    df["job_id"] = "jd_" + df.index.astype(str)
    df = df[["job_id", "title", "description", "location"]].copy()
    df["source"] = "jobs_dataset"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_final_job_list() -> pd.DataFrame:
    """Load and normalize final_job_list.csv (692 curated jobs, strong Data Engineer coverage)."""
    path = settings.FINAL_JOB_LIST_CSV
    if not path.exists():
        logger.warning(f"Optional dataset not found, skipping: {path.name}")
        return pd.DataFrame(columns=["job_id", "title", "description", "location", "source"])
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(
        columns={"Title": "title", "Job Description": "description", "Location": "location"}
    )
    df["job_id"] = "fjl_" + df.index.astype(str)
    df = df[["job_id", "title", "description", "location"]].copy()
    df["source"] = "final_job_list"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_ds_jobs_indeed() -> pd.DataFrame:
    """Load and normalize data_science_jobs_indeed_usa.csv (1,200 Indeed jobs, strong DS/DE coverage)."""
    path = settings.DS_JOBS_INDEED_CSV
    if not path.exists():
        logger.warning(f"Optional dataset not found, skipping: {path.name}")
        return pd.DataFrame(columns=["job_id", "title", "description", "location", "source"])
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(columns={"Title": "title", "Description": "description", "Location": "location"})
    df["job_id"] = "dsi_" + df.index.astype(str)
    df = df[["job_id", "title", "description", "location"]].copy()
    df["source"] = "ds_jobs_indeed"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_postings() -> pd.DataFrame:
    """Load and normalize postings.csv (6,025 LinkedIn jobs, dominated by Data Engineer ~3,441 rows)."""
    path = settings.POSTINGS_CSV
    if not path.exists():
        logger.warning(f"Optional dataset not found, skipping: {path.name}")
        return pd.DataFrame(columns=["job_id", "title", "description", "location", "source"])
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(
        columns={"job_title": "title", "job_summary": "description", "job_location": "location"}
    )
    df["job_id"] = "post_" + df.index.astype(str)
    df = df[["job_id", "title", "description", "location"]].copy()
    df["source"] = "postings"
    logger.info(f"Loaded {len(df):,} rows from {path.name}")
    return df


def load_ml_jobs_us() -> pd.DataFrame:
    """Load and normalize 1000_ml_jobs_us.csv (997 US ML jobs, strong ML Engineer and AI Engineer coverage)."""
    path = settings.ML_JOBS_US_CSV
    if not path.exists():
        logger.warning(f"Optional dataset not found, skipping: {path.name}")
        return pd.DataFrame(columns=["job_id", "title", "description", "location", "source"])
    df = pd.read_csv(path, low_memory=False)
    df["location"] = (
        df["company_address_locality"].fillna("") + ", " + df["company_address_region"].fillna("")
    )
    df = df.rename(columns={"job_title": "title", "job_description_text": "description"})
    df["job_id"] = "mlj_" + df.index.astype(str)
    df = df[["job_id", "title", "description", "location"]].copy()
    df["source"] = "ml_jobs_us"
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

    _source_paths = [
        settings.JOB_POSTINGS_CSV,
        settings.AI_ML_JOBS_CSV,
        settings.CLEAN_JOBS_CSV,
        settings.CSV_ALL_JOBS,
        settings.JOBS_DATASET_CSV,
        settings.FINAL_JOB_LIST_CSV,
        settings.DS_JOBS_INDEED_CSV,
        settings.POSTINGS_CSV,
        settings.ML_JOBS_US_CSV,
    ]
    existing_sources = [p for p in _source_paths if p.exists()]
    sources_changed = any(_has_changed(p) for p in existing_sources)
    if not sources_changed and settings.JOBS_CLEANED_CSV.exists():
        logger.info("No dataset changes detected — returning cached output ✅")
        return pd.read_csv(settings.JOBS_CLEANED_CSV)

    # ── 1. Load all datasets ──────────────────────────────────────────────────
    try:
        df1 = load_job_postings()
        df2 = load_ai_ml_jobs()
        df3 = load_clean_jobs()
        df4 = load_all_jobs_csv()
        df5 = load_jobs_dataset()
        df6 = load_final_job_list()
        df7 = load_ds_jobs_indeed()
        df8 = load_postings()
        df9 = load_ml_jobs_us()
    except FileNotFoundError as e:
        logger.error(str(e))
        raise

    # ── 2. Merge ──────────────────────────────────────────────────────────────
    df = pd.concat([df1, df2, df3, df4, df5, df6, df7, df8, df9], ignore_index=True)
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
    # Vectorized: ~10x faster than apply(strip_html) on 10k rows
    df["description"] = (
        df["description"]
        .str.replace(r"<[^>]+>", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

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

    _commit_hashes(existing_sources)
    logger.info("FR-01: Ingestion complete ✅")
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    ingest()
