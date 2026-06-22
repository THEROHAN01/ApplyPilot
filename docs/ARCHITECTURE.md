# ApplyPilot — Architecture

How the pieces fit together: the system topology, the request path, how each agent
moves data, and the provider-agnostic AI layer. For the *why* behind each decision see
`DESIGN_DOCUMENT.md`; for endpoint and table detail see `API_REFERENCE.md` and
`DATABASE_SCHEMA.md`.

---

## 1. System diagram

```
                              ┌─────────────────────────────┐
                              │   Next.js 14 (App Router)    │
                              │  Blueprint tokens + Tailwind │
                              │  React Query + Zustand       │
                              └──────────────┬──────────────┘
                                             │ HTTPS (JWT bearer)
                                             │ lib/api.ts (axios + refresh)
                              ┌──────────────▼──────────────┐
                              │        FastAPI (8000)        │
                              │  routers / schemas / deps    │
                              │  RateLimitMiddleware · CORS  │
                              │  get_current_user (JWT)      │
                              └───┬──────────┬──────────┬────┘
                                  │          │          │
                  ┌───────────────▼──┐  ┌────▼─────┐ ┌──▼────────────┐
                  │  PostgreSQL 16   │  │  Redis   │ │   MinIO (S3)  │
                  │  + pgvector      │  │ broker / │ │  resumes /    │
                  │  (SQLAlchemy)    │  │ cache /  │ │  artifacts    │
                  │  host :5433      │  │ ratelim  │ │  :9000/:9001  │
                  └───────▲──────────┘  └────▲─────┘ └───────────────┘
                          │                  │ broker/result (Phase 2+)
              ┌───────────┴──────────────────┴──────────────┐
              │       Celery workers + beat  (Phase 2+)      │
              │  scrape · contact-find · generate · fill ·   │
              │  follow-up · feedback-learn · gmail-poll     │
              └───┬───────────────┬──────────────┬───────────┘
                  │               │              │
        ┌─────────▼──┐   ┌────────▼────────┐  ┌──▼──────────────┐
        │ Playwright │   │  AI provider    │  │ External APIs   │
        │ (scrape +  │   │  layer          │  │ SerpAPI/Hunter/ │
        │  ATS fill) │   │  (Sarvam → …)   │  │ Gmail/Stripe    │
        └────────────┘   └────────┬────────┘  └─────────────────┘
                                  │
                       ┌──────────▼───────────────────────┐
                       │ Local embeddings (bge-large-en)   │
                       │ loaded in worker process          │
                       └───────────────────────────────────┘
```

**What exists today (Phase 1):** the top three rows — Next.js, FastAPI, and the
PostgreSQL/Redis/MinIO data plane. The Celery row and everything below it is dashed-in
for Phases 2–6. Redis is wired and used today **only** by the rate limiter; it becomes
the Celery broker in Phase 2.

---

## 2. Request path: frontend → API → (Celery) → external

Synchronous reads/writes (all of Phase 1):

```
Browser
  └─ React component
       └─ React Query hook (useJobs / useApplications / …)
            └─ lib/api.ts  (axios instance)
                 • request interceptor injects  Authorization: Bearer <access JWT>
                 • on 401 → single-flight POST /auth/refresh → retry once
                      └─ HTTP →  FastAPI :8000
                                   • RateLimitMiddleware (Redis sliding window)
                                   • CORSMiddleware
                                   • router dependency get_current_user → decode JWT,
                                     load User, inject
                                   • Pydantic validates body
                                   • handler runs SQLAlchemy query (filtered by user_id)
                                   • returns Pydantic response model
```

Asynchronous work (Phase 2+), e.g. "generate email for this job":

```
POST /applications/{id}/generate          (Phase 2 endpoint)
  └─ handler enqueues a Celery task, writes an agent_runs row (status=queued), returns 202
       └─ Celery worker picks up task (Redis broker)
            • agent_runs → running
            • EmailGeneratorAgent builds GenerationRequest
            • AI provider layer (Sarvam) returns AIResponse (JSON)
            • result written to applications.{email_subject,email_body,...}
            • agent_runs → done (result_json) | failed (error)
  Frontend polls GET /agent_runs/{id}  (or /applications/{id}) until status=done.
```

The `agent_runs` table is the contract between async workers and the UI: the frontend
never blocks on a worker; it polls a row.

---

## 3. Data flow per agent

Each agent is a plain Python class/function invoked by an idempotent Celery task. Inputs
come from the DB and external APIs; outputs are written back to the DB. Phase in parens.

| Agent | Reads | Calls | Writes | Phase |
|-------|-------|-------|--------|-------|
| **Job Scraper** | user resume embedding | Playwright (10 boards), local embeddings | `jobs` (dedup by company+role+posted_at), `jobs.jd_embedding`, `jobs.match_score`, `agent_runs` | 3 |
| **Contact Finder** | `jobs` (company/role) | SerpAPI, Playwright (LinkedIn), Hunter.io, SMTP probe | `contacts`, `agent_runs` | 4 |
| **Email Generator** | `jobs.jd_text`, user `resumes.parsed_text`, recruiter/tone | **AI provider layer** (Sarvam) | `applications.{email_subject,email_body,cover_letter,linkedin_msg}`, `agent_runs` | 2 |
| **Form Filler** | `applications`, target ATS URL, resume file (MinIO) | Playwright, **AI vision** (`AI_PROVIDER=anthropic`) | screenshots/artifacts (MinIO), `agent_runs`; submit only on user confirm | 6 |
| **Follow-up Scheduler** | `applications` sent & unreplied past `follow_up_at` | AI provider layer, Gmail send | `follow_ups`, `applications.follow_up_at`, `agent_runs` | 4 |
| **Feedback Learner** | `feedback`, `applications` reply outcomes, prompt templates | Gmail poll, AI provider layer | updated prompt templates, `feedback`, `agent_runs` | 6 |

Data-flow detail for the **Email Generator** (Phase 2, the first agent built):

```
jobs.jd_text ─┐
resumes.parsed_text ─┤
recruiter/company/role/tone ─┤
                             ▼
              EmailGeneratorAgent.build_request()
                             │  GenerationRequest(messages=[system, user], json mode)
                             ▼
              get_ai_provider()  ──►  SarvamProvider.generate()
                             │
                             ▼
              AIResponse(text=<json string>, usage, model)
                             │  parse + validate {subject, email_body, cover_letter, linkedin_message}
                             ▼
              applications row updated; status → "generated"; agent_runs → done
```

---

## 4. Provider-agnostic AI layer

The single most important architectural rule of Phase 2+: **no agent or router ever
imports an AI SDK.** They depend on a contract; the factory is the only code that knows
which provider is configured.

```
  .env  (AI_PROVIDER=sarvam)
        │
        ▼
  provider_factory.py        ← the ONLY place that knows providers exist
        │   reads AI_PROVIDER, constructs the matching provider
        ▼
  SarvamProvider             ← implements the AIProvider contract
   (or AnthropicProvider,       (one class per provider, same interface)
    OpenAIProvider,
    OllamaProvider)
        │   .generate(GenerationRequest) -> AIResponse
        ▼
  AIResponse                 ← agents receive THIS, always, from any provider
        │
        ▼
  EmailGeneratorAgent        ← zero knowledge of Sarvam or any SDK
```

Contract surface (full detail in `AI_PROVIDER_LAYER.md`):

- `AIMessage` — `{role: "system"|"user"|"assistant", content: str}`
- `GenerationRequest` — `{messages: list[AIMessage], model, temperature, max_tokens, json_mode, ...}`
- `AIResponse` — `{text: str, model: str, usage: {...}, raw: ...}`
- `get_ai_provider()` — returns the configured provider singleton
- `AIProvider` (abstract base) — `async generate(req: GenerationRequest) -> AIResponse`

Why this matters: switching from Sarvam to a local Ollama model for dev, or to Anthropic
for a vision-dependent phase, is **one line in `.env`** and zero code edits in any agent.
It also keeps every agent unit-testable with a fake provider — no network, no keys.

---

## 5. Tenancy & security boundaries

- **Trust boundary** is the FastAPI `get_current_user` dependency: every authed route
  resolves a `User` from the JWT before the handler runs. `/health` is the only
  unauthenticated route in Phase 1.
- **Tenant isolation** is enforced in application code: every query is filtered by
  `current_user.id`. Cross-user access returns **404**, never 403, to avoid ID enumeration.
- **DB-level RLS** policies exist in the migration but are inert without Supabase auth
  roles — they are the documented swap path, not the active mechanism.
- **Rate limiting** keys on the JWT `sub` (per user) or client IP, in a Redis sorted-set
  sliding window; it fails **open** if Redis is unreachable.
- **Secrets** live only in `settings` (backend) / `process.env.NEXT_PUBLIC_*` (frontend).
  Never inline. The logger scrubs token-shaped strings from messages.

---

## 6. Deployment topology (compose)

`docker compose up` starts: `db` (pgvector, host `5433`), `redis` (`6379`), `minio`
(`9000`/`9001`), `backend` (`8000`, reads `backend/.env.example` via `env_file`),
`frontend` (`3000`, `NEXT_PUBLIC_API_URL` baked at build). `backend` waits for `db`
healthy. Celery worker/beat services join compose in Phase 2.
