"""
Module: routers/dashboard.py
Purpose: Aggregate application statistics for the dashboard overview.
         Returns total count, per-status breakdown, reply rate, and recent
         applications — all scoped to the authenticated user.
Dependencies: FastAPI, SQLAlchemy, models.application, schemas.dashboard
Author: ApplyPilot
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.application import Application
from models.user import User
from schemas.application import ApplicationOut
from schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_REPLIED_STATUSES = ("replied", "offer")


@router.get("/stats", response_model=DashboardStats, summary="Dashboard aggregate stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardStats:
    """Return application counts, per-status breakdown, reply rate, and recent items.

    All queries are scoped to current_user.id so users only see their own data.
    reply_rate denominator is total applications; numerator is replied + offer.

    Args:
        db: Injected SQLAlchemy session.
        current_user: Authenticated user from JWT dependency.

    Returns:
        DashboardStats with total_applications, by_status dict, reply_rate,
        and up to five most-recent ApplicationOut items.

    Raises:
        HTTPException 401: If the caller is not authenticated (raised by dep).
    """
    rows = (
        db.query(Application.status, func.count(Application.id))
        .filter(Application.user_id == current_user.id)
        .group_by(Application.status)
        .all()
    )
    by_status: dict[str, int] = {status.value: count for status, count in rows}
    total = sum(by_status.values())
    replied = sum(by_status.get(s, 0) for s in _REPLIED_STATUSES)
    reply_rate = round(replied / total, 4) if total else 0.0
    recent_rows = (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
        .limit(5)
        .all()
    )
    return DashboardStats(
        total_applications=total,
        by_status=by_status,
        reply_rate=reply_rate,
        recent=[ApplicationOut.model_validate(a) for a in recent_rows],
    )
