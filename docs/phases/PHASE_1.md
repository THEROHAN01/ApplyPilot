# Phase 1 — Foundation & Core Data

Status: **COMPLETE**
Branch: `phase1-foundation` → merged to `main` (via the close-out PR)
Started: 2026-06-19 · Completed: 2026-06-22 (per `git log`)

The runnable foundation: a full Docker stack, the complete data model, self-contained JWT
auth, the core CRUD APIs, and a Blueprint-styled Next.js shell — all working end-to-end
with `docker compose up`, no API keys required.

## What was built

### Infrastructure
- `docker-compose.yml` — `db` (pgvector/pgvector:pg16, host port **5433**), `redis` (7), `minio`, `backend`, `frontend`, with healthchecks and dependency ordering.
- `backend/Dockerfile`, `backend/entrypoint.sh`, `backend/.dockerignore`; `frontend/Dockerfile`, `frontend/.dockerignore`.
- `.github/workflows/phase1-ci.yml` — test-only CI.
- Dependency locks: `backend/requirements.txt` (pinned) + `requirements.lock.txt`; `frontend/package.json` (pinned) + `npm-shrinkwrap.json`.

### Database (models + migration)
- `backend/database.py` (engine/SessionLocal/Base), `backend/config.py` (typed settings), `backend/deps.py` (`get_db`/`get_redis`/`get_current_user`).
- `backend/models/` — 10 tables: `user`, `resume`, `job`, `application`, `contact`, `email_account`, `follow_up`, `agent_run`, `feedback`, `usage_log`.
- `backend/alembic/versions/001_initial.py` — pgvector extension, all tables, IVFFlat indexes on both `vector(1024)` columns, `(user_id, status)` composite, `(company, role, posted_at)` dedup unique, and RLS scaffold.

### Backend services & middleware
- `backend/security/jwt.py` — bcrypt hashing + access/refresh JWT issue/verify.
- `backend/services/storage_service.py` — MinIO upload/delete (idempotent delete).
- `backend/middleware/rate_limiter.py` — Redis sliding-window limiter (per-identity, fails open).
- `backend/utils/logger.py` — structured JSON logging with token/PII scrubbing.

### Routers (the endpoints that exist)
- `routers/health.py` — `GET /health`.
- `routers/auth.py` — `signup` / `login` / `refresh` / `me`.
- `routers/resumes.py` — upload / list / delete (MinIO-backed).
- `routers/jobs.py` — list (filter+paginate) / get / create.
- `routers/applications.py` — full CRUD + status PATCH.
- `routers/dashboard.py` — `GET /dashboard/stats`.
- Schemas in `backend/schemas/` (auth, user, job, application, resume, dashboard, common).

### Frontend (Next.js 14, Blueprint)
- App Router pages: `(auth)/login`, `(auth)/signup`; `(dashboard)/dashboard`, `/jobs`, `/jobs/[id]`, `/applications`, `/applications/[id]`, `/settings`.
- Components: `Sidebar`, `TopNav`, `ThemeToggle`, `PlanBadge`, `JobCard`, `JobFeed`, `JobFilters`, `ApplicationKanban`, `ApplicationTable`, `TimelineView`, `StatsGrid`, `ActivityFeed`, `ReplyRateChart`, `ui/{button,card,input,badge}`.
- `lib/api.ts` (axios + single-flight JWT refresh), `lib/auth.ts`, `lib/utils.ts`; hooks `useMe`/`useJobs`/`useApplications`/`useDashboard`/`useResumes`; stores `authStore`/`uiStore`; `types/index.ts`.
- Blueprint tokens in `app/globals.css`; Playwright E2E specs under `frontend/e2e/`.

## Key decisions locked in
- **SQLAlchemy + Alembic only** (no Prisma) — one schema, no drift.
- **Local embeddings** `BAAI/bge-large-en-v1.5` → `vector(1024)` columns (NULL in Phase 1).
- **Self-contained JWT (HS256)** auth, Supabase-shaped for later swap; MinIO for storage.
- **Provider-agnostic AI layer, Sarvam default** (supersedes the original Claude decision) — built in Phase 2.
- **Tenant isolation at the API layer** (`user_id` filtering; 404 on cross-user); RLS is the documented Supabase-swap path only.
- **Blueprint design system** — radius 0, hard offset shadows, VT323/Source Serif 4/JetBrains Mono, `#3553ff` accent; colors are CSS tokens only.
- **Postgres on host port 5433** to avoid clashing with a local Postgres.

## Test coverage
109 tests pass; **98% total** line coverage (host run against `applypilot_test`). Per-module highlights:

| Module | Coverage |
|--------|----------|
| `routers/*` (auth, jobs, applications, dashboard, resumes, health) | 100% |
| `models/*` (all 10) | 100% |
| `schemas/*` | 100% (except `common.py` 0% — unused `Message` model) |
| `middleware/rate_limiter.py` | 100% |
| `security/jwt.py`, `deps.py`, `config.py`, `database.py`, `main.py`, `utils/logger.py` | 100% |
| `services/storage_service.py` | 43% (real MinIO I/O only exercised by the Docker integration test) |
| **TOTAL** | **98%** |

## Known issues carried forward
Tracked in `docs/PRODUCTION_HARDENING.md`; summarized in `CLAUDE.md` → *Known issues*. None block Phase 2. Highlights:
- `entrypoint.sh` uses `uvicorn --reload` (dev mode) — Phase 6.
- `JWT_SECRET` has an insecure default with no startup guard — Phase 6.
- Refresh tokens not revocable/rotated; frontend stores tokens in `localStorage` — Phase 6.
- `storage_service` real I/O thinly covered by unit tests (43%) — Phase 6.
- No `contacts`/user-CRUD router, no resume download, no application status-transition rules, jobs are read/create-only.

## Checklist (all true before Phase 2 starts)
- [x] `docker compose up` starts all services cleanly
- [x] `alembic upgrade head` runs without errors
- [x] `GET /health` returns `{"status":"ok"}`
- [x] All Phase 1 tests pass with >70% coverage (109 tests, 98%)
- [x] `npx next build` completes without errors
- [x] Zero TODO/FIXME in codebase
- [x] CLAUDE.md written and accurate
- [x] docs/ complete and accurate
