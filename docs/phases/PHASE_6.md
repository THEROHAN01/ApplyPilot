# Phase 6 — Form Filler, Feedback Learner & Polish

Status: Queued · Branch: `phase-6` (from `main` after Phase 5)

## Scope
The capstone: ATS auto-fill (vision-driven), a learning loop from reply outcomes, GDPR
data lifecycle, CI/CD, and production hardening. Clears the `docs/PRODUCTION_HARDENING.md`
backlog.

## Key agents / features
- **Form Filler agent** (`backend/agents/form_filler.py`) — Playwright on Greenhouse /
  Lever / Workday: navigate → **vision model maps fields from screenshot + HTML** →
  fill/select/upload resume → **pause + preview screenshot** → submit only on user confirm.
  **Pro/Unlimited only.** Requires vision: **set `AI_PROVIDER=anthropic` for this
  workload** (`sarvam-105b` is text-only). The provider layer makes this a config choice.
- **Feedback Learner agent** (`backend/agents/feedback_learner.py`) — Gmail poll detects
  replies → prompt user 👍/👎 (`feedback` table) → monthly compute per-template reply
  rates → AI compares hi/lo performers → update prompt templates.
- **GDPR** — data-export endpoint (all user data as JSON/zip) + cascade account deletion
  (`DELETE /users/me`); also unblocks per-spec E2E teardown (no delete-user route today).
- **CI/CD** — extend `.github/workflows/` beyond test-only: image build, registry push,
  deploy + rollback.
- **Production hardening** — work the `PRODUCTION_HARDENING.md` blockers: gunicorn +
  UvicornWorker (drop `--reload`), fail-fast on insecure `JWT_SECRET`, refresh-token
  rotation/revocation (Redis jti store), move frontend tokens to httpOnly cookies,
  readiness probe, observability (metrics/tracing/Sentry), security headers, pool tuning.

## Dependencies
- Key: `ANTHROPIC_API_KEY` (vision for form-fill). Reuses Phase 2 AI layer, Phase 3
  Playwright, Phase 4 Gmail/feedback signals, Phase 5 plan guard (pro-gating).

## Risks
- **ATS auto-submit ToS** — many providers prohibit automated submission; the human-confirm
  pause before final submit is a deliberate product-safety design choice.
- **Vision cost/latency** — screenshots + Anthropic vision are pricier/slower; cap usage, cache field maps per ATS template.
- **Form variability** — ATS layouts differ widely; isolate per-ATS strategies, fail safe (never submit on uncertainty).
- **Hardening regressions** — token-cookie + revocation changes touch auth broadly; cover with tests before shipping.
