# ApplyPilot — Design Document

**Date:** 2026-06-19
**Status:** Approved decisions captured; awaiting user review before planning.

---

## 1. What we're building

ApplyPilot is an autonomous AI job-application engine for students and new grads. It
scrapes jobs from multiple sources, discovers recruiter contacts, generates
personalized outreach (emails / cover letters / LinkedIn messages) with Claude,
optionally auto-fills ATS forms, tracks every touchpoint in a CRM dashboard, sends
follow-ups, and learns from reply rates.

This document is the agreed blueprint. Implementation happens in **phases** (Section 9),
one spec→plan→build cycle starting with Phase 1.

### Scope posture (decided)
- **Full feature set as specified.** No features are cut for legal/ToS reasons.
- Legal/ToS/anti-spam risks (LinkedIn scraping, bulk cold email, ATS auto-submit) are
  **documented in the README**, not restricted in code. See Section 10.

---

## 2. Key architectural decisions (decided)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Data access | **FastAPI-only, SQLAlchemy + Alembic single source of truth.** Drop Prisma. | Frontend reads/writes exclusively through the authenticated FastAPI API (`lib/api.ts`). One schema, one migration system, no drift. |
| D2 | Embeddings | **Local `sentence-transformers` (BAAI/bge-large-en-v1.5, 1024 dims).** | Anthropic has no embeddings API. Local model needs no key, runs in Docker, free. Schema uses `vector(1024)`. |
| D3 | Auth + storage | **Self-contained, Supabase-compatible.** Local JWT issuer/verifier + MinIO (S3-compatible). | Runs fully offline with `docker-compose up`. Interfaces kept Supabase-shaped so real Supabase can be swapped in via env later. |
| D4 | LLM | **Anthropic Claude `claude-sonnet-4-6`** for generation; structured JSON outputs. | Per spec. Wrapped with retry/backoff. |
| D5 | Browser automation | **Playwright (Python, async)** for scraping + form fill. | Per spec. Anti-bot headers, timeout + CAPTCHA-detection handling. |

---

## 3. System architecture

```
                              ┌─────────────────────────────┐
                              │   Next.js 14 (App Router)    │
                              │  Tailwind + shadcn/ui        │
                              │  React Query + Zustand       │
                              └──────────────┬──────────────┘
                                             │ HTTPS (JWT bearer)
                                             │ lib/api.ts (axios)
                              ┌──────────────▼──────────────┐
                              │        FastAPI (8000)        │
                              │  routers / schemas / deps    │
                              │  JWT verify · rate limit ·   │
                              │  plan guard middleware       │
                              └───┬──────────┬──────────┬────┘
                                  │          │          │
                  ┌───────────────▼──┐  ┌────▼─────┐ ┌──▼────────────┐
                  │  PostgreSQL 16   │  │  Redis   │ │   MinIO (S3)  │
                  │  + pgvector      │  │ broker / │ │  resumes /    │
                  │  (SQLAlchemy)    │  │ cache /  │ │  artifacts    │
                  └───────▲──────────┘  │ ratelim  │ └───────────────┘
                          │             └────▲─────┘
                          │                  │ broker/result
              ┌───────────┴──────────────────┴──────────────┐
              │            Celery workers + beat             │
              │  scrape · contact-find · generate · fill ·   │
              │  follow-up · feedback-learn · gmail-poll     │
              └───┬───────────────┬──────────────┬───────────┘
                  │               │              │
        ┌─────────▼──┐   ┌────────▼──────┐  ┌────▼────────────┐
        │ Playwright │   │ Anthropic API │  │ External APIs   │
        │ (scrape +  │   │ (Claude       │  │ SerpAPI/Hunter/ │
        │  ATS fill) │   │  sonnet-4-6)  │  │ Gmail/Stripe    │
        └────────────┘   └───────────────┘  └─────────────────┘
                          ┌──────────────────────────────────┐
                          │ Local embeddings (bge-large-en)   │
                          │ loaded in worker process          │
                          └──────────────────────────────────┘
```

**Request path (frontend):** Next.js → axios w/ JWT → FastAPI dependency verifies JWT →
router → SQLAlchemy. Long-running work (scrape, generate, fill, send) is dispatched to
Celery and surfaced as `agent_runs` rows the frontend polls.

---

## 4. Data model

Single SQLAlchemy schema, Alembic migrations, initial raw SQL migration enabling
`pgvector`. Embedding columns are **`vector(1024)`** (D2). All tables carry `user_id`
scoping; RLS policies are written in SQL and documented as the Supabase-swap path
(enforcement in this build is at the API layer via `user_id` filtering — see Section 6).

Tables (per spec, with adjustments noted):
- `users` (id, email, name, avatar_url, plan, stripe_customer_id, password_hash*, created_at)
  - *`password_hash` added for self-contained email/password auth (D3).
- `resumes` (…, embedding `vector(1024)`)
- `jobs` (…, jd_embedding `vector(1024)`, match against resume via cosine distance)
- `applications` (status enum: pending|generated|sent|opened|replied|rejected|offer)
- `contacts`, `email_accounts` (tokens AES-256/Fernet encrypted at rest)
- `follow_ups`, `agent_runs`, `feedback`, `usage_logs`

Indexes: btree on all FKs + `(user_id, status)` on applications; IVFFlat on both
`vector(1024)` columns; unique dedup index on `jobs(company, role, posted_at)`.

---

## 5. Backend (FastAPI) structure

Exactly the file tree from the spec under `backend/`, with these concrete choices:
- `config.py` — pydantic-settings, all secrets via env, typed.
- `database.py` — engine + `SessionLocal` + `get_db` dependency (context-managed).
- `models/` — one module per table. `schemas/` — Pydantic v2 request/response models.
- `routers/` — auth, jobs, applications, agents, contacts, email_accounts, billing, dashboard.
- `services/` — gmail, anthropic (retry/backoff), stripe, storage (MinIO), embeddings.
- `agents/` — the six agents (Section 7).
- `tasks/` — celery_app, scrape_tasks, email_tasks (idempotent, autoretry).
- `middleware/` — rate_limiter (Redis sliding window), plan_guard.
- `utils/` — text_parser, email_validator, logger (structured JSON, PII-scrubbing).

Every endpoint: Pydantic validation, correct status codes (201/404/422/etc.), OpenAPI
docstrings, auth dependency (except `/health` + `/webhooks/stripe`), rate limit, plan
guard where relevant.

---

## 6. Auth, security, multi-tenancy

- **JWT:** self-contained issuer (login/signup → access + refresh JWT, HS256). FastAPI
  dependency verifies and injects `current_user`. Google OAuth deferred to Supabase-swap.
- **Token encryption:** Gmail/Outlook OAuth tokens encrypted with Fernet (AES-256) before DB.
- **Multi-tenancy:** enforced in the API layer — every query filtered by `current_user.id`.
  SQL RLS policies are written into the migration and documented for the Supabase path.
- **Rate limiting:** Redis sliding window, per user per endpoint.
- **Plan guard:** middleware reads plan + `usage_logs`, enforces free/pro/unlimited limits.
- **Logging:** structured JSON; never log tokens, email bodies, or PII.
- **GDPR:** data-export endpoint + cascade account deletion.

---

## 7. AI agents

1. **Job Scraper** — Playwright + BS4 per source (LinkedIn, Greenhouse, Lever, Wellfound,
   YC, Internshala, Remotive, Indeed, Glassdoor, Naukri). Dedup by (company+role+date),
   compute JD embedding, cosine match vs resume → `match_score`. Celery periodic (6h/user).
   Handles timeouts, dynamic loads, anti-bot headers; **CAPTCHA → log + skip, never crash.**
2. **Contact Finder** — SerpAPI query → Playwright LinkedIn profile crawl → name/title/URL;
   email via Hunter.io or pattern guess; SMTP-handshake validation (no send). → `contacts`.
3. **Email/Content Generator** — Claude `sonnet-4-6`, structured prompt from JD + resume +
   company/role/recruiter/tone. Returns JSON {subject, email_body, cover_letter,
   linkedin_message}. Stored on `applications`. **This is the heart of Phase 2.**
4. **Form Filler** — Playwright on Greenhouse/Lever/Workday: navigate → Claude maps fields
   from screenshot+HTML → fill/select/upload → **pause + preview screenshot** → submit on
   user confirm. Pro/Unlimited only.
5. **Follow-up Scheduler** — Celery beat hourly: applications sent & unreplied past
   `follow_up_at` → Claude short follow-up → send → record in `follow_ups`.
6. **Feedback Learner** — Gmail poll detects replies → prompt user 👍/👎 → monthly compute
   per-template reply rates → Claude compares hi/lo performers → update prompt template.

Each agent is a plain class/function callable from a Celery task; tasks are idempotent
with `autoretry_for`, `max_retries`, `default_retry_delay`.

---

## 8. Frontend (Next.js 14)

Exact page/component tree from the spec. Data exclusively via `lib/api.ts` (axios + JWT
interceptor). React Query for server state, Zustand for UI state, Recharts for analytics,
Framer Motion for micro-interactions, shadcn/ui base. No `any` types. Every data view
handles loading/error/empty/success; every form has loading+disabled states. Fully
responsive. API base from `NEXT_PUBLIC_API_URL`.

Key surfaces: dashboard (stats + activity feed + reply-rate chart), jobs feed + detail
(generate CTA), applications kanban + table + detail timeline + email preview modal,
agents run history + trigger panel, contacts book, email-accounts connect, settings
(resume upload), billing (Stripe portal).

---

## 9. Phased implementation plan (build order)

Each phase is independently runnable and ends with something demonstrable. We write a
detailed plan for and build **Phase 1 first**, then return for the next.

- **Phase 1 — Foundation & core data + auth.** Docker stack (PG+pgvector, Redis, MinIO,
  backend, frontend). Migrations, models, config, logging, JWT auth, users/resumes/jobs/
  applications CRUD, storage service, frontend shell + login/signup + jobs + applications
  pages. Runs end-to-end with `docker-compose up`. Tests pass.
- **Phase 2 — AI generation.** Embeddings service, anthropic service, email generator
  agent, prompt templates, generate endpoint + Celery task, agent_runs, job detail
  "generate" flow, email preview/edit modal.
- **Phase 3 — Scraping.** Job scraper agents (all sources), dedup, match scoring, beat
  schedule, agents page triggers.
- **Phase 4 — Email loop.** Gmail OAuth + send, tracking pixel, reply polling, follow-up
  scheduler, contact finder.
- **Phase 5 — Billing & plan enforcement.** Stripe service, checkout/portal, webhook
  handler, plan_guard, usage metering, billing page, upgrade modal.
- **Phase 6 — Form filler + feedback learner + polish.** ATS auto-fill, feedback loop,
  analytics, GDPR export/delete, CI/CD, hardening.

---

## 10. Risk & compliance notes (documented, not restricted — per decision)

The README will state plainly:
- **LinkedIn / Indeed / Glassdoor scraping** violates those sites' ToS and may be blocked
  or trigger legal action; selectors break frequently; use at your own risk.
- **Bulk cold email** is subject to CAN-SPAM (US), CASL (CA), GDPR/PECR (EU): requires
  accurate headers, opt-out, sender identity. Mass sending risks Gmail account suspension.
- **ATS auto-submit** violates many providers' ToS; the Form Filler always pauses for human
  confirmation before final submit (this is a product/safety design choice, not a restriction).
- All third-party API use (SerpAPI, Hunter.io, Stripe, Anthropic) is subject to their terms.

---

## 11. External credentials required (for full functionality)

Local-first parts run with no keys. These features need keys, supplied via `.env`:
`ANTHROPIC_API_KEY` (Phase 2), `SERPAPI_KEY` / `HUNTER_API_KEY` (Phase 4 contacts),
Gmail OAuth client (Phase 4 email), `STRIPE_SECRET_KEY` + webhook secret (Phase 5).
Absent keys: the dependent feature is disabled gracefully with a clear error, not a crash.

---

## 12. Testing & quality gates

- pytest with mocked external APIs (Claude/Gmail/SerpAPI/Stripe), separate test DB
  (fixtures create/teardown), happy + unhappy paths, assert status + body shape.
- Realistic coverage target tracked per phase (CLAUDE.md asks 75%; we report actuals).
- Gates that need live external services (LinkedIn scrape, real Stripe events) are
  documented as manual/integration steps, not asserted as auto-passing in CI.
- Frontend: `tsc --noEmit`, eslint, `next build`.
