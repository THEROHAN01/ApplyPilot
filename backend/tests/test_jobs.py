"""
Module: tests/test_jobs.py
Purpose: Tests for the /jobs router — create, list with filters/pagination,
         get-by-id, and auth enforcement.
Author: ApplyPilot
"""
import uuid

from fastapi.testclient import TestClient


def _auth(client: TestClient) -> dict[str, str]:
    """Sign up and return an Authorization header dict."""
    t = client.post("/auth/signup", json={"email": "j@b.com", "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def _make_job(client: TestClient, headers: dict[str, str], company: str = "Stripe", role: str = "SWE") -> object:
    """POST a minimal job payload and return the response."""
    return client.post("/jobs", headers=headers, json={"source": "greenhouse", "company": company, "role": role})


def test_create_job_201(client: TestClient) -> None:
    """POST /jobs returns 201 and the created job."""
    h = _auth(client)
    r = _make_job(client, h)
    assert r.status_code == 201
    assert r.json()["company"] == "Stripe"


def test_list_jobs_paginated(client: TestClient) -> None:
    """GET /jobs respects page and page_size parameters."""
    h = _auth(client)
    _make_job(client, h, "Stripe", "SWE")
    _make_job(client, h, "Linear", "FE")
    r = client.get("/jobs?page=1&page_size=1", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and len(body["items"]) == 1


def test_filter_jobs_by_company(client: TestClient) -> None:
    """GET /jobs?company= returns only matching jobs."""
    h = _auth(client)
    _make_job(client, h, "Stripe", "SWE")
    _make_job(client, h, "Linear", "FE")
    r = client.get("/jobs?company=Linear", headers=h)
    assert r.json()["total"] == 1 and r.json()["items"][0]["company"] == "Linear"


def test_get_missing_job_404(client: TestClient) -> None:
    """GET /jobs/{id} returns 404 for an unknown UUID."""
    h = _auth(client)
    assert client.get(f"/jobs/{uuid.uuid4()}", headers=h).status_code == 404


def test_jobs_require_auth(client: TestClient) -> None:
    """GET /jobs without a token returns 401."""
    assert client.get("/jobs").status_code == 401
