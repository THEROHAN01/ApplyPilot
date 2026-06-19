"""
Module: tests/test_rate_limiter.py
Purpose: Tests for Redis sliding-window rate limiter middleware.
         Uses fakeredis to exercise the limiter without a live Redis server.
Dependencies: fakeredis, fastapi, pytest
Author: ApplyPilot
"""
import fakeredis
import pytest
from fastapi.testclient import TestClient

import middleware.rate_limiter as rl
from main import create_app


def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that requests exceeding LIMIT within the window receive 429.

    Monkeypatches the module-level _redis indirection to use a FakeRedis
    instance so no real Redis server is required. Sets LIMIT=3 and removes
    /health from EXEMPT so the limiter is exercised on that endpoint.

    Args:
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If 429 is not returned after the limit is exceeded,
                        or if fewer than LIMIT requests succeed.
    """
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_redis", lambda: fake)
    monkeypatch.setattr(rl, "LIMIT", 3)
    monkeypatch.setattr(rl, "EXEMPT", set())
    app = create_app()
    client = TestClient(app)
    codes = [client.get("/health").status_code for _ in range(5)]
    assert 429 in codes, f"Expected a 429 but got: {codes}"
    assert codes.count(200) == 3, f"Expected exactly 3 x 200 but got: {codes}"
