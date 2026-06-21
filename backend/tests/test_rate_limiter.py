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
from security.jwt import create_access_token


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


def test_different_users_get_separate_rate_limit_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that two distinct JWT subjects are rate-limited independently.

    Sets LIMIT=2 so that two requests per identity exhaust the bucket.
    Sends two requests as user-a (consuming that user's entire budget), then
    confirms that user-b's first request still succeeds — proving the per-user
    bucket isolation introduced by the ``sub``-based identity key.

    Args:
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If user-b is throttled by user-a's request history,
                        or if user-a is not throttled after exhausting its own bucket.
    """
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_redis", lambda: fake)
    monkeypatch.setattr(rl, "LIMIT", 2)
    monkeypatch.setattr(rl, "EXEMPT", set())

    tok_a = create_access_token("user-a")
    tok_b = create_access_token("user-b")
    headers_a = {"Authorization": f"Bearer {tok_a}"}
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    app = create_app()
    client = TestClient(app)

    # Exhaust user-a's bucket (2 requests at LIMIT=2 → 3rd should be 429)
    client.get("/health", headers=headers_a)
    client.get("/health", headers=headers_a)
    r3 = client.get("/health", headers=headers_a)
    assert r3.status_code == 429, (
        f"Expected user-a to be throttled on 3rd request (LIMIT=2), got {r3.status_code}"
    )

    # user-b must NOT be throttled by user-a's usage
    r_b = client.get("/health", headers=headers_b)
    assert r_b.status_code == 200, (
        f"Expected user-b first request to succeed (separate bucket), got {r_b.status_code}"
    )
