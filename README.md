# ApplyPilot

Autonomous AI job-application engine for students and new grads.

ApplyPilot scrapes job listings, discovers recruiter contacts, generates personalized outreach (cold emails, cover letters, LinkedIn messages) with Claude, optionally auto-fills ATS forms, tracks every touchpoint in a Kanban CRM dashboard, sends follow-ups, and learns from reply rates.

**Phase 1 (this branch):** Foundation — auth, core CRUD, dashboard shell, Blueprint design system, full Docker stack. No AI keys required to run.

---

## Architecture

```
                          ┌─────────────────────────────┐
                          │   Next.js 14 (App Router)    │
                          │  Blueprint tokens + Tailwind  │
                          │  React Query + Zustand        │
                          └──────────────┬───────────────┘
                                         │ HTTPS (JWT bearer)
                                         │ lib/api.ts (axios)
                          ┌──────────────▼───────────────┐
                          │        FastAPI  :8000         │
                          │  routers / schemas / deps     │
                          │  JWT verify · rate limit ·    │
                          │  plan guard middleware        │
                          └───┬──────────┬──────────┬────┘
                              │          │          │
              ┌───────────────▼──┐  ┌────▼─────┐ ┌──▼────────────┐
              │  PostgreSQL 16   │  │  Redis   │ │   MinIO (S3)  │
              │  + pgvector      │  │ broker / │ │  resumes /    │
              │  (SQLAlchemy)    │  │ cache /  │ │  artifacts    │
              └──────────────────┘  │ ratelim  │ └───────────────┘
                                    └──────────┘
              ┌─────────────────────────────────────────────────┐
              │   Celery workers + beat  (Phase 2+)              │
              │  scrape · contact-find · generate · fill ·       │
              │  follow-up · feedback-learn · gmail-poll         │
              └───┬──────────────────┬──────────────┬───────────┘
                  │                  │              │
        ┌─────────▼──┐   ┌───────────▼───────┐  ┌────▼────────────┐
        │ Playwright │   │  Anthropic Claude  │  │ External APIs   │
        │ (scrape +  │   │  (claude-sonnet-   │  │ SerpAPI/Hunter/ │
        │  ATS fill) │   │   4-6, Phase 2+)   │  │ Gmail/Stripe    │
        └────────────┘   └───────────────────┘  └─────────────────┘
```

**Request path:** Next.js → axios (JWT bearer) → FastAPI verifies JWT → router → SQLAlchemy.
Long-running work (scrape, generate, fill, send) is dispatched to Celery and surfaced as
`agent_runs` rows the frontend polls.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | v2.x |
| Node.js | 20.x (local dev only) |
| Python | 3.12 (local dev only) |

---

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger UI): http://localhost:8000/docs
- MinIO console: http://localhost:9001

> **Note:** PostgreSQL is published on host port **5433** (not 5432) to avoid clashing with
> a locally installed Postgres instance.

---

## Environment Variables

All variables live in `.env` at the repo root (copy from `.env.example`).
The backend also reads `backend/.env.example`; the frontend reads `frontend/.env.local.example`
— both are superseded by the root `.env` under Docker Compose.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Runtime environment (`development` / `production`) |
| `DATABASE_URL` | `postgresql+psycopg2://applypilot:applypilot@db:5432/applypilot` | SQLAlchemy connection string (internal Docker hostname `db`) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection for Celery broker, cache, and rate-limiter |
| `JWT_SECRET` | `dev-only-insecure-change-me` | **Change before production.** HMAC-SHA256 secret for JWT signing |
| `S3_ENDPOINT` | `minio:9000` | S3-compatible storage endpoint (MinIO inside Docker) |
| `S3_ACCESS_KEY` | `minioadmin` | MinIO / S3 access key |
| `S3_SECRET_KEY` | `minioadmin` | MinIO / S3 secret key |
| `S3_BUCKET` | `applypilot` | Bucket for resumes and artifacts |
| `S3_SECURE` | `false` | Set `true` when using TLS on the S3 endpoint |
| `FERNET_KEY` | *(empty)* | AES-256 (Fernet) key for encrypting OAuth tokens at rest. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated origins allowed by FastAPI CORS middleware |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL **baked into the frontend image at build time** (see Deployment note) |

**Phase 2+ keys (absent = feature disabled gracefully, no crash):**

| Variable | Phase | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | 2 | Claude API key for AI generation |
| `SERPAPI_KEY` | 4 | SerpAPI key for recruiter contact discovery |
| `HUNTER_API_KEY` | 4 | Hunter.io key for email pattern guessing |
| `GMAIL_CLIENT_ID` | 4 | Google OAuth 2.0 client ID for Gmail send/receive |
| `GMAIL_CLIENT_SECRET` | 4 | Google OAuth 2.0 client secret |
| `STRIPE_SECRET_KEY` | 5 | Stripe secret key for billing |
| `STRIPE_WEBHOOK_SECRET` | 5 | Stripe webhook signing secret |

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Point at the Dockerized DB+Redis (or your own)
export DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot
export REDIS_URL=redis://localhost:6379/0
export JWT_SECRET=dev-only-insecure-change-me

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
# Create frontend/.env.local with:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Running Tests

### Backend (inside Docker — recommended)

```bash
docker compose run --rm backend python -m pytest tests/ -q
```

Backend tests target a dedicated `applypilot_test` database that fixtures create and
tear down automatically. When running tests against the host (not Docker), set:

```bash
export DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot
cd backend && python -m pytest tests/ -q
```

### Frontend (type-check + build)

```bash
cd frontend
npx tsc --noEmit
npx next build
```

---

## Risk & Compliance

The following risks are **documented here, not restricted in code.** You are responsible
for complying with applicable laws and terms of service.

- **LinkedIn / Indeed / Glassdoor scraping** — these sites' Terms of Service prohibit
  automated access. Scrapers may be blocked or trigger legal action. Selectors break
  frequently. Use at your own risk.

- **Bulk cold email** — mass outreach is subject to CAN-SPAM (US), CASL (Canada), and
  GDPR/PECR (EU). Requirements include accurate sender identity, a physical address, and
  a functional opt-out mechanism. Mass sending via Gmail risks account suspension.

- **ATS auto-submit** — many ATS providers' ToS prohibit automated form submission.
  The Form Filler (Phase 6) always pauses for human confirmation before final submit;
  this is a deliberate product-safety design choice, not an external constraint.

- **Third-party API terms** — SerpAPI, Hunter.io, Stripe, and Anthropic each have their
  own terms of service. Ensure your usage complies.

---

## External Credentials

Local-first parts of ApplyPilot run with **no API keys**. Features that require keys
fail gracefully with a clear error message when the key is absent.

| Credential | Required for | Phase |
|------------|-------------|-------|
| `ANTHROPIC_API_KEY` | AI email/cover-letter generation, match scoring | 2 |
| `SERPAPI_KEY` / `HUNTER_API_KEY` | Recruiter contact discovery | 4 |
| Gmail OAuth client (`GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET`) | Email send/receive/poll | 4 |
| `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` | Subscription billing | 5 |

---

## Phase Roadmap

| Phase | Status | Scope |
|-------|--------|-------|
| **1 — Foundation** | **Done** | Auth (JWT + email/password), core CRUD (users, resumes, jobs, applications, contacts), dashboard shell, Blueprint design system, Docker stack (Postgres + pgvector, Redis, MinIO), 50+ backend tests |
| 2 — AI generation | Upcoming | Claude integration, cold-email + cover-letter generation, resume-to-JD match scoring, agent_runs polling |
| 3 — Job scraping | Upcoming | Playwright scrapers for 10+ boards, Celery beat schedule, deduplication, JD embeddings |
| 4 — Email loop | Upcoming | Gmail OAuth, inbox polling, follow-up scheduler, recruiter contact finder |
| 5 — Billing | Upcoming | Stripe subscriptions, plan guard middleware, usage metering, upgrade modal |
| 6 — Form filler + polish | Upcoming | ATS auto-fill, feedback learner, analytics, GDPR export/delete, CI/CD hardening |

---

## Design System

The UI uses the **Blueprint design system** — a technical/academic aesthetic:
zero border-radius, hard offset drop-shadows, `VT323` / `Source Serif 4` / `JetBrains Mono`
font stack, blueprint-blue accent.

All colors are **CSS custom properties** defined in `frontend/app/globals.css` as token
blocks for light and dark themes. No Tailwind color-scale utilities (`text-red-500`,
`bg-white`, etc.) appear in component files — only semantic tokens (`bg`, `surface`,
`ink`, `accent`, etc.) are used. Swapping the theme means editing one CSS file.

---

## Deployment Note

`NEXT_PUBLIC_API_URL` is baked into the Next.js frontend image at build time (Next.js
bakes `NEXT_PUBLIC_*` variables at `next build`). The default value is `http://localhost:8000`.

For a deployed environment with a non-localhost backend:

```yaml
# docker-compose.yml (or your CI build step)
services:
  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_URL: https://api.yourdomain.com
```

or pass `--build-arg NEXT_PUBLIC_API_URL=...` to `docker build` directly.
The `frontend/Dockerfile` must expose this as a build `ARG` and set it as `ENV` before
the `next build` step.
