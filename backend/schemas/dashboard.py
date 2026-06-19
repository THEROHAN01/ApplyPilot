"""
Module: schemas/dashboard.py
Purpose: Pydantic response schema for the dashboard aggregate stats endpoint.
         Carries total application count, per-status breakdown, reply rate,
         and the five most-recently-created applications (embedded with job).
Dependencies: pydantic, schemas.application
Author: ApplyPilot
"""
from pydantic import BaseModel

from schemas.application import ApplicationOut


class DashboardStats(BaseModel):
    """Aggregate statistics returned by GET /dashboard/stats.

    Attributes:
        total_applications: Count of all applications owned by the user.
        by_status: Mapping of ApplicationStatus value -> count.
        reply_rate: Fraction of applications that received a reply or offer,
                    rounded to 4 decimal places; 0.0 when no applications exist.
        recent: Up to five most recently created applications, newest first.
    """

    total_applications: int
    by_status: dict[str, int]
    reply_rate: float
    recent: list[ApplicationOut]
