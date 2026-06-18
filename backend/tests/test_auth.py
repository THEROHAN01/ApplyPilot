"""
Module: tests/test_auth.py
Purpose: Tests for auth router (signup / login / refresh / me).
Author: ApplyPilot
"""
from fastapi.testclient import TestClient


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
