"""Shared pytest fixtures with isolated DB schema per test."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings
from database import Base
from deps import get_db
from main import create_app
from services.storage_service import get_storage
import models  # noqa: F401


class _FakeStorage:
    """In-memory fake storage that never hits MinIO."""

    def ensure_bucket(self) -> None:
        """No-op: bucket always 'exists' in tests."""
        ...

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Return a deterministic test URL for the given key."""
        return f"http://test-storage/test-bucket/{key}"

    def delete(self, key: str) -> None:
        """No-op: nothing to delete in tests."""
        ...


from sqlalchemy.engine import make_url  # noqa: E402

_base_url = make_url(settings.database_url)
_test_url = _base_url.set(database=f"{_base_url.database}_test")

# Ensure the dedicated test database exists (connect to the maintenance db).
_admin_engine = create_engine(_base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with _admin_engine.connect() as _conn:
    _exists = _conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _test_url.database}
    ).scalar()
    if not _exists:
        _conn.execute(text(f'CREATE DATABASE "{_test_url.database}"'))
_admin_engine.dispose()

engine = create_engine(_test_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _schema() -> None:
    """Create all tables before each test and drop them after."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session():
    """Yield a transactional DB session for use in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session) -> TestClient:
    """Return a TestClient with get_db overridden to use the test session."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage] = lambda: _FakeStorage()
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Convenience fixtures and factories used across the Phase 1 test suite.
# --------------------------------------------------------------------------- #
from collections.abc import Callable  # noqa: E402

from faker import Faker  # noqa: E402

_faker = Faker()


@pytest.fixture
def faker() -> Faker:
    """Return a Faker instance for generating test data."""
    return _faker


@pytest.fixture
def make_user(client: TestClient) -> Callable[..., dict[str, str]]:
    """Return a factory that signs up a user and yields Authorization headers.

    The factory generates a unique email per call (unless one is supplied) so
    tests can create several isolated users without email collisions.

    Returns:
        A callable ``make_user(email=None, password="Password123!")`` that
        returns a dict suitable for use as request headers.
    """

    def _make(email: str | None = None, password: str = "Password123!") -> dict[str, str]:
        email = email or _faker.unique.email()
        resp = client.post(
            "/auth/signup", json={"email": email, "password": password, "name": "Test User"}
        )
        assert resp.status_code == 201, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def auth_headers(make_user: Callable[..., dict[str, str]]) -> dict[str, str]:
    """Pre-created user with valid JWT Authorization headers."""
    return make_user()


@pytest.fixture
def sample_job(client: TestClient, auth_headers: dict[str, str]) -> dict:
    """Seed and return a single Job row (as the API response dict)."""
    resp = client.post(
        "/jobs",
        headers=auth_headers,
        json={
            "source": "greenhouse",
            "company": "Stripe",
            "role": "Software Engineer",
            "jd_url": "https://stripe.com/jobs/1",
            "location": "Remote",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def sample_application(
    client: TestClient, auth_headers: dict[str, str], sample_job: dict
) -> dict:
    """Seed and return a single Application row owned by the auth_headers user."""
    resp = client.post(
        "/applications", headers=auth_headers, json={"job_id": sample_job["id"]}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def sample_resume(client: TestClient, auth_headers: dict[str, str]) -> dict:
    """Seed and return a single Resume row (storage is faked, never hits MinIO)."""
    import io

    files = {"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake resume"), "application/pdf")}
    resp = client.post("/resumes", headers=auth_headers, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()
