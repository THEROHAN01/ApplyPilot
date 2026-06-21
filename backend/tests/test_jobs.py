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


def test_get_job_by_id_200(client: TestClient) -> None:
    """GET /jobs/{id} returns the job for a valid id."""
    h = _auth(client)
    jid = _make_job(client, h).json()["id"]
    r = client.get(f"/jobs/{jid}", headers=h)
    assert r.status_code == 200 and r.json()["id"] == jid


def test_filter_jobs_by_source(client: TestClient) -> None:
    """GET /jobs?source= returns only jobs from that exact source."""
    h = _auth(client)
    client.post("/jobs", headers=h, json={"source": "greenhouse", "company": "A", "role": "X"})
    client.post("/jobs", headers=h, json={"source": "lever", "company": "B", "role": "Y"})
    r = client.get("/jobs?source=lever", headers=h)
    assert r.json()["total"] == 1 and r.json()["items"][0]["company"] == "B"


def test_search_jobs_by_q(client: TestClient) -> None:
    """GET /jobs?q= matches against role and company (case-insensitive)."""
    h = _auth(client)
    _make_job(client, h, "Stripe", "Backend Engineer")
    _make_job(client, h, "Linear", "Frontend Engineer")
    r = client.get("/jobs?q=backend", headers=h)
    assert r.json()["total"] == 1 and r.json()["items"][0]["role"] == "Backend Engineer"


def test_create_job_missing_required_fields_422(client: TestClient) -> None:
    """POST /jobs without the required 'role' field returns 422."""
    h = _auth(client)
    r = client.post("/jobs", headers=h, json={"source": "manual", "company": "Acme"})
    assert r.status_code == 422


def test_list_jobs_invalid_page_422(client: TestClient) -> None:
    """page must be >= 1; page=0 is rejected by Query validation."""
    h = _auth(client)
    assert client.get("/jobs?page=0", headers=h).status_code == 422


def test_list_jobs_page_size_upper_bound_422(client: TestClient) -> None:
    """page_size is capped at 100; 101 is rejected."""
    h = _auth(client)
    assert client.get("/jobs?page_size=101", headers=h).status_code == 422


def test_jobs_are_immutable_no_patch_or_delete(client: TestClient) -> None:
    """Phase 1 jobs are read/create-only: PATCH and DELETE are not routed (405).

    Documents that job mutation/removal endpoints do not exist yet — they are
    not a Phase 1 feature. This guards against silent regressions if a route
    is added without a corresponding test.
    """
    h = _auth(client)
    jid = _make_job(client, h).json()["id"]
    assert client.patch(f"/jobs/{jid}", headers=h, json={"company": "X"}).status_code == 405
    assert client.delete(f"/jobs/{jid}", headers=h).status_code == 405
