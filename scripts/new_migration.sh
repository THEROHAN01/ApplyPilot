#!/usr/bin/env bash
# scripts/new_migration.sh — generate a new Alembic migration from model changes.
# Postgres must be up. Host DB defaults to localhost:5433.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${DATABASE_URL:=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot}"
export DATABASE_URL

read -r -p "Migration description (snake_case): " DESC
cd "$ROOT/backend"
alembic revision --autogenerate -m "$DESC"
echo "Migration created. Review it, then run: alembic upgrade head"
