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
