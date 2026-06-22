# Phase 3 — Job Scraping

Status: Queued · Branch: `phase-3` (from `main` after Phase 2)

## Scope
Populate the global `jobs` table automatically by scraping multiple job boards, dedup,
compute JD embeddings, and score matches against each user's resume. Surface trigger and
run history on the agents page.

## Key agents / features
- **Job Scraper agent** (`backend/agents/job_scraper.py`) — Playwright (async) + BeautifulSoup, one strategy per source: LinkedIn, Greenhouse, Lever, Wellfound, YC, Internshala, Remotive, Indeed, Glassdoor, Naukri.
- **Dedup** by `(company, role, posted_at)` (the existing unique constraint); normalize `posted_at` so NULL-driven duplicates don't slip through (Phase 1 known issue).
- **Embeddings + match score** — reuse Phase 2's embeddings service: compute `jobs.jd_embedding`, write `jobs.match_score` per user via cosine similarity to the resume embedding.
- **Celery beat schedule** — periodic scrape per user (~6h); each run recorded in `agent_runs`. Anti-bot headers, timeouts, dynamic-load handling; **CAPTCHA → log + skip, never crash.**
- **Frontend** — agents page: per-source trigger buttons + run-history table (polls `agent_runs`); job feed shows real scraped rows and `match_score`.

## Dependencies
- New: `playwright` (+ `playwright install chromium`), `beautifulsoup4`, `lxml`.
- Reuses Phase 2 embeddings service and Celery infrastructure.
- No new mandatory API keys (scraping is direct); large Docker image due to browser binaries.

## Risks
- **LinkedIn / Indeed / Glassdoor ToS** prohibit automated access — may be blocked or trigger legal action; selectors break frequently. Documented in README, not restricted in code.
- Per-source selector fragility → isolate each source so one breakage doesn't fail the batch.
- Browser resource usage under Celery concurrency → cap parallel scrapes; reuse contexts.
- Rate-limiting/IP blocks → backoff, jitter, and per-source throttles.
