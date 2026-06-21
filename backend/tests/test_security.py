"""
Module: tests/test_security.py
Purpose: Security-focused tests — JWT primitives plus API-level attack surface:
         SQL injection, stored XSS, forged/alg:none tokens, IDOR, and mass
         assignment. These assert that hostile input is neutralised, not trusted.
Author: ApplyPilot
"""
import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from jose import JWTError, jwt
from sqlalchemy import text

from security.jwt import create_access_token, decode_token, hash_password, verify_password


# --------------------------------------------------------------------------- #
# JWT primitives
# --------------------------------------------------------------------------- #
def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cret!")
    assert h != "s3cret!"
    assert verify_password("s3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_encodes_subject() -> None:
    token = create_access_token("user-123")
    claims = decode_token(token)
    assert claims["sub"] == "user-123"
    assert claims["type"] == "access"


def test_decode_rejects_garbage() -> None:
    with pytest.raises(JWTError):
        decode_token("not-a-jwt")


# --------------------------------------------------------------------------- #
# Forged tokens
# --------------------------------------------------------------------------- #
def test_jwt_signed_with_wrong_key_rejected(client: TestClient) -> None:
    """A token signed with a different secret must not authenticate (401)."""
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access"},
        "a-totally-different-secret",
        algorithm="HS256",
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_jwt_alg_none_rejected(client: TestClient) -> None:
    """An unsigned ``alg: none`` token must be rejected (critical)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": str(uuid.uuid4()), "type": "access"}).encode()
    ).rstrip(b"=")
    none_token = f"{header.decode()}.{payload.decode()}."
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {none_token}"})
    assert r.status_code == 401


def test_decode_token_rejects_alg_none() -> None:
    """The decode helper itself must refuse an alg:none token."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "x", "type": "access"}).encode()).rstrip(b"=")
    with pytest.raises(JWTError):
        decode_token(f"{header.decode()}.{payload.decode()}.")


# --------------------------------------------------------------------------- #
# SQL injection / XSS are stored as inert literals
# --------------------------------------------------------------------------- #
def test_sql_injection_in_job_title_stored_literally(
    client: TestClient, auth_headers: dict[str, str], db_session
) -> None:
    """A SQL-injection payload in a field is parameterised, never executed."""
    payload = "'; DROP TABLE users; --"
    r = client.post(
        "/jobs",
        headers=auth_headers,
        json={"source": "manual", "company": payload, "role": "SWE"},
    )
    assert r.status_code == 201
    assert r.json()["company"] == payload  # stored verbatim, not interpreted
    # The users table must still exist and be queryable.
    assert db_session.execute(text("SELECT count(*) FROM users")).scalar() >= 1


def test_xss_payload_stored_and_returned_as_literal(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """A stored XSS payload round-trips as an inert string (no execution layer)."""
    payload = "<script>alert('xss')</script>"
    job_id = client.post(
        "/jobs", headers=auth_headers, json={"source": "manual", "company": payload, "role": "R"}
    ).json()["id"]
    r = client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert r.json()["company"] == payload


# --------------------------------------------------------------------------- #
# IDOR — cross-user access returns 404 (no existence disclosure)
# --------------------------------------------------------------------------- #
def test_idor_get_other_users_application_404(
    client: TestClient, make_user, sample_application: dict
) -> None:
    """User B requesting user A's application id gets 404, not 403."""
    attacker = make_user()
    r = client.get(f"/applications/{sample_application['id']}", headers=attacker)
    assert r.status_code == 404


def test_idor_patch_other_users_application_404(
    client: TestClient, make_user, sample_application: dict
) -> None:
    attacker = make_user()
    r = client.patch(
        f"/applications/{sample_application['id']}", headers=attacker, json={"status": "sent"}
    )
    assert r.status_code == 404


def test_idor_delete_other_users_application_404(
    client: TestClient, make_user, sample_application: dict
) -> None:
    attacker = make_user()
    r = client.delete(f"/applications/{sample_application['id']}", headers=attacker)
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Mass assignment — unexpected fields are ignored, not persisted
# --------------------------------------------------------------------------- #
def test_mass_assignment_on_application_create_ignored(
    client: TestClient, auth_headers: dict[str, str], sample_job: dict
) -> None:
    """Extra fields (id, user_id, status) in the body must not be honoured."""
    forged_id = str(uuid.uuid4())
    r = client.post(
        "/applications",
        headers=auth_headers,
        json={
            "job_id": sample_job["id"],
            "id": forged_id,
            "user_id": str(uuid.uuid4()),
            "status": "offer",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] != forged_id  # server-generated, not client-supplied
    assert body["status"] == "pending"  # forced default, not the injected "offer"


def test_mass_assignment_on_signup_ignored(client: TestClient) -> None:
    """A signup that tries to set plan='unlimited' must be ignored."""
    r = client.post(
        "/auth/signup",
        json={"email": "ma@b.com", "password": "password123", "plan": "unlimited"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["plan"] == "free"  # not the injected "unlimited"
