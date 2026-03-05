"""
FR-02: Skill Extraction (Hybrid: Dictionary + spaCy NER)
Extracts technical skills from job descriptions using two methods:
  Method A — keyword dictionary (precise, known skills)
  Method B — spaCy NER (catches unknown/emerging skills)

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
import spacy

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Load spaCy model once at module level ─────────────────────────────────────
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("spaCy model loaded ✅")
except OSError:
    raise RuntimeError("spaCy model not found. Run: python -m spacy download en_core_web_sm")

# ── Skills dictionary (Method A) ──────────────────────────────────────────────
SKILLS: dict[str, list[str]] = {
    # Languages
    "Python": ["python"],
    "SQL": ["sql", "mysql", "postgresql", "sqlite"],
    "Java": [" java "],
    "JavaScript": ["javascript", "node.js", "nodejs"],
    "TypeScript": ["typescript"],
    "R": [" r ", "r programming", "rstudio"],
    "Scala": ["scala"],
    "C/C++": ["c/c++", " c ", "c programming"],
    "Go": [" go ", "golang"],
    "Rust": ["rust"],
    "Bash": ["bash", "shell scripting"],
    # ML / AI
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "Keras": ["keras"],
    "Hugging Face": ["hugging face", "huggingface", "transformers"],
    "LangChain": ["langchain"],
    "OpenAI API": ["openai", "gpt-4", "gpt-3", "chatgpt"],
    "Computer Vision": ["computer vision", "opencv", "cv2"],
    "NLP": ["nlp", "natural language processing", "spacy", "nltk"],
    "LLM": ["llm", "large language model"],
    "MLflow": ["mlflow"],
    "Weights & Biases": ["wandb", "weights and biases"],
    "Large Language Models": ["large language models"],
    "Natural Language Processing": ["natural language processing"],
    "XGBoost": ["xgboost", "xgb"],
    # Data
    "pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Spark": ["spark", "pyspark", "apache spark"],
    "Kafka": ["kafka", "apache kafka"],
    "Airflow": ["airflow", "apache airflow"],
    "dbt": ["dbt", "data build tool"],
    "Databricks": ["databricks"],
    "Snowflake": ["snowflake"],
    "BigQuery": ["bigquery", "big query"],
    "Redshift": ["redshift"],
    "ETL": ["etl", "data pipeline", "data ingestion"],
    "PySpark": ["pyspark"],
    "Big Data": ["big data", "hadoop", "mapreduce", "hive"],
    "SQL Server": ["sql server", "mssql", "microsoft sql"],
    "Azure Data Factory": ["azure data factory", "adf"],
    "Microsoft Office": ["microsoft office", "excel", "powerpoint"],
    "MapReduce": ["mapreduce", "map reduce"],
    "Google Analytics": ["google analytics"],
    "PL/SQL": ["pl/sql", "plsql"],
    "Data Analytics": ["data analytics"],
    # Cloud
    "AWS": ["aws", "amazon web services", "s3", "ec2", "sagemaker", "lambda"],
    "GCP": ["gcp", "google cloud", "vertex ai"],
    "Google Cloud": ["google cloud platform", "google cloud"],
    "Azure": ["azure", "microsoft azure"],
    # DevOps / MLOps
    "Docker": ["docker", "dockerfile"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "github actions", "jenkins", "gitlab ci"],
    "Terraform": ["terraform"],
    "Git": ["git", "github", "version control"],
    "GitHub": ["github"],
    "GitLab": ["gitlab"],
    # APIs / Backend
    "FastAPI": ["fastapi"],
    "REST API": ["rest api", "restful"],
    "GraphQL": ["graphql"],
    "Spring Boot": ["spring boot"],
    # Databases
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch"],
    "PostgreSQL": ["postgresql", "postgres"],
    # Viz / BI
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi", "ms office powerbi"],
    "Plotly": ["plotly"],
    "Matplotlib": ["matplotlib"],
    # Soft / Process
    "Agile": ["agile", "scrum", "kanban"],
    "Statistics": ["statistics", "statistical analysis"],
    "Linear Algebra": ["linear algebra"],
    "Deep Learning": ["deep learning", "neural network", "cnn", "rnn", "lstm"],
}

# ── Known tech indicators for spaCy NER filtering ────────────────────────────
TECH_SUFFIXES = {
    "js",
    "py",
    "ai",
    "ml",
    "db",
    "sql",
    "api",
    "sdk",
    "cli",
    "net",
    "io",
    "hub",
    "ops",
    "lab",
    "flow",
    "base",
}
TECH_STOPWORDS = {
    "experience",
    "knowledge",
    "skills",
    "ability",
    "team",
    "work",
    "years",
    "strong",
    "good",
    "excellent",
    "plus",
    "preferred",
    "required",
    "etc",
    "including",
    "using",
    "with",
    "and",
    "or",
    "the",
    "a",
    "an",
    "in",
    "of",
    "for",
    "to",
    "is",
    "are",
}

ROLE_NOISE = {
    "devops",
    "ai/ml",
    "ml/ai",
    "machine learning",
    "data engineering",
    "data scientist",
    "data scientists",
    "data engineer",
    "data engineers",
    "computer science",
    "software engineering",
    "machine learning engineer",
    "machine learning engineers",
    "ml engineer",
    "data science",
    "whatsapp",
    "linkedin",
    "inc.",
    "inc",
    "llc",
    "ltd",
    "electrical engineering",
    "mechanical engineering",
    "civil engineering",
    "powerpoint",
    "microsoft word",
}


# Common English words that start with uppercase but aren't tech skills
COMMON_ENGLISH = {
    # Sentence starters / pronouns
    "what",
    "this",
    "that",
    "these",
    "those",
    "here",
    "there",
    "when",
    "doordash",
    "youtube",
    "covid",
    "covid-19",
    "discrimination",
    "non-discrimination",
    "research",
    "operations",
    "information",
    "technology",
    "engineering",
    "science",
    "statistics",
    "analytics",
    "disability",
    "insurance",
    "diversity",
    "inclusion",
    "equity",
    "benefits",
    "compensation",
    "salary",
    "stock",
    "option",
    "health",
    "dental",
    "vision",
    "mental",
    "savings",
    "commitment",
    "program",
    "programs",
    "plans",
    "injury",
    "life",
    "serious",
    "bachelor",
    "master",
    "where",
    "which",
    "who",
    "how",
    "why",
    "we",
    "you",
    "they",
    "our",
    "your",
    "their",
    "its",
    # Days / months
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    # Places
    "new",
    "york",
    "london",
    "united",
    "states",
    "america",
    "canada",
    "north",
    "south",
    "east",
    "west",
    # Job description noise
    "bachelor",
    "master",
    "phd",
    "degree",
    "university",
    "college",
    "english",
    "french",
    "spanish",
    "about",
    "join",
    "help",
    "role",
    "team",
    "company",
    "position",
    "candidate",
    "please",
    "responsibilities",
    "requirements",
    "qualifications",
    "benefits",
    "opportunity",
    "environment",
    "solutions",
    "services",
    "systems",
    "management",
    "development",
    "engineering",
    "science",
    "business",
    "experience",
    "knowledge",
    "skills",
    "ability",
    "years",
    "work",
    "also",
    "will",
    "must",
    "able",
    "have",
    "with",
    "from",
    "been",
    "some",
    "more",
    "other",
    "both",
    "each",
    "such",
    "well",
    "into",
}


def is_likely_tech_term(text: str) -> bool:
    t = text.strip().lower()
    if len(t) < 4 or len(t) > 30:
        return False
    if t in TECH_STOPWORDS:
        return False
    if t in COMMON_ENGLISH:
        return False
    if t in ROLE_NOISE:
        return False
    if t.isalpha() and t == t.lower() and len(t) < 6:
        return False
    if re.match(r"^[A-Z]\.([A-Z]\.)+$", text):
        return False
    if t[-2:] in TECH_SUFFIXES:
        return True
    if text[0].isupper() and any(c.isdigit() or c in "-_." for c in text):
        return True
    if len(text) >= 5 and text[0].isupper() and any(c.isupper() for c in text[1:]):
        return True
    return False


# ── Extraction functions ───────────────────────────────────────────────────────
def extract_by_dictionary(description: str) -> list[str]:
    """Method A — match against known skill keywords."""
    text = description.lower()
    return [skill for skill, kws in SKILLS.items() if any(kw in text for kw in kws)]


def extract_by_spacy(description: str) -> list[str]:
    """Method B — use spaCy NER + noun chunks to find emerging/unknown skills."""
    doc = nlp(description[:5000])  # cap at 5000 chars for performance
    candidates: list[str] = []

    # Named entities — ORG and PRODUCT often map to tech tools
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT") and is_likely_tech_term(ent.text):
            candidates.append(ent.text.strip())

    # Noun chunks — single-token proper nouns that look like tech
    for chunk in doc.noun_chunks:
        if len(chunk) == 1 and is_likely_tech_term(chunk.text):
            candidates.append(chunk.text.strip())

    return list(set(candidates))


def extract_skills(description: str) -> list[str]:
    """
    Hybrid extraction — combines dictionary + spaCy NER.
    Dictionary skills take canonical names; spaCy adds unknowns.
    """
    dict_skills = extract_by_dictionary(description)
    spacy_skills = extract_by_spacy(description)

    # Remove spaCy results already covered by dictionary
    dict_lower = {s.lower() for s in dict_skills}
    novel_skills = [s for s in spacy_skills if s.lower() not in dict_lower]

    return dict_skills + novel_skills


def extract_all(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Return mapping of job_id -> [skill_list] for all rows.
    Uses nlp.pipe() for batch processing — much faster than iterrows().
    """
    result: dict[str, list[str]] = {}
    descriptions = df["description"].str[:5000].tolist()
    job_ids = df["job_id"].astype(str).tolist()

    logger.info(f"  Batch processing {len(descriptions):,} descriptions with spaCy...")

    docs = nlp.pipe(descriptions, batch_size=64)

    for i, (job_id, doc) in enumerate(zip(job_ids, docs)):
        if i % 500 == 0 and i > 0:
            logger.info(f"  Progress: {i:,} / {len(descriptions):,}")

        # Method A — dictionary on raw text
        dict_skills = extract_by_dictionary(descriptions[i])

        # Method B — spaCy on pre-parsed doc (no re-parsing)
        spacy_skills = extract_by_spacy_doc(doc)

        dict_lower = {s.lower() for s in dict_skills}
        novel = [s for s in spacy_skills if s.lower() not in dict_lower]
        result[job_id] = dict_skills + novel

    return result


def extract_by_spacy_doc(doc: spacy.tokens.Doc) -> list[str]:
    """Method B — accepts pre-parsed spaCy doc (used in batch processing)."""
    candidates: list[str] = []
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT") and is_likely_tech_term(ent.text):
            candidates.append(ent.text.strip())
    for chunk in doc.noun_chunks:
        if len(chunk) == 1 and is_likely_tech_term(chunk.text):
            candidates.append(chunk.text.strip())
    return list(set(candidates))


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

    logger.info("Extracting skills (dictionary + spaCy)...")
    logger.info("This may take 1-2 minutes for spaCy processing...")
    job_skills = extract_all(df)

    # ── Filter low-frequency novel skills ────────────────────────────────────
    MIN_SKILL_FREQUENCY = 10  # must appear in at least 10 jobs
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
    logger.info(f"Novel skills via spaCy:    {len(set(novel)):,} unique")

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
    extract()
