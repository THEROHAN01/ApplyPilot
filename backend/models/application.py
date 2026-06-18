"""
Module: models/application.py
Purpose: Application record tracking outreach state per job.
Author: ApplyPilot
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ApplicationStatus(str, enum.Enum):
    """Lifecycle states of an application."""

    pending = "pending"
    generated = "generated"
    sent = "sent"
    opened = "opened"
    replied = "replied"
    rejected = "rejected"
    offer = "offer"


class Application(Base):
    """A user's application/outreach for a specific job."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.pending, nullable=False
    )
    email_subject: Mapped[str | None] = mapped_column(String(500))
    email_body: Mapped[str | None] = mapped_column(Text)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    linkedin_msg: Mapped[str | None] = mapped_column(Text)
    recruiter_email: Mapped[str | None] = mapped_column(String(320))
    recruiter_linkedin: Mapped[str | None] = mapped_column(String(1000))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship()
