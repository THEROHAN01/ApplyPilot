# Phase 5 — Billing & Plan Enforcement

Status: Queued · Branch: `phase-5` (from `main` after Phase 4)

## Scope
Monetize: Stripe subscriptions, plan-tier enforcement across the API, usage metering, and
the billing UI. The `plan` (on `users`) and `usage_logs` table already exist.

## Key features
- **Stripe service** (`backend/services/stripe_service.py`) — checkout session, customer
  portal, subscription lifecycle. Persist `users.stripe_customer_id`.
- **Webhook handler** — `POST /webhooks/stripe` (unauthenticated but **signature-verified**
  via `STRIPE_WEBHOOK_SECRET`). Handle `checkout.session.completed`,
  `customer.subscription.updated/deleted` → update `users.plan` (`free`/`pro`/`unlimited`).
- **Plan guard middleware** (`backend/middleware/plan_guard.py`) — reads `plan` + current
  month's `usage_logs`; enforces per-tier limits (e.g. generations/month, sends/month,
  form-fills pro+ only). Returns `403 {"error":"plan_limit_reached"}` when exceeded.
- **Usage metering** — increment `usage_logs` (`action`, `count`, `month_year`) on metered
  actions (generate, send, scrape).
- **Frontend** — billing page (current plan, usage bars, manage-subscription → Stripe
  portal), upgrade modal triggered on limit-reached responses, `PlanBadge` reflects tier.

## Dependencies
- Keys: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`. SDK: `stripe` (pinned).
- Touches existing routers (apply plan guard where metered) and `agent_runs`/generation flows.
- Missing key → billing endpoints disabled (503), app still runs on the free tier.

## Risks
- **Webhook security** — must verify signatures; never trust client-reported plan state. Reconcile from Stripe as source of truth.
- **Idempotency** — webhook retries; dedup by event id.
- **Limit-check race conditions** — enforce metering atomically (DB constraint or locked upsert).
- **Test mode vs live** — keep keys/env separate; never hardcode price ids.
