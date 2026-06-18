"""
Module: models/job.py
Purpose: Scraped job posting with pgvector JD embedding.
Author: ApplyPilot
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Job(Base):
    """A job posting scraped from a source board."""

    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("company", "role", "posted_at", name="uq_job_dedup"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    company: Mapped[str] = mapped_column(String(300), nullable=False)
    role: Mapped[str] = mapped_column(String(300), nullable=False)
    jd_url: Mapped[str | None] = mapped_column(String(1000))
    jd_text: Mapped[str | None] = mapped_column(Text)
    jd_embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    location: Mapped[str | None] = mapped_column(String(300))
    salary_range: Mapped[str | None] = mapped_column(String(120))
    match_score: Mapped[float | None] = mapped_column(Float)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
