"""
Module: schemas/job.py
Purpose: Pydantic schemas for job create/read — JobCreate (POST body), JobOut
         (API response), and JobList (paginated list envelope).
Author: ApplyPilot
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    source: str
    company: str
    role: str
    jd_url: str | None = None
    jd_text: str | None = None
    location: str | None = None
    salary_range: str | None = None
    posted_at: datetime | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source: str
    company: str
    role: str
    jd_url: str | None
    location: str | None
    salary_range: str | None
    match_score: float | None
    posted_at: datetime | None
    status: str


class JobList(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int
