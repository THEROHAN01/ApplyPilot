"""User response schema."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from models.user import PlanTier


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    name: str | None
    avatar_url: str | None
    plan: PlanTier
    created_at: datetime
