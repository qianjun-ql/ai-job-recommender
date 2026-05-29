# AI Job Skills & Project Recommendation System

**Product Requirements Document · v4.0**

Status: Active · Target: Production Deployment · 2026

| 8 Weeks | 5 Phases | 11 FRs | 10k+ Jobs | Agentic RAG | Docker Ready |
| :-----: | :------: | :----: | :-------: | :---------: | :----------: |

---

# 01 Problem & Product Vision

## Problem Statement

Developers transitioning into new roles face three compounding challenges:

- Job postings contain required skills, but the data is unstructured and impractical to analyze manually.
- Engineers cannot quickly determine which of their existing skills transfer and which are missing.
- There is no data-driven, conversational mechanism to explore skill gaps and get actionable recommendations.

## Solution

Build a production-grade AI pipeline that:

- Ingests and normalizes 10,000+ job postings from multiple sources.
- Extracts required skills using a curated dictionary + **JobBERT NER** fine-tuned on job postings.
- Semantically matches user skill profiles to job embeddings via FAISS vector search.
- Performs precise skill gap analysis — job skills minus user skills.
- Generates actionable portfolio project recommendations via LLM.
- Exposes an **Agentic RAG chatbot** — an AI agent with tools that answers questions grounded in real job data.
- Traces all LLM calls via Langfuse for observability and cost monitoring.
- Evaluates RAG quality automatically with RAGAS metrics.
- Fully containerized with Docker Compose, deployable to any cloud provider.

## Why This Project, Not a Generic RAG App

| Factor                    | This Project                            | Generic RAG Doc Q&A           |
| :------------------------ | :-------------------------------------- | :---------------------------- |
| RAG component             | ✅ FR-08 agentic chatbot with tools     | ✅ Core feature               |
| FAISS vector search       | ✅ FR-03/04                             | ✅ Core feature               |
| Data pipeline             | ✅ FR-01/02 — unique differentiator     | ❌ Usually just a PDF loader  |
| Skill gap analysis        | ✅ FR-05 — domain-specific feature      | ❌ Not present                |
| Agentic AI (ReAct)        | ✅ FR-08 — multi-tool decision loop     | ❌ Simple chat only           |
| RAG evaluation            | ✅ FR-10 RAGAS — faithfulness/relevancy | ❌ Not present                |
| LLMOps observability      | ✅ FR-11 Langfuse tracing               | ❌ Not present                |
| Portfolio differentiation | ✅ High — unusual combination           | ❌ Low — everyone builds this |
| Time to complete          | 8 weeks                                 | 4–5 weeks                     |

## System Architecture — v4.0

```
User Query / Skills Input
    │
    ├─► FastAPI Layer (FR-07)
    │       │
    │   ┌───▼──────────┐   ┌──────────────┐   ┌──────────────┐
    │   │   FR-04      │   │    FR-05     │   │    FR-06     │
    │   │ FAISS Matcher│──►│ Skill Gap    │──►│ LLM Projects │
    │   └───▲──────────┘   └──────────────┘   └──────────────┘
    │       │                                        │
    │   ┌───┴──────────┐   ┌──────────────┐          │ Langfuse
    │   │   FR-03      │   │    FR-02     │          │ FR-11 traces
    │   │ Embed + FAISS│◄──│ Skill Ext.   │◄── FR-01 Ingest
    │   └──────────────┘   └──────────────┘
    │
    ├─► FR-08 Agentic RAG Chatbot
    │       │
    │       └─► ReAct Agent
    │               ├── Tool: search_jobs(query)
    │               ├── Tool: get_skill_gap(role)
    │               ├── Tool: get_trending_skills(role)
    │               └── Tool: recommend_projects(gaps)
    │
    ├─► FR-10 RAGAS Evaluation (offline)
    │       └── faithfulness · answer_relevancy · context_precision · context_recall
    │
    └─► FR-09 Django + React Frontend
            ├── Django (proxy layer + future auth)
            └── React 18 + TypeScript + Tailwind + Recharts
```

---

# 02 Target Personas & User Stories

## Primary Personas

| Persona                | Background                    | Primary Goal                                        |
| :--------------------- | :---------------------------- | :-------------------------------------------------- |
| Transitioning Engineer | 5 yrs SWE, moving into ML     | Identify gaps vs ML Engineer JDs, get project ideas |
| Junior Developer       | 0–2 yrs, recent bootcamp grad | Understand in-demand skills, build portfolio fast   |
| CS Student             | Final year, no industry exp   | Align coursework to real job requirements           |

## User Stories

| ID    | Story                                                   | Acceptance Criteria                                               |
| :---- | :------------------------------------------------------ | :---------------------------------------------------------------- |
| US-01 | Input skills + target role to see missing skills.       | Returns missing_skills within 2s. Empty input → 400.              |
| US-02 | See top 5 matching jobs for my profile.                 | Top-5 with match_score ≥ 0, sorted descending.                    |
| US-03 | Get AI project ideas based on my skill gaps.            | Returns 2–5 projects. LLM failure → cache fallback, not 500.      |
| US-04 | Filter jobs by location.                                | Returns only postings matching city. Invalid → empty 200.         |
| US-05 | Chat with AI career agent about my skill gaps.          | Agent calls correct tools. Answers cite real job postings.        |
| US-06 | See trending skills for my target role.                 | Ordered skill list with demand_count. Refreshes per request.      |
| US-07 | Ask the agent to explain why a specific job matches me. | Agent calls search_jobs + get_skill_gap, returns grounded answer. |

---

# 03 Functional Requirements

---

### FR-01 — Job Data Ingestion

**Priority:** P0 · **Owner:** Data Engineering · **Status:** ✅ Complete

**Inputs:** 3 raw CSVs: `job_postings.csv`, `ai_ml_jobs_linkedin.csv`, `clean_jobs.csv`

**Processing:**

1. Merge 3 datasets (target ≥ 10,000 rows — add 4th dataset if needed)
2. Remove duplicate job_ids
3. Strip HTML, normalize whitespace
4. Classify role via keyword match on `title + description[:300]`
5. Balance roles (cap 2,000 per role)
6. Hash-based change detection — skip reprocessing if unchanged

**Outputs:** `jobs_cleaned.csv` · `ingestion_report.json` (row counts, dupe count, role breakdown)

**Schema:**

```
job_id       STRING NOT NULL UNIQUE
title        STRING NOT NULL
role         ENUM[ML Engineer | Data Scientist | AI Engineer | SWE | Data Engineer]
description  TEXT NOT NULL
location     STRING NULLABLE
source       STRING NOT NULL
```

**Done When ✅** `jobs_cleaned.csv` exists · row count ≥ 10,000 · zero duplicate job_ids · all roles valid

---

### FR-02 — Skill Extraction

**Priority:** P0 · **Owner:** NLP · **Status:** ✅ Complete

**Inputs:** `jobs_cleaned.csv`

**Processing:**

1. Method A: curated keyword dictionary (≥ 200 skills, canonical names — primary method)
2. Method B: **JobBERT NER** fine-tuned on SkillSpan dataset (domain-specific, ~3.2M job postings pre-training)
   - Run `make train-jobbert` once to fine-tune and save to `models/jobbert-skill-ner/`
   - Falls back to spaCy `en_core_web_sm` if JobBERT model not yet trained
3. Deduplicate NER candidates against all dictionary aliases (not just canonical names)
4. Normalize skill names (case-insensitive canonical form)
5. Store `job_id → [skill_list]` mapping

**Training pipeline:** `pipelines/train_jobbert.py`

- Dataset: `jjzha/skillspan` (HuggingFace) — pre-labeled job postings
- Base model: `jjzha/jobbert-base-cased`
- Fine-tuning: ~15 min on Apple MPS / ~1-2 hr on CPU
- Output: `models/jobbert-skill-ner/` (model + tokenizer + label config)

**Outputs:** `job_skills.json` · `skill_frequency.csv` (skill, count, pct_of_jobs)

**Schema:** `{ "job_id": "string", "skills": ["string"] }`

**Done When ✅** Every job_id has non-empty skills list · `skill_frequency.csv` has ≥ 200 unique skills · JobBERT F1 ≥ 0.85 on SkillSpan test set

---

### FR-03 — Embedding Generation

**Priority:** P0 · **Owner:** ML

**Inputs:** `jobs_cleaned.csv` · user_profile (skills list + target role)

**Processing:**

1. Use `sentence-transformers/all-MiniLM-L6-v2` (384-dim, local, no API cost)
2. Generate one embedding per job description
3. Store in `FAISS IndexFlatIP` (inner product = cosine similarity on normalized vectors)
4. Cache — regenerate only on dataset hash change
5. Save `job_id_map.json` (FAISS index position → job_id)

**Outputs:** `models/faiss_jobs.index` · `models/job_id_map.json`

**Done When ✅** FAISS index loads without error · query returns results < 100ms on 10k vectors · index size matches job count

---

### FR-04 — Semantic Job Matching

**Priority:** P0 · **Owner:** ML

**Inputs:** user skills list · k (default=5, max=20) · optional: location filter

**Processing:**

1. Join user skills into a single string, embed with same model as FR-03
2. Query FAISS index, retrieve top-k job_ids + cosine scores
3. Apply location filter post-retrieval if provided
4. Fetch job metadata from `jobs_cleaned.csv` for each match

**Outputs:** `[{ job_id, title, role, location, match_score, description_snippet }]`

**Done When ✅** Returns ≥ 1 result for valid input · scores in [0,1] · Precision@5 ≥ 0.80 · latency < 200ms

---

### FR-05 — Skill Gap Analysis

**Priority:** P0 · **Owner:** ML

**Inputs:** `user_skills: list[str]` · `target_role: str` (must match role enum)

**Processing:**

1. Aggregate all skills for `target_role` from `job_skills.json`
2. Frequency threshold: skills in ≥ 30% of role postings = required
3. `missing_skills = required_skills − user_skills` (case-insensitive set diff)
4. `match_score = len(matched) / len(required) × 100`

**Outputs:** `{ matched_skills, missing_skills, match_score, total_required }`

**Done When ✅** `missing_skills` never null · `match_score` float 0–100 · deterministic for same inputs

---

### FR-06 — LLM Project Recommendations

**Priority:** P1 · **Owner:** LLM

**Inputs:** `missing_skills: list[str]` · `target_role: str` · `user_skills: list[str]`

**Processing:**

1. Build structured prompt with constraints (see CLAUDE.md prompt template)
2. Call Gemini 2.0 Flash via `google-genai` SDK
3. Parse structured JSON response
4. Validate: `title`, `description`, `skills_addressed`, `difficulty`, `estimated_hours`
5. On LLM failure (timeout > 10s): return `projects_cache.json` fallback
6. All LLM calls decorated with `@observe()` for Langfuse tracing (FR-11)

**Outputs:** `[{ title, description, skills_addressed, difficulty, estimated_hours }]`

**Schema:**

```json
{
  "title": "str",
  "description": "str",
  "skills_addressed": ["str"],
  "difficulty": "Beginner | Intermediate | Advanced",
  "estimated_hours": 0
}
```

**Done When ✅** Returns 2–5 projects · each addresses ≥ 1 missing skill · LLM timeout → cache fallback, no 500

---

### FR-07 — REST API Layer

**Priority:** P0 · **Owner:** Backend

**Inputs:** See endpoint contract in Section 04

**Processing:**

1. Validate all inputs with Pydantic v2 models
2. Consistent error envelope: `{ error, message, request_id }`
3. Log all requests with `request_id` for traceability
4. API key middleware for authentication
5. Rate limiting: 100 requests/day per key

**Outputs:** JSON responses per endpoint specs · OpenAPI docs at `/docs`

**Done When ✅** All endpoints return correct status codes · `/health` → 200 · `/docs` loads · Pydantic rejects bad input → 422

---

### FR-08 — Agentic RAG Chatbot ⭐ UPGRADED

**Priority:** P1 · **Owner:** LLM + Retrieval

**Inputs:** `message: str` · `session_id: str` · `user_skills: list[str]` (optional context)

**Processing:**

1. User message passed to a **LangChain ReAct agent**
2. Agent decides which tools to call based on the question:
   - `search_jobs(query)` → embeds query, searches FAISS index, returns top-5 job snippets
   - `get_skill_gap(role)` → calls FR-05 service, returns missing skills
   - `get_trending_skills(role)` → calls `/top_skills` endpoint, returns demand-ranked skills
   - `recommend_projects(gaps)` → calls FR-06 service, returns project ideas
3. Agent builds answer grounded in tool outputs — must cite source job_ids
4. Conversation history maintained with `ConversationBufferWindowMemory` (last 10 turns)
5. All LLM calls decorated with `@observe()` for Langfuse tracing (FR-11)

**Outputs:** `{ answer: str, sources: [job_id], tool_calls_made: [str], session_id: str }`

**Schema:** `POST /chat { message, session_id, user_skills } → { answer, sources, tool_calls_made, session_id }`

**Done When ✅** Agent calls correct tools for different question types · answers cite real job postings · multi-turn conversation works · `tool_calls_made` populated in every response

---

### FR-09 — Django + React Frontend

**Priority:** P2 · **Owner:** Frontend

**Architecture decision:** Django sits between React and FastAPI. React never calls FastAPI directly — Django proxies all ML requests. This shields the ML service from the public internet, enables future auth without rewriting, and follows the industry pattern (Python ML service behind an internal API).

**Inputs:** Django proxy views → FastAPI endpoints (FR-07, FR-08)

**Processing:**

**Django layer** (`frontend/django_backend/`):

1. Proxy views: forward `/api/ml/analyze`, `/api/ml/chat`, `/api/ml/top_skills` to FastAPI
2. Auth app (`accounts/`): register, login, logout — Django built-in auth, foundation for Phase 2 profiles
3. Django REST Framework for JSON API responses to React

**React layer** (`frontend/react_app/`):

1. `SkillInput.tsx` — tag chip input (Enter to add, × to remove) + role selector
2. `AnalyzePage.tsx` — calls `/api/ml/analyze`, renders job cards + gap chart + project cards
3. `ChatPage.tsx` — calls `/api/ml/chat`, maintains message thread, shows tool call badges per message
4. `SkillFreqChart.tsx` — Recharts horizontal bar chart from `/api/ml/top_skills`
5. `App.tsx` — tab toggle between Analyze and Chat (no React Router needed)
6. Responsive design — Tailwind `sm:` / `md:` breakpoints

**Outputs:** Running Django server (`:8001`) + Vite dev server (`:5173`) · single `make django` + `make frontend` to start

**Tech:** Django 5 + DRF · React 18 + TypeScript · Vite · Tailwind CSS · Recharts · Axios

**Deploy:** React → Azure Static Web Apps (free tier) · Django → Azure App Service (B1, GitHub Education credit) · FastAPI → Azure App Service (internal, not public)

**Done When ✅** All FR-07 endpoints accessible via UI · chat interface works · Django proxies correctly · loads in < 2s

---

### FR-10 — RAG Evaluation (RAGAS) ⭐ NEW

**Priority:** P1 · **Owner:** ML

**Why:** The previous success metric for FR-08 was "manual review of 20 sessions ≥ 4.0/5.0" — a vibe check, not a metric. RAGAS provides automated, reproducible quality scores.

**Inputs:** 50-question evaluation dataset (`eval/ragas_questions.json`) · chatbot responses from FR-08

**Processing:**

1. For each eval question, run FR-08 agent and capture: `question`, `answer`, `contexts` (retrieved job snippets), `ground_truth`
2. Compute RAGAS metrics:
   - **Faithfulness** — is the answer grounded in retrieved job postings, or hallucinated?
   - **Answer Relevancy** — does the answer actually address the question asked?
   - **Context Precision** — are the retrieved job postings relevant to the question?
   - **Context Recall** — are relevant job postings being missed?
3. Output scores as `eval/ragas_report.json`
4. Run via `make eval`

**Outputs:** `eval/ragas_report.json` · printed score table

**Done When ✅** All 4 RAGAS scores computed without error · faithfulness ≥ 0.85 · answer_relevancy ≥ 0.80

---

### FR-11 — LLMOps Observability (Langfuse) ⭐ NEW

**Priority:** P1 · **Owner:** MLOps

**Why:** Without tracing, there is no visibility into LLM call latency, token cost, prompt changes, or failure patterns. This is table stakes for production LLM systems in 2026.

**Inputs:** All LLM calls in FR-06 and FR-08

**Processing:**

1. Instrument FR-06 (`generate_recommendations`) and FR-08 (`agent_chat`) with `@observe()` decorator
2. Each trace captures: prompt text, response, latency (ms), token count, model name, estimated cost
3. Traces visible in Langfuse cloud dashboard (free tier — no self-hosting needed for Phase 1)
4. Prompt templates versioned and managed in Langfuse Prompt Management
5. `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` loaded from `.env`

**Outputs:** Langfuse dashboard with trace history, latency trends, token cost tracking

**Done When ✅** Every FR-06 and FR-08 LLM call creates a trace in Langfuse · dashboard shows latency + token cost · prompt versions tracked

---

# 04 API Contract

## POST /analyze — Full Pipeline

**Request:**

```json
{
  "skills": ["Python", "TensorFlow", "SQL"],
  "target_role": "ML Engineer",
  "location": "Calgary"
}
```

**Response 200:**

```json
{
  "top_jobs": [
    { "job_id": "str", "title": "str", "match_score": 0.92, "location": "str" }
  ],
  "matched_skills": ["Python", "SQL"],
  "missing_skills": ["PyTorch", "Docker", "AWS"],
  "match_score": 40.0,
  "projects": [
    { "title": "str", "description": "str", "skills_addressed": ["PyTorch"] }
  ]
}
```

## POST /chat — Agentic RAG Chatbot

**Request:**

```json
{
  "message": "What skills do I need for ML Engineer in Calgary?",
  "session_id": "uuid-1234",
  "user_skills": ["Python", "SQL"]
}
```

**Response 200:**

```json
{
  "answer": "Based on 696 ML Engineer postings in our dataset, the top required skills are PyTorch (52%), Docker (38%), and AWS SageMaker (27%)...",
  "sources": ["job_124", "job_891", "job_203"],
  "tool_calls_made": ["search_jobs", "get_trending_skills"],
  "session_id": "uuid-1234"
}
```

## GET /top_skills?role={role}&limit={n}

**Response 200:**

```json
{
  "role": "ML Engineer",
  "skills": [
    { "skill": "Python", "demand_count": 696, "pct_of_jobs": 0.52 },
    { "skill": "PyTorch", "demand_count": 433, "pct_of_jobs": 0.15 }
  ]
}
```

## GET /health

```json
{
  "status": "ok",
  "version": "4.0.0",
  "dataset_rows": 10000,
  "index_size": 10000
}
```

## HTTP Status Codes

| Status | Code                | When                                         |
| :----- | :------------------ | :------------------------------------------- |
| 200    | OK                  | Successful response                          |
| 400    | BAD_REQUEST         | Missing required field                       |
| 422    | VALIDATION_ERROR    | Pydantic schema violation                    |
| 404    | NOT_FOUND           | job_id not found                             |
| 503    | SERVICE_UNAVAILABLE | LLM or FAISS unavailable; fallback triggered |

---

# 05 CLAUDE.md Reference

```markdown
## Project Purpose

AI pipeline: ingest → extract skills → embed → FAISS match → gap analysis →
LLM projects → Agentic RAG chatbot → RAGAS eval → Langfuse observability.

## Architecture

data/raw/ → pipelines/ingest.py → data/processed/jobs_cleaned.csv
→ pipelines/extract_skills.py → data/processed/job_skills.json
→ pipelines/embed.py → models/faiss_jobs.index

api/main.py (FastAPI — internal only, not public)
→ services/matcher.py FR-04
→ services/gap.py FR-05
→ services/recommender.py FR-06 ← @observe() Langfuse
→ services/chatbot.py FR-08 ← ReAct Agent + @observe() Langfuse

frontend/ FR-09
→ django_backend/ Django 5 + DRF: proxy views + auth
→ react_app/ React 18 + TypeScript + Tailwind + Recharts

eval/
→ precision_at_k.py FR-04 evaluation
→ ragas_eval.py FR-10 RAG evaluation

## Commands

make ingest # pipelines/ingest.py
make extract # pipelines/extract_skills.py
make embed # pipelines/embed.py
make api # uvicorn api.main:app --reload --port 8000
make django # python frontend/django_backend/manage.py runserver 8001
make frontend # cd frontend/react_app && npm run dev
make test # pytest tests/ -v
make eval # python eval/precision_at_k.py && python eval/ragas_eval.py
make docker # docker-compose up --build

## LLM Prompt Template (FR-06)

system: "You are a senior ML engineer. Return ONLY valid JSON. No markdown, no explanation."
user: "Generate {n} projects for {role}.
Missing: {missing_skills}. Have: {user_skills}.
Each must: use ≥1 missing skill, completable ≤40 hrs, deployable to GitHub."

## Agentic RAG System Prompt (FR-08)

system: "You are an AI career advisor with access to tools.
Use tools to answer questions grounded in real job data.
Always cite which job postings informed your answer.
Never answer from memory alone — always call a tool first."

## Agent Tools (FR-08)

search_jobs(query: str) → top-5 FAISS job snippets
get_skill_gap(role: str) → missing_skills for user's role
get_trending_skills(role: str) → demand-ranked skill list
recommend_projects(gaps: list) → 2-5 portfolio project ideas

## Critical Constraints

- FAISS index rebuilt when dataset changes (hash detection)
- All API inputs validated with Pydantic before processing
- LLM calls: 10s timeout + fallback to projects_cache.json
- Skill normalization case-insensitive (canonical form in dictionary)
- Never log user skill lists to disk (PII)
- RAG agent must always return source job_ids in response
- All LLM calls must be traced via Langfuse (@observe decorator)
- LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be in .env
```

---

# 06 Project Folder Structure

```
ai-job-recommender/
├── CLAUDE.md
├── Makefile
├── README.md
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── .env.example
│
├── config/
│   └── settings.py              # Pydantic settings, all env vars
│
├── data/
│   ├── raw/job_details/         # Original CSVs (gitignored)
│   └── processed/
│       ├── jobs_cleaned.csv
│       ├── job_skills.json
│       └── skill_frequency.csv
│
├── models/
│   ├── faiss_jobs.index
│   ├── job_id_map.json
│   ├── skills_dictionary.json
│   └── projects_cache.json
│
├── pipelines/
│   ├── ingest.py                # FR-01 ✅
│   ├── extract_skills.py        # FR-02 ✅
│   └── embed.py                 # FR-03
│
├── api/
│   ├── main.py                  # FastAPI app
│   ├── models.py                # Pydantic schemas
│   └── services/
│       ├── matcher.py           # FR-04
│       ├── gap.py               # FR-05
│       ├── recommender.py       # FR-06
│       └── chatbot.py           # FR-08 (Agentic RAG + tools)
│
├── frontend/                    # FR-09
│   ├── django_backend/          # Django 5 + DRF
│   │   ├── manage.py
│   │   ├── config/              # settings, urls, wsgi
│   │   ├── accounts/            # register, login, logout
│   │   └── proxy/               # views forwarding to FastAPI
│   └── react_app/               # React 18 + Vite
│       ├── src/
│       │   ├── api/             # typed Axios client
│       │   ├── components/
│       │   │   ├── SkillInput.tsx
│       │   │   ├── JobCard.tsx
│       │   │   ├── GapChart.tsx
│       │   │   ├── ProjectCard.tsx
│       │   │   ├── SkillFreqChart.tsx
│       │   │   └── ChatInterface.tsx  # Shows tool_calls_made
│       │   └── App.tsx
│       ├── vite.config.ts
│       └── package.json
│
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.frontend
│
├── eval/
│   ├── precision_at_k.py        # FR-04 evaluation
│   ├── ragas_eval.py            # FR-10 RAG evaluation ← NEW
│   └── ragas_questions.json     # 50-question eval dataset ← NEW
│
└── tests/
    ├── test_ingest.py           # ✅ passing
    ├── test_skills.py           # ✅ passing
    ├── test_embed.py
    ├── test_api.py
    ├── test_chatbot.py          # FR-08 agent tool routing tests
    └── test_ragas.py            # FR-10 smoke tests ← NEW
```

---

# 07 Success Metrics & Evaluation

| Category | Metric                         | Target                 | Measurement                             |
| :------- | :----------------------------- | :--------------------- | :-------------------------------------- |
| Quality  | Precision@5 (job matching)     | ≥ 0.80                 | `eval/precision_at_k.py` on 100 queries |
| Quality  | RAG faithfulness (RAGAS)       | ≥ 0.85                 | `eval/ragas_eval.py` · 50 questions     |
| Quality  | RAG answer relevancy (RAGAS)   | ≥ 0.80                 | `eval/ragas_eval.py` · 50 questions     |
| Quality  | RAG context precision (RAGAS)  | ≥ 0.75                 | `eval/ragas_eval.py` · 50 questions     |
| Quality  | Project usefulness rating      | ≥ 4.0 / 5.0            | Internal review of 20 outputs           |
| Quality  | Skill extraction recall        | ≥ 80% on 50 random JDs | Manual audit                            |
| Perf     | POST /analyze latency p95      | < 500ms (no LLM)       | locust, 10 concurrent users             |
| Perf     | POST /chat latency p95         | < 3s                   | locust load test                        |
| Perf     | FAISS vector search            | < 100ms on 10k vectors | pytest-benchmark                        |
| LLMOps   | LLM call trace coverage        | 100% of FR-06/08 calls | Langfuse dashboard                      |
| LLMOps   | Avg LLM latency (Gemini Flash) | < 1s p50               | Langfuse metrics                        |
| Data     | Job postings ingested          | ≥ 10,000 unique        | `ingestion_report.json`                 |
| Data     | Unique skills in dictionary    | ≥ 200                  | `len(skill_frequency.csv)`              |

---

# 08 Technology Stack

| Layer          | Technology                                                   | Rationale                                                                    |
| :------------- | :----------------------------------------------------------- | :--------------------------------------------------------------------------- |
| Language       | Python 3.11                                                  | Type hints, performance improvements                                         |
| API            | FastAPI + Uvicorn                                            | Auto OpenAPI docs; async-ready                                               |
| Data           | pandas 2.x + pyarrow                                         | Parquet support; fast filtering on 50k rows                                  |
| NLP            | JobBERT fine-tuned on SkillSpan (`jjzha/jobbert-base-cased`) | Domain-specific NER; F1 ≥ 0.85 on job postings                               |
| Embeddings     | sentence-transformers all-MiniLM-L6-v2                       | Local, no API cost, 384-dim, strong quality                                  |
| Vector DB      | FAISS IndexFlatIP                                            | < 100ms on 50k vectors; no external service                                  |
| LLM            | Gemini 2.0 Flash (google-genai)                              | Free tier; structured JSON output; fast                                      |
| Agent          | LangChain ReAct Agent                                        | Tool-use decision loop; conversation memory                                  |
| RAG Eval       | RAGAS                                                        | Automated faithfulness + relevancy scoring                                   |
| Observability  | Langfuse                                                     | LLM tracing, cost tracking, prompt versioning                                |
| Validation     | Pydantic v2                                                  | All API I/O + settings management                                            |
| Frontend       | React 18 + TypeScript + Vite                                 | Hireable stack; type-safe; fast HMR                                          |
| User-facing BE | Django 5 + Django REST Framework                             | Auth built-in; proxy layer; Calgary/.NET market familiar with Django pattern |
| Styling        | Tailwind CSS                                                 | Rapid UI development                                                         |
| Charts         | Recharts                                                     | Skill frequency visualizations                                               |
| Deploy         | Azure Static Web Apps + App Service (GitHub Education $100)  | Calgary market signal; free via student credit                               |
| Testing        | pytest + pytest-benchmark                                    | Unit + performance tests                                                     |
| Container      | Docker + Docker Compose                                      | Production deployment; reproducible env                                      |
| Storage        | CSV/Parquet → PostgreSQL (Phase 2)                           | CSV for Phase 1; Postgres when multi-user                                    |

---

# 09 Milestones & Deliverables

| Phase            | Timeline | Deliverables                                                              | Done When                                                                                           |
| :--------------- | :------- | :------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------- |
| P1 — Data        | Week 1–2 | FR-01 ✅, FR-02 ✅, +4th dataset for 10k rows                             | `jobs_cleaned.csv` ≥ 10k · `skill_frequency` ≥ 200 skills                                           |
| P2 — ML Core     | Week 3–4 | FR-03 Embeddings + FAISS, FR-04 Matching, FR-05 Gap                       | All FRs pass tests · Precision@5 ≥ 0.80                                                             |
| P3 — LLM + Agent | Week 5   | FR-06 LLM Recommendations, FR-08 Agentic RAG, FR-10 RAGAS, FR-11 Langfuse | Agent calls tools correctly · RAGAS meets targets · all LLM calls traced                            |
| P4 — API         | Week 6   | FR-07 FastAPI complete, auth + rate limiting, all tests                   | POST /analyze < 500ms · /chat < 3s · /docs loads                                                    |
| P5 — Deploy      | Week 7–8 | FR-09 Django + React Frontend, Dockerfiles, Azure deploy                  | Django proxy works · React UI live · Azure Static Web Apps + App Service deployed · README complete |

---

# 10 Risks & Mitigations

| Risk                           | Likelihood | Impact | Mitigation                                                       |
| :----------------------------- | :--------- | :----- | :--------------------------------------------------------------- |
| Dataset < 10k rows             | High       | High   | Add 4th Kaggle dataset (LinkedIn 33k rows)                       |
| Agent selects wrong tool       | Medium     | Medium | Unit test each tool independently; test 20 question/tool pairs   |
| LLM hallucinates projects      | Medium     | Medium | Strict JSON schema; hours/difficulty constraints; fallback cache |
| RAG faithfulness < 0.85        | Medium     | High   | Tighten system prompt; add "only use context" constraint         |
| FAISS degrades > 50k vectors   | Low        | High   | Switch to IndexIVFFlat with nlist=100                            |
| API latency > 500ms under load | Medium     | Medium | Async FastAPI; FAISS in-memory; non-blocking LLM calls           |
| Langfuse free tier rate limits | Low        | Low    | Batch trace upload; sampling in high-volume scenarios            |

---

# 11 Phase 2 — Optional Extensions

| Feature                      | Description                                                                                                                 | Dependencies                              |
| :--------------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------- |
| ~~JobBERT Skill Extraction~~ | ✅ **Done in Phase 1** — `jjzha/jobbert-base-cased` fine-tuned on SkillSpan, integrated in FR-02. Run `make train-jobbert`. | FR-02 complete                            |
| ESCO Taxonomy Validation     | Validate extracted skills against 13,890-skill ESCO taxonomy. Eliminates manual stopword filtering.                         | JobBERT complete · ESCO CSV downloaded    |
| PostgreSQL Migration         | Replace CSV with PostgreSQL + pgvector for multi-user support and concurrent writes.                                        | Phase 1 complete · Docker Compose         |
| Location Intelligence        | Compare skill demand across Calgary, Toronto, Vancouver. Surface city-specific trending skills.                             | FR-05 complete · location field populated |
| Skill Trend Analysis         | Track skill demand over time. Surface top-10 rising skills per role per quarter.                                            | FR-01/02 complete · date field populated  |
| Multi-Role Blending          | User inputs multiple target roles. System returns blended skill gap across all targets.                                     | FR-05 complete                            |

---

_End of PRD v4.0 — AI Job Skills & Project Recommendation System_
