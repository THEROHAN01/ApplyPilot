# ApplyPilot — Phase 2 Kickoff Prompt

Paste the block below as the first message of a fresh Claude Code session to start
Phase 2 with full context.

---

```
# ApplyPilot — Phase 2 Kickoff: AI Generation Engine

You are continuing ApplyPilot, an autonomous AI job-application SaaS. Phase 1
(foundation) is complete and merged. You are building Phase 2.

## Step 0 — Orient before writing any code
Read these, in order, fully:
1. CLAUDE.md                      — project constitution (rules, what already exists)
2. docs/phases/PHASE_2.md         — your complete build spec for this phase
3. docs/AI_PROVIDER_LAYER.md      — the AI contract you must implement
4. docs/ARCHITECTURE.md + docs/DATABASE_SCHEMA.md + docs/API_REFERENCE.md — current system

Then run and confirm the baseline is healthy:
    docker compose up -d db        # Postgres on host port 5433
    cd backend && DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
      pytest tests/ -q             # expect 109 passing
Never rebuild anything Phase 1 already built — import and extend only.

## What Phase 2 delivers (detail in docs/phases/PHASE_2.md)
- Provider-agnostic AI layer (backend/services/ai/), default provider Sarvam AI
- Local embeddings service (BAAI/bge-large-en-v1.5, 1024-d) + resume↔JD match score
- Email Generator agent → {subject, email_body, cover_letter, linkedin_message}
- Celery (worker + beat) on Redis, with agent_runs tracking
- POST /applications/{id}/generate + GET /agent_runs/{id}
- Frontend: Generate CTA + email preview/edit modal (poll agent_runs)

## Iron rules (from CLAUDE.md — do not violate)
- Agents/routers/tasks MUST import only from services.ai — NEVER an AI SDK directly.
- Sarvam gotchas: AsyncSarvamAI, constructor param api_subscription_key (not api_key),
  method client.chat.completions(...) NOT .completions.create().
- Missing SARVAM_API_KEY → 503 {"error":"feature_unavailable",...}, never a crash.
- Python: type hints + Google docstrings, no bare except, no print (use logger).
- Frontend: no `any`, all calls via lib/api.ts, Blueprint tokens only (no hardcoded colors).
- Pinned deps only. Tests mock all providers (no real API calls). Keep coverage ≥70%.

## Workflow
First branch from main: git checkout main && git checkout -b phase-2
Use brainstorming/planning before implementing. Build in the order in PHASE_2.md §10,
compile/test after each file. Do not add the Co-Authored-By trailer to commits.
Run the quality gates in PHASE_2.md §11 before declaring the phase done.
```
