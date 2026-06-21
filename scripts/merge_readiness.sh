#!/usr/bin/env bash
#
# scripts/merge_readiness.sh
# Phase 1 merge-readiness gate. Every check must pass before opening a PR to
# main. Run from anywhere; it operates on the repo root.
#
# Backend Python is taken from a local virtualenv if one exists (./.venv or
# ./backend/.venv), otherwise from `python`/`python3` on PATH (as in CI).
#
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

# Resolve a python interpreter that has the backend deps installed.
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python";
elif [ -x "$ROOT/backend/.venv/bin/python" ]; then PY="$ROOT/backend/.venv/bin/python";
elif command -v python >/dev/null 2>&1; then PY="python";
else PY="python3"; fi

# Backend test env. Override DATABASE_URL/REDIS_URL externally to match your DB.
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export S3_ENDPOINT="${S3_ENDPOINT:-localhost:9000}"
export JWT_SECRET="${JWT_SECRET:-test-secret-key-not-for-prod}"

fail=0
echo "=== PHASE 1 MERGE READINESS GATE ==="

echo "[1] Python compiles clean"
if find backend -name "*.py" -not -path "*/.venv/*" -not -path "*/alembic/*" | xargs "$PY" -m py_compile 2>/dev/null; then
  echo "✓ Python compiles clean"; else echo "✗ Python compile errors"; fail=1; fi

echo "[2] TypeScript clean"
if (cd frontend && npx tsc --noEmit); then echo "✓ TypeScript clean"; else echo "✗ TypeScript errors"; fail=1; fi

echo "[3] Lint clean"
if (cd frontend && npx eslint . --ext .ts,.tsx --max-warnings=0 --quiet); then echo "✓ ESLint clean"; else echo "✗ ESLint errors"; fail=1; fi
if (cd backend && "$PY" -m flake8 . --count >/dev/null); then echo "✓ Flake8 clean"; else echo "✗ Flake8 errors"; fail=1; fi

echo "[4] No leftover TODOs"
COUNT=$(grep -rn "TODO\|FIXME\|NotImplemented" --include="*.py" --include="*.ts" --include="*.tsx" . \
  | grep -v .git | grep -v node_modules | grep -v "\.venv/" | grep -v "\.next/" | wc -l)
[ "$COUNT" -eq 0 ] && echo "✓ Zero TODOs" || { echo "✗ $COUNT TODOs remaining"; fail=1; }

echo "[5] No hardcoded secrets"
SECRETS=$(grep -rn "sk-ant\|password123\|secret123" --include="*.py" --include="*.ts" --include="*.tsx" . \
  | grep -v .git | grep -v node_modules | grep -v "\.venv/" | grep -v "tests/" | grep -v "e2e/" | wc -l)
[ "$SECRETS" -eq 0 ] && echo "✓ No hardcoded secrets" || { echo "✗ Secrets found"; fail=1; }

echo "[6] Backend tests pass with coverage (>=70%)"
if (cd backend && "$PY" -m pytest tests/ --cov=. --cov-fail-under=70 -q >/tmp/mr_pytest.log 2>&1); then
  tail -1 /tmp/mr_pytest.log; echo "✓ Backend tests pass"; else tail -5 /tmp/mr_pytest.log; echo "✗ Backend tests failed"; fail=1; fi

echo "[7] Frontend builds"
if (cd frontend && NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}" npx next build >/tmp/mr_build.log 2>&1); then
  echo "✓ Next.js builds"; else tail -10 /tmp/mr_build.log; echo "✗ Next.js build failed"; fail=1; fi

echo ""
if [ "$fail" -eq 0 ]; then echo "ALL GATES ✓ — open your PR to main."; else echo "SOME GATES FAILED — fix before opening the PR."; exit 1; fi
