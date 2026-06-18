"""
Module: security/jwt.py
Purpose: Password hashing and JWT issue/verify for self-contained auth.
Dependencies: passlib[bcrypt], python-jose
Author: ApplyPilot
"""
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password."""
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return _pwd.verify(password, password_hash)


def _create_token(subject: str, token_type: str, expires: timedelta) -> str:
    """Create a signed JWT with subject, type, and expiry."""
    now = datetime.now(timezone.utc)
    claims = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    """Create a short-lived access token for the subject (user id)."""
    return _create_token(subject, "access", timedelta(minutes=settings.access_token_ttl_min))


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token for the subject (user id)."""
    return _create_token(subject, "refresh", timedelta(days=settings.refresh_token_ttl_days))


def decode_token(token: str) -> dict[str, object]:
    """Decode and validate a JWT, raising jose.JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
