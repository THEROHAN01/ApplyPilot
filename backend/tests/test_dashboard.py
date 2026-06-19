"""
Module: tests/test_dashboard.py
Purpose: Tests for the GET /dashboard/stats endpoint — shape validation,
         per-status counts, reply_rate calculation, and auth enforcement.
Author: ApplyPilot
"""
from fastapi.testclient import TestClient


def _auth(client: TestClient) -> dict[str, str]:
    """Sign up a fresh user and return an Authorization header dict."""
    t = client.post("/auth/signup", json={"email": "d@b.com", "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_dashboard_stats_shape(client: TestClient) -> None:
    """Stats reflect a single replied application: total=1, reply_rate=1.0."""
    h = _auth(client)
    jid = client.post("/jobs", headers=h, json={"source": "yc", "company": "C", "role": "R"}).json()["id"]
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    client.patch(f"/applications/{aid}", headers=h, json={"status": "replied"})
    r = client.get("/dashboard/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_applications"] == 1
    assert body["by_status"]["replied"] == 1
    assert body["reply_rate"] == 1.0
    assert len(body["recent"]) == 1


def test_dashboard_requires_auth(client: TestClient) -> None:
    """Unauthenticated request must return 401."""
    assert client.get("/dashboard/stats").status_code == 401
