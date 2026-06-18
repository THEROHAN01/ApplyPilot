"""
Module: models/user.py
Purpose: User ORM model and plan tier enum.
Author: ApplyPilot
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PlanTier(str, enum.Enum):
    """Subscription plan tiers."""

    free = "free"
    pro = "pro"
    unlimited = "unlimited"


class User(Base):
    """Application user with auth credentials and plan."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[PlanTier] = mapped_column(Enum(PlanTier, name="plan_tier"), default=PlanTier.free, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")
