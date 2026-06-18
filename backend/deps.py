"""
Module: deps.py
Purpose: FastAPI dependencies for DB session, Redis, and current user.
Author: ApplyPilot
"""
import uuid as _uuid
from collections.abc import Iterator

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.user import User
from security.jwt import decode_token

_redis_pool = redis.ConnectionPool.from_url(settings.redis_url)
_bearer = HTTPBearer(auto_error=False)


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


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        claims = decode_token(creds.credentials)
        if claims.get("type") != "access":
            raise JWTError("wrong token type")
        user_id = _uuid.UUID(str(claims["sub"]))
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
