"""
Module: tests/test_auth.py
Purpose: Tests for auth router (signup / login / refresh / me) covering the
         full happy/unhappy matrix: validation errors, wrong credentials,
         token type confusion, expiry, tampering, and malformed headers.
Author: ApplyPilot
"""
from datetime import timedelta

from fastapi.testclient import TestClient

from security.jwt import _create_token, create_access_token


def _signup(client: TestClient, email: str = "a@b.com", pw: str = "password123") -> object:
    """Helper to POST /auth/signup."""
    return client.post("/auth/signup", json={"email": email, "password": pw, "name": "A"})


def test_signup_returns_201_and_tokens(client: TestClient) -> None:
    r = _signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_signup_duplicate_email_409(client: TestClient) -> None:
    _signup(client)
    r = _signup(client)
    assert r.status_code == 409


def test_login_wrong_password_401(client: TestClient) -> None:
    _signup(client)
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_returns_user(client: TestClient) -> None:
    token = _signup(client).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"
    assert r.json()["plan"] == "free"


def test_refresh_returns_new_token_pair(client: TestClient) -> None:
    refresh_token = _signup(client).json()["refresh_token"]
    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]


def test_refresh_rejects_access_token_as_refresh(client: TestClient) -> None:
    access_token = _signup(client).json()["access_token"]
    r = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# Signup validation
# --------------------------------------------------------------------------- #
def test_signup_weak_password_422(client: TestClient) -> None:
    """Password shorter than 8 chars is rejected by the schema (422)."""
    r = client.post("/auth/signup", json={"email": "weak@b.com", "password": "short"})
    assert r.status_code == 422


def test_signup_missing_email_422(client: TestClient) -> None:
    """Missing the required email field returns 422."""
    r = client.post("/auth/signup", json={"password": "password123"})
    assert r.status_code == 422


def test_signup_invalid_email_422(client: TestClient) -> None:
    """A malformed email is rejected by EmailStr validation (422)."""
    r = client.post("/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Login validation / unhappy paths
# --------------------------------------------------------------------------- #
def test_login_success_200(client: TestClient) -> None:
    """Valid credentials return a fresh token pair."""
    _signup(client)
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["access_token"] and r.json()["refresh_token"]


def test_login_unknown_email_401(client: TestClient) -> None:
    """Logging in with an email that was never registered returns 401."""
    r = client.post("/auth/login", json={"email": "ghost@b.com", "password": "password123"})
    assert r.status_code == 401


def test_login_missing_fields_422(client: TestClient) -> None:
    """A login request missing the password field returns 422."""
    r = client.post("/auth/login", json={"email": "a@b.com"})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Refresh token edge cases
# --------------------------------------------------------------------------- #
def test_refresh_tampered_token_401(client: TestClient) -> None:
    """A refresh token whose payload has been altered fails signature check."""
    refresh_token = _signup(client).json()["refresh_token"]
    tampered = refresh_token[:-3] + ("aaa" if not refresh_token.endswith("aaa") else "bbb")
    r = client.post("/auth/refresh", json={"refresh_token": tampered})
    assert r.status_code == 401


def test_refresh_expired_token_401(client: TestClient) -> None:
    """An expired refresh token is rejected with 401."""
    expired = _create_token("00000000-0000-0000-0000-000000000000", "refresh", timedelta(days=-1))
    r = client.post("/auth/refresh", json={"refresh_token": expired})
    assert r.status_code == 401


def test_refresh_garbage_token_401(client: TestClient) -> None:
    """A non-JWT string in the refresh field returns 401, not 500."""
    r = client.post("/auth/refresh", json={"refresh_token": "not.a.jwt"})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# /auth/me header / token edge cases
# --------------------------------------------------------------------------- #
def test_me_malformed_bearer_401(client: TestClient) -> None:
    """An Authorization header that is not a well-formed Bearer token → 401."""
    r = client.get("/auth/me", headers={"Authorization": "Basic abc123"})
    assert r.status_code == 401


def test_me_expired_access_token_401(client: TestClient) -> None:
    """An expired access token is rejected by the dependency with 401."""
    expired = _create_token("00000000-0000-0000-0000-000000000000", "access", timedelta(minutes=-5))
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_me_refresh_token_used_as_access_401(client: TestClient) -> None:
    """A refresh token presented as an access token is rejected (type guard)."""
    refresh_token = _signup(client).json()["refresh_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert r.status_code == 401


def test_me_access_token_for_deleted_user_401(client: TestClient) -> None:
    """A validly signed token for a non-existent user id returns 401."""
    token = create_access_token("00000000-0000-0000-0000-000000000000")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_token_with_non_uuid_subject_401(client: TestClient) -> None:
    """A token whose ``sub`` is not a UUID is rejected (ValueError → 401)."""
    token = create_access_token("not-a-uuid")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
