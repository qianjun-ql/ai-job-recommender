"""
FR-04: Semantic Job Matching
Embeds a user skill profile and retrieves the top-K most similar jobs
from the pre-built FAISS index.

Inputs:
    user_skills  — list of canonical skill strings
    role_filter  — optional target role (e.g. "ML Engineer")
    location     — optional city/region substring filter (case-insensitive)
    k            — number of results to return (default: settings.TOP_K_JOBS)

Outputs:
    list[JobMatchResponse] — sorted by match_score descending

Design principles:
    - Lazy-load: index + model loaded on first query call, not at import time
    - Stateless: no session state; safe under multi-worker FastAPI
    - Deterministic: same input → same output (no sampling)
    - Graceful: missing index file → clear error, not cryptic crash
"""

import json
import logging

import faiss
import numpy as np

from api.models import JobMatchResponse
from config.settings import settings

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ────────────────────────────────────────────────────
# Loaded once on first call, reused across all requests in the same process.

_index: faiss.IndexFlatIP | None = None
_job_id_map: list[dict] | None = None
_model: object | None = None  # SentenceTransformer


def _load_resources() -> tuple[faiss.IndexFlatIP, list[dict], object]:
    """
    Load FAISS index, job metadata map, and sentence encoder.
    Called once; results cached in module-level singletons.
    Raises FileNotFoundError if index or map is missing (run `make embed` first).
    """
    global _index, _job_id_map, _model

    if _index is not None and _job_id_map is not None and _model is not None:
        return _index, _job_id_map, _model

    if not settings.FAISS_INDEX.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {settings.FAISS_INDEX}\n" "Run: make embed"
        )
    if not settings.JOB_ID_MAP.exists():
        raise FileNotFoundError(f"Job ID map not found: {settings.JOB_ID_MAP}\n" "Run: make embed")

    logger.info("Loading FAISS index …")
    _index = faiss.read_index(str(settings.FAISS_INDEX))
    logger.info(f"  {_index.ntotal:,} vectors, dim={_index.d}")

    logger.info("Loading job_id_map …")
    _job_id_map = json.loads(settings.JOB_ID_MAP.read_text())
    logger.info(f"  {len(_job_id_map):,} job records")

    logger.info(f"Loading sentence encoder: {settings.EMBEDDING_MODEL} …")
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    logger.info("  Encoder ready ✅")

    return _index, _job_id_map, _model


# ── Query builder ─────────────────────────────────────────────────────────────


def _build_query_text(user_skills: list[str], role_filter: str | None) -> str:
    """
    Build the query string for the sentence encoder.
    Mirrors _build_job_text() in embed.py so the query lives in the same
    embedding space as the indexed documents.

    Format: "<role>: job candidate. Skills: <skill1>, <skill2>, ..."
    """
    role = role_filter or "job candidate"
    skills_str = ", ".join(sorted(user_skills)[:60]) if user_skills else "none"
    return f"{role}: job candidate. Skills: {skills_str}"


# ── Location filter ───────────────────────────────────────────────────────────


def _location_matches(job_location: str, location_filter: str) -> bool:
    """
    Case-insensitive substring match.
    "calgary" matches "Calgary, AB", "CALGARY", "Greater Calgary Area".
    """
    return location_filter.lower() in job_location.lower()


# ── Main entry point ──────────────────────────────────────────────────────────


def match_jobs(
    user_skills: list[str],
    role_filter: str | None = None,
    location: str | None = None,
    k: int | None = None,
) -> list[JobMatchResponse]:
    """
    Embed the user's skill profile and return the top-K most similar jobs.

    Args:
        user_skills:  Canonical skill names (e.g. ["Python", "AWS", "SQL"]).
                      Empty list returns lowest-confidence results — valid.
        role_filter:  Optional role enum ("ML Engineer", "AI Engineer", etc.).
                      Embedded into the query string for better alignment.
        location:     Optional location substring filter applied post-retrieval.
                      Filters are applied after fetching top-(k * LOCATION_OVERSAMPLE)
                      candidates to avoid returning fewer than k results when
                      most jobs don't match the location.
        k:            Number of results. Defaults to settings.TOP_K_JOBS (5).
                      Capped at 20 per US-02 acceptance criteria.

    Returns:
        list[JobMatchResponse] sorted by match_score descending.
        Empty list if index exists but nothing passes the location filter.

    Raises:
        FileNotFoundError: FAISS index or job_id_map not built yet.
        ValueError: k < 1 or k > 20.
    """
    k = k or settings.TOP_K_JOBS
    if not 1 <= k <= 20:
        raise ValueError(f"k must be between 1 and 20, got {k}")

    index, job_id_map, model = _load_resources()

    # ── Encode query ─────────────────────────────────────────────────────────
    query_text = _build_query_text(user_skills, role_filter)
    query_vec: np.ndarray = model.encode(
        [query_text],
        convert_to_numpy=True,
        normalize_embeddings=True,  # must match how index was built
    ).astype(np.float32)

    # ── FAISS search ─────────────────────────────────────────────────────────
    # Over-fetch when location filtering to avoid under-returning results.
    # 10× oversample: if only 5% of jobs are in target city we still fill k slots.
    LOCATION_OVERSAMPLE = 10 if location else 1
    fetch_k = min(k * LOCATION_OVERSAMPLE, index.ntotal)

    scores, indices = index.search(query_vec, fetch_k)
    raw_scores: list[float] = scores[0].tolist()
    raw_indices: list[int] = indices[0].tolist()

    # ── Build results ─────────────────────────────────────────────────────────
    results: list[JobMatchResponse] = []
    for score, idx in zip(raw_scores, raw_indices):
        if idx < 0:  # FAISS returns -1 for empty slots
            continue

        job = job_id_map[idx]

        # Role filter: skip jobs that don't match requested role
        if role_filter and job.get("role", "") != role_filter:
            continue

        # Location filter: substring match
        if location and not _location_matches(job.get("location", ""), location):
            continue

        results.append(
            JobMatchResponse(
                job_id=job["job_id"],
                title=job.get("title", ""),
                role=job.get("role", ""),
                location=job.get("location", ""),
                match_score=round(float(score), 4),
                skills=job.get("skills", []),
                snippet=job.get("snippet", ""),
            )
        )

        if len(results) >= k:
            break

    logger.debug(
        f"match_jobs: query={query_text[:60]!r}  "
        f"fetched={fetch_k}  returned={len(results)}  "
        f"location_filter={location!r}"
    )
    return results
