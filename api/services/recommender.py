"""
FR-06: LLM Project Recommendations

Generates 2–5 personalised portfolio project ideas using Gemini 2.0 Flash.
Each project targets at least one missing skill and is completable in ≤40 hours.

On any LLM failure (timeout, API error, bad JSON): falls back to
models/projects_cache.json — no 500s ever reach the user.

Prompt template (from CLAUDE.md):
    system: "You are a senior ML engineer. Return ONLY valid JSON. No markdown,
             no explanation."
    user:   "Generate {n} portfolio projects for a developer targeting {role}.
             Missing skills: {missing_skills}. Existing skills: {user_skills}.
             Each project must: use ≥1 missing skill, completable in ≤40 hours,
             deployable to GitHub. Return a JSON array matching the
             ProjectRecommendation schema."

Langfuse @observe() decorator is stubbed here — FR-11 will install and
activate it without any change to this file's logic.
"""

import json
import logging
import time
from functools import wraps

from api.models import ProjectResponse
from config.settings import settings

logger = logging.getLogger(__name__)

# ── Langfuse stub (FR-11 will replace with real decorator) ────────────────────


def observe(name: str | None = None):
    """No-op decorator — replaced by Langfuse at FR-11."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ── Prompt builder ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a senior ML engineer. " "Return ONLY valid JSON. No markdown, no explanation."
)

_USER_TEMPLATE = (
    "Generate {n} portfolio projects for a developer targeting {role}. "
    "Missing skills: {missing_skills}. "
    "Existing skills: {user_skills}. "
    "Each project must: use at least 1 missing skill, be completable in "
    "at most 40 hours, and be deployable to GitHub. "
    "Return a JSON array where each element has exactly these fields: "
    "title (str), description (str), skills_addressed (list[str]), "
    "difficulty (one of: Beginner, Intermediate, Advanced), "
    "estimated_hours (int)."
)


def _build_prompt(
    missing_skills: list[str],
    user_skills: list[str],
    target_role: str,
    n: int,
) -> str:
    return _USER_TEMPLATE.format(
        n=n,
        role=target_role,
        missing_skills=", ".join(missing_skills[:20]) or "none identified",
        user_skills=", ".join(user_skills[:20]) or "none provided",
    )


# ── Cache fallback ────────────────────────────────────────────────────────────


def _load_cache(target_role: str) -> list[ProjectResponse]:
    """
    Return cached projects for target_role from projects_cache.json.
    Returns empty list if file missing or role not found — never raises.
    """
    try:
        raw: list[dict] = json.loads(settings.PROJECTS_CACHE.read_text())
        for entry in raw:
            if entry.get("role") == target_role:
                return [ProjectResponse(**p) for p in entry.get("projects", [])]
        # Role not in cache — return first entry's projects as generic fallback
        if raw:
            return [ProjectResponse(**p) for p in raw[0].get("projects", [])]
    except Exception as exc:
        logger.warning(f"Could not load projects cache: {exc}")
    return []


# ── JSON parser ───────────────────────────────────────────────────────────────


def _parse_llm_response(text: str) -> list[dict]:
    """
    Extract a JSON array from the LLM response.
    Handles edge cases where the model wraps the array in ```json ... ```.

    Raises:
        ValueError: if no valid JSON array can be extracted.
    """
    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()

    # Find first [ ... ] block
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in LLM response: {text[:200]!r}")

    return json.loads(text[start : end + 1])


# ── Validator ─────────────────────────────────────────────────────────────────


def _validate_projects(
    raw: list[dict],
    missing_skills_lower: set[str],
) -> list[ProjectResponse]:
    """
    Validate each project dict against ProjectResponse schema.
    Silently drops invalid entries. Guarantees each project addresses
    at least one missing skill.
    """
    results: list[ProjectResponse] = []
    for item in raw:
        try:
            project = ProjectResponse(**item)
        except Exception as exc:
            logger.debug(f"Dropping invalid project: {exc} — {item}")
            continue

        # Ensure ≥1 missing skill is addressed
        addressed_lower = {s.lower() for s in project.skills_addressed}
        if not addressed_lower & missing_skills_lower:
            logger.debug(f"Dropping project with no missing skills: {project.title!r}")
            continue

        # Cap hours at 40
        if project.estimated_hours > 40:
            project = project.model_copy(update={"estimated_hours": 40})

        results.append(project)
    return results


# ── Main entry point ──────────────────────────────────────────────────────────


@observe(name="recommend_projects")
def recommend_projects(
    missing_skills: list[str],
    user_skills: list[str],
    target_role: str,
    n: int = 3,
) -> list[ProjectResponse]:
    """
    Generate n personalised portfolio project recommendations.

    Calls Gemini 2.0 Flash with a structured prompt. Falls back to
    projects_cache.json on any failure (timeout, API error, bad JSON).

    Args:
        missing_skills:  Skills the user doesn't have that the role requires.
        user_skills:     Skills the user already has (context for the LLM).
        target_role:     One of the 5 valid roles.
        n:               Number of projects to request (default 3, max 5).

    Returns:
        list[ProjectResponse] — 2–5 items. Never empty (fallback guarantees ≥1).

    Never raises — all exceptions caught and fallback returned.
    """
    n = min(max(n, 2), 5)

    if not missing_skills:
        logger.info("recommend_projects: no missing skills — returning cache")
        return _load_cache(target_role)[:n]

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — using cache fallback")
        return _load_cache(target_role)[:n]

    prompt = _build_prompt(missing_skills, user_skills, target_role, n)
    missing_lower = {s.lower() for s in missing_skills}

    for attempt in range(2):  # try once, retry once on 429
        try:
            projects = _call_gemini(prompt, missing_lower, n)
            if projects:
                return projects
            logger.warning("Gemini returned 0 valid projects — using cache fallback")
            break
        except Exception as exc:
            is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            if is_rate_limit and attempt == 0:
                logger.warning("Gemini 429 rate limit — retrying in 5s")
                time.sleep(5)
                continue
            logger.warning(
                f"Gemini call failed ({type(exc).__name__}: {str(exc)[:120]}) "
                "— using cache fallback"
            )
            break

    return _load_cache(target_role)[:n]


def _call_gemini(
    prompt: str,
    missing_lower: set[str],
    n: int,
) -> list[ProjectResponse]:
    """
    Make the Gemini API call, parse and validate the response.
    Raises on timeout or API error (caller catches and falls back).
    """
    import signal

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Timeout via SIGALRM (Unix only — safe on macOS/Linux API servers)
    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Gemini call exceeded {settings.LLM_TIMEOUT}s timeout")

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(settings.LLM_TIMEOUT)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
    finally:
        signal.alarm(0)  # always cancel the alarm

    raw_text: str = response.text
    logger.debug(f"Gemini raw response ({len(raw_text)} chars): {raw_text[:200]!r}")

    raw_list = _parse_llm_response(raw_text)
    projects = _validate_projects(raw_list, missing_lower)

    logger.info(f"Gemini returned {len(raw_list)} projects, {len(projects)} valid")
    return projects
