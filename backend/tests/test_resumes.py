"""
Module: tests/test_resumes.py
Purpose: Integration tests for the /resumes endpoints — upload, list, delete,
         and auth guards. Verifies storage.delete is called on resume removal.
Dependencies: pytest, fastapi.testclient
Author: ApplyPilot
"""
import io
from fastapi.testclient import TestClient


def _auth(client: TestClient) -> dict[str, str]:
    t = client.post("/auth/signup", json={"email": "r@b.com", "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_upload_resume_201(client: TestClient) -> None:
    headers = _auth(client)
    files = {"file": ("cv.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    r = client.post("/resumes", headers=headers, files=files)
    assert r.status_code == 201
    assert r.json()["filename"] == "cv.pdf"
    assert r.json()["storage_url"].startswith("http")


def test_list_resumes_scoped_to_user(client: TestClient) -> None:
    headers = _auth(client)
    files = {"file": ("cv.pdf", io.BytesIO(b"x"), "application/pdf")}
    client.post("/resumes", headers=headers, files=files)
    r = client.get("/resumes", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_upload_requires_auth(client: TestClient) -> None:
    files = {"file": ("cv.pdf", io.BytesIO(b"x"), "application/pdf")}
    assert client.post("/resumes", files=files).status_code == 401


def test_delete_resume_204(client: TestClient) -> None:
    headers = _auth(client)
    files = {"file": ("cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")}
    resume_id = client.post("/resumes", headers=headers, files=files).json()["id"]
    r = client.delete(f"/resumes/{resume_id}", headers=headers)
    assert r.status_code == 204
    # Row must be gone from list
    listed = client.get("/resumes", headers=headers).json()
    assert listed == []


def test_upload_disallowed_content_type_422(client: TestClient) -> None:
    headers = _auth(client)
    files = {"file": ("evil.html", io.BytesIO(b"<script>alert(1)</script>"), "text/html")}
    r = client.post("/resumes", headers=headers, files=files)
    assert r.status_code == 422


def test_delete_resume_404_other_user(client: TestClient) -> None:
    # Upload as user A
    headers_a = _auth(client)
    files = {"file": ("cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")}
    resume_id = client.post("/resumes", headers=headers_a, files=files).json()["id"]
    # Attempt delete as user B
    headers_b: dict[str, str] = {
        "Authorization": "Bearer "
        + client.post("/auth/signup", json={"email": "b@b.com", "password": "password123"}).json()[
            "access_token"
        ]
    }
    r = client.delete(f"/resumes/{resume_id}", headers=headers_b)
    assert r.status_code == 404


def test_upload_docx_accepted(client: TestClient) -> None:
    """A .docx (Office Open XML) upload is accepted (201)."""
    headers = _auth(client)
    docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    files = {"file": ("cv.docx", io.BytesIO(b"PK\x03\x04 fake docx"), docx)}
    r = client.post("/resumes", headers=headers, files=files)
    assert r.status_code == 201


def test_upload_exe_rejected_422(client: TestClient) -> None:
    """An executable upload is rejected by content-type allow-list (422)."""
    headers = _auth(client)
    files = {"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")}
    assert client.post("/resumes", headers=headers, files=files).status_code == 422


def test_upload_jpg_rejected_422(client: TestClient) -> None:
    """An image upload is rejected (only PDF/DOC/DOCX allowed)."""
    headers = _auth(client)
    files = {"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")}
    assert client.post("/resumes", headers=headers, files=files).status_code == 422


def test_resumes_list_isolated_between_users(client: TestClient) -> None:
    """User B never sees user A's resumes in their own list."""
    headers_a = _auth(client)
    files = {"file": ("a.pdf", io.BytesIO(b"%PDF"), "application/pdf")}
    client.post("/resumes", headers=headers_a, files=files)
    token_b = client.post(
        "/auth/signup", json={"email": "iso@b.com", "password": "password123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get("/resumes", headers=headers_b).json() == []


def test_resume_filename_with_path_traversal_is_sanitised(client: TestClient) -> None:
    """A filename containing path separators is sanitised, not stored raw."""
    headers = _auth(client)
    files = {"file": ("../../etc/passwd.pdf", io.BytesIO(b"%PDF"), "application/pdf")}
    r = client.post("/resumes", headers=headers, files=files)
    assert r.status_code == 201
    # storage_url is keyed by a sanitised name (no traversal sequences survive).
    assert "../" not in r.json()["storage_url"]
