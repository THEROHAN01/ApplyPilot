#!/usr/bin/env bash
# scripts/check_health.sh — quick liveness probe of the running stack.
# Uses docker compose service names (db/redis/minio) so it works regardless of the
# generated container-name prefix.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f $ROOT/docker-compose.yml"

echo "=== ApplyPilot Service Health ==="

if curl -sf http://localhost:8000/health | (command -v jq >/dev/null && jq '.' || cat); then
  echo "✓ Backend (FastAPI)"
else
  echo "✗ Backend (FastAPI) unreachable on :8000"
fi

curl -sf http://localhost:3000 > /dev/null && echo "✓ Frontend (Next.js)" \
  || echo "✗ Frontend (Next.js) unreachable on :3000"

$COMPOSE exec -T db pg_isready -U applypilot >/dev/null 2>&1 \
  && echo "✓ PostgreSQL" || echo "✗ PostgreSQL not ready"

$COMPOSE exec -T redis redis-cli ping >/dev/null 2>&1 \
  && echo "✓ Redis" || echo "✗ Redis not responding"

$COMPOSE exec -T minio curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1 \
  && echo "✓ MinIO" || echo "✗ MinIO not healthy"

echo "=== Done ==="
