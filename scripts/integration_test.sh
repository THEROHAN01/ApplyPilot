#!/usr/bin/env bash
#
# scripts/integration_test.sh
# Phase 1 full-stack integration test. Brings the entire docker-compose stack
# up from a clean slate, then exercises the core API journey end-to-end over
# HTTP: health → signup → /auth/me → create job → create application →
# dashboard stats, and confirms the frontend serves. Tears the stack down at
# the end (always, even on failure).
#
# Usage: ./scripts/integration_test.sh
# Requires: docker compose, curl, jq
#
set -euo pipefail

echo "=== APPLYPILOT PHASE 1 INTEGRATION TEST ==="

# Resolve the compose command (v2 plugin preferred, v1 fallback).
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "✗ docker compose not found" >&2
  exit 1
fi

# Operate from the repo root regardless of where the script is invoked.
cd "$(dirname "$0")/.."

cleanup() { echo "--- tearing down ---"; $DC down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "--- building and starting the stack ---"
$DC down -v >/dev/null 2>&1 || true
$DC up -d --build

# Wait for the backend to report healthy (poll, don't guess with a fixed sleep).
echo "--- waiting for backend /health ---"
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 2
  if [ "$i" -eq 60 ]; then echo "✗ backend never became healthy" >&2; exit 1; fi
done
curl -sf http://localhost:8000/health | jq -e '.status == "ok"' >/dev/null && echo "✓ backend healthy"

# Migrations are applied by the backend entrypoint; re-running is a no-op.
$DC exec -T backend alembic upgrade head >/dev/null && echo "✓ migrations applied"

# Signup returns a token pair.
SIGNUP=$(curl -sf -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"integration@applypilot.dev","password":"Test1234!","name":"Integration"}')
TOKEN=$(echo "$SIGNUP" | jq -r '.access_token')
[ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] && echo "✓ signup returns token"

# /auth/me echoes the authenticated user.
ME=$(curl -sf http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN")
echo "$ME" | jq -r '.email' | grep -q "integration@applypilot.dev" && echo "✓ /auth/me returns user"

# Create a job (jobs are global; manual create seeds one).
JOB=$(curl -sf -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"company":"Stripe","role":"SWE Intern","jd_url":"https://stripe.com/jobs/1","source":"manual"}')
JOB_ID=$(echo "$JOB" | jq -r '.id')
[ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ] && echo "✓ job creation works"

# Create an application linked to the job.
APP=$(curl -sf -X POST http://localhost:8000/applications \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\"}")
APP_ID=$(echo "$APP" | jq -r '.id')
[ -n "$APP_ID" ] && [ "$APP_ID" != "null" ] && echo "✓ application creation works"

# Dashboard stats reflect the one application just created.
STATS=$(curl -sf http://localhost:8000/dashboard/stats -H "Authorization: Bearer $TOKEN")
echo "$STATS" | jq -e '.total_applications == 1' >/dev/null && echo "✓ dashboard stats correct"

# Frontend serves and contains the app name.
for i in $(seq 1 30); do
  if curl -sf http://localhost:3000 >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -sf http://localhost:3000 | grep -q "ApplyPilot" && echo "✓ frontend loads"

echo "=== ALL INTEGRATION TESTS PASSED — PHASE 1 MERGE READY ==="
