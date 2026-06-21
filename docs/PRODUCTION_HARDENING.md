# Production Hardening Checklist

Phase 1 is a **tested, merge-ready foundation** — not a production-ready product.
This checklist tracks the work required to take the codebase from "robust
foundation" to "safe to deploy and serve real users." Items are grouped by
urgency. Nothing here was in scope for the Phase 1 robustness audit (which was
test/QA only); this is the forward-looking backlog.

Legend: 🔴 blocker before any prod deploy · 🟠 operational gap · 🟢 nice-to-have

---

## 🔴 Blockers (fix before any production deploy)

- [ ] **Run the app server in production mode.** `backend/entrypoint.sh` runs
      `uvicorn main:app --reload` — that is dev mode (file-watching, single
      worker). Switch to a production process manager (e.g. `gunicorn` with
      `uvicorn.workers.UvicornWorker`, multiple workers) and drop `--reload`.
- [ ] **Fail fast on an insecure JWT secret.** `config.py` defaults
      `jwt_secret` to `"dev-only-insecure-change-me"`. In production this must
      be a required, high-entropy value — raise on startup if it is unset or
      equals the default when `app_env != "development"`.
- [ ] **Refresh-token revocation / rotation.** Refresh tokens are valid for 14
      days and cannot be invalidated (no server-side blocklist, no rotation on
      use, no logout-everywhere). A leaked refresh token is usable until expiry.
      Add a token store (Redis) with rotation + revocation, or switch to
      short-lived sessions.
- [ ] **Move frontend tokens out of `localStorage`.** `store/authStore.ts`
      persists tokens to `localStorage` (`applypilot-auth`), which is readable
      by any XSS. Prefer httpOnly, Secure, SameSite cookies set by the backend.

## 🟠 Operational readiness

- [ ] **Readiness probe.** `/health` is liveness-only. Add a readiness endpoint
      that checks DB, Redis, and MinIO connectivity so orchestrators don't route
      traffic to a half-up instance.
- [ ] **Observability.** Structured JSON logging with token scrubbing exists
      (`utils/logger.py`), but there are no metrics, no distributed tracing, and
      no error tracking. Add Prometheus/OpenTelemetry and an error reporter
      (e.g. Sentry).
- [ ] **Deploy pipeline.** `.github/workflows/phase1-ci.yml` is test-only. Add a
      build-and-ship workflow (image build, registry push, deploy + rollback).
- [ ] **Rate limiter fail-open decision.** `middleware/rate_limiter.py` fails
      open on Redis errors — during a Redis outage all limiting is disabled.
      Confirm this availability/security trade-off is intentional, or add a
      bounded in-process fallback.
- [ ] **Secrets management.** Replace `.env.example` defaults with a real
      secrets source (vault / cloud secret manager); never bake secrets into
      images or env files.
- [ ] **CORS / security headers.** Audit `cors_origins` for prod, and add
      security headers (HSTS, X-Content-Type-Options, etc.) — e.g. via a
      middleware or reverse proxy.
- [ ] **DB connection pool tuning.** `database.py` uses default pool settings;
      size them for the expected concurrency and the deployment topology.

## 🟢 Account & data lifecycle

- [ ] **Email verification on signup.**
- [ ] **Password reset flow.**
- [ ] **Account lockout / brute-force protection** beyond per-identity rate
      limiting.
- [ ] **User deletion endpoint** (also unblocks per-spec E2E teardown, which
      currently reuses a stable test account because no delete-user route
      exists).

## 🟢 Testing depth

- [ ] **Live MinIO I/O coverage.** `services/storage_service.py` real upload/
      delete paths are mocked in unit tests (43% line coverage) and only
      exercised by the Docker integration test. Add focused tests against a
      MinIO test container.
- [ ] **Load / performance / concurrency tests** (none today).
- [ ] **Failure-injection / chaos** (DB down, Redis down, MinIO down).

---

## Notes for future phases

Several routes the original Phase 1 spec referenced do **not** exist yet and are
expected to arrive in later phases — they are not bugs:

- No `contacts` or `users` CRUD router (only `/auth/me`).
- No plan-guard / billing middleware (Stripe is a later phase).
- Jobs are read/create-only (no `PATCH`/`DELETE`); they are populated by the
  scraper in a later phase.
- No resume download / presigned-URL endpoint.
- Application status has no transition rules — any valid enum value is accepted.

When those features land, fold their hardening needs into this checklist.
