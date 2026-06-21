"""
Module: tests/e2e/conftest.py
Purpose: Fixtures for API-level end-to-end tests that drive the real FastAPI
         app over HTTP via a live uvicorn server (no TestClient shortcut).

         The server runs in a daemon thread bound to a random free port and
         talks to the database configured by DATABASE_URL. Tables are created
         once for the session; any users created by E2E tests use the reserved
         ``@e2e.test`` email domain and are deleted on teardown so the suite is
         self-cleaning and never leaves residue in the database.
Dependencies: uvicorn, httpx, sqlalchemy
Author: ApplyPilot
"""
import socket
import threading
import time
from collections.abc import Callable, Iterator

import httpx
import pytest
import uvicorn
from sqlalchemy import create_engine, text

import models  # noqa: F401  (ensure all tables are registered on Base.metadata)
from config import settings
from database import Base

E2E_EMAIL_DOMAIN = "e2e.applypilot.dev"


def _free_port() -> int:
    """Return an available TCP port on the loopback interface."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port: int = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Start the real app under uvicorn and yield its base URL.

    Creates the schema (and the pgvector extension) on the configured database,
    boots uvicorn in a daemon thread, waits for /health to report ready, yields
    the base URL, then shuts the server down and purges E2E users.
    """
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)

    port = _free_port()
    config = uvicorn.Config("main:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=10)
        raise RuntimeError("Live E2E server failed to start within 20s")

    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM users WHERE email LIKE :pat"), {"pat": f"%@{E2E_EMAIL_DOMAIN}"})
            conn.commit()
        engine.dispose()


@pytest.fixture
def http(live_server: str) -> Iterator[httpx.Client]:
    """Yield an httpx client bound to the live server base URL."""
    with httpx.Client(base_url=live_server, timeout=10) as client:
        yield client


@pytest.fixture
def seeded_user(http: httpx.Client) -> Callable[..., dict]:
    """Return a factory that creates a real user via the API.

    Returns:
        A callable that signs up a user (unique ``@e2e.test`` email) and returns
        a dict with ``email``, ``password``, ``access_token``, ``refresh_token``,
        and ready-to-use ``headers``.
    """
    counter = {"n": 0}

    def _make(password: str = "Password123!") -> dict:
        counter["n"] += 1
        email = f"user{counter['n']}-{int(time.monotonic() * 1000)}@{E2E_EMAIL_DOMAIN}"
        resp = http.post("/auth/signup", json={"email": email, "password": password, "name": "E2E"})
        assert resp.status_code == 201, resp.text
        body = resp.json()
        return {
            "email": email,
            "password": password,
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
        }

    return _make
