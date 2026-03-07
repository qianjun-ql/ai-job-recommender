"""
FR-05: Skill Gap Analysis

For a given target role, computes which skills are required (appear in
>= SKILL_FREQUENCY_THRESHOLD of role postings) and which of those the
user is missing.

Data sources:
    job_skills.json  — { job_id: [skill, ...] }   (NER extraction output)
    job_id_map.json  — [{ job_id, role, ... }]     (FAISS index metadata)

Design:
    - Role skill index built once on first call, cached in module scope
    - Skills normalised to lowercase for all comparisons
    - Obvious NER noise (## subwords, len < 3) filtered before indexing
    - 30% frequency threshold does the heavy noise filtering; rare junk
      tokens never hit the threshold across 2,000 jobs
"""

import json
import logging
from collections import Counter

from api.models import GapResult, Role, SkillDemand
from config.settings import settings

logger = logging.getLogger(__name__)

# ── Valid roles ───────────────────────────────────────────────────────────────

VALID_ROLES: frozenset[str] = frozenset(r.value for r in Role)

# ── Lazy-loaded role index ────────────────────────────────────────────────────
# Built once on first call.  Structure:
#   _role_skill_counts  { role -> Counter { skill_lower -> count } }
#   _role_job_counts    { role -> int }

_role_skill_counts: dict[str, Counter] | None = None
_role_job_counts: dict[str, int] | None = None


def _build_role_index() -> tuple[dict[str, Counter], dict[str, int]]:
    """
    Join job_skills.json and job_id_map.json to build a per-role skill
    frequency index.  Called once; results cached in module singletons.

    Raises:
        FileNotFoundError: if either data file is missing.
    """
    global _role_skill_counts, _role_job_counts

    if _role_skill_counts is not None and _role_job_counts is not None:
        return _role_skill_counts, _role_job_counts

    if not settings.JOB_SKILLS.exists():
        raise FileNotFoundError(
            f"job_skills.json not found: {settings.JOB_SKILLS}\n" "Run: make extract"
        )
    if not settings.JOB_ID_MAP.exists():
        raise FileNotFoundError(
            f"job_id_map.json not found: {settings.JOB_ID_MAP}\n" "Run: make embed"
        )

    logger.info("Building role skill index …")

    job_id_map: list[dict] = json.loads(settings.JOB_ID_MAP.read_text())
    job_skills: dict[str, list[str]] = json.loads(settings.JOB_SKILLS.read_text())

    # job_id -> role lookup (O(1) per lookup)
    id_to_role: dict[str, str] = {j["job_id"]: j["role"] for j in job_id_map}

    skill_counts: dict[str, Counter] = {}
    job_counts: dict[str, int] = {}

    for job_id, skills in job_skills.items():
        role = id_to_role.get(job_id)
        if not role:
            continue

        job_counts[role] = job_counts.get(role, 0) + 1

        if role not in skill_counts:
            skill_counts[role] = Counter()

        for skill in skills:
            if _is_indexable(skill):
                skill_counts[role][skill.lower()] += 1

    _role_skill_counts = skill_counts
    _role_job_counts = job_counts
    logger.info(f"  Role index built: {len(job_counts)} roles, " f"{sum(job_counts.values())} jobs")
    return _role_skill_counts, _role_job_counts


def _is_indexable(skill: str) -> bool:
    """
    Reject obvious NER noise before it enters the frequency index.
    The 30% threshold handles the rest — junk tokens don't span 600+ jobs.
    """
    if not skill or len(skill) < 3:
        return False
    if skill.startswith("##"):  # BERT subword tokens
        return False
    return True


# ── Required skills for a role ────────────────────────────────────────────────


def get_required_skills(
    role: str,
    threshold: float | None = None,
) -> list[SkillDemand]:
    """
    Return all skills that appear in >= threshold fraction of role postings,
    sorted by demand (highest first).

    Args:
        role:       Must be one of VALID_ROLES.
        threshold:  Frequency threshold (default: settings.SKILL_FREQUENCY_THRESHOLD = 0.30).

    Returns:
        list[SkillDemand] sorted by pct_of_jobs descending.

    Raises:
        ValueError: unknown role.
        FileNotFoundError: data files missing.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Unknown role {role!r}. Valid: {sorted(VALID_ROLES)}")

    threshold = threshold if threshold is not None else settings.SKILL_FREQUENCY_THRESHOLD

    skill_counts, job_counts = _build_role_index()
    total = job_counts.get(role, 0)
    if total == 0:
        return []

    counts = skill_counts.get(role, Counter())
    required = [
        SkillDemand(
            skill=skill,
            demand_count=count,
            pct_of_jobs=round(count / total, 4),
        )
        for skill, count in counts.items()
        if count / total >= threshold
    ]
    required.sort(key=lambda x: -x.pct_of_jobs)
    return required


# ── Main entry point ──────────────────────────────────────────────────────────


def compute_gap(
    user_skills: list[str],
    target_role: str,
    threshold: float | None = None,
) -> GapResult:
    """
    Compute the skill gap between a user's current skills and the skills
    required for a target role.

    Args:
        user_skills:  Canonical skill names — case-insensitive comparison.
        target_role:  One of VALID_ROLES.
        threshold:    Frequency threshold override (default 0.30).

    Returns:
        GapResult with matched_skills, missing_skills, match_score (0–100),
        total_required, and top_role_skills sorted by demand.

    Raises:
        ValueError: unknown role.
        FileNotFoundError: data files missing.
    """
    required: list[SkillDemand] = get_required_skills(target_role, threshold)

    # Normalise user skills to lowercase for case-insensitive comparison
    user_lower: set[str] = {s.lower().strip() for s in user_skills if s}

    matched: list[str] = []
    missing: list[str] = []

    for sd in required:
        if sd.skill in user_lower:
            matched.append(sd.skill)
        else:
            missing.append(sd.skill)

    total_required = len(required)
    match_score = round(len(matched) / total_required * 100, 2) if total_required else 0.0

    logger.debug(
        f"compute_gap: role={target_role!r} "
        f"required={total_required} matched={len(matched)} "
        f"score={match_score:.1f}%"
    )

    return GapResult(
        matched_skills=matched,
        missing_skills=missing,
        match_score=match_score,
        total_required=total_required,
        top_role_skills=required,  # already sorted by demand
        target_role=target_role,
    )


# ── Top-skills helper (for GET /top_skills/{role}) ───────────────────────────


def get_top_skills(role: str, n: int = 20) -> list[SkillDemand]:
    """
    Return the top-n most demanded skills for a role, regardless of user input.
    Used by the GET /top_skills/{role} endpoint.

    Args:
        role:  Must be one of VALID_ROLES.
        n:     Number of skills to return (default 20, capped at 50).
    """
    n = min(n, 50)
    return get_required_skills(role)[:n]
