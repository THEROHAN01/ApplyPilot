"""
Module: schemas/resume.py
Purpose: Pydantic response schema for resume resources.
Author: ApplyPilot
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeOut(BaseModel):
    """Serialised representation of a stored resume."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    storage_url: str
    created_at: datetime
