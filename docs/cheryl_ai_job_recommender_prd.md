| AI Job Skills & Project Recommendation System _Product Requirements Document • v2.0_ Status: Draft Target: Claude Code AI Pipeline Author: TBD Date: 2025 |
| :-------------------------------------------------------------------------------------------------------------------------------------------------------: |

| 6 Weeks Timeline | 4 Phases Delivery | 7 FRs Features | 10k+ Jobs Data Target |
| :--------------: | :---------------: | :------------: | :-------------------: |

# **01 Problem & Product Vision**

## **Problem Statement**

Developers transitioning into new roles — e.g., Software Engineer to AI Engineer — face three compounding challenges:

- Job postings contain required skills, but the data is unstructured and impractical to analyze manually.

- Engineers cannot quickly determine which of their existing skills transfer and which are missing.

- There is no data-driven mechanism to suggest portfolio projects that close skill gaps efficiently.

## **Solution**

Build an AI-powered pipeline that:

- Ingests and normalizes job postings at scale.

- Extracts required skills using NLP \+ LLM hybrid methods.

- Semantically matches user skill profiles to job embeddings via FAISS.

- Performs precise skill gap analysis (job skills minus user skills).

- Generates actionable portfolio project recommendations via an LLM.

- Exposes everything via a FastAPI REST layer \+ Streamlit dashboard.

## **Example User Workflow**

| INPUT Current skills : Python, TensorFlow, SQL Target role : ML Engineer Location : Calgary, AB OUTPUT Top matching jobs : ML Engineer, Data Scientist, AI Engineer Missing skills : PyTorch, Docker, AWS SageMaker Suggested projects : 1\. NLP document classifier with PyTorch \+ Docker deployment 2\. SageMaker model training & inference pipeline |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

# **02 Target Personas & User Stories**

## **Primary Personas**

| Persona                    | Background                        | Primary Goal                                                |
| :------------------------- | :-------------------------------- | :---------------------------------------------------------- |
| **Transitioning Engineer** | 5 yrs SWE, wants to move into ML  | Identify gaps vs ML Engineer JDs, get project ideas         |
| **Junior Developer**       | 0-2 yrs exp, recent bootcamp grad | Understand which skills are in demand, build portfolio fast |
| **CS Student**             | Final year, no industry exp       | Align coursework to real job requirements                   |

## **User Stories**

| ID        | Story                                                                                                                | Acceptance Criteria                                                                                                     |
| :-------- | :------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| **US-01** | As a transitioning engineer, I want to input my skills and target role so I can see which skills I am missing.       | Given valid skills \+ role, system returns missing_skills list within 2s. Empty input returns 400 error.                |
| **US-02** | As a user, I want to see the top 5 matching job postings for my profile so I can evaluate fit.                       | Top-5 jobs returned with title, match_score ≥ 0, sorted descending. No results returns empty array, not error.          |
| **US-03** | As a junior developer, I want AI-generated project ideas based on my skill gaps so I can build a targeted portfolio. | Returns 2-5 projects. Each has title, description, and skills_addressed. LLM failure returns cached fallback, not 500\. |
| **US-04** | As a user, I want to filter jobs by location so I can see market demand in my city.                                  | Location filter returns only postings matching city string. Invalid location returns empty list with 200 status.        |
| **US-05** | As a user, I want to see trending skills for my target role so I can prioritize learning.                            | Returns ordered skill list with demand_count. Data refreshes from dataset on each request.                              |

# **03 Functional Requirements**

**FR-01 Job Data Ingestion** Priority: **P0** Owner: Data Eng

Import, deduplicate, and normalize raw job postings into a clean dataset for downstream processing.

| Inputs         | • Raw CSV with fields: job_id, title, role, description, location, date                                                                                                                                                          |
| :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Processing** | 1\. Remove duplicate job_id entries 2\. Strip HTML tags and normalize whitespace 3\. Standardize role names to enum: \[ML Engineer, Data Scientist, AI Engineer, SWE, Data Engineer\] 4\. Drop rows missing description or title |
| **Outputs**    | • jobs_cleaned.csv • ingestion_report.json (row counts, dupe count, error count)                                                                                                                                                 |
| **Schema**     | job_id STRING NOT NULL UNIQUE title STRING NOT NULL role ENUM NOT NULL description TEXT NOT NULL location STRING NULLABLE date DATE NULLABLE                                                                                     |
| **Done When**  | **jobs_cleaned.csv exists, row count ≥ 10,000, zero duplicate job_ids, all role values in enum.**                                                                                                                                |

**FR-02 Skill Extraction** Priority: **P0** Owner: NLP

Extract a normalized list of technical skills from each job description using a hybrid NLP approach.

| Inputs         | • jobs_cleaned.csv                                                                                                                                                                                                                                                                     |
| :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Processing** | 1\. Method A: keyword matching against skills_dictionary.json (≥200 skills) 2\. Method B: spaCy NER \+ LLM extraction for skills not caught by dictionary 3\. Deduplicate and normalize skill names (e.g., "pytorch" → "PyTorch") 4\. Store results as job_id → \[skill_list\] mapping |
| **Outputs**    | • job_skills.json • skill_frequency.csv (skill, count, pct_of_jobs)                                                                                                                                                                                                                    |
| **Schema**     | { "job_id": "string", "skills": \["string"\] }                                                                                                                                                                                                                                         |
| **Done When**  | **Every job_id in cleaned dataset has a non-empty skills list. skill_frequency.csv has ≥200 unique skills.**                                                                                                                                                                           |

**FR-03 Embedding Generation** Priority: **P0** Owner: ML

Convert job descriptions and user skill profiles into dense vector embeddings for semantic similarity.

| Inputs         | • jobs_cleaned.csv • user_profile (skills list \+ target role)                                                                                                                                                                                                      |
| :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Processing** | 1\. Use sentence-transformers/all-MiniLM-L6-v2 (default) or OpenAI text-embedding-3-small 2\. Generate one embedding per job description 3\. Store in FAISS IndexFlatIP (inner product / cosine similarity) 4\. Cache embeddings; regenerate only on dataset change |
| **Outputs**    | • faiss_jobs.index • job_id_map.json (index position → job_id)                                                                                                                                                                                                      |
| **Schema**     | faiss_jobs.index — FAISS binary index file job_id_map.json — { "0": "job_124", "1": "job_125", ... }                                                                                                                                                                |
| **Done When**  | **FAISS index loads without error. Query returns results in \< 100ms on 10k vectors. Index size matches job count.**                                                                                                                                                |

**FR-04 Semantic Job Matching** Priority: **P0** Owner: ML

Return the top-k job postings most semantically similar to a user's skill profile.

| Inputs         | • user skills list • k (default=5, max=20) • optional: location filter                                                                                                                                                                                     |
| :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Processing** | 1\. Join user skills into a single string, embed with same model as FR-03 2\. Query FAISS index, retrieve top-k job_ids and cosine scores 3\. Apply location filter post-retrieval if provided 4\. Fetch job metadata from jobs_cleaned.csv for each match |
| **Outputs**    | • \[{ job_id, title, role, location, match_score, description_snippet }\]                                                                                                                                                                                  |
| **Done When**  | **Returns ≥1 result for any valid skill input. Scores in range \[0,1\]. Precision@5 ≥ 0.8 on evaluation set. Latency \< 200ms.**                                                                                                                           |

**FR-05 Skill Gap Analysis** Priority: **P0** Owner: ML

Compute the delta between the skills required for a target role and the skills the user already has.

| Inputs         | • user_skills: list\[str\] • target_role: str (must match role enum)                                                                                                                                                                                                                                                     |
| :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Processing** | 1\. Aggregate all skills for postings in target_role from job_skills.json 2\. Compute frequency threshold: skills appearing in ≥30% of role postings are "required" 3\. missing_skills \= required_skills − user_skills (case-insensitive set difference) 4\. Compute match_score \= len(matched) / len(required) \* 100 |
| **Outputs**    | • { matched_skills, missing_skills, match_score, total_required }                                                                                                                                                                                                                                                        |
| **Done When**  | **missing_skills is never null (empty list if full match). match_score is float 0–100. Deterministic output for same inputs.**                                                                                                                                                                                           |

**FR-06 AI Project Recommendations** Priority: **P1** Owner: LLM

Generate 2–5 concrete portfolio project ideas that address the user's missing skills for their target role.

| Inputs         | • missing_skills: list\[str\] • target_role: str • user_skills: list\[str\] (context)                                                                                                                                                                                                                                                                       |
| :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ----------------------------------- |
| **Processing** | 1\. Build structured prompt with constraints (see CLAUDE.md prompt template) 2\. Call Claude claude-sonnet-4-20250514 via GEMINI API 3\. Parse structured JSON response 4\. Validate each project has: title, description, skills_addressed, difficulty, estimated_hours 5\. On LLM failure: return top-3 cached fallback projects from projects_cache.json |
| **Outputs**    | • \[{ title, description, skills_addressed, difficulty, estimated_hours }\]                                                                                                                                                                                                                                                                                 |
| **Schema**     | { "title": "str", "description": "str", "skills_addressed": \["str"\], "difficulty": "Beginner                                                                                                                                                                                                                                                              | Intermediate | Advanced", "estimated_hours": int } |
| **Done When**  | **Returns 2-5 projects. Each project addresses ≥1 missing skill. LLM timeout (\>10s) falls back to cache without 500 error.**                                                                                                                                                                                                                               |

**FR-07 REST API Layer** Priority: **P0** Owner: Backend

Expose all pipeline functionality via a documented FastAPI REST interface.

| Inputs         | • See endpoint specs below                                                                                                                                              |
| :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Processing** | 1\. Validate all inputs with Pydantic models 2\. Return consistent error envelope: { error, message, request_id } 3\. Log all requests with request_id for traceability |
| **Outputs**    | • See endpoint specs below                                                                                                                                              |
| **Done When**  | **All endpoints return correct status codes. /health returns 200\. /docs (Swagger) loads without error. Pydantic rejects bad input with 422\.**                         |

# **04 API Contract**

## **POST /analyze — Skill Gap Analysis**

| // REQUEST { "skills" : \["Python", "TensorFlow", "SQL"\], "target_role" : "ML Engineer", "location" : "Calgary" // optional } // RESPONSE 200 { "top_jobs" : \[{ "job_id": "str", "title": "str", "match_score": 0.92, "location": "str" }\], "matched_skills": \["Python", "SQL"\], "missing_skills": \["PyTorch", "Docker", "AWS"\], "match_score" : 40.0, "projects" : \[{ "title": "str", "description": "str", "skills_addressed": \["PyTorch"\] }\] } // ERROR ENVELOPE { "error": "VALIDATION_ERROR", "message": "str", "request_id": "uuid" } |
| :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

## **GET /top_skills?role={role}\&limit={n}**

| // RESPONSE 200 { "role" : "ML Engineer", "skills": \[ { "skill": "Python", "demand_count": 8420, "pct_of_jobs": 0.94 }, { "skill": "PyTorch", "demand_count": 6130, "pct_of_jobs": 0.68 } \] } |
| :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

## **GET /health**

| { "status": "ok", "version": "1.0.0", "dataset_rows": 10523, "index_size": 10523 } |
| :--------------------------------------------------------------------------------- |

| Status  | Code                | When                                          |
| :------ | :------------------ | :-------------------------------------------- |
| **200** | OK                  | Successful response                           |
| **400** | BAD_REQUEST         | Missing required field                        |
| **422** | VALIDATION_ERROR    | Pydantic schema violation (e.g. unknown role) |
| **404** | NOT_FOUND           | job_id not found                              |
| **503** | SERVICE_UNAVAILABLE | LLM or FAISS unavailable; fallback triggered  |

# **05 CLAUDE.md Reference — What Claude Code Must Know**

Claude Code reads CLAUDE.md automatically at session start. Create this file at the repo root. Below is the complete required content.

| \# CLAUDE.md — AI Job Skills Recommender \#\# Project Purpose AI pipeline: ingest job data → extract skills → embed → FAISS match → gap analysis → LLM projects. \#\# Architecture data/raw/ → pipelines/ingest.py → data/processed/jobs_cleaned.csv → pipelines/extract_skills.py → data/processed/job_skills.json → pipelines/embed.py → models/faiss_jobs.index api/main.py (FastAPI) → services/matcher.py, services/gap.py, services/recommender.py ui/app.py (Streamlit) \#\# Commands make ingest \# runs pipelines/ingest.py make extract \# runs pipelines/extract_skills.py make embed \# runs pipelines/embed.py make api \# uvicorn api.main:app \--reload \--port 8000 make ui \# streamlit run ui/app.py make test \# pytest tests/ \-v make eval \# python eval/precision_at_k.py \#\# Code Style \- Python 3.11, type hints on all functions, docstrings on all public methods \- Black formatter, isort imports, max line length 100 \- Pydantic v2 models for all API I/O \- No hardcoded paths — use config/settings.py (pydantic-settings) \#\# LLM Prompt Template (FR-06) system: "You are a senior ML engineer. Return ONLY valid JSON. No markdown, no explanation." user: "Generate {n} portfolio projects for a developer targeting {role}. Missing skills: {missing_skills}. Existing skills: {user_skills}. Each project must: use ≥1 missing skill, be completable in ≤40 hours, be deployable to GitHub. Return JSON array matching ProjectRecommendation schema." \#\# Critical Constraints \- FAISS index must be rebuilt when dataset changes (detect via hash) \- All API inputs validated with Pydantic before any processing \- LLM calls must have 10s timeout \+ fallback to projects_cache.json \- Skill normalization must be case-insensitive (store canonical form in skills_dictionary.json) \- Never log user skill lists to disk (PII consideration) |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |

# **06 Project Folder Structure**

| ai-job-recommender/ ├── CLAUDE.md \# ← Claude Code reads this first ├── Makefile \# ingest | extract | embed | api | ui  | test | eval ├── README.md ├── pyproject.toml │ ├── config/ │ └── settings.py \# pydantic-settings, all env vars │ ├── data/ │ ├── raw/ \# original CSVs (gitignored if large) │ └── processed/ │ ├── jobs_cleaned.csv │ ├── job_skills.json │ └── skill_frequency.csv │ ├── models/ │ ├── faiss_jobs.index │ ├── job_id_map.json │ └── skills_dictionary.json \# canonical skill list ≥200 skills │ ├── pipelines/ │ ├── ingest.py \# FR-01 │ ├── extract_skills.py \# FR-02 │ └── embed.py \# FR-03 │ ├── api/ │ ├── main.py \# FastAPI app, /analyze, /top_skills, /health │ ├── models.py \# Pydantic request/response schemas │ └── services/ │ ├── matcher.py \# FR-04 │ ├── gap.py \# FR-05 │ └── recommender.py \# FR-06 │ ├── ui/ │ └── app.py \# Streamlit dashboard │ ├── eval/ │ └── precision_at_k.py \# evaluation harness │ └── tests/ ├── test_ingest.py ├── test_skills.py ├── test_api.py └── fixtures/ |
| :----------------------------------------------------------------------------------------- | ------- | ----- | --- | --- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

# **07 Success Metrics & Evaluation**

| Category    | Metric                      | Target                                  | Measurement                                   |
| :---------- | :-------------------------- | :-------------------------------------- | :-------------------------------------------- |
| **Quality** | Precision@5 (job matching)  | **≥ 0.80**                              | eval/precision_at_k.py on 100 labeled queries |
| **Quality** | Skill extraction recall     | **≥ 80% of known skills found**         | Manual audit of 50 random job descriptions    |
| **Quality** | Project usefulness rating   | **≥ 4.0 / 5.0**                         | Internal review of 20 generated outputs       |
| **Perf**    | POST /analyze latency (p95) | **\< 500ms (no LLM), \< 5s (with LLM)** | locust load test, 10 concurrent users         |
| **Perf**    | FAISS vector search         | **\< 100ms on 10k vectors**             | pytest benchmark                              |
| **Data**    | Job postings ingested       | **≥ 10,000 unique**                     | ingestion_report.json                         |
| **Data**    | Unique skills in dictionary | **≥ 200**                               | len(skills_dictionary.json)                   |

# **08 Technology Stack**

| Layer          | Technology                                       | Rationale / Notes                                       |
| :------------- | :----------------------------------------------- | :------------------------------------------------------ |
| **Language**   | **Python 3.11**                                  | Type hints, match-case, performance improvements        |
| **API**        | **FastAPI \+ Uvicorn**                           | Auto-generated OpenAPI docs; async-ready                |
| **Data**       | **pandas 2.x \+ pyarrow**                        | Parquet support; fast filtering on 50k rows             |
| **NLP**        | **spaCy 3.x \+ NLTK**                            | Tokenization, entity recognition for skill extraction   |
| **Embeddings** | **sentence-transformers (all-MiniLM-L6-v2)**     | Local, no API cost, 384-dim, strong semantic quality    |
| **Vector DB**  | **FAISS (IndexFlatIP)**                          | \< 100ms on 50k vectors; no external service dependency |
| **LLM**        | **GEMINI**                                       | Structured JSON output; reliable tool use               |
| **Validation** | **Pydantic v2**                                  | All API I/O; settings via pydantic-settings             |
| **UI**         | **Streamlit 1.x**                                | Fast prototyping; built-in charting                     |
| **Viz**        | **Plotly**                                       | Skill trend charts, location comparison                 |
| **Testing**    | **pytest \+ pytest-benchmark**                   | Unit \+ perf tests                                      |
| **Storage**    | **CSV/Parquet (Phase 1), PostgreSQL (Phase 2\)** | CSV for simplicity; Postgres when multi-user needed     |

# **09 Milestones & Deliverables**

| Phase  | Timeline | Deliverables                                                                    | Done When                                                          |
| :----- | :------- | :------------------------------------------------------------------------------ | :----------------------------------------------------------------- |
| **P1** | Week 1–2 | Dataset ingestion (FR-01), Skill extraction (FR-02), skills_dictionary.json     | jobs_cleaned.csv ≥10k rows; skill_frequency.csv ≥200 skills        |
| **P2** | Week 3–4 | Embeddings \+ FAISS (FR-03), Job matching (FR-04), Skill gap (FR-05)            | All FRs pass unit tests; Precision@5 ≥ 0.80 on eval set            |
| **P3** | Week 5   | LLM project generator (FR-06), evaluation harness, projects_cache.json fallback | Returns 2–5 projects; LLM timeout handled; usefulness ≥ 4/5        |
| **P4** | Week 6   | FastAPI layer (FR-07), Streamlit dashboard, Docker Compose, README              | /analyze \< 500ms p95; /docs loads; Docker Compose brings up stack |

# **10 Risks & Mitigations**

| Risk                                          | Likelihood | Impact     | Mitigation                                                                 |
| :-------------------------------------------- | :--------- | :--------- | :------------------------------------------------------------------------- |
| Skill extraction misses domain-specific tools | **High**   | **Medium** | Hybrid dictionary \+ LLM; manual audit of 50 JDs; expandable dictionary    |
| LLM hallucinates unrealistic projects         | **Medium** | **Medium** | Strict JSON schema in prompt; difficulty/hours constraints; fallback cache |
| Dataset skewed toward US roles                | **Medium** | **Low**    | Supplement with Kaggle \+ LinkedIn scrapes; location filter in API         |
| FAISS search degrades \>50k vectors           | **Low**    | **High**   | Switch to IndexIVFFlat with nlist=100 for larger datasets                  |
| API latency \>500ms under load                | **Medium** | **Medium** | Async FastAPI; FAISS in-memory; LLM calls non-blocking with fallback       |

# **11 Phase 2 — Optional Extensions**

| Feature                     | Description                                                                                                       | Dependencies                                |
| :-------------------------- | :---------------------------------------------------------------------------------------------------------------- | :------------------------------------------ |
| **Trend Analyzer**          | Track skill demand over time using date field in job postings. Surface top-10 rising skills per role per quarter. | FR-01, FR-02 complete; date field populated |
| **Location Comparison**     | Compare skill demand across cities (Calgary vs Toronto vs Vancouver). Surface city-specific in-demand skills.     | location field populated in ≥70% of rows    |
| **Multi-Role Support**      | Allow user to input multiple target roles and see blended skill gap across all.                                   | FR-05 complete                              |
| **Visualization Dashboard** | Streamlit pages for: skill demand bar chart, skill gap radar, project board with difficulty filter.               | FR-07 complete; Plotly                      |
| **PostgreSQL Migration**    | Replace CSV/parquet with PostgreSQL for multi-user support, query performance, and concurrent writes.             | Phase 1 complete; Docker Compose            |

_End of PRD v2.0 — AI Job Skills & Project Recommendation System_
