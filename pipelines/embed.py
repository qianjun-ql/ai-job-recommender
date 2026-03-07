"""
FR-03: Embedding + FAISS Index
Encodes all jobs with all-MiniLM-L6-v2 and builds a cosine-similarity FAISS index.

Input:
    data/processed/jobs_cleaned.csv
    data/processed/job_skills.json

Output:
    models/faiss_jobs.index   — FAISS IndexFlatIP (L2-normalised vectors → cosine sim)
    models/job_id_map.json    — list[dict] ordered by FAISS position; used at query time
    data/processed/.hashes/embed_inputs.sha256 — rebuild guard

Rebuild is skipped when both input files are unchanged (SHA-256 hash match).
"""

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
JOBS_CSV = settings.JOBS_CLEANED_CSV
JOB_SKILLS = settings.JOB_SKILLS
FAISS_INDEX = settings.FAISS_INDEX
JOB_ID_MAP = settings.JOB_ID_MAP
HASH_FILE = settings.PROCESSED_DIR / ".hashes" / "embed_inputs.sha256"
EMBEDDING_MODEL = settings.EMBEDDING_MODEL


# ── Hash helpers ──────────────────────────────────────────────────────────────


def _file_sha256(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _combined_hash() -> str:
    """Single hash representing both input files."""
    return _file_sha256(JOBS_CSV) + "|" + _file_sha256(JOB_SKILLS)


def _needs_rebuild() -> bool:
    """Return True if inputs changed since last build."""
    if not FAISS_INDEX.exists() or not JOB_ID_MAP.exists():
        return True
    if not HASH_FILE.exists():
        return True
    stored = HASH_FILE.read_text().strip()
    return stored != _combined_hash()


# ── Text builder ──────────────────────────────────────────────────────────────


def _build_job_text(role: str, title: str, skills: list[str]) -> str:
    """
    Construct the text fed to the sentence encoder.
    Format: "<role>: <title>. Skills: <skill1>, <skill2>, ..."
    Skills are sorted for determinism; limited to 60 to stay within model context.
    """
    skills_str = ", ".join(sorted(skills)[:60]) if skills else "none"
    return f"{role}: {title}. Skills: {skills_str}"


# ── Main ──────────────────────────────────────────────────────────────────────


def build_index() -> None:
    """Load jobs + skills, encode, build FAISS index, persist outputs."""

    if not _needs_rebuild():
        logger.info(
            "Input files unchanged — skipping rebuild. " "Delete models/faiss_jobs.index to force."
        )
        return

    # ── Load data ─────────────────────────────────────────────────────────────
    logger.info("Loading jobs_cleaned.csv …")
    df = pd.read_csv(JOBS_CSV, dtype=str).fillna("")
    logger.info(f"  {len(df):,} jobs loaded")

    logger.info("Loading job_skills.json …")
    job_skills: dict[str, list[str]] = json.loads(JOB_SKILLS.read_text())
    logger.info(f"  {len(job_skills):,} jobs have skill data")

    # ── Build text corpus ─────────────────────────────────────────────────────
    logger.info("Building job text representations …")
    job_id_map: list[dict[str, Any]] = []
    texts: list[str] = []

    for _, row in df.iterrows():
        jid = str(row["job_id"])
        skills: list[str] = job_skills.get(jid, [])
        text = _build_job_text(
            role=row.get("role", ""),
            title=row.get("title", ""),
            skills=skills,
        )
        texts.append(text)
        job_id_map.append(
            {
                "job_id": jid,
                "role": row.get("role", ""),
                "title": row.get("title", ""),
                "location": row.get("location", ""),
                "source": row.get("source", ""),
                "skills": skills,
                "snippet": row.get("description", "")[:300],  # for FR-08 RAG context
            }
        )

    logger.info(f"  {len(texts):,} texts built")

    # ── Encode ────────────────────────────────────────────────────────────────
    logger.info(f"Loading sentence encoder: {EMBEDDING_MODEL} …")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL)

    logger.info("Encoding job corpus (this takes ~1-3 min) …")
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=256,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # L2-normalise → inner product = cosine
    )
    logger.info(f"  Embeddings shape: {embeddings.shape}")

    # ── Build FAISS index ───────────────────────────────────────────────────
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine sim (vectors are already normalised)
    index.add(embeddings.astype(np.float32))
    logger.info(f"  FAISS index: {index.ntotal:,} vectors, dim={dim}")

    # ── Persist ───────────────────────────────────────────────────────────────
    FAISS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX))
    logger.info(f"  Saved → {FAISS_INDEX}")

    JOB_ID_MAP.write_text(json.dumps(job_id_map, ensure_ascii=False, indent=2))
    logger.info(f"  Saved → {JOB_ID_MAP}")

    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(_combined_hash())

    # ── Summary ───────────────────────────────────────────────────────────────
    role_counts: dict[str, int] = {}
    for j in job_id_map:
        role_counts[j["role"]] = role_counts.get(j["role"], 0) + 1
    logger.info("Jobs indexed by role:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        bar = "█" * int(count / len(job_id_map) * 40)
        logger.info(f"  {role:<25} {bar} {count:,}")

    with_skills = sum(1 for j in job_id_map if j["skills"])
    logger.info(
        f"FR-03: FAISS index built ✅  "
        f"({index.ntotal:,} vectors | {with_skills:,} jobs with skills | dim={dim})"
    )


if __name__ == "__main__":
    build_index()
