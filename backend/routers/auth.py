"""
Module: routers/auth.py
Purpose: Self-contained signup/login/refresh/me endpoints (JWT).
Author: ApplyPilot
"""
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.user import User
from schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenPair
from schemas.user import UserOut
from security.jwt import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user_id: str) -> TokenPair:
    """Issue an access+refresh token pair for a user id."""
    return TokenPair(access_token=create_access_token(user_id),
                     refresh_token=create_refresh_token(user_id))


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED,
             summary="Register a new user")
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Create a user and return a token pair. 409 if email exists."""
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=payload.email, name=payload.name,
                password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _tokens(str(user.id))


@router.post("/login", response_model=TokenPair, summary="Authenticate and get tokens")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Validate credentials and return a token pair. 401 on failure."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return _tokens(str(user.id))


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token")
def refresh(payload: RefreshRequest) -> TokenPair:
    """Issue a new token pair from a valid refresh token. 401 otherwise."""
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise JWTError("not a refresh token")
        return _tokens(str(claims["sub"]))
    except (JWTError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc


@router.get("/me", response_model=UserOut, summary="Get the current user")
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
