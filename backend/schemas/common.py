"""Common response schemas."""
from pydantic import BaseModel


class Message(BaseModel):
    """Simple message envelope."""
    detail: str
