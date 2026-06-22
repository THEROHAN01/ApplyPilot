# ApplyPilot — Development Guide

From a fresh macOS/Linux machine to a running, tested stack. Commands are exact. Phase 1
needs **no API keys**.

---

## 1. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Docker + Compose v2 | latest | `docker --version && docker compose version` |
| Python | 3.11+ (3.12 used here) | `python3 --version` |
| Node.js | 20.x | `node --version` |
| git | any recent | `git --version` |

macOS: install Docker Desktop. Linux: install Docker Engine + the compose plugin.

## 2. Clone + checkout

```bash
git clone <repo-url> ApplyPilot
cd ApplyPilot
git checkout main           # Phase 1 is on main
```

## 3. Copy env files

Phase 1 runs on committed defaults — copying is only needed for host (non-Docker) dev or
to change a value.

```bash
cp backend/.env.example backend/.env           # backend (optional for Docker)
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > frontend/.env.local
```

**Required vars for Phase 1 alone:** none — the defaults work. For a non-local run, set a
strong `JWT_SECRET` and correct `DATABASE_URL`/`REDIS_URL`/`S3_*`/`CORS_ORIGINS`/
`NEXT_PUBLIC_API_URL`. Full list: `docs/ENVIRONMENT_VARIABLES.md`. No AI keys are needed
until Phase 2.

## 4. Start the stack

```bash
docker compose up -d --build
```

Brings up `db` (Postgres+pgvector, host **5433**), `redis` (6379), `minio` (9000/9001),
`backend` (8000), `frontend` (3000). The backend waits for the DB to be healthy.

## 5. Run migrations

The backend container does not auto-migrate. Apply the schema:

```bash
docker compose exec backend alembic upgrade head
```

Host-side equivalent (DB must be up; note port 5433):
```bash
cd backend
DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
  alembic upgrade head
```

## 6. Seed sample data

Idempotent — safe to run repeatedly. Creates 2 users, 5 jobs, 3 applications, 1 resume row.

```bash
DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
  python scripts/seed.py
```
Login with `dev@applypilot.local / DevTest1234!` (free) or `pro@applypilot.local / ProTest1234!` (pro).

## 7. Verify backend

```bash
curl http://localhost:8000/health        # {"status":"ok"}
open http://localhost:8000/docs           # Swagger UI
```

## 8. Verify frontend

Open `http://localhost:3000`, log in with a seeded account, confirm the dashboard,
jobs, and applications pages render. (MinIO console: `http://localhost:9001`,
`minioadmin`/`minioadmin`.)

## 9. Run the test suite

```bash
bash scripts/run_tests.sh
```
Runs backend pytest + coverage (HTML → `docs/coverage/`), then frontend `tsc`, eslint, and
`next build`. The backend tests need Postgres up; they target a dedicated
`applypilot_test` DB that fixtures create/teardown. Quick health probe of running
services: `bash scripts/check_health.sh`.

---

## 10. How to add a new API endpoint (5-step checklist)

1. **Schema** — add request/response Pydantic models in `backend/schemas/<area>.py` (no `any`-equivalent loose dicts; type every field).
2. **Router** — add the handler in `backend/routers/<area>.py`. Use `Depends(get_current_user)` for auth and `Depends(get_db)` for the session. Filter every query by `current_user.id`; return 404 (not 403) on cross-user access. Add an OpenAPI `summary=` and a Google-style docstring. Use correct status codes (201 create / 200 read+update / 204 delete).
3. **Register** — `app.include_router(<area>.router)` in `backend/main.py`.
4. **Test** — add `backend/tests/test_<area>.py` covering happy + unhappy paths (401, 404, 422); assert status code **and** body shape. Mock external services.
5. **Verify** — `python -m py_compile` the new files, then `pytest tests/test_<area>.py -q` (DB up, `DATABASE_URL` pointing at 5433). Update `docs/API_REFERENCE.md`.

## 11. How to add a new frontend page (5-step checklist)

1. **Route** — create `frontend/app/(dashboard)/<route>/page.tsx` (or `(auth)/…`). Use only Blueprint semantic tokens — no hardcoded colors.
2. **Types** — add/extend interfaces in `frontend/types/index.ts` to mirror the backend schema. No `any`.
3. **Data** — fetch via a React Query hook in `frontend/hooks/use<Area>.ts` that calls `lib/api.ts` (never raw `fetch`). Handle **loading / error / empty / success** states; forms get loading+disabled states.
4. **Nav** — add the link to `components/shared/Sidebar.tsx` if it belongs in the dashboard nav.
5. **Verify** — `cd frontend && npx tsc --noEmit && npx eslint . --ext .ts,.tsx --max-warnings=0 && npx next build`.

## 12. How to switch AI provider (Phase 2+)

One line in `.env`:
```bash
AI_PROVIDER=sarvam     # sarvam | anthropic | openai | ollama
```
Set the matching key (`SARVAM_API_KEY`, `ANTHROPIC_API_KEY`, …). No code changes anywhere.
Full contract and the add-a-provider guide: `docs/AI_PROVIDER_LAYER.md`.

---

## Troubleshooting

- **`could not translate host name "db"`** when running tests/uvicorn on the host: you
  didn't override `DATABASE_URL`. The default points at the in-Docker hostname `db`. Use
  `…@localhost:5433/…` for host runs.
- **Port 5432 already in use:** intentional — Compose publishes Postgres on **5433** to
  avoid clashing with a local Postgres. In-container clients still use `db:5432`.
- **Frontend calls go to the wrong API:** `NEXT_PUBLIC_API_URL` is baked at `next build`.
  Rebuild the image (or pass it as a build arg) after changing it.
- **Tests can't find pgvector:** the `_schema` fixture runs `CREATE EXTENSION IF NOT
  EXISTS vector`; ensure you're on the `pgvector/pgvector:pg16` image (compose `db` service).
