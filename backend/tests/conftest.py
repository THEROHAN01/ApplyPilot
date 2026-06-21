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
