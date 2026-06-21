"""
Module: models/follow_up.py
Purpose: Scheduled follow-up for an application.
Author: ApplyPilot
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class FollowUp(Base):
    """A scheduled or sent follow-up message."""
    __tablename__ = "follow_ups"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False)
