"""
Module: deps.py
Purpose: FastAPI dependencies for DB session, Redis, and current user.
Author: ApplyPilot
"""
from collections.abc import Iterator

import redis
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal

_redis_pool = redis.ConnectionPool.from_url(settings.redis_url)


def get_db() -> Iterator[Session]:
    """Yield a database session and ensure it is closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_redis() -> redis.Redis:
    """Return a Redis client bound to the shared pool."""
    return redis.Redis(connection_pool=_redis_pool)
