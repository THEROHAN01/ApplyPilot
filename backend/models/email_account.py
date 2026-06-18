"""
Module: models/email_account.py
Purpose: Connected email account with encrypted tokens.
Author: ApplyPilot
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class EmailProvider(str, enum.Enum):
    """Supported email service providers."""

    gmail = "gmail"
    outlook = "outlook"


class EmailAccount(Base):
    """OAuth-connected sending account; tokens stored encrypted."""
    __tablename__ = "email_accounts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider, name="email_provider"), nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
