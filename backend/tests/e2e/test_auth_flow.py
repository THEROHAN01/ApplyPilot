"""
Module: tests/e2e/test_auth_flow.py
Purpose: API-level end-to-end flows driven over real HTTP against a live
         uvicorn server. Exercises the full token lifecycle and a complete
         job → application → dashboard journey the way a client would.
Author: ApplyPilot
"""
import httpx


def test_full_auth_lifecycle(http: httpx.Client, seeded_user) -> None:
    """signup → login → /me → refresh → /me-with-new-token, over the wire."""
    user = seeded_user()

    # The signup-issued access token authenticates /auth/me.
    me = http.get("/auth/me", headers=user["headers"])
    assert me.status_code == 200
    assert me.json()["email"] == user["email"]

    # Logging in returns a fresh, working token pair.
    login = http.post("/auth/login", json={"email": user["email"], "password": user["password"]})
    assert login.status_code == 200
    login_access = login.json()["access_token"]
    login_refresh = login.json()["refresh_token"]
    assert login_access and login_refresh

    # Exchanging the refresh token yields a new usable access token.
    refreshed = http.post("/auth/refresh", json={"refresh_token": login_refresh})
    assert refreshed.status_code == 200
    new_access = refreshed.json()["access_token"]
    assert new_access

    me2 = http.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me2.status_code == 200
    assert me2.json()["email"] == user["email"]


def test_protected_route_rejected_without_token(http: httpx.Client) -> None:
    """A protected route returns 401 when called over HTTP with no token."""
    assert http.get("/applications").status_code == 401


def test_job_application_dashboard_journey(http: httpx.Client, seeded_user) -> None:
    """End-to-end: create job → create application → read dashboard stats."""
    user = seeded_user()
    headers = user["headers"]

    job = http.post(
        "/jobs",
        headers=headers,
        json={"source": "manual", "company": "Stripe", "role": "SWE Intern",
              "jd_url": "https://stripe.com/jobs/1"},
    )
    assert job.status_code == 201
    job_id = job.json()["id"]

    app_resp = http.post("/applications", headers=headers, json={"job_id": job_id})
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]
    assert app_resp.json()["status"] == "pending"

    # Advance the application and confirm it surfaces in dashboard stats.
    patch = http.patch(f"/applications/{app_id}", headers=headers, json={"status": "replied"})
    assert patch.status_code == 200

    stats = http.get("/dashboard/stats", headers=headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_applications"] == 1
    assert body["by_status"]["replied"] == 1
    assert body["reply_rate"] == 1.0


def test_user_isolation_over_http(http: httpx.Client, seeded_user) -> None:
    """User B cannot read user A's application (404, not 403) over real HTTP."""
    user_a = seeded_user()
    user_b = seeded_user()
    job_id = http.post(
        "/jobs", headers=user_a["headers"],
        json={"source": "manual", "company": "Acme", "role": "Eng"},
    ).json()["id"]
    app_id = http.post(
        "/applications", headers=user_a["headers"], json={"job_id": job_id}
    ).json()["id"]

    leaked = http.get(f"/applications/{app_id}", headers=user_b["headers"])
    assert leaked.status_code == 404
