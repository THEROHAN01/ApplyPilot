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


def test_patch_other_users_application_404(client: TestClient) -> None:
    h1 = _auth(client, "owner1@b.com")
    jid = _job(client, h1)
    aid = client.post("/applications", headers=h1, json={"job_id": jid}).json()["id"]
    h2 = _auth(client, "intruder1@b.com")
    assert client.patch(f"/applications/{aid}", headers=h2, json={"status": "sent"}).status_code == 404


def test_delete_other_users_application_404(client: TestClient) -> None:
    h1 = _auth(client, "owner2@b.com")
    jid = _job(client, h1)
    aid = client.post("/applications", headers=h1, json={"job_id": jid}).json()["id"]
    h2 = _auth(client, "intruder2@b.com")
    assert client.delete(f"/applications/{aid}", headers=h2).status_code == 404


def test_list_filter_by_status(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    client.patch(f"/applications/{aid}", headers=h, json={"status": "sent"})
    r = client.get("/applications?status=sent", headers=h)
    assert r.status_code == 200 and len(r.json()) == 1


# --------------------------------------------------------------------------- #
# CRUD happy paths and lifecycle
# --------------------------------------------------------------------------- #
def test_get_application_200(client: TestClient) -> None:
    h = _auth(client, "get@b.com")
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    r = client.get(f"/applications/{aid}", headers=h)
    assert r.status_code == 200 and r.json()["id"] == aid


def test_get_missing_application_404(client: TestClient) -> None:
    import uuid

    h = _auth(client, "miss@b.com")
    assert client.get(f"/applications/{uuid.uuid4()}", headers=h).status_code == 404


def test_delete_application_204_then_404(client: TestClient) -> None:
    """Deleting an application returns 204; a second delete returns 404."""
    h = _auth(client, "del@b.com")
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    assert client.delete(f"/applications/{aid}", headers=h).status_code == 204
    assert client.get(f"/applications/{aid}", headers=h).status_code == 404
    assert client.delete(f"/applications/{aid}", headers=h).status_code == 404


def test_create_application_for_nonexistent_job_404(client: TestClient) -> None:
    import uuid

    h = _auth(client, "nojob@b.com")
    r = client.post("/applications", headers=h, json={"job_id": str(uuid.uuid4())})
    assert r.status_code == 404


def test_update_application_content_fields(client: TestClient) -> None:
    """PATCH updates non-status content fields and persists them."""
    h = _auth(client, "content@b.com")
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    r = client.patch(
        f"/applications/{aid}",
        headers=h,
        json={"email_subject": "Hello", "recruiter_email": "rec@corp.com"},
    )
    assert r.status_code == 200
    assert r.json()["email_subject"] == "Hello"
    assert r.json()["recruiter_email"] == "rec@corp.com"
    assert r.json()["status"] == "pending"  # unchanged


def test_list_applications_scoped_and_ordered(client: TestClient) -> None:
    """List returns only the caller's apps, newest first."""
    h = _auth(client, "scope@b.com")
    jid = _job(client, h)
    a1 = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    a2 = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    ids = [a["id"] for a in client.get("/applications", headers=h).json()]
    assert set(ids) == {a1, a2}
    assert ids[0] == a2  # most recent first


def test_applications_require_auth(client: TestClient) -> None:
    assert client.get("/applications").status_code == 401


def test_all_status_values_accepted(client: TestClient) -> None:
    """Every ApplicationStatus enum value is a valid PATCH target (no transition rules)."""
    from models.application import ApplicationStatus

    h = _auth(client, "states@b.com")
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    for st in ApplicationStatus:
        r = client.patch(f"/applications/{aid}", headers=h, json={"status": st.value})
        assert r.status_code == 200 and r.json()["status"] == st.value
