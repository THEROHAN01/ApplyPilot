# Phase 2 — AI Generation Engine

Status: **NEXT (not started)**
Branch: create `phase-2` from `main`.

This is a complete, standalone build spec. With this file + `CLAUDE.md` +
`docs/AI_PROVIDER_LAYER.md` + the existing Phase 1 code, a fresh session can build all of
Phase 2. Read `docs/AI_PROVIDER_LAYER.md` first — it is the contract this phase implements.

---

## 1. Overview

Phase 2 turns the static CRM into a generator. It delivers:
- A **provider-agnostic AI layer** (`services/ai/`) with **Sarvam AI** as the default provider.
- A **local embeddings service** (`BAAI/bge-large-en-v1.5`, 1024-d) that fills `resumes.embedding` and `jobs.jd_embedding`.
- A **resume↔JD match score** written to `jobs.match_score` (cosine via pgvector).
- An **Email Generator agent** that produces `{subject, email_body, cover_letter, linkedin_message}` from a JD + resume.
- **Celery** (worker + beat scaffold) wired to Redis, with `agent_runs` tracking.
- A **generate endpoint** the frontend calls, plus an `agent_runs` polling endpoint.
- Frontend: a "Generate" CTA on the job/application detail and an **email preview/edit modal**.

Demo at the end: pick a job → click Generate → watch the application fill with a tailored
email/cover letter/LinkedIn message → edit → save.

---

## 2. Provider-agnostic AI layer (`backend/services/ai/`)

Build exactly the package in `docs/AI_PROVIDER_LAYER.md` §1:

```
services/ai/
├── __init__.py     # re-export get_ai_provider, GenerationRequest, AIResponse, AIMessage
├── base.py         # AIProvider (ABC); AIMessage, GenerationRequest, AIResponse (Pydantic)
├── factory.py      # get_ai_provider() — reads settings.ai_provider, caches instances
├── errors.py       # AIError, AIProviderUnavailable (→503), AIBadResponse
└── providers/
    ├── __init__.py
    ├── sarvam.py    # SarvamProvider (default)
    ├── anthropic.py # AnthropicProvider (text now; vision used in Phase 6)
    ├── openai.py    # OpenAIProvider (optional)
    └── ollama.py    # OllamaProvider (local dev)
```

Contract (fields/types) is in `docs/AI_PROVIDER_LAYER.md` §2. **Hard rule:** agents,
routers, and tasks import only from `services.ai` — never an SDK (§3 there).

Add to `config.py`: `ai_provider` (default `"sarvam"`), `sarvam_api_key`,
`sarvam_model` (default `"sarvam-105b"`), `anthropic_api_key`, `anthropic_model`,
`openai_api_key`, `openai_model`, `openai_base_url`, `ollama_base_url`, `ollama_model`.
Document each in `docs/ENVIRONMENT_VARIABLES.md` (rows already drafted there).

`get_ai_provider()` raises `AIProviderUnavailable` when the selected provider's key is
missing; the generate route maps that to `503 {"error":"feature_unavailable","reason":"api_key_not_configured"}`.

## 3. Sarvam AI integration (`providers/sarvam.py`)

Gotchas (repeat from `AI_PROVIDER_LAYER.md` §6 — getting these wrong fails silently):
- Method is **`client.chat.completions(...)`**, NOT `.completions.create(...)`.
- Constructor param is **`api_subscription_key`**, NOT `api_key`.
- Use **`AsyncSarvamAI`** in async contexts.

```python
from sarvamai import AsyncSarvamAI

client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
response = await client.chat.completions(
    model=settings.sarvam_model,
    messages=[{"role": m.role, "content": m.content} for m in req.messages],
    response_format={"type": "json_object"} if req.json_mode else None,
    temperature=req.temperature,
    max_tokens=req.max_tokens,
)
# Note: method is .completions() NOT .completions.create()
```

- **JSON mode:** pass `response_format={"type":"json_object"}`. Still defensively
  `json.loads()` the result and raise `AIBadResponse` on parse failure (the generator
  retries once with a stricter system instruction).
- **Retry/backoff:** wrap transient errors (HTTP 429/5xx, timeouts) with exponential
  backoff (e.g. `tenacity`, 3 attempts). Missing key → non-retryable `AIProviderUnavailable`.
- **Usage:** populate `AIResponse.usage` from the response when available; log via the
  PII-scrubbing logger with `metadata.task_type`/`user_id` (never log full prompt bodies).

## 4. Email generator agent (`backend/agents/email_generator.py`)

- Class `EmailGeneratorAgent` with a method like `generate(application, resume, tone) -> dict`.
- Builds a `GenerationRequest` (system prompt from `backend/prompts/cold_email.txt`; user
  message from JD text + resume parsed text + company/role/recruiter/tone), `json_mode=True`.
- Calls `get_ai_provider().generate(req)`, parses JSON into
  `{subject, email_body, cover_letter, linkedin_message}`, validates with a Pydantic model.
- Writes results onto the `applications` row; sets `status="generated"`.
- **Zero SDK imports.** Unit-tested against a fake `AIProvider` (no network).
- Add `backend/prompts/cold_email.txt` — the prompt template (instructs strict JSON output, persona = a concise, specific student applicant; no fabricated experience).

## 5. Embeddings service (`backend/services/embeddings.py`)

- Loads `sentence-transformers` model `BAAI/bge-large-en-v1.5` once at worker startup (1024-d output). Lazy/global singleton — heavy; never load per request.
- `embed_text(text: str) -> list[float]` and `embed_batch(texts) -> list[list[float]]`.
- Used to fill `resumes.embedding` (on upload/parse) and `jobs.jd_embedding`.
- **Match score:** cosine similarity (pgvector `<=>` cosine distance → `1 - distance`)
  between a user's active resume embedding and a job's `jd_embedding`, written to
  `jobs.match_score`. Provide a helper that runs the ranking query via SQLAlchemy +
  pgvector. (Resume text extraction from PDF/DOCX also lands here or in `utils/text_parser.py`.)

## 6. Celery tasks (`backend/tasks/`)

```
tasks/
├── __init__.py
├── celery_app.py     # Celery() with Redis broker+backend from settings.redis_url
└── generation.py     # generate_email_task, embed_resume_task, score_jobs_task
```
- Every task: idempotent, with `autoretry_for=(AIError, ...)`, `max_retries`, `default_retry_delay`.
- Each task writes an `agent_runs` row: `queued → running → done|failed` (store output in `result_json`, error text in `error`, set `started_at`/`finished_at`).
- Add **`celery-worker`** (and a **`celery-beat`** placeholder) services to `docker-compose.yml`, sharing the backend image, depending on `redis` + `db`.

## 7. New API endpoints

| Method | Path | Auth | Body / Notes |
|--------|------|------|--------------|
| POST | `/applications/{id}/generate` | yes | Body: `{tone?}`. Enqueues `generate_email_task`, creates an `agent_runs` row, returns **202** `{agent_run_id}`. 503 if AI key missing. 404 if not owned. |
| GET | `/agent_runs/{id}` | yes | Returns `{id, task_type, status, result_json, error, created_at, finished_at}`. Owner-scoped (404 otherwise). |
| GET | `/agent_runs` | yes | List the user's recent runs (optional `?task_type=`/`?status=`). |
| POST | `/resumes/{id}/parse` *(optional)* | yes | Trigger parse+embed for an uploaded resume (or do it inline on upload). |

Follow the Phase 1 router conventions (OpenAPI summary, Google docstrings, `get_current_user`, owner-scoped 404, correct status codes). Add Pydantic schemas under `schemas/agent_run.py`.

## 8. Frontend additions

- **Generate CTA** on `app/(dashboard)/jobs/[id]` and/or `applications/[id]`: calls
  `POST /applications/{id}/generate` via a `lib/api.ts` hook, then **polls** `GET
  /agent_runs/{id}` (React Query `refetchInterval` until `done`/`failed`).
- **Email preview/edit modal** (Radix dialog, Blueprint-themed): shows
  subject/email_body/cover_letter/linkedin_msg, editable, saves via
  `PATCH /applications/{id}`.
- Loading/error/empty/success states everywhere; disable the Generate button while a run
  is in flight; surface the 503 `feature_unavailable` as a friendly "AI not configured" state.
- Extend `types/index.ts` with `AgentRun` and the generate request/response types. No `any`.
- Blueprint tokens only — no hardcoded colors.

## 9. Test requirements

- `tests/test_agents/test_email_generator.py` — fake `AIProvider`; assert JSON parse,
  Pydantic validation, that the application row is updated and `status` becomes `generated`,
  and the retry-on-bad-JSON path.
- `tests/test_services/test_ai_factory.py` — `get_ai_provider()` returns the configured
  provider; missing key raises `AIProviderUnavailable`; **assert no agent/router/task
  imports an SDK** (grep test or import check).
- `tests/test_services/test_embeddings.py` — mock the model; assert 1024-d output and
  cosine ranking helper (or mark as integration if loading the real model).
- `tests/test_generation_routes.py` — `POST /generate` returns 202 + creates `agent_runs`;
  503 when key missing; 404 cross-user; `GET /agent_runs/{id}` owner-scoping.
- Mock Sarvam/all providers — **no real API calls in tests**. Keep coverage ≥70%.

## 10. Build order

1. `services/ai/base.py` + `errors.py` (contract first). Compile-check.
2. `providers/sarvam.py`, then `factory.py`; add `config.py` fields. Unit-test the factory with a fake key.
3. `services/embeddings.py` (+ resume text parsing). Unit-test (mock the model).
4. `prompts/cold_email.txt` + `agents/email_generator.py`. Unit-test against a fake provider.
5. `tasks/celery_app.py` + `tasks/generation.py`; `agent_runs` schema + writes. Import-check the worker.
6. `schemas/agent_run.py` + `routers/agent_runs.py` + `POST /applications/{id}/generate`; register in `main.py`. curl each.
7. Compose: add `celery-worker`/`celery-beat`. `docker compose config` + boot check.
8. Frontend: hooks, Generate CTA, preview/edit modal, polling. `tsc`/eslint/build.
9. Full test pass; update `docs/API_REFERENCE.md`, `docs/ARCHITECTURE.md` (mark the async path live), `docs/phases/PHASE_2.md` status.

## 11. Quality gates (exact)

```bash
# Backend (Postgres up; Redis up for task tests)
cd backend && DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
  pytest tests/ --cov=. --cov-fail-under=70 -q

# No SDK leakage into business logic (must print nothing)
grep -rn "from sarvamai\|import sarvamai\|SarvamAI\|from anthropic\|import anthropic\|AsyncAnthropic\|from openai\|import openai" \
  backend/agents/ backend/routers/ backend/tasks/

# Celery imports cleanly
cd backend && python -c "from tasks.celery_app import app; print('ok')"

# Frontend
cd frontend && npx tsc --noEmit && npx eslint . --ext .ts,.tsx --max-warnings=0 && npx next build
```

## 12. New dependencies to add (`backend/requirements.txt`, pinned)

- `sarvamai` (Sarvam SDK)
- `celery[redis]`
- `sentence-transformers` (+ its torch dependency — large; document the image size impact)
- `tenacity` (retry/backoff)
- `pypdf` / `python-docx` (resume text extraction) as needed
- Re-pin: `pip install -r requirements.txt && pip freeze > requirements.lock.txt`
- Optionally `anthropic` / `openai` SDKs (only imported inside their provider modules).
