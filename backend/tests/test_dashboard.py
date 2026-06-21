"""
Module: tests/test_dashboard.py
Purpose: Tests for the GET /dashboard/stats endpoint — shape validation,
         per-status counts, reply_rate calculation, and auth enforcement.
Author: ApplyPilot
"""
from fastapi.testclient import TestClient


def _auth(client: TestClient, email: str = "d@b.com") -> dict[str, str]:
    """Sign up a fresh user and return an Authorization header dict."""
    t = client.post("/auth/signup", json={"email": email, "password": "password123"}).json()
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


def test_dashboard_empty_state_returns_zeroes(client: TestClient) -> None:
    """A brand-new user with no applications gets zeroes, not an error."""
    h = _auth(client)
    r = client.get("/dashboard/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_applications"] == 0
    assert body["by_status"] == {}
    assert body["reply_rate"] == 0.0
    assert body["recent"] == []


def test_dashboard_isolated_between_users(client: TestClient) -> None:
    """User B's stats never count user A's applications."""
    h_a = _auth(client, "stats_a@b.com")
    jid = client.post("/jobs", headers=h_a, json={"source": "x", "company": "C", "role": "R"}).json()["id"]
    client.post("/applications", headers=h_a, json={"job_id": jid})
    h_b = _auth(client, "stats_b@b.com")
    r = client.get("/dashboard/stats", headers=h_b)
    assert r.json()["total_applications"] == 0


def test_dashboard_reply_rate_partial(client: TestClient) -> None:
    """reply_rate = (replied + offer) / total, rounded to 4 dp."""
    h = _auth(client, "rate@b.com")
    jid = client.post("/jobs", headers=h, json={"source": "x", "company": "C", "role": "R"}).json()["id"]
    a1 = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    client.post("/applications", headers=h, json={"job_id": jid})  # stays pending
    client.patch(f"/applications/{a1}", headers=h, json={"status": "replied"})
    body = client.get("/dashboard/stats", headers=h).json()
    assert body["total_applications"] == 2
    assert body["reply_rate"] == 0.5
