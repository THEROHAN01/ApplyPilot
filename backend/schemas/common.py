"""
Module: schemas/common.py
Purpose: Common response schemas.
Author: ApplyPilot
"""
from pydantic import BaseModel


class Message(BaseModel):
    """Simple message envelope."""
    detail: str
