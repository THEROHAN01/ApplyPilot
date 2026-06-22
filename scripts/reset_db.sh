#!/usr/bin/env bash
# scripts/reset_db.sh — DESTROY and recreate the local database, then re-migrate + seed.
# Drops the Postgres volume (all local data is lost) and brings it back clean.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f $ROOT/docker-compose.yml"
: "${DATABASE_URL:=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot}"
export DATABASE_URL

echo "!! This DESTROYS all local Postgres data (the pgdata volume) for ApplyPilot."
read -r -p "Type 'yes' to continue: " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 1; }

echo "-- Stopping db and removing its volume --"
$COMPOSE stop db
$COMPOSE rm -fsv db

echo "-- Starting a fresh db --"
$COMPOSE up -d db
echo -n "Waiting for Postgres to be ready"
until $COMPOSE exec -T db pg_isready -U applypilot >/dev/null 2>&1; do echo -n "."; sleep 1; done
echo " ready."

echo "-- Applying migrations --"
( cd "$ROOT/backend" && alembic upgrade head )

echo "-- Seeding sample data --"
python "$ROOT/scripts/seed.py"

echo "=== Database reset complete ==="
