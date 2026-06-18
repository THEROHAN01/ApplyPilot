"""Shared pytest fixtures."""
import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient over a fresh app instance."""
    return TestClient(create_app())
