"""
Module: models/usage_log.py
Purpose: Per-user monthly usage counters.
Author: ApplyPilot
"""
import uuid
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class UsageLog(Base):
    """Counter of a user's actions for a given month_year (YYYY-MM)."""
    __tablename__ = "usage_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    month_year: Mapped[str] = mapped_column(String(7), nullable=False)
