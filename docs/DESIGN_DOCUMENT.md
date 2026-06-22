# ApplyPilot — Design Document

**Original date:** 2026-06-19
**Reconciled at Phase 1 close-out:** 2026-06-22
**Status:** Phase 1 built and merged. This is the current, authoritative spec.

> This document supersedes `docs/superpowers/specs/2026-06-19-applypilot-design.md`.
> The only material change is the LLM decision (D4): generation now runs through a
> **provider-agnostic AI layer** with **Sarvam AI** as the default provider, not
> Anthropic Claude directly. Everything else is as originally agreed.

---

## 1. What we're building

ApplyPilot is an autonomous AI job-application engine for students and new grads. It
scrapes jobs from multiple sources, discovers recruiter contacts, generates
personalized outreach (emails / cover letters / LinkedIn messages) via the AI provider
layer, optionally auto-fills ATS forms, tracks every touchpoint in a CRM dashboard,
sends follow-ups, and learns from reply rates.

Implementation happens in **phases** (Section 9), one spec→plan→build cycle each.

### Scope posture (decided)
- **Full feature set as specified.** No features cut for legal/ToS reasons.
- Legal/ToS/anti-spam risks (LinkedIn scraping, bulk cold email, ATS auto-submit) are
  **documented in the README**, not restricted in code. See Section 10.

---

## 2. Key architectural decisions (decided)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Data access | **FastAPI-only, SQLAlchemy + Alembic single source of truth.** No Prisma. | Frontend reads/writes exclusively through the authenticated FastAPI API (`lib/api.ts`). One schema, one migration system, no drift. |
| D2 | Embeddings | **Local `sentence-transformers` (`BAAI/bge-large-en-v1.5`, 1024 dims).** | No external embeddings API needed. Local model needs no key, runs in Docker, free. Schema uses `vector(1024)`. |
| D3 | Auth + storage | **Self-contained, Supabase-compatible.** Local JWT issuer/verifier (HS256) + MinIO (S3-compatible). | Runs fully offline with `docker compose up`. Interfaces kept Supabase-shaped so real Supabase can be swapped in via env later. |
| **D4** | **LLM** | **Provider-agnostic AI layer; default provider Sarvam AI (`sarvam-105b`).** Structured JSON outputs. | One contract (`GenerationRequest`/`AIResponse`); agents never import an SDK. Provider switched by one env var. Sarvam for text; Anthropic for vision (Phase 6). See `docs/AI_PROVIDER_LAYER.md`. |
| D5 | Browser automation | **Playwright (Python, async)** for scraping + form fill. | Anti-bot headers, timeout + CAPTCHA-detection handling. |
| D6 | Frontend visual design | **Blueprint design system** (technical/academic: radius 0, hard offset shadows, VT323/Source Serif 4/JetBrains Mono, blueprint-blue accent). shadcn/Radix primitives retained for behavior, re-themed to Blueprint tokens. | User-selected. See Section 8 and the `blueprint-design-system` skill. |

---

## 3. System architecture

```
                              ┌─────────────────────────────┐
                              │   Next.js 14 (App Router)    │
                              │  Blueprint tokens + Tailwind │
                              │  React Query + Zustand       │
                              └──────────────┬──────────────┘
                                             │ HTTPS (JWT bearer)
                                             │ lib/api.ts (axios)
                              ┌──────────────▼──────────────┐
                              │        FastAPI (8000)        │
                              │  routers / schemas / deps    │
                              │  JWT verify · rate limit ·   │
                              │  plan guard (Phase 5)        │
                              └───┬──────────┬──────────┬────┘
                                  │          │          │
                  ┌───────────────▼──┐  ┌────▼─────┐ ┌──▼────────────┐
                  │  PostgreSQL 16   │  │  Redis   │ │   MinIO (S3)  │
                  │  + pgvector      │  │ broker / │ │  resumes /    │
                  │  (SQLAlchemy)    │  │ cache /  │ │  artifacts    │
                  └───────▲──────────┘  │ ratelim  │ └───────────────┘
                          │             └────▲─────┘
                          │                  │ broker/result (Phase 2+)
              ┌───────────┴──────────────────┴──────────────┐
              │            Celery workers + beat             │
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

**Request path (frontend):** Next.js → axios w/ JWT → FastAPI dependency verifies JWT →
router → SQLAlchemy. Long-running work (scrape, generate, fill, send) is dispatched to
Celery and surfaced as `agent_runs` rows the frontend polls.

---

## 4. Data model

Single SQLAlchemy schema, Alembic migrations, initial migration enabling `pgvector`.
Embedding columns are **`vector(1024)`** (D2). User-owned tables carry `user_id`;
RLS policies are written in SQL and documented as the Supabase-swap path (enforcement
in this build is at the API layer via `user_id` filtering — see Section 6).

Ten tables: `users`, `resumes`, `jobs`, `applications`, `contacts`, `email_accounts`,
`follow_ups`, `agent_runs`, `feedback`, `usage_logs`. Full column-level detail:
`docs/DATABASE_SCHEMA.md`.

Indexes: btree on all FKs + `(user_id, status)` on `applications`; IVFFlat cosine on
both `vector(1024)` columns; unique dedup constraint on `jobs(company, role, posted_at)`.

---

## 5. Backend (FastAPI) structure

- `config.py` — pydantic-settings, all secrets via env, typed.
- `database.py` — engine + `SessionLocal` + declarative `Base`. `deps.py` — `get_db`/`get_redis`/`get_current_user`.
- `models/` — one module per table. `schemas/` — Pydantic v2 request/response models.
- `routers/` — Phase 1: auth, jobs, applications, resumes, dashboard, health. Later: agents, contacts, email_accounts, billing.
- `services/` — Phase 1: storage (MinIO). Phase 2+: `ai/` (provider layer), embeddings; Phase 4+: gmail, stripe.
- `agents/` — the six agents (Section 7), arriving Phase 2–6.
- `tasks/` — celery_app + task modules (idempotent, autoretry), arriving Phase 2.
- `middleware/` — rate_limiter (Redis sliding window, built); plan_guard (Phase 5).
- `utils/` — logger (structured JSON, PII-scrubbing, built); text_parser/email_validator (later).

Every endpoint: Pydantic validation, correct status codes, OpenAPI docstrings, auth
dependency (except `/health` and Phase 5 `/webhooks/stripe`), rate limit, plan guard where relevant.

---

## 6. Auth, security, multi-tenancy

- **JWT:** self-contained issuer (signup/login → access + refresh JWT, HS256). FastAPI
  dependency verifies and injects `current_user`. Google OAuth deferred to Supabase-swap.
- **Token encryption:** Gmail/Outlook OAuth tokens encrypted with Fernet (AES-256) before DB (Phase 4).
- **Multi-tenancy:** enforced in the API layer — every query filtered by `current_user.id`;
  ownership mismatch returns 404 (not 403) to prevent enumeration. SQL RLS policies are
  written into the migration and documented for the Supabase path.
- **Rate limiting:** Redis sliding window, per identity (JWT `sub` or client IP). Fails open on Redis errors.
- **Plan guard:** middleware reads plan + `usage_logs`, enforces free/pro/unlimited limits (Phase 5).
- **Logging:** structured JSON; never log tokens, email bodies, or PII.
- **GDPR:** data-export endpoint + cascade account deletion (Phase 6).

---

## 7. AI agents

1. **Job Scraper** (Phase 3) — Playwright + BS4 per source (LinkedIn, Greenhouse, Lever,
   Wellfound, YC, Internshala, Remotive, Indeed, Glassdoor, Naukri). Dedup by
   (company+role+date), compute JD embedding, cosine match vs resume → `match_score`.
   Celery periodic (6h/user). CAPTCHA → log + skip, never crash.
2. **Contact Finder** (Phase 4) — SerpAPI query → Playwright LinkedIn profile crawl →
   name/title/URL; email via Hunter.io or pattern guess; SMTP-handshake validation. → `contacts`.
3. **Email/Content Generator** (Phase 2 — **the heart of Phase 2**) — AI provider layer
   (Sarvam default), structured prompt from JD + resume + company/role/recruiter/tone.
   Returns JSON `{subject, email_body, cover_letter, linkedin_message}`. Stored on `applications`.
4. **Form Filler** (Phase 6) — Playwright on Greenhouse/Lever/Workday: navigate → vision
   model (`AI_PROVIDER=anthropic`) maps fields from screenshot+HTML → fill/select/upload →
   **pause + preview screenshot** → submit on user confirm. Pro/Unlimited only.
5. **Follow-up Scheduler** (Phase 4) — Celery beat hourly: applications sent & unreplied
   past `follow_up_at` → AI short follow-up → send → record in `follow_ups`.
6. **Feedback Learner** (Phase 6) — Gmail poll detects replies → prompt user 👍/👎 →
   monthly per-template reply rates → AI compares hi/lo performers → update prompt template.

Each agent is a plain class/function callable from a Celery task; tasks are idempotent
with `autoretry_for`, `max_retries`, `default_retry_delay`.

---

## 8. Frontend (Next.js 14)

Data exclusively via `lib/api.ts` (axios + JWT interceptor with single-flight refresh).
React Query for server state, Zustand for UI state, Recharts for analytics, Framer Motion
for micro-interactions. No `any` types. Every data view handles loading/error/empty/success;
every form has loading+disabled states. Fully responsive. API base from `NEXT_PUBLIC_API_URL`.

### Visual design system: **Blueprint** (decided)

| Rule | Value |
|------|-------|
| Border radius | **0** — sharp corners everywhere |
| Shadows | Hard offset `3px 3px 0 var(--ink)` — never blurred |
| Heading/label/button font | `VT323` (retro monospace) |
| Body font | `Source Serif 4` (scholarly serif) |
| Code/metadata/tags font | `JetBrains Mono` |
| Accent | Blueprint blue `#3553ff` (`#6b8eff` dark), used sparingly |
| Light bg | `#fafaf5` (warm off-white, never pure white) |
| Dark bg | `#0a0d1a` (deep navy, never pure black) |

All colors are CSS custom properties in `frontend/app/globals.css`. No Tailwind
color-scale utilities in components — only semantic tokens. shadcn/Radix primitives are
kept for behavior and re-themed to Blueprint tokens with `--radius: 0`. Fonts via
`next/font`. Light/dark via `data-theme` on `<html>`, persisted to `localStorage`.

---

## 9. Phased implementation plan (build order)

- **Phase 1 — Foundation & core data + auth.** ✅ COMPLETE. Docker stack, migrations,
  models, config, logging, JWT auth, jobs/applications/resumes CRUD, dashboard stats,
  storage service, frontend shell + auth + jobs + applications + settings pages.
- **Phase 2 — AI generation.** Provider-agnostic AI layer (Sarvam), embeddings service,
  email generator agent, prompt templates, generate endpoint + Celery task, `agent_runs`,
  job-detail "generate" flow, email preview/edit modal.
- **Phase 3 — Scraping.** Job scraper agents (all sources), dedup, match scoring, beat schedule.
- **Phase 4 — Email loop.** Gmail OAuth + send, tracking pixel, reply polling, follow-up
  scheduler, contact finder.
- **Phase 5 — Billing & plan enforcement.** Stripe service, checkout/portal, webhook
  handler, plan_guard, usage metering, billing page.
- **Phase 6 — Form filler + feedback learner + polish.** ATS auto-fill (vision via
  Anthropic), feedback loop, analytics, GDPR export/delete, CI/CD, hardening.

---

## 10. Risk & compliance notes (documented, not restricted — per decision)

- **LinkedIn / Indeed / Glassdoor scraping** violates those sites' ToS and may be blocked
  or trigger legal action; selectors break frequently; use at your own risk.
- **Bulk cold email** is subject to CAN-SPAM (US), CASL (CA), GDPR/PECR (EU): requires
  accurate headers, opt-out, sender identity. Mass sending risks Gmail account suspension.
- **ATS auto-submit** violates many providers' ToS; the Form Filler always pauses for human
  confirmation before final submit (product/safety design choice, not a restriction).
- All third-party API use (SerpAPI, Hunter.io, Stripe, Sarvam, Anthropic) is subject to their terms.

---

## 11. External credentials required

Local-first parts run with no keys. Feature keys via `.env`: `SARVAM_API_KEY` (Phase 2),
`SERPAPI_KEY` / `HUNTER_API_KEY` + Gmail OAuth client (Phase 4), `STRIPE_SECRET_KEY` +
webhook secret (Phase 5), `ANTHROPIC_API_KEY` (Phase 6 vision). Absent keys disable the
dependent feature gracefully with a 503 `feature_unavailable`, never a crash.

---

## 12. Testing & quality gates

- pytest with mocked external APIs, separate `applypilot_test` DB (fixtures create/teardown),
  happy + unhappy paths, assert status + body shape. **Phase 1 actual: 109 tests, 98% coverage.**
- Coverage target tracked per phase (CLAUDE.md asks ≥70%; we report actuals).
- Gates needing live external services are documented as manual/integration steps.
- Frontend: `tsc --noEmit`, eslint, `next build`.
