"""
Module: routers/health.py
Purpose: Unauthenticated liveness endpoint.
Author: ApplyPilot
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}
