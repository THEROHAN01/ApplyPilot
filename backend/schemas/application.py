"""
Module: schemas/application.py
Purpose: Pydantic request/response schemas for the applications router.
         Covers ApplicationCreate (POST body), ApplicationUpdate (PATCH body),
         and ApplicationOut (API response with embedded JobOut).
Author: ApplyPilot
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.application import ApplicationStatus
from schemas.job import JobOut


class ApplicationCreate(BaseModel):
    """Payload for creating a new application linked to an existing job."""

    job_id: uuid.UUID


class ApplicationUpdate(BaseModel):
    """Partial-update payload for an existing application."""

    status: ApplicationStatus | None = None
    email_subject: str | None = None
    email_body: str | None = None
    cover_letter: str | None = None
    linkedin_msg: str | None = None
    recruiter_email: str | None = None
    recruiter_linkedin: str | None = None


class ApplicationOut(BaseModel):
    """Full application record returned by the API, with embedded job details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    email_subject: str | None
    email_body: str | None
    cover_letter: str | None
    linkedin_msg: str | None
    recruiter_email: str | None
    recruiter_linkedin: str | None
    sent_at: datetime | None
    follow_up_at: datetime | None
    reply_at: datetime | None
    created_at: datetime
    job: JobOut
