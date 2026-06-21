# ApplyPilot — Phase 1 Complete Walkthrough

> A full, end-to-end explanation of everything built in Phase 1: every component,
> what it does, where Redis is used, where MinIO is used, where files are stored,
> and the complete user journey — with ASCII diagrams throughout.

**Phase 1 scope:** the *foundation* — a running, multi-tenant SaaS skeleton with auth,
core data, file storage, a dashboard UI, and a one-command Docker stack. **No AI yet**
(that's Phase 2). The point of Phase 1 is: a real user can sign up, upload a resume,
browse/seed jobs, create applications, move them through a pipeline, and see stats —
all persisted, all isolated per user, all running in containers.

---

## 1. The 10,000-foot view

```
                          YOUR BROWSER
                               │
              ┌────────────────┴─────────────────┐
              │  Next.js frontend  (port 3000)    │   ← the UI you click
              │  Blueprint design system          │
              └────────────────┬─────────────────┘
                               │  HTTPS + JSON
                               │  Authorization: Bearer <JWT>
                               ▼
              ┌──────────────────────────────────┐
              │  FastAPI backend   (port 8000)    │   ← the brain / API
              │  auth · jobs · applications ·     │
              │  resumes · dashboard · /health    │
              └───┬───────────┬──────────────┬────┘
                  │           │              │
       ┌──────────▼──┐  ┌─────▼─────┐  ┌─────▼──────────┐
       │ PostgreSQL  │  │   Redis   │  │     MinIO      │
       │ + pgvector  │  │  (cache/  │  │  (S3-style     │
       │ port 5433*  │  │  rate-    │  │  file storage) │
       │             │  │  limit)   │  │  ports 9000/1  │
       │ ALL DATA    │  │           │  │  RESUME FILES  │
       └─────────────┘  └───────────┘  └────────────────┘

  * Postgres is published on host port 5433 (not 5432) to avoid clashing with a
    local Postgres you already run. Inside Docker, services still talk to it as db:5432.
```

**One sentence per box:**
- **Next.js frontend** — everything you see and click; never touches the database directly, only calls the FastAPI API.
- **FastAPI backend** — the only thing that talks to the database; enforces auth, validates input, enforces "you can only see your own data".
- **PostgreSQL + pgvector** — the single source of truth for all structured data (users, jobs, applications, resume *metadata*, …). pgvector is installed and the embedding columns exist, but they stay empty until Phase 2.
- **Redis** — used in Phase 1 for **one thing**: rate limiting (see §5). It's also the future Celery broker.
- **MinIO** — S3-compatible object storage. Holds the **actual resume files** (the PDF/DOC bytes). Postgres only stores *where* the file lives, not the file itself.

---

## 2. Container topology (what `docker compose up` starts)

```
                     docker compose up
                            │
      ┌──────────┬──────────┼───────────┬────────────┬───────────┐
      ▼          ▼          ▼           ▼            ▼           ▼
   ┌──────┐  ┌───────┐  ┌───────┐  ┌─────────┐  ┌──────────┐
   │  db  │  │ redis │  │ minio │  │ backend │  │ frontend │
   │ pg16 │  │  7    │  │       │  │ FastAPI │  │ Next.js  │
   │+vec  │  │       │  │       │  │ uvicorn │  │ node     │
   └──────┘  └───────┘  └───────┘  └────┬────┘  └────┬─────┘
      ▲          ▲          ▲           │            │
      └──────────┴──────────┴───────────┘            │
              backend depends_on (healthy/started)   │
                                                      │
                            frontend depends_on backend(healthy)

   Startup order is enforced by docker-compose `depends_on` + healthchecks:
   db must be HEALTHY (pg_isready) → backend boots → backend HEALTHY (/health 200) → frontend boots.

   When `backend` starts, its entrypoint.sh runs:
       1) alembic upgrade head   (apply DB migrations → create all tables)
       2) uvicorn main:app       (serve the API)
```

Host ports you can hit:
| Service  | Host port | What it's for |
|----------|-----------|---------------|
| frontend | 3000      | the app UI (open this) |
| backend  | 8000      | the API + Swagger docs at `/docs` |
| db       | 5433      | Postgres (host access for tools/tests) |
| minio    | 9000      | S3 API; **9001** = MinIO web console |
| redis    | 6379      | Redis |

---

## 3. Backend anatomy — the layers

The backend is a layered FastAPI app. Each layer has one job. Data flows
**top → bottom** on the way in, and **bottom → top** on the way out.

```
  HTTP request
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ main.py            App factory. Builds the FastAPI app,       │
│                    attaches middleware (rate limit, CORS),    │
│                    mounts all routers.                        │
├─────────────────────────────────────────────────────────────┤
│ middleware/        rate_limiter.py — Redis sliding-window     │
│                    limiter (runs on every request).           │
├─────────────────────────────────────────────────────────────┤
│ routers/           One file per resource: auth, resumes,      │
│                    jobs, applications, dashboard, health.     │
│                    Defines endpoints + status codes + OpenAPI.│
├─────────────────────────────────────────────────────────────┤
│ deps.py            Dependency-injection helpers:              │
│                    get_db(), get_redis(), get_current_user(). │
├─────────────────────────────────────────────────────────────┤
│ schemas/           Pydantic models — validate request bodies  │
│                    and shape JSON responses. (auth, user,     │
│                    job, application, resume, dashboard).      │
├─────────────────────────────────────────────────────────────┤
│ security/jwt.py    Password hashing (bcrypt) + JWT create/    │
│                    decode. The crypto core.                   │
├─────────────────────────────────────────────────────────────┤
│ services/          storage_service.py — MinIO wrapper.        │
│                    (Phase 2+ adds anthropic, gmail, stripe.)  │
├─────────────────────────────────────────────────────────────┤
│ models/            SQLAlchemy ORM classes — one per table.    │
│                    The Python ↔ Postgres mapping.             │
├─────────────────────────────────────────────────────────────┤
│ database.py        Engine + SessionLocal + Base.              │
│ alembic/           Migrations (001_initial creates schema).   │
├─────────────────────────────────────────────────────────────┤
│ config.py          Typed settings from env vars.             │
│ utils/logger.py    Structured JSON logging (scrubs tokens).   │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
  PostgreSQL / Redis / MinIO
```

**What each file actually does:**

- **`config.py`** — a `Settings` class (pydantic-settings) that reads every secret/URL
  from environment variables (DB URL, Redis URL, JWT secret, S3 creds, CORS origins,
  rate limit). Nothing is hardcoded; everything is `settings.X`.
- **`database.py`** — creates the SQLAlchemy `engine` (connection to Postgres),
  `SessionLocal` (factory for DB sessions), and `Base` (the parent class all models
  inherit from).
- **`deps.py`** — FastAPI "dependencies" that endpoints declare they need:
  - `get_db()` — opens a DB session for the request, guarantees it's closed afterward.
  - `get_redis()` — hands out a Redis client from a shared connection pool.
  - `get_current_user()` — reads the `Authorization: Bearer <token>` header, decodes
    the JWT, verifies it's an *access* token, loads the `User` from the DB. Returns 401
    on any failure. **This is the gate that makes an endpoint "logged-in only".**
- **`models/`** — 10 ORM classes (users, resumes, jobs, applications, contacts,
  email_accounts, follow_ups, agent_runs, feedback, usage_logs). Phase 1 actively uses
  users/resumes/jobs/applications; the rest exist in the schema for later phases.
- **`schemas/`** — Pydantic request/response models. E.g. `SignupRequest` validates that
  a password is ≥ 8 chars; `ApplicationOut` shapes what an application looks like in JSON
  (and embeds the related job).
- **`security/jwt.py`** — `hash_password`/`verify_password` (bcrypt) and
  `create_access_token`/`create_refresh_token`/`decode_token` (HS256 JWTs with a `type`
  claim distinguishing access vs refresh).
- **`services/storage_service.py`** — the MinIO wrapper (upload/delete/ensure-bucket).
- **`routers/`** — the actual endpoints (next section maps them all).
- **`middleware/rate_limiter.py`** — the Redis rate limiter (§5).
- **`utils/logger.py`** — JSON logs that redact tokens/passwords so secrets never leak
  into logs.

---

## 4. Every endpoint in Phase 1

```
PUBLIC (no auth)
  GET    /health                      → {"status":"ok"}   (also the container healthcheck)
  POST   /auth/signup                 → 201 + {access_token, refresh_token}
  POST   /auth/login                  → 200 + {access_token, refresh_token}
  POST   /auth/refresh                → 200 + new token pair (from a refresh token)

AUTHENTICATED (require Authorization: Bearer <access token>)
  GET    /auth/me                     → the current user

  POST   /resumes                     → 201  upload a resume file (multipart)
  GET    /resumes                     → list YOUR resumes
  DELETE /resumes/{id}                → 204  (also deletes the file from MinIO)

  POST   /jobs                        → 201  create/seed a job (jobs are global)
  GET    /jobs?company=&source=&q=&page=&page_size=  → paginated, filtered list
  GET    /jobs/{id}                   → one job

  POST   /applications                → 201  apply to a job (status starts "pending")
  GET    /applications?status=        → list YOUR applications (optional status filter)
  GET    /applications/{id}           → one of YOUR applications
  PATCH  /applications/{id}           → update status / fields
  DELETE /applications/{id}           → 204

  GET    /dashboard/stats             → totals, per-status counts, reply rate, recent
```

Interactive version of all of these: **http://localhost:8000/docs** (Swagger UI).

---

## 5. Where Redis is used (exactly one place: rate limiting)

In Phase 1, Redis backs **the rate limiter** — nothing else yet. Every incoming request
(except `/health` and CORS preflight `OPTIONS`) passes through `RateLimitMiddleware`.

**The algorithm — a sliding window using a Redis sorted set:**

```
For each request:
   identity = "user:<uuid>"   (decoded from the JWT 'sub' claim)
             or "ip:<addr>"   (if not logged in / token undecodable)
   key      = "rl:<identity>"

   Redis pipeline (one round-trip):
     1. ZREMRANGEBYSCORE key 0 (now-60s)   ← drop timestamps older than the window
     2. ZADD            key now            ← record this request
     3. ZCARD           key                ← how many requests in the last 60s?
     4. EXPIRE          key 60             ← auto-clean idle keys

   if ZCARD > LIMIT (default 120/min):  → 429 Too Many Requests (+ Retry-After: 60)
   else:                                → allow
```

```
   request ──► RateLimitMiddleware ──► CORS ──► router ──► handler
                     │
                     ▼
              ┌──────────────┐
              │    Redis     │   sorted set per identity, 60s window
              │  rl:user:..  │
              └──────────────┘
                     │
        Redis down?  └─► FAIL OPEN: log a warning, allow the request.
                         (A Redis outage must never 500 the whole API.)
```

Two important design choices baked in:
- **Per-user buckets** — the key uses the JWT `sub` (user id), so one abusive user can't
  rate-limit everyone. (An early bug keyed on the JWT header prefix, identical for all
  users — caught and fixed in the final review.)
- **Fail-open** — if Redis is unreachable, the limiter logs and lets the request through
  rather than crashing. This is also why the whole test suite passes without a Redis server.

Middleware order matters: **CORS is outermost** so even a 429 comes back with CORS headers
the browser can read, and `OPTIONS` preflights skip the limiter entirely.

---

## 6. Where MinIO is used & where files get stored (resume upload)

**MinIO is used for one thing in Phase 1: storing the actual resume files.** Postgres
never holds file bytes — it only stores *metadata* (filename + where the bytes live).

This is the classic split:
- **Object storage (MinIO)** ← the binary file (could be megabytes)
- **Relational DB (Postgres)** ← a small row describing it (id, owner, filename, URL, key)

**The storage key scheme** (how files are namespaced so users can't collide or peek):

```
   bucket: "applypilot"
   key:    "<user_id>/<random-uuid>-<sanitized-filename>"

   e.g.    "3f9c.../8a21...-Jane_Doe_Resume.pdf"
            └─ owner ┘ └ unique ┘ └ filename (sanitized: only [A-Za-z0-9._-]) ┘
```

Every user's files are under their own `user_id/` prefix. The filename is sanitized
before it goes into the key (so a malicious filename can't inject path segments), but the
*original* filename is preserved in the DB row for display.

**Upload flow — browser → FastAPI → MinIO → Postgres:**

```
 Browser (Settings page)
   │  POST /resumes  (multipart file)  + Bearer token
   ▼
 FastAPI upload_resume()
   │  1. get_current_user()  ── verify JWT, load user ──► Postgres (users)
   │  2. check content-type ∈ {pdf, msword, docx}  else → 422
   │  3. build key = "<user_id>/<uuid>-<safe_filename>"
   │  4. read file bytes
   │  5. storage.upload(key, bytes, content_type) ──────► MinIO  (stores the FILE)
   │           returns a URL
   │  6. INSERT Resume{user_id, filename, storage_url, storage_key} ► Postgres (metadata)
   ▼
 201 + ResumeOut {id, filename, storage_url, created_at}
```

**Delete flow** removes the file from MinIO *first*, then deletes the DB row — so you
never end up with a DB row pointing at a file that's gone, or vice-versa. `storage.delete`
is idempotent (a missing object is treated as already-deleted).

---

## 7. Authentication in detail (JWT, self-contained)

Phase 1 uses a self-contained JWT auth system (Supabase-swappable later). No third-party
auth service required to run locally.

```
SIGNUP                                          LOGIN
──────                                          ─────
email+password                                  email+password
   │                                               │
   ▼                                               ▼
bcrypt-hash the password                        find user by email
store User{email, password_hash, plan=free}     bcrypt-verify password
   │                                               │ (generic 401 if wrong —
   ▼                                               │  doesn't reveal which field)
issue token pair  ◄─────────────────────────────  issue token pair
   │
   ▼
{ access_token  (short-lived, ~30 min, type=access),
  refresh_token (long-lived, ~14 days, type=refresh) }


USING THE API                                   REFRESH (access token expired)
─────────────                                   ──────
every request sends                             POST /auth/refresh {refresh_token}
  Authorization: Bearer <access_token>            │
   │                                              ▼
   ▼                                            decode, verify type==refresh
get_current_user():                             issue a brand-new token pair
  decode JWT (HS256, our secret)                  │
  verify type == "access"                         ▼
  load User from DB by 'sub' (user id)          { access_token, refresh_token }
  → 401 on any failure
```

On the **frontend**, this is automated by `lib/api.ts` (an axios instance):
- A **request interceptor** attaches the access token to every call.
- A **response interceptor** catches a `401`, calls `/auth/refresh` once, retries the
  original request, and—if refresh fails—clears tokens (forcing re-login). Tokens are
  persisted in `localStorage` via a Zustand store, so a page reload keeps you logged in.

---

## 8. The data model (what's in Postgres)

```
        ┌──────────────┐
        │    users     │  id, email(unique), password_hash, name, plan, …
        └──────┬───────┘
               │ 1
       ┌───────┼───────────────────────────┐
       │ *     │ *                           │ *
 ┌─────▼────┐  ┌────▼─────────┐        ┌──────▼──────┐
 │ resumes  │  │ applications │        │  (contacts, │
 │          │  │              │        │ email_accts,│
 │ storage_ │  │ status enum: │        │ usage_logs, │
 │ url/key  │  │ pending →    │        │ agent_runs, │
 │ embedding│  │ generated →  │        │ feedback,   │
 │ (vec1024 │  │ sent →opened │        │ follow_ups) │
 │  empty)  │  │ →replied →   │        │ — schema    │
 └──────────┘  │ rejected/    │        │   ready,    │
               │ offer        │        │   used in   │
               │     │ *      │        │   Phase 2+  │
               │     ▼ 1      │        └─────────────┘
               │ ┌──────────┐ │
               └─┤   jobs   ├─┘   source, company, role, jd_text,
                 │ (global, │     jd_embedding(vec1024, empty),
                 │  shared) │     match_score(null until Phase 2)
                 └──────────┘

  Key rules enforced:
   • Every user-owned row has a user_id FK with ON DELETE CASCADE
     (delete a user → their resumes/applications vanish too).
   • applications are scoped to the owner; jobs are a shared global catalog.
   • Embedding columns are vector(1024) — present but NULL in Phase 1
     (populated by the Phase 2 embeddings service).
   • Migration 001_initial also writes RLS policies (the Supabase-swap path);
     in this build, isolation is enforced in the API layer.
```

**Multi-tenancy ("I only see my own data")** is enforced in every query: the router
filters by `current_user.id`, and if you ask for someone else's application by id you get
a **404** (not 403 — so the API doesn't even reveal that the row exists).

---

## 9. Frontend anatomy (Next.js 14 + Blueprint design system)

```
 app/
 ├─ layout.tsx          root: loads fonts (VT323 / Source Serif 4 / JetBrains Mono),
 │                      sets the theme, wraps everything in <Providers>
 ├─ providers.tsx       React Query client (server-state cache)
 ├─ page.tsx            "/" → redirects to /dashboard
 ├─ globals.css         ★ the ONLY place colors are defined (CSS variables) ★
 │
 ├─ (auth)/             route group, NO sidebar
 │   ├─ login/          email+password form
 │   └─ signup/         name+email+password form
 │
 └─ (dashboard)/        route group, WITH sidebar + topnav + auth guard
     ├─ layout.tsx      calls useMe(); if not logged in → redirect to /login
     ├─ dashboard/      stats grid + bar chart + recent activity
     ├─ jobs/           feed + filters ; jobs/[id] detail + "Create application"
     ├─ applications/   kanban  ⇄  table toggle ; applications/[id] detail + timeline
     └─ settings/       resume upload + list

 components/
 ├─ ui/                 Blueprint primitives: button, input, card, badge
 ├─ shared/             Sidebar, TopNav, PlanBadge, ThemeToggle
 ├─ jobs/               JobCard, JobFeed, JobFilters
 ├─ applications/       ApplicationKanban, ApplicationTable, TimelineView
 └─ dashboard/          StatsGrid, ReplyRateChart (Recharts), ActivityFeed

 lib/      api.ts (axios + JWT refresh), auth.ts (login/signup/me/logout), utils.ts (cn)
 hooks/    useMe, useJobs, useApplications, useDashboard, useResumes  (React Query)
 store/    authStore (tokens, persisted), uiStore (sidebar)
 types/    index.ts — TS mirrors of every backend schema (no `any` anywhere)
```

**How data moves on the frontend:** components call a **hook** (e.g. `useJobs`) → the hook
uses **React Query** to call **`lib/api.ts`** (axios) → which calls **FastAPI** with the
JWT attached. React Query caches results and re-fetches/invalidates automatically (e.g.
after creating an application, the applications list refreshes).

**The Blueprint design system** (a hard rule of this project): radius 0, hard offset
shadows, monospace headings (VT323), serif body (Source Serif 4), one blueprint-blue
accent, warm-paper light bg / deep-navy dark bg. **No color is ever hardcoded in a
component** — every color is a CSS variable defined once in `globals.css`. Change those
variables → the entire app re-themes. A light/dark toggle (top-right) flips `data-theme`
on `<html>` and persists the choice.

---

## 10. THE COMPLETE USER JOURNEY (end-to-end)

This is the whole Phase 1 product, start to finish, showing which box handles each step.

```
 ┌─ STEP 1: SIGN UP ───────────────────────────────────────────────────────────┐
 │ Browser /signup → POST /auth/signup → bcrypt-hash pw, INSERT user (Postgres) │
 │ → tokens returned → stored in localStorage → redirect to /dashboard          │
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 2: DASHBOARD LOADS ─────────▼───────────────────────────────────────────┐
 │ (dashboard)/layout guard calls GET /auth/me (Bearer token) → 200 → you're in. │
 │ dashboard page calls GET /dashboard/stats → empty stats (0 applications yet). │
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 3: UPLOAD RESUME (Settings) ▼────────────────────────────────────────────┐
 │ pick PDF → POST /resumes (multipart) → FastAPI stores FILE in MinIO,           │
 │ stores METADATA row in Postgres → appears in your resume list.                 │
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 4: BROWSE JOBS (Jobs) ──────▼────────────────────────────────────────────┐
 │ GET /jobs (paginated, filterable by company/source/search).                    │
 │ (In Phase 1 jobs are seeded via POST /jobs / curl; Phase 3 scrapers fill this  │
 │  automatically.) Click a job → GET /jobs/{id} detail.                          │
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 5: CREATE APPLICATION ──────▼────────────────────────────────────────────┐
 │ "Create application" → POST /applications {job_id} → new row, status=pending,  │
 │ owned by you → React Query invalidates → navigate to /applications/{id}.       │
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 6: WORK THE PIPELINE (Applications) ▼─────────────────────────────────────┐
 │ Kanban board, 7 columns: pending→generated→sent→opened→replied→rejected→offer. │
 │ "Advance" buttons → PATCH /applications/{id}{status} → card moves columns.     │
 │ Toggle to Table view; open detail → email fields (empty: "Phase 2") + timeline.│
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 7: SEE PROGRESS (Dashboard) ▼─────────────────────────────────────────────┐
 │ GET /dashboard/stats → total applications, per-status counts, reply rate,      │
 │ recent activity → StatsGrid + Recharts bar chart + ActivityFeed update.        │
 └──────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌─ STEP 8: THEME / LOGOUT ──────────▼────────────────────────────────────────────┐
 │ Toggle light/dark (persists). Logout clears tokens → back to /login.           │
 └──────────────────────────────────────────────────────────────────────────────┘
```

**A single request, traced through every layer** (e.g. "advance an application to sent"):

```
 Browser click "→ sent"
   │  PATCH /applications/<id> {status:"sent"}   Authorization: Bearer <jwt>
   ▼
 RateLimitMiddleware ── Redis: under limit? ──► yes, continue
   ▼
 CORS middleware ── adds headers
   ▼
 applications router → update_application()
   ▼
 get_current_user() ── decode JWT → load User ──► Postgres
   ▼
 _owned(id, user) ── SELECT ... WHERE id=? AND user_id=? ──► Postgres
   │                                   └─ not yours? → 404
   ▼
 apply status change → UPDATE applications ──► Postgres (COMMIT)
   ▼
 serialize ApplicationOut (embeds the related job) → 200 JSON
   ▼
 React Query updates cache → Kanban re-renders, card now in "sent" column
```

---

## 11. Testing & the database-isolation story

- **51 backend tests** (pytest) cover auth, resumes, jobs, applications, dashboard,
  the rate limiter, models, migration, logging, and security — happy and unhappy paths,
  with external services mocked (e.g. an in-memory fake for MinIO, `fakeredis` for Redis).
- **Critical detail discovered via end-to-end testing:** tests run against a **separate
  database** (`applypilot_test`), auto-created on first run. Originally the tests pointed
  at the app's real `applypilot` DB and their teardown *dropped its tables* — which made
  the live `/auth/signup` return 500 because the running app had no tables. Isolating the
  test DB fixed it. This is why a green unit-test suite is *not* the same as a working
  app, and why we always smoke-test the real running stack.
- **Frontend gates:** `tsc --noEmit` (no `any`), `next build`, and a grep gate that fails
  if any hardcoded color sneaks in outside `globals.css`.

---

## 12. What is NOT built yet (the Phase 1 boundary)

Phase 1 is deliberately the skeleton. These are real, present-but-empty seams:

| Seam | Phase 1 state | Filled in |
|------|---------------|-----------|
| `jd_embedding`, `resume.embedding` (vector 1024) | columns exist, NULL | Phase 2 (embeddings) |
| `match_score` on jobs | NULL | Phase 2 |
| Email subject/body/cover letter on applications | NULL ("Phase 2" placeholder copy) | Phase 2 (Claude) |
| Jobs auto-populated | manual seed via API | Phase 3 (scrapers) |
| `contacts`, `email_accounts`, `follow_ups`, `agent_runs`, `feedback`, `usage_logs` tables | created, unused | Phases 2–6 |
| Celery workers/beat | not running (Redis is broker-ready) | Phase 2+ |
| Stripe billing / plan enforcement | plan field exists (`free`) | Phase 5 |
| Gmail send / reply polling / form auto-fill | not built | Phases 4 & 6 |

The full 6-phase roadmap lives in `docs/superpowers/specs/2026-06-19-applypilot-design.md` §9.

---

## 13. Quick reference — "where is X?"

| Question | Answer |
|----------|--------|
| Where's all the data? | PostgreSQL (`db` container, host port 5433) |
| Where are uploaded resume **files**? | MinIO bucket `applypilot`, key `<user_id>/<uuid>-<name>` |
| Where's resume **metadata**? | Postgres `resumes` table (filename, storage_url, storage_key) |
| What is Redis doing? | Rate limiting (sliding window). Future: Celery broker / cache |
| Where are passwords? | Postgres `users.password_hash`, bcrypt-hashed (never plaintext) |
| Where do tokens live? | Issued by backend; stored in browser `localStorage` |
| Who can talk to the DB? | Only the FastAPI backend. The frontend never does. |
| How is "my data only" enforced? | Every query filtered by `current_user.id`; mismatch → 404 |
| Where are colors defined? | Only in `frontend/app/globals.css` (CSS variables) |
| How do I run it? | `docker compose up --build`, then open http://localhost:3000 |
| Where's the API explorer? | http://localhost:8000/docs |
```
