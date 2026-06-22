#!/usr/bin/env bash
# scripts/run_tests.sh — full test suite: backend pytest+coverage, frontend tsc/eslint/build.
# Postgres must be up (docker compose up -d db). Host DB defaults to localhost:5433.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${DATABASE_URL:=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot}"
export DATABASE_URL

echo "=== ApplyPilot Test Suite ==="

printf '\n-- Backend: pytest --\n'
cd "$ROOT/backend"
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html:../docs/coverage/
echo "Coverage HTML: docs/coverage/index.html"

printf '\n-- Frontend: TypeScript --\n'
cd "$ROOT/frontend" && npx tsc --noEmit

printf '\n-- Frontend: ESLint --\n'
npx eslint . --ext .ts,.tsx --max-warnings=0

printf '\n-- Frontend: Build --\n'
npx next build

printf '\n=== All checks passed ===\n'
