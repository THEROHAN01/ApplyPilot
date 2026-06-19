"""
Module: tests/test_applications.py
Purpose: Tests for the /applications CRUD router including status transitions,
         ownership enforcement, and status filtering.
Author: ApplyPilot
"""
from fastapi.testclient import TestClient


def _auth(client, email="ap@b.com"):
    t = client.post("/auth/signup", json={"email": email, "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def _job(client, h):
    return client.post("/jobs", headers=h, json={"source": "lever", "company": "Vercel", "role": "SWE"}).json()["id"]


def test_create_application_201(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    r = client.post("/applications", headers=h, json={"job_id": jid})
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert r.json()["job"]["company"] == "Vercel"


def test_patch_status_transition(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    r = client.patch(f"/applications/{aid}", headers=h, json={"status": "sent"})
    assert r.status_code == 200 and r.json()["status"] == "sent"


def test_patch_invalid_status_422(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    assert client.patch(f"/applications/{aid}", headers=h, json={"status": "bogus"}).status_code == 422


def test_other_users_application_404(client: TestClient) -> None:
    h1 = _auth(client, "u1@b.com")
    jid = _job(client, h1)
    aid = client.post("/applications", headers=h1, json={"job_id": jid}).json()["id"]
    h2 = _auth(client, "u2@b.com")
    assert client.get(f"/applications/{aid}", headers=h2).status_code == 404


def test_list_filter_by_status(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    client.patch(f"/applications/{aid}", headers=h, json={"status": "sent"})
    r = client.get("/applications?status=sent", headers=h)
    assert r.status_code == 200 and len(r.json()) == 1
