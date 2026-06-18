# RESUME STATE — ApplyPilot Phase 1 (Subagent-Driven Execution)

**Last updated:** after Task A4 approved. **Branch:** `phase1-foundation`.

This file lets a fresh session resume the build with zero context loss. The
authoritative per-task ledger lives at `.git/sdd/progress.md` (persists on disk
across sessions; not committed). This committed file is the recovery map.

---

## How to resume (read this first)

1. Confirm branch: `git checkout phase1-foundation` (work is on this branch, NOT main).
2. Read the ledger: `cat "$(git rev-parse --git-path sdd)/progress.md"`. Tasks marked
   complete there are DONE — verify with `git log --oneline`; do NOT re-dispatch them.
3. Re-invoke the **superpowers:subagent-driven-development** skill to restore the process,
   then continue from the first incomplete task (currently **A5**).
4. Bring back the helper + environment (below), then dispatch A5.

## Environment to restore each session

- **Plan:** `docs/superpowers/plans/2026-06-19-applypilot-phase1-foundation.md`
- **Design:** `docs/superpowers/specs/2026-06-19-applypilot-design.md`
- **Python venv:** `backend/.venv` (deps already installed). Run python/pytest/alembic as
  `backend/.venv/bin/python`, `backend/.venv/bin/alembic`.
- **Database:** Postgres 16 + pgvector runs in Docker, published on **host port 5433**
  (5432 is taken by a local Postgres). Start it: `docker compose up -d db` (wait until
  healthy). The committed compose maps `5433:5432`; in-container clients use `db:5432`.
- **Running host tests** (the default `database_url` uses `db:5432`, unreachable from host) —
  ALWAYS override the env var:
  ```
  cd backend
  export DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot
  .venv/bin/python -m pytest tests/ -v
  ```
  Never hardcode `localhost:5433` in committed code; it's a test-run override only.

## The per-task loop (subagent-driven)

For each task N (A5, A6, … then B1–B8):

1. **Extract the brief** to a file (the plan uses `A1`/`B1` headers, so the skill's
   numeric `task-brief` script does NOT work — use this awk extractor):
   ```bash
   PLAN=docs/superpowers/plans/2026-06-19-applypilot-phase1-foundation.md
   SDD="$(cd "$(git rev-parse --git-path sdd)" && pwd)"
   ID=A5   # the task id
   awk -v id="$ID" '
     /^```/ { infence = !infence }
     !infence && /^### Task / { intask = ($0 ~ ("^### Task " id ":")) }
     !infence && intask && /^# PART/ { intask = 0 }
     !infence && intask && /^## Self-Review/ { intask = 0 }
     intask { print }
   ' "$PLAN" > "$SDD/task-$ID-brief.md"
   ```
2. **Record BASE:** `git rev-parse --short HEAD` (use this as review-package BASE — never HEAD~1).
3. **Dispatch implementer** (general-purpose agent, **model: sonnet**). Prompt must include:
   where the task fits (1 line), the brief path ("read this first — your requirements,
   verbatim values"), interfaces/decisions from earlier tasks, the host-DB run instructions
   above (for any task with DB-touching tests), the report path
   `.git/sdd/task-$ID-report.md`, and the report contract (Status / commits / 1-line test
   summary / concerns / report path).
4. **Generate review package:**
   `BASE_HEAD` via the skill script:
   `/home/rohan/.claude/plugins/cache/claude-plugins-official/superpowers/6.0.2/skills/subagent-driven-development/scripts/review-package BASE HEAD`
   (prints the diff file path).
5. **Dispatch task reviewer** (general-purpose, sonnet for substantial diffs / haiku for tiny
   transcription diffs). Give it: brief path, report path, diff path, and the task's binding
   Global Constraints copied verbatim. Do NOT pre-judge findings.
6. **Triage findings yourself** (you hold plan context the reviewer lacks): fix real
   Critical/Important via one fix subagent; decline plan-mandated/spec-contradicting findings
   with reasoning; record declined + Minor findings in the ledger for the final review.
7. **Re-review** fix passes (cheap model ok for small fixes) or spot-verify trivial mechanical
   fixes directly.
8. **Update ledger** (`Task N: complete (commits base7..head7, review clean)`) and mark the
   harness todo complete. Continue to next task without pausing.

After all tasks (A5–A12, B1–B8): dispatch the **final whole-branch review**
(superpowers:requesting-code-review's code-reviewer.md, most capable model) over
`review-package $(git merge-base main HEAD) HEAD`, hand it the deferred-findings backlog from
the ledger, fix in ONE batch, then use **superpowers:finishing-a-development-branch**.

## Global Constraints (bind every task — copy into reviewer prompts)

- Python ≥ 3.11; all functions type-hinted; Google-style docstrings; no bare `except:`; no
  `print()` (use logger); DB sessions via context-managed dependency; no secrets in code
  (only `settings.X`).
- TypeScript only, no `any`; all data views handle loading/error/empty/success; all forms have
  loading+disabled; API base from `NEXT_PUBLIC_API_URL`; all server calls via `lib/api.ts`.
- Pinned versions only (`==` / no `^`/`~`).
- Embeddings `vector(1024)` (NULL in Phase 1).
- HTTP: 201 create / 200 read+update / 204 delete / 401 / 403 / 404 / 422; OpenAPI summary on
  every endpoint.
- Multi-tenancy: every query filtered by `current_user.id`; ownership mismatch → 404. SQL RLS
  is the documented Supabase-swap path; API-layer filtering is the active mechanism.
- **Blueprint design system:** radius 0; hard offset shadows `3px 3px 0 var(--ink)` (never
  blurred); VT323 headings/labels/buttons, Source Serif 4 body, JetBrains Mono code; accent
  blueprint-blue; light `#fafaf5`, dark `#0a0d1a`.
- **NO hardcoded colors** outside `app/globals.css` token blocks — only semantic Tailwind
  tokens (`bg`, `ink`, `blueprint`, `on-accent`, `warn`, …). Forbid `text-white`/`bg-black`/
  hex/`rgb()`/color-scale utilities in components.

## Progress

| Task | Status | Commits |
|------|--------|---------|
| A1 Infra scaffold/config/logger/health/compose | ✅ done | 55506f8..725eccf |
| A2 DB engine/session/deps | ✅ done | 9a848be..8e633a6 |
| A3 ORM models (10 tables) | ✅ done | 8e633a6..278f98c |
| A4 Alembic migration (pgvector/indexes/RLS) | ✅ done | 278f98c..1cbff7f |
| **A5 JWT security + auth schemas + current-user dep** | ⏭️ **NEXT** | — |
| A6 Auth router | pending | — |
| A7 Storage service + resume upload | pending | — |
| A8 Jobs router | pending | — |
| A9 Applications router | pending | — |
| A10 Dashboard stats | pending | — |
| A11 Rate limiter | pending | — |
| A12 Backend Dockerfile + container test | pending | — |
| B1 Next.js scaffold + Blueprint | pending | — |
| B2 Types + api client + stores | pending | — |
| B3 Providers + UI primitives + auth pages | pending | — |
| B4 Dashboard shell | pending | — |
| B5 Jobs feed + detail | pending | — |
| B6 Applications + dashboard + settings | pending | — |
| B7 Frontend Dockerfile + full-stack smoke | pending | — |
| B8 README + verification gates | pending | — |

## Deferred findings backlog (fix during final review)

- **A1 finding 1 (declined):** credentials typed `str` not `SecretStr` (jwt_secret, s3 keys,
  fernet_key). Local-dev defaults, consumed as plain strings downstream. Revisit if hardening.
- **A1 finding 7 (declined):** compose `env_file: ./backend/.env.example` (deliberate
  zero-config local `docker compose up`).
- **A4 Minor 1:** conftest `_schema` fixture should be annotated
  `-> Generator[None, None, None]` (mypy --strict).
- **A4 Minor 2:** add inline comment in `001_initial.py` above `jobs` ENABLE RLS noting the
  Supabase-swap path needs a permissive SELECT policy on the global `jobs` table.

## Notes / decisions made mid-flight

- Host db port remapped 5432→5433 (commit 9a848be) to avoid clash with the user's local PG.
- MinIO image pinned (was `:latest`) during A1 fix pass.
- Logger scrubs token patterns in message bodies (A1 fix), not just `extra_fields`.
- `Application.job` relationship added in A3 (required for A9 `ApplicationOut` serialization).
- A7 will EXTEND `tests/conftest.py` to add a fake `get_storage` override (don't recreate it).
- A11 uses `fakeredis` (add `fakeredis==2.26.1` to requirements); A7/unit tests use a fake
  storage override — so only the DB container is needed for unit tests. A12/B7 full-stack runs
  also need redis (6379) and minio (9000/9001) host ports — watch for host port clashes then.
