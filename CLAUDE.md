# ApplyPilot — Claude Code Project Constitution

> This file is read at the start of every session. It is the single source of
> truth for how this project is built and what already exists. Read it fully
> before writing any code.

## What this project is
ApplyPilot is an autonomous AI job-application SaaS for students and new grads.
It scrapes jobs, finds recruiter contacts, generates personalized outreach using
Sarvam AI, auto-fills ATS forms, tracks all touchpoints in a CRM dashboard,
and learns from reply rates.

Full spec: read `docs/DESIGN_DOCUMENT.md`
Current phase: **Phase 2 (AI generation engine) — not yet started**
Phase 1 (foundation) is **complete** and merged to `main`.

---

## Non-negotiable rules for every session

### Before writing any code
- Run: `find . -type f | grep -v node_modules | grep -v __pycache__ | grep -v .git | sort`
- Read every file you will touch BEFORE touching it
- Never rebuild what Phase 1 already built — only extend it
- Bring up the DB first for any DB-touching work: `docker compose up -d db` (Postgres is on host port **5433**, not 5432)

### Architecture decisions (decided — do not relitigate)

| Decision | Choice | Reason |
|----------|--------|--------|
| ORM | SQLAlchemy 2.0 + Alembic only | One schema system, no drift. No Prisma. |
| Embeddings | sentence-transformers `BAAI/bge-large-en-v1.5` (1024 dims) | No external embedding API needed. Runs in Docker. Schema columns are `vector(1024)`. |
| Auth | Self-contained JWT (HS256) | Runs fully offline. Supabase-shaped for easy swap. |
| AI Provider | Sarvam AI (`sarvam-105b`) — via provider-agnostic layer | See AI Provider Layer section below |
| Browser automation | Playwright (Python, async) | Best Python ATS automation support |
| Frontend data | `lib/api.ts` (axios + JWT interceptor) only | No direct URL/`fetch()` calls in components ever |
| UI system | Blueprint design system | radius=0, hard offset shadows, VT323/Source Serif 4/JetBrains Mono fonts, `#3553ff` accent |

> **Note on the AI provider decision:** the original Phase 1 design document
> (`docs/superpowers/specs/2026-06-19-applypilot-design.md`) named Anthropic
> Claude as the generation LLM. That decision was superseded at Phase 1
> close-out: generation now runs through a **provider-agnostic AI layer** with
> **Sarvam AI** as the default provider. Anthropic remains available as a
> provider for vision tasks only (Phase 6). `docs/DESIGN_DOCUMENT.md` carries the
> reconciled, current version.

### AI Provider Layer (provider-agnostic — Phase 2+)

Current provider: **Sarvam AI**
```
AI_PROVIDER=sarvam
Model: sarvam-105b   (or sarvam-30b for lower cost)
```

To switch provider: change `AI_PROVIDER` in `.env`. **Zero code changes anywhere else.**
Available: `sarvam | anthropic | openai | ollama`

**THE RULE:** Agents and routers MUST NEVER import AI SDKs directly.
Always use:
```python
from services.ai import get_ai_provider, GenerationRequest, AIMessage
```

To add a new provider: see `docs/AI_PROVIDER_LAYER.md`

Vision tasks (Phase 6 form-fill): set `AI_PROVIDER=anthropic`.
`sarvam-105b` is text-only — no image input.

> **Status:** The `services/ai/` layer does **not exist yet** — it is the first
> deliverable of Phase 2. The contract above is the agreed shape; build it per
> `docs/phases/PHASE_2.md`.

### Code quality rules (every session)
- All Python functions: type hints on every param and return value
- All Python functions: Google-style docstrings (Args / Returns / Raises)
- No bare `except:` — always `except SpecificError as e:`
- No `print()` — always `logger.info()` / `logger.error()`
- No `any` TypeScript types — use proper interfaces or `unknown` with guards
- No hardcoded secrets — always `settings.VARIABLE_NAME` or `process.env.NEXT_PUBLIC_*`
- No direct `fetch()` in frontend — always `lib/api.ts`
- No hardcoded colors in frontend — only semantic Blueprint tokens (`bg`, `ink`, `blueprint`, `warn`, …); hex/`rgb()`/Tailwind color-scale utilities are forbidden outside `app/globals.css`

### After writing every file
```bash
# Python
python -m py_compile <file>.py

# TypeScript
cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20

# No TODOs
grep -n "TODO\|FIXME\|placeholder" <file>
```

### Quality gates (run before declaring any phase done)
```bash
# Postgres must be up first: docker compose up -d db
cd backend && DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
  pytest tests/ --cov=. --cov-fail-under=70 -q
cd frontend && npx tsc --noEmit && npx eslint . --ext .ts,.tsx --max-warnings=0
cd frontend && npx next build
```

---

## Phase completion status

| Phase | Status | Branch | Key deliverables |
|-------|--------|--------|-----------------|
| 1 — Foundation | **COMPLETE** | `main` | Docker stack, all 10 DB models + migration, JWT auth, CRUD APIs, frontend shell, Blueprint UI, 109 tests @ 98% |
| 2 — AI Generation | **NEXT (not started)** | `phase-2` (create from `main`) | Provider-agnostic AI layer, embeddings service, Sarvam service, email generator agent, match scoring |
| 3 — Scraping | Queued | — | Job scraper agents (10 sources), dedup, beat schedule |
| 4 — Email Loop | Queued | — | Gmail OAuth, send, tracking, reply polling, follow-ups, contact finder |
| 5 — Billing | Queued | — | Stripe, plan enforcement, usage metering |
| 6 — Polish | Queued | — | ATS form filler (needs vision — use `AI_PROVIDER=anthropic`), feedback learner, GDPR, CI/CD |

Per-phase specs live in `docs/phases/PHASE_*.md`. Phase 2 is a complete standalone
build spec; Phases 3–6 are one-page overviews.

---

## What Phase 1 built (never rebuild — only import and extend)

### Database (all 10 tables exist and are migrated — `backend/alembic/versions/001_initial.py`)
`users`, `resumes`, `jobs`, `applications`, `contacts`,
`email_accounts`, `follow_ups`, `agent_runs`, `feedback`, `usage_logs`.
pgvector extension enabled. `vector(1024)` columns on `resumes.embedding` and
`jobs.jd_embedding` (both NULL in Phase 1 — populated in Phase 2/3). IVFFlat
cosine indexes exist on both. RLS policies are written into the migration as the
documented Supabase-swap path; **active tenant isolation is at the API layer**
(every query filtered by `current_user.id`).

### Backend (working — just import)
- `backend/config.py` — typed `settings` (pydantic-settings). All config via env.
- `backend/database.py` — `engine`, `SessionLocal`, declarative `Base`.
- `backend/deps.py` — `get_db`, `get_redis`, `get_current_user` (use this dependency on every new authed route).
- `backend/security/jwt.py` — `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`.
- `backend/services/storage_service.py` — MinIO file upload/delete (`get_storage` dependency).
- `backend/middleware/rate_limiter.py` — Redis sliding-window limiter (fails open on Redis errors; `/health` exempt).
- `backend/utils/logger.py` — structured JSON logger with token/PII scrubbing.

### Working API endpoints (the ONLY routers that exist — read `docs/API_REFERENCE.md`)
- `/health` — liveness (unauthenticated)
- `/auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/me` — full JWT flow
- `/jobs` — list (filter/paginate) + get-by-id + create (manual/seed). **No update/delete** (scraper owns jobs in Phase 3).
- `/applications` — full CRUD (POST/GET-list/GET-id/PATCH/DELETE) + status transitions via PATCH
- `/resumes` — upload to MinIO + list + delete
- `/dashboard/stats` — aggregate stats (counts, per-status, reply_rate, recent)

> **No routers exist yet for** `contacts`, `email_accounts`, `follow_ups`,
> `agent_runs`, `feedback`, `usage_logs`, or user management beyond `/auth/me`.
> The tables exist; the routers arrive in later phases. Do not assume a
> `/contacts` endpoint — it is not built.

### Frontend pages (working — extend, do not recreate)
`/login`, `/signup` (auth group); `/dashboard`, `/jobs`, `/jobs/[id]`,
`/applications`, `/applications/[id]`, `/settings` (dashboard group).
Components: `Sidebar`, `TopNav`, `ThemeToggle`, `PlanBadge`, `JobCard`, `JobFeed`,
`JobFilters`, `ApplicationKanban`, `ApplicationTable`, `TimelineView`, `StatsGrid`,
`ActivityFeed`, `ReplyRateChart`, and `ui/` primitives (`button`, `card`, `input`, `badge`).
Hooks: `useMe`, `useJobs`, `useApplications`, `useDashboard`, `useResumes`.
Stores: `authStore` (tokens), `uiStore` (theme/UI).

### Infrastructure
`docker-compose.yml` — `db` (postgres+pgvector, host `5433`), `redis`, `minio`,
`backend`, `frontend`. **Celery worker/beat are NOT in compose yet** — they arrive
in Phase 2 when the first async task lands.
Env documented in `backend/.env.example` and `frontend/.env.local.example`.

---

## External credentials needed

| Key | Feature | Phase | Missing-key behaviour |
|-----|---------|-------|-----------------------|
| `SARVAM_API_KEY` | AI generation | 2 | Return `503 feature_unavailable` |
| `SERPAPI_KEY` | Recruiter contact search | 4 | Disable contact finder |
| `HUNTER_API_KEY` | Email discovery | 4 | Fall back to pattern guessing |
| `STRIPE_SECRET_KEY` | Billing | 5 | Disable billing endpoints |
| Gmail OAuth creds | Email send | 4 | Disable send feature |
| `ANTHROPIC_API_KEY` | ATS form-fill vision (Phase 6) | 6 | Disable form filler |

All missing optional keys: return `{"error":"feature_unavailable","reason":"api_key_not_configured"}` with HTTP **503**.
Never crash on a missing optional key. (Phase 1 needs **no** keys to run.)

---

## Common commands

```bash
# Start everything
docker compose up -d

# Start just the DB (needed for host-side tests)
docker compose up -d db                # Postgres on host port 5433

# Backend dev (outside Docker)
cd backend && DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
  uvicorn main:app --reload --port 8000

# Run tests (host) — DB must be up
cd backend && DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
  pytest tests/ -v

# Coverage
cd backend && DATABASE_URL=...localhost:5433/applypilot pytest tests/ --cov=. --cov-report=term-missing

# Run tests (Docker)
docker compose run --rm backend pytest tests/ -q

# Seed sample data (DB must be up)
DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot python scripts/seed.py

# New DB migration
cd backend && alembic revision --autogenerate -m "describe_change"
cd backend && alembic upgrade head
# (helper: bash scripts/new_migration.sh)

# Frontend dev
cd frontend && npm run dev

# Celery worker (Phase 2+, once tasks/celery_app.py exists)
cd backend && celery -A tasks.celery_app worker --loglevel=info

# Full rebuild
docker compose down -v && docker compose up -d --build

# Health check / test runner helpers
bash scripts/check_health.sh
bash scripts/run_tests.sh
```

---

## Known issues / watch-outs
Source: `docs/PRODUCTION_HARDENING.md` (full backlog) and the Phase 1 deferred ledger.

- **ISSUE:** `backend/entrypoint.sh` runs `uvicorn --reload` (dev mode, single worker). | WORKAROUND: fine for local/dev. | PHASE: 6 (prod hardening — switch to gunicorn + UvicornWorker).
- **ISSUE:** `JWT_SECRET` defaults to `dev-only-insecure-change-me`; no startup guard. | WORKAROUND: override via env in any non-local run. | PHASE: 6 (fail fast when `app_env != development`).
- **ISSUE:** Refresh tokens (14d) cannot be revoked/rotated; no logout-everywhere. | WORKAROUND: short access TTL (30 min) limits blast radius. | PHASE: 6 (Redis jti store + rotation).
- **ISSUE:** Frontend stores tokens in `localStorage` (XSS-readable). | WORKAROUND: acceptable for local dev. | PHASE: 6 (httpOnly Secure SameSite cookies).
- **ISSUE:** `/health` is liveness-only (does not check DB/Redis/MinIO). | WORKAROUND: none needed for Phase 1. | PHASE: 6 (add readiness probe).
- **ISSUE:** Rate limiter fails **open** on Redis errors (a Redis outage disables limiting). | WORKAROUND: intentional availability trade-off, documented. | PHASE: 6 (confirm or add bounded in-process fallback).
- **ISSUE:** `storage_service.py` real MinIO I/O is only covered by the Docker integration test (43% unit-line coverage). | WORKAROUND: faked in unit tests. | PHASE: 6 (MinIO testcontainer).
- **ISSUE:** Signup returns `409` on existing email = user enumeration. | WORKAROUND: deliberate per UX spec. | PHASE: N/A (documented choice).
- **ISSUE:** Application status transitions have no rules — any valid enum value is accepted via PATCH. | WORKAROUND: none. | PHASE: 2+ (add a state machine if needed).
- **ISSUE:** Job dedup unique key is `(company, role, posted_at)`; rows with NULL `posted_at` are not deduped. | WORKAROUND: manual/seed jobs only in Phase 1. | PHASE: 3 (scraper normalizes `posted_at`).
- **ISSUE:** No `contacts`/user-CRUD router, no resume download/presigned-URL endpoint. | WORKAROUND: tables exist; access deferred. | PHASE: 4 (contacts), 2+ (resume download if needed).

---
(end of CLAUDE.md)
