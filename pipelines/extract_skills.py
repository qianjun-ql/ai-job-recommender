"""
FR-02: Skill Extraction (Hybrid: Dictionary + NER)
Extracts technical skills from job descriptions using two methods:
  Method A — keyword dictionary (precise, known skills)
  Method B — JobBERT NER (fine-tuned on job postings; dictionary-only if not yet trained)

Run:  python pipelines/train_jobbert.py  to fine-tune JobBERT.

Input:  data/processed/jobs_cleaned.csv
Output: data/processed/job_skills.json
        data/processed/skill_frequency.csv
"""

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import torch

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from pipelines.utils import get_torch_device

logger = logging.getLogger(__name__)


# ── Method B backend: JobBERT (lazy-loaded on first use) ─────────────────────
JOBBERT_DIR = settings.BASE_DIR / "models" / "jobbert-skill-ner"

# Labels that count as "skill" at inference time.
# With aggregation_strategy="simple", HuggingFace strips B-/I- prefixes —
# entity_group will be "Skill" or "Knowledge", never "B-Skill" etc.
_SKILL_ENTITY_GROUPS = {"Skill", "Knowledge"}

# Detect model availability at import time (fast — no weights loaded).
_METHOD_B: str = (
    "jobbert" if JOBBERT_DIR.exists() and (JOBBERT_DIR / "config.json").exists() else "none"
)
if _METHOD_B == "none":
    logger.warning(
        "JobBERT model not found — dictionary-only mode. " "Run: python pipelines/train_jobbert.py"
    )

_jobbert_pipe: object | None = None  # loaded on first extract call
_jobbert_load_failed: bool = False


def _get_pipe() -> object | None:
    """Lazy-load JobBERT NER pipeline on first call (~400 MB; skipped at API import time)."""
    global _jobbert_pipe, _jobbert_load_failed
    if _jobbert_load_failed or _METHOD_B != "jobbert":
        return None
    if _jobbert_pipe is not None:
        return _jobbert_pipe
    try:
        from transformers import AutoTokenizer
        from transformers import pipeline as hf_pipeline

        _tok = AutoTokenizer.from_pretrained(str(JOBBERT_DIR), model_max_length=512)
        _jobbert_pipe = hf_pipeline(
            "ner",
            model=str(JOBBERT_DIR),
            tokenizer=_tok,
            aggregation_strategy="simple",
            device=get_torch_device(),
        )
        logger.info("Method B: JobBERT NER loaded ✅  (domain-tuned on job postings)")
        return _jobbert_pipe
    except Exception as e:
        logger.warning(f"JobBERT load failed ({e}) — dictionary-only mode")
        _jobbert_load_failed = True
        return None


# ── Skills dictionary (Method A) ──────────────────────────────────────────────
# Edit models/skills_dictionary.json to add/remove skills — no code changes needed.
if not settings.SKILLS_DICT.exists():
    raise FileNotFoundError(
        f"Skills dictionary not found: {settings.SKILLS_DICT}\n"
        "Expected: models/skills_dictionary.json"
    )
SKILLS: dict[str, list[str]] = json.loads(settings.SKILLS_DICT.read_text())

# Flat set of all alias strings — for O(1) dedup against ALL aliases, not just canonical names
SKILL_ALIASES_LOWER: set[str] = {alias.strip() for aliases in SKILLS.values() for alias in aliases}

# ── Compiled regex for fast dictionary lookup ──────────────────────────────────
# Sort aliases longest-first so "apache spark" matches before "spark".
# Strips space-hack aliases (" java " → "java"); word boundaries handle isolation.
_ALIAS_TO_SKILL: dict[str, str] = {
    alias.strip(): skill for skill, aliases in SKILLS.items() for alias in aliases
}
_DICT_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(a) for a in sorted(_ALIAS_TO_SKILL, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def _filter_novel(ner_skills: list[str]) -> list[str]:
    """Remove NER results already covered by the dictionary (any alias, case-insensitive)."""
    return [s for s in ner_skills if s.lower() not in SKILL_ALIASES_LOWER]


# Stopwords / noise tokens loaded from models/ner_stopwords.json.
# Edit that file to add/remove entries — no code changes needed.
_NER_STOPWORDS: frozenset[str] = frozenset(
    json.loads(settings.NER_STOPWORDS.read_text())["stopwords"]
    if settings.NER_STOPWORDS.exists()
    else []
)

_TRAILING_PUNCT: frozenset[str] = frozenset(".,;:!?")


def _is_valid_ner_word(word: str) -> bool:
    """
    Return True if a NER-tagged word is a plausible skill token.
    Rejects:
      - BERT subword artifacts (e.g. "##ing", "##s" — not merged by aggregation)
      - tokens not starting with a letter (fragments like "s degree", "##bor")
      - tokens ending with punctuation (e.g. "design,")
      - spans longer than 5 words (run-on phrases from bad aggregation)
      - min length < 3 chars
      - stopwords
    """
    w = word.strip()
    if "##" in w:
        return False
    if not w or not w[0].isalpha():
        return False
    if len(w.split()[0]) <= 1:  # single-letter fragment: "s degree", "c + +"
        return False
    if w[-1] in _TRAILING_PUNCT:
        return False
    if len(w) < 3:
        return False
    if len(w.split()) > 5:
        return False
    if w.lower() in _NER_STOPWORDS:
        return False
    return True


# ── Extraction functions ──────────────────────────────────────────────────────
def extract_by_dictionary(description: str) -> list[str]:
    """Method A — single compiled-regex pass across all aliases (~10x faster than per-alias loop)."""
    matches = _DICT_PATTERN.findall(description)
    return list({_ALIAS_TO_SKILL[m.lower()] for m in matches})


def extract_by_jobbert(description: str) -> list[str]:
    """Method B (primary) — use fine-tuned JobBERT NER to detect skill spans."""
    pipe = _get_pipe()
    if pipe is None:
        return []
    results = pipe(description[:2048])  # tokenizer model_max_length=512 handles token truncation
    return list(
        {
            r["word"].strip()
            for r in results
            if r["entity_group"] in _SKILL_ENTITY_GROUPS and _is_valid_ner_word(r["word"])
        }
    )


def extract_by_jobbert_batch(texts: list[str]) -> list[list[str]]:
    """Batch JobBERT inference — much faster than calling extract_by_jobbert() per row."""
    pipe = _get_pipe()
    if pipe is None:
        return [[] for _ in texts]
    batch_results = pipe(
        texts, batch_size=settings.JOBBERT_BATCH_SIZE
    )  # texts already truncated upstream
    output = []
    for results in batch_results:
        skills = list(
            {
                r["word"].strip()
                for r in results
                if r["entity_group"] in _SKILL_ENTITY_GROUPS and _is_valid_ner_word(r["word"])
            }
        )
        output.append(skills)
    return output


def extract_skills(description: str) -> list[str]:
    """
    Single-item hybrid extraction — for tests and one-off calls only.
    Use extract_all() for bulk processing: it uses batch NER inference (~8x faster).
    """
    dict_skills = extract_by_dictionary(description)
    ner_skills = extract_by_jobbert(description)  # returns [] if pipe unavailable
    return dict_skills + _filter_novel(ner_skills)


def extract_all(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Return mapping of job_id -> [skill_list] for all rows.
    JobBERT uses batch inference (pipeline batch_size=32) for speed.
    Falls back to dictionary-only if JobBERT is not trained.
    """
    result: dict[str, list[str]] = {}
    MAX_DESC_CHARS = 2048  # single truncation point for both dict and NER passes
    descriptions = df["description"].str[:MAX_DESC_CHARS].tolist()
    job_ids = df["job_id"].astype(str).tolist()

    if _METHOD_B == "jobbert":
        logger.info(f"  Batch processing {len(descriptions):,} descriptions with JobBERT NER...")
        ner_results = extract_by_jobbert_batch(descriptions)
        for job_id, dict_desc, ner_skills in zip(job_ids, descriptions, ner_results):
            dict_skills = extract_by_dictionary(dict_desc)
            result[job_id] = dict_skills + _filter_novel(ner_skills)

    else:
        logger.warning("JobBERT not available — dictionary-only extraction")
        for job_id, desc in zip(job_ids, descriptions):
            result[job_id] = extract_by_dictionary(desc)

    return result


def compute_frequency(job_skills: dict[str, list[str]], total_jobs: int) -> pd.DataFrame:
    """Compute skill frequency and percentage across all jobs."""
    counter: Counter[str] = Counter()
    for skills in job_skills.values():
        counter.update(skills)
    rows = [
        {
            "skill": skill,
            "count": count,
            "pct_of_jobs": round(count / total_jobs, 4),
        }
        for skill, count in counter.most_common()
    ]
    return pd.DataFrame(rows)


# ── Main pipeline ─────────────────────────────────────────────────────────────
def extract() -> dict[str, list[str]]:
    """Run the full hybrid skill extraction pipeline."""
    logger.info("═" * 60)
    logger.info("FR-02: Starting hybrid skill extraction pipeline")
    logger.info("═" * 60)

    if not settings.JOBS_CLEANED_CSV.exists():
        raise FileNotFoundError(
            f"Cleaned jobs not found: {settings.JOBS_CLEANED_CSV}\n"
            "Run pipelines/ingest.py first."
        )

    df = pd.read_csv(settings.JOBS_CLEANED_CSV)
    logger.info(f"Loaded {len(df):,} jobs")

    backend = "JobBERT" if _METHOD_B == "jobbert" else "dictionary-only"
    logger.info(f"Extracting skills (dictionary + {backend})...")
    job_skills = extract_all(df)

    # ── Filter low-frequency novel skills ────────────────────────────────────
    MIN_SKILL_FREQUENCY = settings.NOVEL_SKILL_MIN_FREQUENCY
    known_skills = set(SKILLS.keys())

    # Count novel skill frequency
    novel_freq: Counter[str] = Counter()
    for skills in job_skills.values():
        for s in skills:
            if s not in known_skills:
                novel_freq[s] += 1

    # Keep only novel skills above threshold
    high_freq_novel = {s for s, c in novel_freq.items() if c >= MIN_SKILL_FREQUENCY}
    logger.info(
        f"Novel skills after frequency filter (≥{MIN_SKILL_FREQUENCY}): {len(high_freq_novel):,}"
    )

    # Rebuild job_skills keeping all dictionary skills + only high-freq novel
    job_skills = {
        job_id: [s for s in skills if s in known_skills or s in high_freq_novel]
        for job_id, skills in job_skills.items()
    }

    # ── Stats ─────────────────────────────────────────────────────────────────
    all_skills: list[str] = [s for skills in job_skills.values() for s in skills]
    dict_skills_set = set(SKILLS.keys())
    novel = [s for s in all_skills if s not in dict_skills_set]
    jobs_with_skills = sum(1 for v in job_skills.values() if v)
    avg = len(all_skills) / len(job_skills) if job_skills else 0

    logger.info(f"Jobs with ≥1 skill:        {jobs_with_skills:,} / {len(df):,}")
    logger.info(f"Average skills per job:    {avg:.1f}")
    logger.info(f"Novel skills via {backend}:    {len(set(novel)):,} unique")

    # ── Save outputs ──────────────────────────────────────────────────────────
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    settings.JOB_SKILLS.write_text(json.dumps(job_skills, indent=2))
    logger.info(f"Saved → {settings.JOB_SKILLS}")

    freq_df = compute_frequency(job_skills, total_jobs=len(df))
    freq_df.to_csv(settings.SKILL_FREQUENCY, index=False)
    logger.info(f"Saved → {settings.SKILL_FREQUENCY}")
    logger.info(f"Total unique skills found: {len(freq_df)}")

    logger.info("Top 15 skills:")
    for _, row in freq_df.head(15).iterrows():
        bar = "█" * int(row["pct_of_jobs"] * 40)
        logger.info(f"  {row['skill']:20} {bar} {row['pct_of_jobs']*100:.1f}%")

    logger.info("FR-02: Hybrid extraction complete ✅")
    return job_skills


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    extract()
