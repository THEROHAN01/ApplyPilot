"""Shared pytest fixtures with isolated DB schema per test."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings
from database import Base
from deps import get_db
from main import create_app
import models  # noqa: F401

engine = create_engine(settings.database_url, pool_pre_ping=True)
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
    return TestClient(app)
