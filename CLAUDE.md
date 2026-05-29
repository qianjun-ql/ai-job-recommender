# CLAUDE.md — AI Job Skills Recommender

## Project Purpose

AI pipeline: ingest job data → extract skills → embed → FAISS match → gap analysis → LLM projects.

## Architecture

data/raw/ → pipelines/ingest.py → data/processed/jobs_cleaned.csv
→ pipelines/extract_skills.py → data/processed/job_skills.json
→ pipelines/embed.py → models/faiss_jobs.index

api/main.py (FastAPI — ML layer, internal only)
→ services/matcher.py (FR-04)
→ services/gap.py (FR-05)
→ services/recommender.py (FR-06)
→ services/chatbot.py (FR-08)

frontend/ (Django + React — FR-09, user-facing layer)
→ django_backend/ Django project: auth, user profiles, proxy views to FastAPI
→ react_app/ React 18 + TypeScript + Tailwind CSS + Recharts

## Commands

make ingest # pipelines/ingest.py
make extract # pipelines/extract_skills.py
make embed # pipelines/embed.py
make api # uvicorn api.main:app --reload --port 8000
make django # python frontend/django_backend/manage.py runserver 8001
make frontend # cd frontend/react_app && npm run dev
make test # pytest tests/ -v
make eval # python eval/precision_at_k.py

## Code Style

- Python 3.11, type hints on all functions, docstrings on all public methods
- Black formatter, isort imports, max line length 100
- Pydantic v2 for all API I/O
- No hardcoded paths — use config/settings.py (pydantic-settings)

## LLM Prompt Template (FR-06)

system: "You are a senior ML engineer. Return ONLY valid JSON. No markdown, no explanation."
user:
"Generate {n} portfolio projects for a developer targeting {role}.
Missing skills: {missing_skills}. Existing skills: {user_skills}.
Each project must: use ≥1 missing skill, completable in ≤40 hours, deployable to GitHub.
Return a JSON array matching the ProjectRecommendation schema."

## Critical Constraints

- FAISS index must be rebuilt when dataset changes (detect via file hash)
- All API inputs validated with Pydantic before any processing
- LLM calls must have 10s timeout + fallback to models/projects_cache.json
- Skill normalization is case-insensitive (canonical form in skills_dictionary.json)
- Never log user skill lists to disk (PII)
