# Phase 4 — Email Loop & Contact Finder

Status: Queued · Branch: `phase-4` (from `main` after Phase 3)

## Scope
Close the outreach loop: connect a Gmail account, send generated emails, track opens and
replies, schedule follow-ups, and discover recruiter contacts.

## Key agents / features
- **Gmail OAuth + send** (`backend/services/gmail_service.py`) — OAuth 2.0 connect flow; store tokens **Fernet-encrypted** in `email_accounts` (columns already exist). Send the application's `email_body`/`subject`.
- **Tracking** — open-tracking pixel + reply detection; update `applications.sent_at` / `reply_at` / `status` (`sent` → `opened` → `replied`).
- **Reply polling** — Celery beat polls connected inboxes for replies; writes `reply_at` and flips status.
- **Follow-up Scheduler agent** — beat hourly: applications sent & unreplied past `follow_up_at` → AI short follow-up (provider layer) → send → record in `follow_ups` (table exists).
- **Contact Finder agent** (`backend/agents/contact_finder.py`) — SerpAPI → Playwright LinkedIn profile crawl → name/title/URL; email via Hunter.io or pattern guess; SMTP-handshake validation (no send). Writes `contacts` (table exists). New `/contacts` router.
- **Frontend** — email-accounts connect screen; contacts book; application timeline shows sent/opened/replied events and scheduled follow-ups.

## Dependencies
- Keys: `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` (send/poll), `SERPAPI_KEY` (contact search), `HUNTER_API_KEY` (optional). `FERNET_KEY` (already in config) for token encryption.
- Reuses Phase 2 AI layer + Celery; Phase 3 Playwright.
- Missing keys disable the relevant feature with a 503 `feature_unavailable` — never crash.

## Risks
- **Bulk cold email** — CAN-SPAM / CASL / GDPR-PECR: accurate sender identity, physical address, working opt-out. Mass sending risks Gmail account suspension.
- **LinkedIn scraping** for contacts — same ToS risk as Phase 3.
- Token security — encrypt at rest, scope OAuth minimally, never log tokens.
- Deliverability/spam classification — warm-up, throttling, per-account send caps.
