"""
Module: tests/test_middleware.py
Purpose: Tests for the request middleware stack present in Phase 1.

         Phase 1 ships exactly one custom middleware: the Redis sliding-window
         rate limiter (middleware/rate_limiter.py). There is NO plan-guard
         middleware in Phase 1 — billing/plan enforcement is a later phase — so
         the spec's "plan guard" cases are intentionally not implemented here.
         test_plan_guard_not_present_in_phase1 documents that absence so the
         gap is explicit rather than silently missing.

         Auth enforcement in Phase 1 is performed per-route via the
         get_current_user dependency (not a global middleware); the
         "/health is always open, protected routes need a token" behaviour is
         asserted below against that design.
Dependencies: fakeredis, fastapi, pytest
Author: ApplyPilot
"""
import fakeredis
import pytest
from fastapi.testclient import TestClient

import middleware.rate_limiter as rl
from main import create_app


def _client_with_fake_redis(monkeypatch: pytest.MonkeyPatch, limit: int) -> TestClient:
    """Build a TestClient whose rate limiter is backed by FakeRedis at LIMIT=limit."""
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_redis", lambda: fake)
    monkeypatch.setattr(rl, "LIMIT", limit)
    monkeypatch.setattr(rl, "EXEMPT", set())
    return TestClient(create_app())


# --------------------------------------------------------------------------- #
# Rate limiter
# --------------------------------------------------------------------------- #
def test_rate_limit_429_includes_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    """The 429 response carries a Retry-After header equal to the window."""
    client = _client_with_fake_redis(monkeypatch, limit=2)
    last = None
    for _ in range(4):
        last = client.get("/health")
    assert last is not None and last.status_code == 429
    assert last.headers.get("Retry-After") == str(rl.WINDOW_SEC)
    assert last.json()["detail"] == "Rate limit exceeded"


def test_rate_limiter_fails_open_on_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Redis raises, the limiter must allow the request through (fail open)."""
    import redis as _redis_mod

    class _BrokenRedis:
        def pipeline(self):  # noqa: ANN201
            raise _redis_mod.ConnectionError("redis down")

    monkeypatch.setattr(rl, "_redis", lambda: _BrokenRedis())
    monkeypatch.setattr(rl, "EXEMPT", set())
    client = TestClient(create_app())
    # Despite Redis being down, the request still succeeds.
    assert client.get("/health").status_code == 200


def test_options_requests_bypass_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS preflight (OPTIONS) requests are never rate limited."""
    client = _client_with_fake_redis(monkeypatch, limit=1)
    codes = [client.options("/health").status_code for _ in range(5)]
    assert 429 not in codes


# --------------------------------------------------------------------------- #
# Health endpoint exemption (against the real Redis used by the suite)
# --------------------------------------------------------------------------- #
def test_health_is_exempt_from_rate_limiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """/health is in the EXEMPT set and is never throttled, even past LIMIT."""
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_redis", lambda: fake)
    monkeypatch.setattr(rl, "LIMIT", 1)
    # Keep the default EXEMPT (which includes /health).
    client = TestClient(create_app())
    codes = [client.get("/health").status_code for _ in range(5)]
    assert codes == [200] * 5


def test_health_open_without_token(client: TestClient) -> None:
    """/health requires no Authorization and always returns 200."""
    assert client.get("/health").status_code == 200


def test_protected_route_requires_token(client: TestClient) -> None:
    """A protected route returns 401 without a token (per-route dependency)."""
    assert client.get("/applications").status_code == 401
    assert client.get("/dashboard/stats").status_code == 401
    assert client.get("/jobs").status_code == 401


# --------------------------------------------------------------------------- #
# Plan-guard middleware: not a Phase 1 feature (documented absence)
# --------------------------------------------------------------------------- #
def test_plan_guard_not_present_in_phase1() -> None:
    """There is intentionally no plan-guard middleware in Phase 1.

    Billing and plan enforcement arrive in a later phase. This test asserts
    the current app has only the rate limiter as a custom middleware so the
    absence is explicit and a future addition is a deliberate, tested change.
    """
    app = create_app()
    middleware_classes = {m.cls.__name__ for m in app.user_middleware}
    assert "RateLimitMiddleware" in middleware_classes
    assert not any("Plan" in name for name in middleware_classes)
