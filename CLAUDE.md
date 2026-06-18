# CLAUDE.md — Project directives. Read this fully before writing any code.
# These rules apply for the entire session, every session, without exception.



## CLAUDE CODE EXECUTION DIRECTIVES

You are running inside Claude Code with full tool access. These directives govern HOW you build — not just what you build. Follow them unconditionally throughout the entire session.

---

### TOOL USAGE MANDATES

**Bash tool — use continuously, not occasionally:**
- After writing EVERY file, immediately run it through a linter/type-checker in bash
- After writing EVERY Python file: `cd backend && python -m py_compile <file>.py && echo "✓ syntax ok"`
- After writing EVERY TypeScript file: `cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -40`
- After writing EVERY router/endpoint: spin up the FastAPI server in bash, hit the endpoint with curl, confirm 200
- After writing EVERY Celery task: import it in a Python REPL and confirm no import errors
- After ALL files are written: run the full test suite in bash, fix every failure before finishing
- Never assume code works. Prove it in bash.

**File reading — read before every edit:**
- Before modifying any existing file, use the Read tool to load its current contents
- Never edit from memory — always read first, edit second
- After every str_replace, read the file again to confirm the change applied correctly

**Grep/search — use to enforce consistency:**
- After writing all backend files: `grep -rn "TODO\|FIXME\|placeholder\|pass$\|NotImplemented\|raise Exception" backend/` — fix every hit
- After writing all frontend files: `grep -rn "TODO\|any\b\|@ts-ignore\|@ts-nocheck" frontend/src/` — fix every hit
- Run `grep -rn "hardcoded\|your_key\|sk-\|password123" .` — crash if any secrets found in code
- Before final handoff: `grep -rn "\.\.\.todo\|coming soon\|insert here\|example only" .` — must return zero results

**Directory/tree view — maintain awareness:**
- After creating each major section (backend, frontend, agents, etc.), run `find . -type f | sort` and verify the structure matches the spec exactly
- If any file from the spec is missing, create it before moving on

---

### CODE QUALITY GATES

Each gate must pass before moving to the next section. Do not proceed if a gate fails — fix it first.

**Gate 1 — After database schema:**
```bash
# Validate SQL syntax
psql $DATABASE_URL -f alembic/versions/001_initial.sql --dry-run
# Confirm all tables exist
psql $DATABASE_URL -c "\dt"
# Confirm pgvector extension
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Gate 2 — After all backend Python files:**
```bash
cd backend
pip install -r requirements.txt -q
python -m pytest tests/ -v --tb=short 2>&1
mypy . --ignore-missing-imports --strict 2>&1 | tail -20
flake8 . --max-line-length=100 --exclude=alembic/ 2>&1 | head -30
```

**Gate 3 — After all frontend files:**
```bash
cd frontend
npm install --silent
npx tsc --noEmit 2>&1
npx eslint . --ext .ts,.tsx --max-warnings=0 2>&1 | tail -30
npx next build 2>&1 | tail -20
```

**Gate 4 — After docker-compose:**
```bash
docker-compose config --quiet && echo "✓ compose valid"
docker-compose build --no-cache 2>&1 | tail -30
docker-compose up -d
sleep 10
curl -f http://localhost:8000/health && echo "✓ backend up"
curl -f http://localhost:3000 && echo "✓ frontend up"
docker-compose down
```

**Gate 5 — Final integration check:**
```bash
# Run full test suite inside Docker
docker-compose run --rm backend pytest tests/ -v
# Confirm no circular imports
cd backend && python -c "from main import app; print('✓ app imports clean')"
# Confirm all env vars documented
diff <(grep -oP '(?<=os.getenv\(")[^"]+' backend/**/*.py | sort -u) \
     <(grep -oP '(?<==)[A-Z_]+(?=\n|$)' .env.example | sort -u)
```

---

### SELF-REVIEW PROTOCOL

After completing each major module, stop and run this review before continuing:

**For every Python file, verify:**
- [ ] All functions have type hints (params + return type)
- [ ] All functions have docstrings (Google style: Args, Returns, Raises)
- [ ] No bare `except:` clauses — always `except SpecificError as e:`
- [ ] No `print()` statements — use `logger.info()` / `logger.error()`
- [ ] All database sessions properly closed (use context managers)
- [ ] All Playwright browser instances have `async with` / proper cleanup
- [ ] No secrets or tokens in code — only `settings.VARIABLE_NAME` references
- [ ] Every Celery task has `autoretry_for`, `max_retries`, and `default_retry_delay`

**For every TypeScript/React file, verify:**
- [ ] No `any` types — use proper interfaces or `unknown` with type guards
- [ ] All async functions have try/catch with user-facing error states
- [ ] All API calls use the centralized `lib/api.ts` instance (not raw fetch)
- [ ] All forms have loading + disabled states during submission
- [ ] All error states render user-friendly messages (not raw error objects)
- [ ] All data-fetching hooks handle: loading, error, empty, and success states
- [ ] No hardcoded API URLs — use `process.env.NEXT_PUBLIC_API_URL`

**For every API endpoint, verify:**
- [ ] Auth middleware applied (no unprotected routes except /health and /webhooks)
- [ ] Input validated via Pydantic schema
- [ ] Returns correct HTTP status codes (201 for create, 404 for not found, 422 for validation)
- [ ] Has OpenAPI summary + description docstring
- [ ] Rate limiting middleware applied
- [ ] Plan guard middleware applied where needed

---

### DOCUMENTATION STANDARDS

Every file must have a header block. Use these exact formats:

**Python:**
```python
"""
Module: agents/job_scraper.py
Purpose: Playwright-based scraper for 10 job board sources. Runs as a
         Celery periodic task, deduplicates by (company+role+date), computes
         JD embeddings, and scores match against user resume.
Dependencies: Playwright, BeautifulSoup4, anthropic, celery
Celery task: scrape_jobs_for_user (triggered by beat schedule every 6h)
Author: ApplyPilot
"""
```

**TypeScript:**
```typescript
/**
 * @module components/applications/ApplicationKanban
 * @description Drag-and-drop Kanban board for tracking application pipeline.
 *              Columns map to application.status enum values. Optimistic
 *              updates via React Query mutation on card move.
 * @dependencies @dnd-kit/core, @tanstack/react-query, shadcn/ui
 */
```

**Every function/method must have:**
```python
def find_recruiter_contact(company: str, role: str, user_id: str) -> Contact | None:
    """
    Discovers recruiter contact info for a given company and role.

    Uses SerpAPI to find LinkedIn profiles, then crawls the profile
    page with Playwright to extract name, title, and LinkedIn URL.
    Email is guessed via pattern matching and validated via SMTP handshake.

    Args:
        company: Company name as it appears on their website (e.g. "Stripe")
        role: Job role title (e.g. "Software Engineer Intern")
        user_id: UUID of the requesting user (for usage logging)

    Returns:
        Contact object if found, None if no reliable contact discovered.

    Raises:
        RateLimitError: If SerpAPI quota is exhausted for the day.
        ScrapingBlockedError: If LinkedIn detects and blocks the crawler.

    Example:
        >>> contact = find_recruiter_contact("Stripe", "SWE Intern", "uuid-123")
        >>> contact.email
        'recruiting@stripe.com'
    """
```

---

### TESTING REQUIREMENTS

Write tests as you build each module — not after. Minimum coverage:

**Backend (pytest):**
tests/

├── conftest.py                  # fixtures: test DB, mock Claude, mock Gmail

├── test_auth.py                 # JWT validation, expired token, wrong user

├── test_jobs.py                 # scrape trigger, dedup logic, match scoring

├── test_applications.py         # CRUD, status transitions, plan limit enforcement

├── test_agents/

│   ├── test_job_scraper.py      # mock Playwright, assert dedup + embedding

│   ├── test_contact_finder.py   # mock SerpAPI, assert email pattern logic

│   ├── test_email_generator.py  # mock Claude, assert JSON parse + storage

│   └── test_form_filler.py      # mock Playwright, assert field mapping

├── test_billing.py              # Stripe webhook signature, plan upgrade/downgrade

├── test_rate_limiter.py         # Redis sliding window, plan limits

└── test_security.py             # SQL injection attempts, auth bypass attempts

Every test must:
- Mock all external APIs (Claude, Gmail, SerpAPI, Stripe) — no real API calls in tests
- Use a separate test database (fixtures create + teardown per test)
- Test the unhappy path as much as the happy path
- Assert on HTTP status codes AND response body shape

Run and fix until this passes:
```bash
pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=75
```

---

### DEPENDENCY PINNING

requirements.txt must use exact versions. After writing it, run:
```bash
pip install -r requirements.txt
pip freeze > requirements.lock.txt
```

package.json must use exact versions (no `^` or `~`). After writing it, run:
```bash
npm install
npm shrinkwrap
```

---

### FINAL HANDOFF CHECKLIST

Before declaring the build complete, run this full checklist in bash and output the results:

```bash
echo "=== APPLYPILOT BUILD VERIFICATION ==="

echo "\n[1] No broken imports (Python)"
find backend -name "*.py" | xargs python -m py_compile && echo "✓ All Python files compile"

echo "\n[2] No TypeScript errors"
cd frontend && npx tsc --noEmit && echo "✓ TypeScript clean" && cd ..

echo "\n[3] No TODO/placeholder code remaining"
TODOS=$(grep -rn "TODO\|FIXME\|placeholder\|NotImplemented\|coming soon" --include="*.py" --include="*.ts" --include="*.tsx" . | grep -v ".git" | grep -v "node_modules" | wc -l)
echo "TODOs found: $TODOS" && [ "$TODOS" -eq 0 ] && echo "✓ Zero TODOs"

echo "\n[4] No hardcoded secrets"
SECRETS=$(grep -rn "sk-ant\|sk-\|password123\|hardcoded" --include="*.py" --include="*.ts" . | grep -v ".git" | wc -l)
echo "Secrets found: $SECRETS" && [ "$SECRETS" -eq 0 ] && echo "✓ No hardcoded secrets"

echo "\n[5] Test suite"
cd backend && pytest tests/ --tb=short -q 2>&1 | tail -5 && cd ..

echo "\n[6] All spec files present"
REQUIRED_FILES=(
  "backend/main.py"
  "backend/agents/job_scraper.py"
  "backend/agents/contact_finder.py"
  "backend/agents/email_generator.py"
  "backend/agents/form_filler.py"
  "backend/agents/follow_up_scheduler.py"
  "backend/agents/feedback_learner.py"
  "backend/tasks/celery_app.py"
  "backend/services/gmail_service.py"
  "backend/services/anthropic_service.py"
  "backend/services/stripe_service.py"
  "backend/prompts/cold_email.txt"
  "frontend/app/(dashboard)/dashboard/page.tsx"
  "frontend/app/(dashboard)/applications/page.tsx"
  "frontend/app/(dashboard)/agents/page.tsx"
  "frontend/components/applications/ApplicationKanban.tsx"
  "docker-compose.yml"
  ".github/workflows/deploy.yml"
  "README.md"
)
for f in "${REQUIRED_FILES[@]}"; do
  [ -f "$f" ] && echo "✓ $f" || echo "✗ MISSING: $f"
done

echo "\n=== BUILD VERIFICATION COMPLETE ==="
```

If any check fails, fix it. Do not output "build complete" until every check passes with ✓.

---

### CLAUDE CODE SESSION STRATEGY

Work in this exact order. Do not skip ahead:

1. Scaffold directory structure (mkdir -p all folders, touch all files)
2. Write + validate database schema → Gate 1
3. Write config.py, database.py, all models → compile check
4. Write all services (Gmail, Claude, Stripe, Storage) → compile check
5. Write all agents (one at a time, test each) → Gate 2 partial
6. Write Celery tasks → import check
7. Write all FastAPI routers → curl each endpoint
8. Write middleware (rate limiter, plan guard) → Gate 2 full
9. Write full pytest test suite → must hit 75% coverage
10. Write Next.js frontend (pages + components) → Gate 3
11. Write Docker + CI/CD config → Gate 4
12. Write README.md
13. Run final handoff checklist → Gate 5
14. Output a summary of every file created, its line count, and its test coverage

After step 14, the build is done. Not before.
