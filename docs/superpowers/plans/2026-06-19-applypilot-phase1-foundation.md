# ApplyPilot Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the ApplyPilot foundation — a Dockerized FastAPI + Postgres/pgvector + Redis + MinIO backend with JWT auth and core CRUD (users, resumes, jobs, applications, dashboard stats), plus a Next.js 14 frontend shell in the Blueprint design system (auth, jobs, applications, dashboard) — all runnable with `docker-compose up` and covered by passing tests.

**Architecture:** Frontend (Next.js) talks only to FastAPI over HTTPS with a JWT bearer (no direct DB access). FastAPI uses SQLAlchemy 2.0 + Alembic as the single schema source over Postgres 16 + pgvector. Redis backs rate limiting (and later Celery). MinIO provides S3-compatible storage for resumes. Auth is self-contained (HS256 JWT issuer/verifier, bcrypt password hashing) with a Supabase-compatible shape. No AI in Phase 1.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 / Alembic / pydantic v2 / Postgres 16 + pgvector / Redis 7 / MinIO / pytest. Next.js 14 (App Router, TS) / Tailwind / shadcn-style primitives re-themed to Blueprint / TanStack Query / Zustand / axios / Recharts / Framer Motion.

## Global Constraints

- **Python ≥ 3.11**; all functions fully type-hinted; Google-style docstrings; no bare `except:`; no `print()` (use `logger`); DB sessions via context-managed dependency; no secrets in code (only `settings.X`).
- **TypeScript only, no `any`**; all data views handle loading/error/empty/success; all forms have loading+disabled states; API base from `NEXT_PUBLIC_API_URL`; all server calls via `lib/api.ts` (never raw `fetch`).
- **Pinned versions only** in `requirements.txt` (`==`) and `package.json` (no `^`/`~`).
- **Embeddings dimension:** `vector(1024)` everywhere (bge-large-en-v1.5). Columns exist in Phase 1 schema but stay NULL (populated in Phase 2).
- **HTTP semantics:** 201 create, 200 read/update, 204 delete, 401 unauth, 403 plan/owner, 404 not found, 422 validation. Every endpoint has an OpenAPI `summary`/docstring.
- **Multi-tenancy:** every data query filtered by `current_user.id`; ownership mismatch → 404 (not 403, to avoid leaking existence). SQL RLS policies written into the migration as the documented Supabase-swap path.
- **Blueprint design system (non-negotiable):** border-radius `0`; shadows are hard offset `3px 3px 0 var(--ink)` (never blurred); headings/labels/buttons use `VT323`; body uses `Source Serif 4`; code/metadata uses `JetBrains Mono`; accent blueprint-blue `#3553ff` (`#6b8eff` dark); light bg `#fafaf5`; dark bg `#0a0d1a`.
- **No hardcoded colors anywhere except token definitions.** Every component/style references a CSS custom property (via a Tailwind token like `bg-blueprint`, `text-ink`, `text-on-accent`, or `var(--warn)`). Literal color values (hex/`white`/`black`/`rgb()`) appear in exactly ONE place: the `:root` / `[data-theme="dark"]` token blocks in `app/globals.css`. This lets the user re-theme the entire app by editing only those blocks. Tailwind utilities that bake in a color (`text-white`, `bg-black`, `text-red-500`, etc.) are forbidden in components.
- **Repo layout:** backend under `backend/`, frontend under `frontend/`, infra files at repo root. Conventional-commit messages; commit at the end of every task.

---

## File Structure (Phase 1)

```
backend/
  main.py                       # FastAPI app factory, router mounting, /health
  config.py                     # pydantic-settings Settings
  database.py                   # engine, SessionLocal, get_db dependency, Base
  models/__init__.py            # imports all models so Alembic sees them
  models/user.py resume.py job.py application.py contact.py
  models/email_account.py follow_up.py agent_run.py feedback.py usage_log.py
  schemas/__init__.py
  schemas/auth.py user.py resume.py job.py application.py dashboard.py common.py
  security/jwt.py               # hashing + token issue/verify
  deps.py                       # get_db, get_current_user, get_redis
  routers/auth.py jobs.py applications.py resumes.py dashboard.py health.py
  services/storage_service.py   # MinIO/S3 wrapper
  middleware/rate_limiter.py    # Redis sliding-window
  utils/logger.py               # structured JSON logging, PII scrub
  alembic.ini  alembic/env.py  alembic/versions/001_initial.py
  tests/conftest.py
  tests/test_auth.py test_jobs.py test_applications.py test_resumes.py
  tests/test_dashboard.py test_health.py
  Dockerfile  .env.example  requirements.txt  pytest.ini

frontend/
  app/layout.tsx globals.css providers.tsx
  app/(auth)/login/page.tsx  (auth)/signup/page.tsx
  app/(dashboard)/layout.tsx
  app/(dashboard)/dashboard/page.tsx
  app/(dashboard)/jobs/page.tsx  jobs/[id]/page.tsx
  app/(dashboard)/applications/page.tsx  applications/[id]/page.tsx
  app/(dashboard)/settings/page.tsx          # resume upload only in P1
  components/shared/Sidebar.tsx TopNav.tsx ThemeToggle.tsx PlanBadge.tsx
  components/ui/{button,card,input,dialog,badge,table,tabs}.tsx
  components/jobs/{JobCard,JobFeed,JobFilters}.tsx
  components/applications/{ApplicationKanban,ApplicationTable,TimelineView}.tsx
  components/dashboard/{StatsGrid,ReplyRateChart,ActivityFeed}.tsx
  lib/api.ts auth.ts utils.ts
  hooks/useJobs.ts useApplications.ts useDashboard.ts
  store/uiStore.ts authStore.ts
  types/index.ts
  Dockerfile  .env.local.example  tailwind.config.ts  next.config.ts
  package.json  tsconfig.json  postcss.config.js

# repo root
docker-compose.yml  .env.example  README.md
```

---

# PART A — BACKEND

### Task A1: Infra scaffold, config, logger, health endpoint, infra compose

**Files:**
- Create: `backend/config.py`, `backend/utils/logger.py`, `backend/main.py`, `backend/routers/health.py`, `backend/requirements.txt`, `backend/pytest.ini`, `backend/.env.example`, `docker-compose.yml`, `.env.example`
- Test: `backend/tests/test_health.py`, `backend/tests/conftest.py`

**Interfaces:**
- Produces: `settings: Settings` (singleton in `config.py`); `get_logger(name) -> logging.Logger`; `create_app() -> FastAPI` in `main.py`; `GET /health -> {"status":"ok"}`.

- [ ] **Step 1: Write `backend/requirements.txt`** (pinned)

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
alembic==1.14.0
psycopg2-binary==2.9.10
pgvector==0.3.6
pydantic==2.10.3
pydantic-settings==2.6.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.2.1
python-multipart==0.0.19
redis==5.2.1
minio==7.2.12
httpx==0.28.1
email-validator==2.2.0
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Write `backend/config.py`**

```python
"""
Module: config.py
Purpose: Typed application settings loaded from environment variables.
Dependencies: pydantic-settings
Author: ApplyPilot
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = Field(default="development")
    database_url: str = Field(default="postgresql+psycopg2://applypilot:applypilot@db:5432/applypilot")
    redis_url: str = Field(default="redis://redis:6379/0")

    # Auth
    jwt_secret: str = Field(default="dev-only-insecure-change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_min: int = Field(default=30)
    refresh_token_ttl_days: int = Field(default=14)

    # Storage (MinIO / S3-compatible)
    s3_endpoint: str = Field(default="minio:9000")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="applypilot")
    s3_secure: bool = Field(default=False)

    # Encryption for OAuth tokens (Fernet key, used Phase 4)
    fernet_key: str = Field(default="")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000")

    # Rate limiting
    rate_limit_per_min: int = Field(default=120)

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
```

- [ ] **Step 3: Write `backend/utils/logger.py`**

```python
"""
Module: utils/logger.py
Purpose: Structured JSON logging with PII scrubbing. Never logs tokens/PII.
Dependencies: stdlib logging, json
Author: ApplyPilot
"""
import json
import logging
import sys

_SENSITIVE = ("password", "token", "access_token", "refresh_token", "authorization", "secret")


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON with sensitive keys redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = "***" if key.lower() in _SENSITIVE else value
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """Return a configured JSON logger for the given name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
```

- [ ] **Step 4: Write `backend/routers/health.py`**

```python
"""
Module: routers/health.py
Purpose: Unauthenticated liveness endpoint.
Author: ApplyPilot
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}
```

- [ ] **Step 5: Write `backend/main.py`**

```python
"""
Module: main.py
Purpose: FastAPI application factory; mounts routers and CORS.
Author: ApplyPilot
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import health


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(title="ApplyPilot API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 6: Write `backend/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
asyncio_mode = auto
```

- [ ] **Step 7: Write `backend/tests/conftest.py`** (TestClient fixture; DB fixture added in A3)

```python
"""Shared pytest fixtures."""
import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient over a fresh app instance."""
    return TestClient(create_app())
```

- [ ] **Step 8: Write `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 9: Run test (expect FAIL first if imports broken, then PASS)**

Run: `cd backend && pip install -r requirements.txt -q && python -m pytest tests/test_health.py -v`
Expected: `test_health_returns_ok PASSED`. Also `python -m py_compile config.py main.py utils/logger.py routers/health.py` prints nothing.

- [ ] **Step 10: Write `docker-compose.yml`** (infra + backend placeholder; frontend added in B7)

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: applypilot
      POSTGRES_PASSWORD: applypilot
      POSTGRES_DB: applypilot
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U applypilot"]
      interval: 5s
      timeout: 3s
      retries: 10
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]
  backend:
    build: ./backend
    env_file: ./backend/.env.example
    environment:
      DATABASE_URL: postgresql+psycopg2://applypilot:applypilot@db:5432/applypilot
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: minio:9000
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
      minio: { condition: service_started }
volumes:
  pgdata:
  miniodata:
```

- [ ] **Step 11: Write `backend/.env.example` and root `.env.example`**

`backend/.env.example`:
```
APP_ENV=development
DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@db:5432/applypilot
REDIS_URL=redis://redis:6379/0
JWT_SECRET=dev-only-insecure-change-me
S3_ENDPOINT=minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=applypilot
S3_SECURE=false
FERNET_KEY=
CORS_ORIGINS=http://localhost:3000
```
Root `.env.example`: same keys plus `NEXT_PUBLIC_API_URL=http://localhost:8000`.

- [ ] **Step 12: Commit**

```bash
git add backend docker-compose.yml .env.example
git commit -m "feat(backend): scaffold config, logging, health endpoint, infra compose"
```

---

### Task A2: Database engine, Base, session dependency

**Files:**
- Create: `backend/database.py`, `backend/deps.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `Base` (declarative base), `engine`, `SessionLocal`, `get_db() -> Iterator[Session]` (in `deps.py`), `get_redis() -> redis.Redis`.

- [ ] **Step 1: Write failing test `backend/tests/test_db.py`**

```python
from sqlalchemy import text
from database import SessionLocal


def test_session_executes_select_one() -> None:
    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_db.py -v`
Expected: FAIL (`ImportError: cannot import name 'SessionLocal'`).

- [ ] **Step 3: Write `backend/database.py`**

```python
"""
Module: database.py
Purpose: SQLAlchemy engine, session factory, and declarative Base.
Dependencies: SQLAlchemy 2.0
Author: ApplyPilot
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
```

- [ ] **Step 4: Write `backend/deps.py`**

```python
"""
Module: deps.py
Purpose: FastAPI dependencies for DB session, Redis, and current user.
Author: ApplyPilot
"""
from collections.abc import Iterator

import redis
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal

_redis_pool = redis.ConnectionPool.from_url(settings.redis_url)


def get_db() -> Iterator[Session]:
    """Yield a database session and ensure it is closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_redis() -> redis.Redis:
    """Return a Redis client bound to the shared pool."""
    return redis.Redis(connection_pool=_redis_pool)
```

- [ ] **Step 5: Run test to verify it passes** (requires DB up: `docker compose up -d db`)

Run: `cd backend && python -m pytest tests/test_db.py -v`
Expected: PASS. (If DB not reachable locally, this test runs in CI/Docker — see Task A12.)

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/deps.py backend/tests/test_db.py
git commit -m "feat(backend): add database engine, session and redis dependencies"
```

---

### Task A3: SQLAlchemy models for all tables

**Files:**
- Create: `backend/models/__init__.py` and one module per table (`user.py`, `resume.py`, `job.py`, `application.py`, `contact.py`, `email_account.py`, `follow_up.py`, `agent_run.py`, `feedback.py`, `usage_log.py`)
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces: ORM classes `User, Resume, Job, Application, Contact, EmailAccount, FollowUp, AgentRun, Feedback, UsageLog`. Enums: `ApplicationStatus`, `AgentRunStatus`, `EmailProvider`, `PlanTier`. All have `id: uuid`, timestamps. `User.email` unique. Embedding columns use `pgvector.sqlalchemy.Vector(1024)`.

- [ ] **Step 1: Write failing test `backend/tests/test_models.py`**

```python
from models import User, Application, ApplicationStatus


def test_user_tablename_and_columns() -> None:
    assert User.__tablename__ == "users"
    assert {"id", "email", "name", "plan", "stripe_customer_id", "created_at"} <= set(
        c.name for c in User.__table__.columns
    )


def test_application_status_enum_values() -> None:
    assert {s.value for s in ApplicationStatus} == {
        "pending", "generated", "sent", "opened", "replied", "rejected", "offer"
    }
    assert Application.__tablename__ == "applications"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'models'`).

- [ ] **Step 3: Write `backend/models/user.py`**

```python
"""
Module: models/user.py
Purpose: User ORM model and plan tier enum.
Author: ApplyPilot
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PlanTier(str, enum.Enum):
    """Subscription plan tiers."""

    free = "free"
    pro = "pro"
    unlimited = "unlimited"


class User(Base):
    """Application user with auth credentials and plan."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[PlanTier] = mapped_column(Enum(PlanTier, name="plan_tier"), default=PlanTier.free, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")
```

- [ ] **Step 4: Write `backend/models/resume.py`**

```python
"""
Module: models/resume.py
Purpose: Resume ORM model with pgvector embedding column.
Author: ApplyPilot
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Resume(Base):
    """Uploaded resume file plus parsed text and embedding."""

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="resumes")
```

- [ ] **Step 5: Write `backend/models/job.py`**

```python
"""
Module: models/job.py
Purpose: Scraped job posting with pgvector JD embedding.
Author: ApplyPilot
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Job(Base):
    """A job posting scraped from a source board."""

    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("company", "role", "posted_at", name="uq_job_dedup"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    company: Mapped[str] = mapped_column(String(300), nullable=False)
    role: Mapped[str] = mapped_column(String(300), nullable=False)
    jd_url: Mapped[str | None] = mapped_column(String(1000))
    jd_text: Mapped[str | None] = mapped_column(Text)
    jd_embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    location: Mapped[str | None] = mapped_column(String(300))
    salary_range: Mapped[str | None] = mapped_column(String(120))
    match_score: Mapped[float | None] = mapped_column(Float)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
```

- [ ] **Step 6: Write `backend/models/application.py`**

```python
"""
Module: models/application.py
Purpose: Application record tracking outreach state per job.
Author: ApplyPilot
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ApplicationStatus(str, enum.Enum):
    """Lifecycle states of an application."""

    pending = "pending"
    generated = "generated"
    sent = "sent"
    opened = "opened"
    replied = "replied"
    rejected = "rejected"
    offer = "offer"


class Application(Base):
    """A user's application/outreach for a specific job."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.pending, nullable=False
    )
    email_subject: Mapped[str | None] = mapped_column(String(500))
    email_body: Mapped[str | None] = mapped_column(Text)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    linkedin_msg: Mapped[str | None] = mapped_column(Text)
    recruiter_email: Mapped[str | None] = mapped_column(String(320))
    recruiter_linkedin: Mapped[str | None] = mapped_column(String(1000))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="applications")
```

- [ ] **Step 7: Write the remaining models** (`contact.py`, `email_account.py`, `follow_up.py`, `agent_run.py`, `feedback.py`, `usage_log.py`)

```python
# backend/models/contact.py
"""Module: models/contact.py — Recruiter/hiring contact record."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Contact(Base):
    """A discovered recruiter or hiring-manager contact."""
    __tablename__ = "contacts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(300), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(300))
    email: Mapped[str | None] = mapped_column(String(320))
    linkedin_url: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[str | None] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

```python
# backend/models/email_account.py
"""Module: models/email_account.py — Connected email account with encrypted tokens."""
import enum, uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class EmailProvider(str, enum.Enum):
    gmail = "gmail"
    outlook = "outlook"


class EmailAccount(Base):
    """OAuth-connected sending account; tokens stored encrypted."""
    __tablename__ = "email_accounts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider, name="email_provider"), nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

```python
# backend/models/follow_up.py
"""Module: models/follow_up.py — Scheduled follow-up for an application."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class FollowUp(Base):
    """A scheduled or sent follow-up message."""
    __tablename__ = "follow_ups"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False)
```

```python
# backend/models/agent_run.py
"""Module: models/agent_run.py — Background agent task run record."""
import enum, uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AgentRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class AgentRun(Base):
    """A record of an agent/Celery task execution."""
    __tablename__ = "agent_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus, name="agent_run_status"), default=AgentRunStatus.queued, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

```python
# backend/models/feedback.py
"""Module: models/feedback.py — User rating feedback on an application's email."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Feedback(Base):
    """Thumbs rating + notes on a generated email."""
    __tablename__ = "feedback"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

```python
# backend/models/usage_log.py
"""Module: models/usage_log.py — Per-user monthly usage counters."""
import uuid
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class UsageLog(Base):
    """Counter of a user's actions for a given month_year (YYYY-MM)."""
    __tablename__ = "usage_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    month_year: Mapped[str] = mapped_column(String(7), nullable=False)
```

- [ ] **Step 8: Write `backend/models/__init__.py`** (import all so Alembic autogen sees them)

```python
"""Aggregate model imports so SQLAlchemy metadata is complete."""
from models.user import User, PlanTier
from models.resume import Resume
from models.job import Job
from models.application import Application, ApplicationStatus
from models.contact import Contact
from models.email_account import EmailAccount, EmailProvider
from models.follow_up import FollowUp
from models.agent_run import AgentRun, AgentRunStatus
from models.feedback import Feedback
from models.usage_log import UsageLog

__all__ = [
    "User", "PlanTier", "Resume", "Job", "Application", "ApplicationStatus",
    "Contact", "EmailAccount", "EmailProvider", "FollowUp", "AgentRun",
    "AgentRunStatus", "Feedback", "UsageLog",
]
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models.py -v && python -m py_compile models/*.py`
Expected: both tests PASS; compile clean.

- [ ] **Step 10: Commit**

```bash
git add backend/models backend/tests/test_models.py
git commit -m "feat(backend): add SQLAlchemy models for all tables"
```

---

### Task A4: Alembic + initial migration (pgvector, tables, indexes, RLS)

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/001_initial.py`
- Test: `backend/tests/test_migration.py`

**Interfaces:**
- Produces: a migration that `CREATE EXTENSION IF NOT EXISTS vector`, creates all tables via `Base.metadata`, adds IVFFlat indexes on `resumes.embedding` and `jobs.jd_embedding`, the `(user_id,status)` index on applications, and writes RLS `CREATE POLICY` statements (guarded, documented). `conftest.py` gains a `db_session` fixture that creates/drops schema per test.

- [ ] **Step 1: Write `backend/alembic.ini`** (minimal — URL injected in env.py)

```ini
[alembic]
script_location = alembic
[loggers]
keys = root
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Write `backend/alembic/env.py`**

```python
"""Alembic environment using app settings and model metadata."""
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from config import settings
from database import Base
import models  # noqa: F401  ensures all tables registered

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

(Provide a standard `script.py.mako` — copy Alembic's default template verbatim.)

- [ ] **Step 3: Write `backend/alembic/versions/001_initial.py`**

```python
"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from database import Base
import models  # noqa: F401

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

# RLS policy SQL — applied only when the `app.current_user_id` GUC path is used
# (Supabase-swap target). The API layer enforces tenant isolation in Phase 1.
_RLS_TABLES = ["resumes", "jobs", "applications", "contacts", "email_accounts",
               "follow_ups", "agent_runs", "feedback", "usage_logs"]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(op.get_bind())
    op.execute("CREATE INDEX IF NOT EXISTS ix_resumes_embedding ON resumes "
               "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_jd_embedding ON jobs "
               "USING ivfflat (jd_embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_user_status "
               "ON applications (user_id, status)")
    # Documented Supabase-swap RLS path (no-op without Supabase auth roles):
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_owner ON {table} USING "
            f"(user_id::text = current_setting('app.current_user_id', true))"
        ) if table != "follow_ups" else None


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
```

> Note: `follow_ups` has no direct `user_id`; its RLS is via `application_id`. The
> guarded `if ... else None` skips it here; document this in README. For Phase 1
> tests we rely on API-layer filtering, so RLS being permissive locally is fine.

- [ ] **Step 4: Replace `conftest.py` DB fixture** (schema create/drop per test, app dependency override)

```python
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
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)
```

- [ ] **Step 5: Write `backend/tests/test_migration.py`**

```python
from sqlalchemy import inspect
from conftest import engine


def test_all_tables_created() -> None:
    names = set(inspect(engine).get_table_names())
    assert {"users", "resumes", "jobs", "applications", "contacts",
            "email_accounts", "follow_ups", "agent_runs", "feedback",
            "usage_logs"} <= names
```

- [ ] **Step 6: Run tests** (DB required)

Run: `cd backend && python -m pytest tests/test_migration.py -v`
Expected: PASS. Also verify Alembic: `alembic upgrade head` then `psql $DATABASE_URL -c "\dt"` lists all tables and `SELECT * FROM pg_extension WHERE extname='vector';` returns a row.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic backend/alembic.ini backend/tests/test_migration.py backend/tests/conftest.py
git commit -m "feat(backend): alembic initial migration with pgvector, indexes, RLS scaffold"
```

---

### Task A5: JWT security + auth schemas + current-user dependency

**Files:**
- Create: `backend/security/jwt.py`, `backend/schemas/auth.py`, `backend/schemas/user.py`, `backend/schemas/common.py`; Modify: `backend/deps.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(p)->str`, `verify_password(p,h)->bool`, `create_access_token(sub)->str`, `create_refresh_token(sub)->str`, `decode_token(t)->dict`; Pydantic `SignupRequest{email,password,name?}`, `LoginRequest{email,password}`, `TokenPair{access_token,refresh_token,token_type}`, `UserOut{id,email,name,avatar_url,plan,created_at}`; dependency `get_current_user(...)->User` raising 401.

- [ ] **Step 1: Write failing test `backend/tests/test_security.py`**

```python
import pytest
from security.jwt import hash_password, verify_password, create_access_token, decode_token


def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cret!")
    assert h != "s3cret!"
    assert verify_password("s3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_encodes_subject() -> None:
    token = create_access_token("user-123")
    claims = decode_token(token)
    assert claims["sub"] == "user-123"
    assert claims["type"] == "access"


def test_decode_rejects_garbage() -> None:
    with pytest.raises(Exception):
        decode_token("not-a-jwt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_security.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'security'`).

- [ ] **Step 3: Write `backend/security/jwt.py`**

```python
"""
Module: security/jwt.py
Purpose: Password hashing and JWT issue/verify for self-contained auth.
Dependencies: passlib[bcrypt], python-jose
Author: ApplyPilot
"""
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password."""
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return _pwd.verify(password, password_hash)


def _create_token(subject: str, token_type: str, expires: timedelta) -> str:
    """Create a signed JWT with subject, type, and expiry."""
    now = datetime.now(timezone.utc)
    claims = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    """Create a short-lived access token for the subject (user id)."""
    return _create_token(subject, "access", timedelta(minutes=settings.access_token_ttl_min))


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token for the subject (user id)."""
    return _create_token(subject, "refresh", timedelta(days=settings.refresh_token_ttl_days))


def decode_token(token: str) -> dict[str, object]:
    """Decode and validate a JWT, raising jose.JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

- [ ] **Step 4: Write `backend/schemas/common.py`, `auth.py`, `user.py`**

```python
# backend/schemas/common.py
"""Common response schemas."""
from pydantic import BaseModel


class Message(BaseModel):
    """Simple message envelope."""
    detail: str
```

```python
# backend/schemas/auth.py
"""Auth request/response schemas."""
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

```python
# backend/schemas/user.py
"""User response schema."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from models.user import PlanTier


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    name: str | None
    avatar_url: str | None
    plan: PlanTier
    created_at: datetime
```

- [ ] **Step 5: Add `get_current_user` to `backend/deps.py`** (append)

```python
import uuid as _uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session
from models.user import User
from security.jwt import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        claims = decode_token(creds.credentials)
        if claims.get("type") != "access":
            raise JWTError("wrong token type")
        user_id = _uuid.UUID(str(claims["sub"]))
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_security.py -v`
Expected: 3 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/security backend/schemas backend/deps.py backend/tests/test_security.py
git commit -m "feat(backend): JWT auth primitives, auth schemas, current-user dependency"
```

---

### Task A6: Auth router (signup / login / refresh / me)

**Files:**
- Create: `backend/routers/auth.py`; Modify: `backend/main.py` (mount router)
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`, `get_current_user`, schemas from A5.
- Produces: `POST /auth/signup -> 201 TokenPair`; `POST /auth/login -> 200 TokenPair`; `POST /auth/refresh -> 200 TokenPair`; `GET /auth/me -> 200 UserOut`.

- [ ] **Step 1: Write failing tests `backend/tests/test_auth.py`**

```python
from fastapi.testclient import TestClient


def _signup(client: TestClient, email="a@b.com", pw="password123"):
    return client.post("/auth/signup", json={"email": email, "password": pw, "name": "A"})


def test_signup_returns_201_and_tokens(client: TestClient) -> None:
    r = _signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_signup_duplicate_email_409(client: TestClient) -> None:
    _signup(client)
    r = _signup(client)
    assert r.status_code == 409


def test_login_wrong_password_401(client: TestClient) -> None:
    _signup(client)
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_returns_user(client: TestClient) -> None:
    token = _signup(client).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"
    assert r.json()["plan"] == "free"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL (404s — router not mounted).

- [ ] **Step 3: Write `backend/routers/auth.py`**

```python
"""
Module: routers/auth.py
Purpose: Self-contained signup/login/refresh/me endpoints (JWT).
Author: ApplyPilot
"""
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.user import User
from schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenPair
from schemas.user import UserOut
from security.jwt import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user_id: str) -> TokenPair:
    """Issue an access+refresh token pair for a user id."""
    return TokenPair(access_token=create_access_token(user_id),
                     refresh_token=create_refresh_token(user_id))


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED,
             summary="Register a new user")
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Create a user and return a token pair. 409 if email exists."""
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=payload.email, name=payload.name,
                password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _tokens(str(user.id))


@router.post("/login", response_model=TokenPair, summary="Authenticate and get tokens")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Validate credentials and return a token pair. 401 on failure."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return _tokens(str(user.id))


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token")
def refresh(payload: RefreshRequest) -> TokenPair:
    """Issue a new token pair from a valid refresh token. 401 otherwise."""
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise JWTError("not a refresh token")
        return _tokens(str(claims["sub"]))
    except (JWTError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc


@router.get("/me", response_model=UserOut, summary="Get the current user")
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
```

- [ ] **Step 4: Mount router in `main.py`** (add import + `app.include_router(auth.router)`)

```python
from routers import auth, health
# ... inside create_app:
    app.include_router(health.router)
    app.include_router(auth.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: all 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/auth.py backend/main.py backend/tests/test_auth.py
git commit -m "feat(backend): auth router (signup/login/refresh/me)"
```

---

### Task A7: Storage service + resume upload/list/delete router

**Files:**
- Create: `backend/services/storage_service.py`, `backend/schemas/resume.py`, `backend/routers/resumes.py`; Modify `backend/main.py`
- Test: `backend/tests/test_resumes.py`

**Interfaces:**
- Produces: `StorageService.upload(key, data, content_type)->str (url)`, `.delete(key)->None`, `ensure_bucket()`; `ResumeOut{id,filename,storage_url,created_at}`; `POST /resumes (multipart file) -> 201 ResumeOut`; `GET /resumes -> 200 list[ResumeOut]`; `DELETE /resumes/{id} -> 204`.

- [ ] **Step 1: Write failing tests `backend/tests/test_resumes.py`** (storage mocked via dependency override)

```python
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
```

> The `client` fixture is extended (Step 4) to override the storage dependency with an
> in-memory fake so tests never hit MinIO.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resumes.py -v`
Expected: FAIL (404 — router missing).

- [ ] **Step 3: Write `backend/services/storage_service.py`**

```python
"""
Module: services/storage_service.py
Purpose: S3-compatible object storage (MinIO) for resume files.
Dependencies: minio
Author: ApplyPilot
"""
import io

from minio import Minio

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Wrapper around a MinIO/S3 bucket for file upload and deletion."""

    def __init__(self) -> None:
        self._client = Minio(
            settings.s3_endpoint, access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key, secure=settings.s3_secure,
        )
        self._bucket = settings.s3_bucket

    def ensure_bucket(self) -> None:
        """Create the configured bucket if it does not exist."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes under key and return a retrievable URL."""
        self.ensure_bucket()
        self._client.put_object(self._bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
        scheme = "https" if settings.s3_secure else "http"
        return f"{scheme}://{settings.s3_endpoint}/{self._bucket}/{key}"

    def delete(self, key: str) -> None:
        """Delete the object at key (idempotent)."""
        self._client.remove_object(self._bucket, key)


def get_storage() -> StorageService:
    """FastAPI dependency returning a StorageService."""
    return StorageService()
```

- [ ] **Step 4: Write `backend/schemas/resume.py` and `backend/routers/resumes.py`**

```python
# backend/schemas/resume.py
"""Resume response schema."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    storage_url: str
    created_at: datetime
```

```python
# backend/routers/resumes.py
"""
Module: routers/resumes.py
Purpose: Upload, list, and delete user resumes (stored in MinIO).
Author: ApplyPilot
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.resume import Resume
from models.user import User
from schemas.resume import ResumeOut
from services.storage_service import StorageService, get_storage

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED,
             summary="Upload a resume")
def upload_resume(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
) -> Resume:
    """Store an uploaded resume file and persist its metadata."""
    key = f"{current_user.id}/{uuid.uuid4()}-{file.filename}"
    data = file.file.read()
    url = storage.upload(key, data, file.content_type or "application/octet-stream")
    resume = Resume(user_id=current_user.id, filename=file.filename or "resume", storage_url=url)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeOut], summary="List the user's resumes")
def list_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Resume]:
    """Return all resumes owned by the current user."""
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a resume")
def delete_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a resume owned by the current user. 404 if not found/owned."""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    db.delete(resume)
    db.commit()
```

- [ ] **Step 5: Extend `conftest.py` client fixture to override `get_storage`**

```python
# add to conftest.py
from services.storage_service import get_storage


class _FakeStorage:
    def ensure_bucket(self) -> None: ...
    def upload(self, key: str, data: bytes, content_type: str) -> str:
        return f"http://test-storage/{key}"
    def delete(self, key: str) -> None: ...


# in the client fixture, after the get_db override:
    app.dependency_overrides[get_storage] = lambda: _FakeStorage()
```

- [ ] **Step 6: Mount router in `main.py`** (`from routers import auth, health, resumes` + `app.include_router(resumes.router)`).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resumes.py -v`
Expected: 3 PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/services backend/schemas/resume.py backend/routers/resumes.py backend/main.py backend/tests/test_resumes.py backend/tests/conftest.py
git commit -m "feat(backend): MinIO storage service + resume upload/list/delete"
```

---

### Task A8: Jobs router (list with filters/pagination, get, seed-create)

**Files:**
- Create: `backend/schemas/job.py`, `backend/routers/jobs.py`; Modify `backend/main.py`
- Test: `backend/tests/test_jobs.py`

**Interfaces:**
- Produces: `JobOut{id,source,company,role,jd_url,location,salary_range,match_score,posted_at,status}`, `JobCreate{source,company,role,jd_url?,jd_text?,location?,salary_range?,posted_at?}`, `JobList{items,total,page,page_size}`. `POST /jobs -> 201` (manual/seed insert; scraper fills these in Phase 3), `GET /jobs?company=&source=&q=&page=&page_size= -> 200 JobList`, `GET /jobs/{id} -> 200 JobOut | 404`.

- [ ] **Step 1: Write failing tests `backend/tests/test_jobs.py`**

```python
from fastapi.testclient import TestClient


def _auth(client: TestClient) -> dict[str, str]:
    t = client.post("/auth/signup", json={"email": "j@b.com", "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def _make_job(client, headers, company="Stripe", role="SWE"):
    return client.post("/jobs", headers=headers, json={"source": "greenhouse", "company": company, "role": role})


def test_create_job_201(client: TestClient) -> None:
    h = _auth(client)
    r = _make_job(client, h)
    assert r.status_code == 201
    assert r.json()["company"] == "Stripe"


def test_list_jobs_paginated(client: TestClient) -> None:
    h = _auth(client)
    _make_job(client, h, "Stripe", "SWE")
    _make_job(client, h, "Linear", "FE")
    r = client.get("/jobs?page=1&page_size=1", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and len(body["items"]) == 1


def test_filter_jobs_by_company(client: TestClient) -> None:
    h = _auth(client)
    _make_job(client, h, "Stripe", "SWE")
    _make_job(client, h, "Linear", "FE")
    r = client.get("/jobs?company=Linear", headers=h)
    assert r.json()["total"] == 1 and r.json()["items"][0]["company"] == "Linear"


def test_get_missing_job_404(client: TestClient) -> None:
    h = _auth(client)
    import uuid
    assert client.get(f"/jobs/{uuid.uuid4()}", headers=h).status_code == 404


def test_jobs_require_auth(client: TestClient) -> None:
    assert client.get("/jobs").status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_jobs.py -v`
Expected: FAIL (404 — router missing).

- [ ] **Step 3: Write `backend/schemas/job.py`**

```python
"""Job request/response schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    source: str
    company: str
    role: str
    jd_url: str | None = None
    jd_text: str | None = None
    location: str | None = None
    salary_range: str | None = None
    posted_at: datetime | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source: str
    company: str
    role: str
    jd_url: str | None
    location: str | None
    salary_range: str | None
    match_score: float | None
    posted_at: datetime | None
    status: str


class JobList(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 4: Write `backend/routers/jobs.py`**

```python
"""
Module: routers/jobs.py
Purpose: Job listing with filters/pagination, retrieval, and manual create
         (the scraper populates jobs in Phase 3; manual create supports seeding).
Author: ApplyPilot
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.job import Job
from models.user import User
from schemas.job import JobCreate, JobList, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED, summary="Create a job")
def create_job(payload: JobCreate, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)) -> Job:
    """Insert a job (manual/seed). Jobs are global, not user-scoped."""
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=JobList, summary="List jobs with filters and pagination")
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: str | None = None,
    source: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> JobList:
    """Return a paginated, filterable list of jobs ordered by recency."""
    query = db.query(Job)
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if source:
        query = query.filter(Job.source == source)
    if q:
        query = query.filter(or_(Job.role.ilike(f"%{q}%"), Job.company.ilike(f"%{q}%")))
    total = query.with_entities(func.count(Job.id)).scalar() or 0
    items = (query.order_by(Job.scraped_at.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return JobList(items=[JobOut.model_validate(j) for j in items],
                   total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobOut, summary="Get a job by id")
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)) -> Job:
    """Return a single job or 404."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job
```

- [ ] **Step 5: Mount router; run tests**

Modify `main.py` (`from routers import auth, health, jobs, resumes` + include). Run:
`cd backend && python -m pytest tests/test_jobs.py -v` → all 6 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/schemas/job.py backend/routers/jobs.py backend/main.py backend/tests/test_jobs.py
git commit -m "feat(backend): jobs router with filters and pagination"
```

---

### Task A9: Applications router (CRUD + status transitions)

**Files:**
- Create: `backend/schemas/application.py`, `backend/routers/applications.py`; Modify `backend/main.py`
- Test: `backend/tests/test_applications.py`

**Interfaces:**
- Produces: `ApplicationCreate{job_id}`, `ApplicationUpdate{status?,email_subject?,email_body?,cover_letter?,linkedin_msg?,recruiter_email?,recruiter_linkedin?}`, `ApplicationOut{...all fields...,job:JobOut}`. `POST /applications -> 201`, `GET /applications?status= -> 200 list`, `GET /applications/{id} -> 200|404`, `PATCH /applications/{id} -> 200` (validates status enum), `DELETE /applications/{id} -> 204`. All scoped to `current_user`.

- [ ] **Step 1: Write failing tests `backend/tests/test_applications.py`**

```python
import uuid
from fastapi.testclient import TestClient


def _auth(client, email="ap@b.com"):
    t = client.post("/auth/signup", json={"email": email, "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def _job(client, h):
    return client.post("/jobs", headers=h, json={"source": "lever", "company": "Vercel", "role": "SWE"}).json()["id"]


def test_create_application_201(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    r = client.post("/applications", headers=h, json={"job_id": jid})
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert r.json()["job"]["company"] == "Vercel"


def test_patch_status_transition(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    r = client.patch(f"/applications/{aid}", headers=h, json={"status": "sent"})
    assert r.status_code == 200 and r.json()["status"] == "sent"


def test_patch_invalid_status_422(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    assert client.patch(f"/applications/{aid}", headers=h, json={"status": "bogus"}).status_code == 422


def test_other_users_application_404(client: TestClient) -> None:
    h1 = _auth(client, "u1@b.com")
    jid = _job(client, h1)
    aid = client.post("/applications", headers=h1, json={"job_id": jid}).json()["id"]
    h2 = _auth(client, "u2@b.com")
    assert client.get(f"/applications/{aid}", headers=h2).status_code == 404


def test_list_filter_by_status(client: TestClient) -> None:
    h = _auth(client)
    jid = _job(client, h)
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    client.patch(f"/applications/{aid}", headers=h, json={"status": "sent"})
    r = client.get("/applications?status=sent", headers=h)
    assert r.status_code == 200 and len(r.json()) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_applications.py -v` → FAIL (404).

- [ ] **Step 3: Write `backend/schemas/application.py`**

```python
"""Application request/response schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from models.application import ApplicationStatus
from schemas.job import JobOut


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    email_subject: str | None = None
    email_body: str | None = None
    cover_letter: str | None = None
    linkedin_msg: str | None = None
    recruiter_email: str | None = None
    recruiter_linkedin: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    email_subject: str | None
    email_body: str | None
    cover_letter: str | None
    linkedin_msg: str | None
    recruiter_email: str | None
    recruiter_linkedin: str | None
    sent_at: datetime | None
    follow_up_at: datetime | None
    reply_at: datetime | None
    created_at: datetime
    job: JobOut
```

- [ ] **Step 4: Write `backend/routers/applications.py`**

```python
"""
Module: routers/applications.py
Purpose: CRUD and status transitions for a user's applications.
Author: ApplyPilot
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.application import Application, ApplicationStatus
from models.job import Job
from models.user import User
from schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


def _owned(db: Session, app_id: uuid.UUID, user: User) -> Application:
    """Return a user-owned application or raise 404."""
    obj = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id).first()
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return obj


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED,
             summary="Create an application for a job")
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)) -> Application:
    """Create a pending application referencing an existing job."""
    if db.get(Job, payload.job_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    app_obj = Application(user_id=current_user.id, job_id=payload.job_id,
                          status=ApplicationStatus.pending)
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    return app_obj


@router.get("", response_model=list[ApplicationOut], summary="List applications")
def list_applications(status_filter: ApplicationStatus | None = None,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)) -> list[Application]:
    """List the user's applications, optionally filtered by status."""
    query = db.query(Application).filter(Application.user_id == current_user.id)
    if status_filter is not None:
        query = query.filter(Application.status == status_filter)
    return query.order_by(Application.created_at.desc()).all()


@router.get("/{application_id}", response_model=ApplicationOut, summary="Get an application")
def get_application(application_id: uuid.UUID, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)) -> Application:
    """Return a single owned application or 404."""
    return _owned(db, application_id, current_user)


@router.patch("/{application_id}", response_model=ApplicationOut, summary="Update an application")
def update_application(application_id: uuid.UUID, payload: ApplicationUpdate,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)) -> Application:
    """Apply partial updates (including status transitions) to an application."""
    obj = _owned(db, application_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete an application")
def delete_application(application_id: uuid.UUID, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)) -> None:
    """Delete an owned application. 404 if not found."""
    db.delete(_owned(db, application_id, current_user))
    db.commit()
```

> Note: the `status` query param is named `status_filter` in Python but exposed as
> `?status=` — add `Query(alias="status")`. Update signature:
> `status_filter: ApplicationStatus | None = Query(default=None, alias="status")` and
> `from fastapi import Query`.

- [ ] **Step 5: Apply the alias fix, mount router, run tests**

Edit the import to `from fastapi import APIRouter, Depends, HTTPException, Query, status` and the param to use `Query(default=None, alias="status")`. Mount in `main.py`. Run:
`cd backend && python -m pytest tests/test_applications.py -v` → all 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/schemas/application.py backend/routers/applications.py backend/main.py backend/tests/test_applications.py
git commit -m "feat(backend): applications router with CRUD and status transitions"
```

---

### Task A10: Dashboard stats router

**Files:**
- Create: `backend/schemas/dashboard.py`, `backend/routers/dashboard.py`; Modify `backend/main.py`
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Produces: `DashboardStats{total_applications,by_status:dict[str,int],reply_rate:float,recent:list[ApplicationOut]}`. `GET /dashboard/stats -> 200`.

- [ ] **Step 1: Write failing test `backend/tests/test_dashboard.py`**

```python
from fastapi.testclient import TestClient


def _auth(client):
    t = client.post("/auth/signup", json={"email": "d@b.com", "password": "password123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_dashboard_stats_shape(client: TestClient) -> None:
    h = _auth(client)
    jid = client.post("/jobs", headers=h, json={"source": "yc", "company": "C", "role": "R"}).json()["id"]
    aid = client.post("/applications", headers=h, json={"job_id": jid}).json()["id"]
    client.patch(f"/applications/{aid}", headers=h, json={"status": "replied"})
    r = client.get("/dashboard/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_applications"] == 1
    assert body["by_status"]["replied"] == 1
    assert body["reply_rate"] == 1.0
    assert len(body["recent"]) == 1


def test_dashboard_requires_auth(client: TestClient) -> None:
    assert client.get("/dashboard/stats").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (404).

- [ ] **Step 3: Write `backend/schemas/dashboard.py` and `backend/routers/dashboard.py`**

```python
# backend/schemas/dashboard.py
"""Dashboard aggregate schema."""
from pydantic import BaseModel
from schemas.application import ApplicationOut


class DashboardStats(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    reply_rate: float
    recent: list[ApplicationOut]
```

```python
# backend/routers/dashboard.py
"""
Module: routers/dashboard.py
Purpose: Aggregate application statistics for the dashboard overview.
Author: ApplyPilot
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.application import Application
from models.user import User
from schemas.application import ApplicationOut
from schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_REPLIED = ("replied", "offer")


@router.get("/stats", response_model=DashboardStats, summary="Dashboard aggregate stats")
def stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> DashboardStats:
    """Return application counts, per-status breakdown, reply rate, and recent items."""
    rows = (db.query(Application.status, func.count(Application.id))
            .filter(Application.user_id == current_user.id)
            .group_by(Application.status).all())
    by_status = {status.value: count for status, count in rows}
    total = sum(by_status.values())
    replied = sum(by_status.get(s, 0) for s in _REPLIED)
    sent_like = total  # denominator: all applications created
    reply_rate = round(replied / sent_like, 4) if sent_like else 0.0
    recent = (db.query(Application).filter(Application.user_id == current_user.id)
              .order_by(Application.created_at.desc()).limit(5).all())
    return DashboardStats(total_applications=total, by_status=by_status,
                          reply_rate=reply_rate,
                          recent=[ApplicationOut.model_validate(a) for a in recent])
```

- [ ] **Step 4: Mount router; run test** → 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/dashboard.py backend/routers/dashboard.py backend/main.py backend/tests/test_dashboard.py
git commit -m "feat(backend): dashboard aggregate stats endpoint"
```

---

### Task A11: Redis sliding-window rate limiter middleware

**Files:**
- Create: `backend/middleware/rate_limiter.py`; Modify `backend/main.py`
- Test: `backend/tests/test_rate_limiter.py`

**Interfaces:**
- Produces: `RateLimitMiddleware` (ASGI middleware) limiting per client identity (user id from token if present, else IP) to `settings.rate_limit_per_min` requests/60s using a Redis sorted-set sliding window; returns 429 with `Retry-After` when exceeded. `/health` exempt.

- [ ] **Step 1: Write failing test `backend/tests/test_rate_limiter.py`** (fakeredis via override)

```python
import fakeredis
from fastapi.testclient import TestClient
from main import create_app
import middleware.rate_limiter as rl


def test_rate_limit_returns_429(monkeypatch) -> None:
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_redis", lambda: fake)
    monkeypatch.setattr(rl, "LIMIT", 3)
    app = create_app()
    client = TestClient(app)
    codes = [client.get("/health").status_code for _ in range(5)]
    assert 429 in codes
    assert codes.count(200) == 3
```

> Add `fakeredis==2.26.1` to `requirements.txt`. `/health` is NOT exempt in this test
> so the limiter is observable; in production exempt-list is `{"/health"}` — the test
> monkeypatches `EXEMPT=set()`. Add `monkeypatch.setattr(rl, "EXEMPT", set())`.

- [ ] **Step 2: Run test to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Write `backend/middleware/rate_limiter.py`**

```python
"""
Module: middleware/rate_limiter.py
Purpose: Redis sliding-window per-identity rate limiting (ASGI middleware).
Dependencies: redis, starlette
Author: ApplyPilot
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import settings
from deps import get_redis

LIMIT = settings.rate_limit_per_min
WINDOW_SEC = 60
EXEMPT = {"/health"}


def _redis():
    """Return a Redis client (indirection point for tests)."""
    return get_redis()


def _identity(request: Request) -> str:
    """Derive a rate-limit key from auth token subject or client IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return f"tok:{auth[7:][:24]}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter using a Redis sorted set per identity."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Reject with 429 when the identity exceeds LIMIT within WINDOW_SEC."""
        if request.url.path in EXEMPT:
            return await call_next(request)
        client = _redis()
        key = f"rl:{_identity(request)}"
        now = time.time()
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - WINDOW_SEC)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SEC)
        count = pipe.execute()[2]
        if count > LIMIT:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429,
                                headers={"Retry-After": str(WINDOW_SEC)})
        return await call_next(request)
```

- [ ] **Step 4: Wire into `main.py`** (`app.add_middleware(RateLimitMiddleware)` after CORS).

- [ ] **Step 5: Run test to verify it passes** → PASS.

- [ ] **Step 6: Run full backend suite + grep gates**

Run:
```bash
cd backend && python -m pytest tests/ -q
grep -rn "TODO\|FIXME\|placeholder\|NotImplemented\|raise Exception\b" --include="*.py" . || echo "clean"
```
Expected: all tests pass; grep prints `clean` (or only this plan's allowed matches — none in code).

- [ ] **Step 7: Commit**

```bash
git add backend/middleware backend/main.py backend/tests/test_rate_limiter.py backend/requirements.txt
git commit -m "feat(backend): Redis sliding-window rate limiter middleware"
```

---

### Task A12: Backend Dockerfile + compose wiring + container test run

**Files:**
- Create: `backend/Dockerfile`, `backend/entrypoint.sh`; Modify `docker-compose.yml`
- Test: container boot + `/health` + in-container pytest

**Interfaces:**
- Produces: a backend image that runs migrations then serves uvicorn; `docker compose up backend` healthy.

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh
EXPOSE 8000
CMD ["./entrypoint.sh"]
```

- [ ] **Step 2: Write `backend/entrypoint.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 3: Add healthcheck to `backend` service in `docker-compose.yml`**

```yaml
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

- [ ] **Step 4: Build and boot**

Run:
```bash
docker compose build backend
docker compose up -d db redis minio backend
sleep 15
curl -f http://localhost:8000/health && echo " ✓ backend up"
```
Expected: `{"status":"ok"} ✓ backend up`.

- [ ] **Step 5: Run the suite inside the container** (DB reachable as `db`)

Run: `docker compose run --rm backend python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile backend/entrypoint.sh docker-compose.yml
git commit -m "feat(backend): Dockerfile + entrypoint migrations + compose healthcheck"
```

---

# PART B — FRONTEND (Blueprint design system)

### Task B1: Next.js scaffold + Tailwind + Blueprint tokens, fonts, theme

**Files:**
- Create: `frontend/package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.js`, `app/globals.css`, `app/layout.tsx`, `lib/utils.ts`, `components/shared/ThemeToggle.tsx`, `frontend/.env.local.example`
- Test: `npx tsc --noEmit` clean + `next build` succeeds

**Interfaces:**
- Produces: App Router project; Blueprint CSS variables in `globals.css`; `next/font` for VT323 / Source Serif 4 / JetBrains Mono exposed as CSS vars `--font-display/--font-body/--font-mono`; `cn()` util; theme toggle writing `data-theme` to `<html>`.

- [ ] **Step 1: Write `frontend/package.json`** (pinned)

```json
{
  "name": "applypilot-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.2.18",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@tanstack/react-query": "5.62.7",
    "axios": "1.7.9",
    "zustand": "5.0.2",
    "recharts": "2.14.1",
    "framer-motion": "11.13.5",
    "clsx": "2.1.1",
    "tailwind-merge": "2.5.5",
    "lucide-react": "0.468.0",
    "class-variance-authority": "0.7.1",
    "@radix-ui/react-dialog": "1.1.4",
    "@radix-ui/react-dropdown-menu": "2.1.4",
    "@radix-ui/react-tabs": "1.1.2"
  },
  "devDependencies": {
    "typescript": "5.7.2",
    "@types/node": "22.10.2",
    "@types/react": "18.3.17",
    "@types/react-dom": "18.3.5",
    "tailwindcss": "3.4.16",
    "postcss": "8.4.49",
    "autoprefixer": "10.4.20",
    "eslint": "8.57.1",
    "eslint-config-next": "14.2.18"
  }
}
```

- [ ] **Step 2: Write `tsconfig.json`, `next.config.ts`, `postcss.config.js`**

```jsonc
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022", "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false, "skipLibCheck": true, "strict": true,
    "noEmit": true, "esModuleInterop": true, "module": "esnext",
    "moduleResolution": "bundler", "resolveJsonModule": true,
    "isolatedModules": true, "jsx": "preserve", "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```
```ts
// next.config.ts
import type { NextConfig } from "next";
const nextConfig: NextConfig = { reactStrictMode: true };
export default nextConfig;
```
```js
// postcss.config.js
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 3: Write `tailwind.config.ts`** (radius 0, Blueprint tokens, hard shadow, fonts)

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--bg-surface)",
        "surface-hover": "var(--bg-surface-hover)",
        ink: "var(--ink)", "ink-soft": "var(--ink-soft)", "ink-mute": "var(--ink-mute)",
        rule: "var(--rule)", "rule-soft": "var(--rule-soft)",
        blueprint: "var(--blueprint)", "accent-hover": "var(--accent-hover)",
        "on-accent": "var(--on-accent)", warn: "var(--warn)",
        "blueprint-tint": "var(--blueprint-tint)",
      },
      borderRadius: { none: "0", DEFAULT: "0", sm: "0", md: "0", lg: "0", xl: "0", full: "0" },
      boxShadow: { hard: "3px 3px 0 var(--ink)", "hard-lg": "5px 5px 0 var(--ink)" },
      fontFamily: {
        display: ["var(--font-display)", "monospace"],
        body: ["var(--font-body)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 4: Write `app/globals.css`** (paste Blueprint tokens + base reset)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Blueprint tokens (light + dark) — from blueprint-design-system/tokens.md */
:root {
  --font-heading: var(--font-display);
  --bg:#fafaf5; --bg-surface:#f3f1e8; --bg-surface-hover:#ece9dc;
  --header-bg:rgba(250,250,245,0.94); --modal-bg:#fafaf5; --overlay-bg:rgba(26,26,26,0.55);
  --code-bg:#efece0; --ink:#1a1a1a; --ink-soft:#4a4a4a; --ink-mute:#7a7a78;
  --rule:#1a1a1a; --rule-soft:rgba(26,26,26,0.16); --paper-rule:rgba(26,26,26,0.08);
  --blueprint:#3553ff; --blueprint-tint:rgba(53,83,255,0.08);
  --blueprint-tint-strong:rgba(53,83,255,0.18); --accent-hover:#2840d6;
  --on-accent:#ffffff;  /* text/icon color on a blueprint background */
  --status-complete:#3553ff; --status-in-progress:#4a4a4a; --status-planned:#b8b6ad;
  --warn:#b8870f; --dot-color:var(--paper-rule);
  --shadow-hard:3px 3px 0 var(--ink); --shadow-hard-lg:5px 5px 0 var(--ink);
  --sidebar-width:240px; --header-height:64px;
}
[data-theme="dark"] {
  --bg:#0a0d1a; --bg-surface:#131830; --bg-surface-hover:#1b2244;
  --header-bg:rgba(10,13,26,0.94); --modal-bg:#0f1424; --overlay-bg:rgba(10,13,26,0.78);
  --code-bg:#131830; --ink:#e8e6dc; --ink-soft:#a8a6a0; --ink-mute:#7a7878;
  --rule:#e8e6dc; --rule-soft:rgba(232,230,220,0.18); --paper-rule:rgba(232,230,220,0.08);
  --blueprint:#6b8eff; --blueprint-tint:rgba(107,142,255,0.12);
  --blueprint-tint-strong:rgba(107,142,255,0.22); --accent-hover:#8aa5ff;
  --on-accent:#0a0d1a;  /* dark text on the lighter blueprint accent in dark mode */
  --status-complete:#6b8eff; --status-in-progress:#c8c6c0; --status-planned:#4a4a48; --warn:#d4a83d;
}
*, *::before, *::after { box-sizing: border-box; }
html { font-size: 18px; scroll-behavior: smooth; }
body { margin:0; font-family:var(--font-body); background:var(--bg); color:var(--ink);
  line-height:1.62; transition:background-color .2s,color .2s; }
h1,h2,h3,h4,h5,h6 { font-family:var(--font-display); font-weight:400; line-height:1; letter-spacing:.02em; }
a { color:var(--blueprint); text-decoration:none; }
a:hover { color:var(--accent-hover); }
.label { font-family:var(--font-mono); font-size:.72rem; font-weight:500; letter-spacing:.12em;
  text-transform:uppercase; color:var(--ink-soft); }
::selection { background:var(--blueprint-tint-strong); color:var(--ink); }
:focus-visible { outline:2px solid var(--blueprint); outline-offset:2px; }
@media (prefers-reduced-motion: reduce){ *,*::before,*::after{ animation-duration:.01ms!important; transition-duration:.01ms!important; } }
```

- [ ] **Step 5: Write `app/layout.tsx`** (fonts via next/font + no-flash theme script)

```tsx
import type { Metadata } from "next";
import { VT323, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const display = VT323({ weight: "400", subsets: ["latin"], variable: "--font-display" });
const body = Source_Serif_4({ subsets: ["latin"], variable: "--font-body" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = { title: "ApplyPilot", description: "Autonomous job application engine" };

const themeScript = `(function(){try{var t=localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
```

- [ ] **Step 6: Write `lib/utils.ts` and `components/shared/ThemeToggle.tsx`**

```ts
// lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]): string { return twMerge(clsx(inputs)); }
```
```tsx
// components/shared/ThemeToggle.tsx
"use client";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    setTheme((document.documentElement.getAttribute("data-theme") as "light" | "dark") ?? "light");
  }, []);
  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    setTheme(next);
  }
  return (
    <button onClick={toggle} aria-label="Toggle theme"
      className="border border-ink p-2 hover:bg-ink hover:text-bg transition-colors">
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
```

- [ ] **Step 7: Write `frontend/.env.local.example`**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

(Providers component is created in B3; create a temporary pass-through now so build works:)
```tsx
// app/providers.tsx (temporary; replaced in B3)
"use client";
export function Providers({ children }: { children: React.ReactNode }) { return <>{children}</>; }
```

- [ ] **Step 8: Install, typecheck, build**

Run:
```bash
cd frontend && npm install
npx tsc --noEmit
npx next build
```
Expected: typecheck clean; build succeeds (a default `app/page.tsx` may be needed — add one redirecting to `/login`, see B3 Step 6).

- [ ] **Step 9: Commit**

```bash
git add frontend
git commit -m "feat(frontend): Next.js scaffold with Blueprint tokens, fonts, theme toggle"
```

---

### Task B2: Types + API client (axios + JWT interceptor) + auth store

**Files:**
- Create: `frontend/types/index.ts`, `lib/api.ts`, `lib/auth.ts`, `store/authStore.ts`, `store/uiStore.ts`
- Test: `npx tsc --noEmit` clean (type-level contract). Runtime exercised in B3+.

**Interfaces:**
- Produces: TS types mirroring backend schemas (`User`, `Job`, `JobList`, `Application`, `ApplicationStatus`, `Resume`, `DashboardStats`, `TokenPair`); `api` axios instance injecting `Authorization` from `authStore` and auto-refreshing on 401; `useAuthStore` (Zustand, persists tokens to `localStorage`); `useUiStore` (sidebar open state).

- [ ] **Step 1: Write `frontend/types/index.ts`**

```ts
export type Plan = "free" | "pro" | "unlimited";
export type ApplicationStatus =
  | "pending" | "generated" | "sent" | "opened" | "replied" | "rejected" | "offer";

export interface User { id: string; email: string; name: string | null;
  avatar_url: string | null; plan: Plan; created_at: string; }
export interface TokenPair { access_token: string; refresh_token: string; token_type: string; }
export interface Job { id: string; source: string; company: string; role: string;
  jd_url: string | null; location: string | null; salary_range: string | null;
  match_score: number | null; posted_at: string | null; status: string; }
export interface JobList { items: Job[]; total: number; page: number; page_size: number; }
export interface Resume { id: string; filename: string; storage_url: string; created_at: string; }
export interface Application {
  id: string; job_id: string; status: ApplicationStatus;
  email_subject: string | null; email_body: string | null; cover_letter: string | null;
  linkedin_msg: string | null; recruiter_email: string | null; recruiter_linkedin: string | null;
  sent_at: string | null; follow_up_at: string | null; reply_at: string | null;
  created_at: string; job: Job;
}
export interface DashboardStats { total_applications: number;
  by_status: Record<string, number>; reply_rate: number; recent: Application[]; }
```

- [ ] **Step 2: Write `store/authStore.ts` and `store/uiStore.ts`**

```ts
// store/authStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null; refreshToken: string | null;
  setTokens: (a: string, r: string) => void; clear: () => void;
}
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null, refreshToken: null,
      setTokens: (a, r) => set({ accessToken: a, refreshToken: r }),
      clear: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: "applypilot-auth" },
  ),
);
```
```ts
// store/uiStore.ts
import { create } from "zustand";
interface UiState { sidebarOpen: boolean; toggleSidebar: () => void; }
export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));
```

- [ ] **Step 3: Write `lib/api.ts`**

```ts
import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/store/authStore";
import type { TokenPair } from "@/types";

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const api = axios.create({ baseURL });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;
async function refresh(): Promise<string | null> {
  const rt = useAuthStore.getState().refreshToken;
  if (!rt) return null;
  try {
    const { data } = await axios.post<TokenPair>(`${baseURL}/auth/refresh`, { refresh_token: rt });
    useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch { useAuthStore.getState().clear(); return null; }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      refreshing = refreshing ?? refresh();
      const token = await refreshing;
      refreshing = null;
      if (token) { original.headers.Authorization = `Bearer ${token}`; return api(original); }
    }
    return Promise.reject(error);
  },
);
```

- [ ] **Step 4: Write `lib/auth.ts`** (typed call helpers)

```ts
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { TokenPair, User } from "@/types";

export async function signup(email: string, password: string, name?: string): Promise<void> {
  const { data } = await api.post<TokenPair>("/auth/signup", { email, password, name });
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
}
export async function login(email: string, password: string): Promise<void> {
  const { data } = await api.post<TokenPair>("/auth/login", { email, password });
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
}
export async function getMe(): Promise<User> {
  return (await api.get<User>("/auth/me")).data;
}
export function logout(): void { useAuthStore.getState().clear(); }
```

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npx tsc --noEmit` → clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/types frontend/lib frontend/store
git commit -m "feat(frontend): types, axios client with JWT refresh, auth/ui stores"
```

---

### Task B3: Providers (React Query), UI primitives, auth pages

**Files:**
- Create: `app/providers.tsx` (replace temp), `components/ui/{button,input,card,badge}.tsx`, `app/(auth)/login/page.tsx`, `app/(auth)/signup/page.tsx`, `app/page.tsx`
- Test: `npx tsc --noEmit` + manual: signup/login round-trip against running backend

**Interfaces:**
- Consumes: `login`, `signup` from `lib/auth.ts`; `useAuthStore`.
- Produces: `Providers` wrapping `QueryClientProvider`; Blueprint-styled `Button`, `Input`, `Card`, `Badge`; functional login/signup forms (loading + disabled + error states) redirecting to `/dashboard` on success; root `/` redirects to `/dashboard` (or `/login` if unauthenticated, handled in dashboard layout).

- [ ] **Step 1: Write `app/providers.tsx`**

```tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
  }));
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 2: Write `components/ui/button.tsx`** (Blueprint: mono uppercase, hard border, no radius)

```tsx
import { cn } from "@/lib/utils";
import { forwardRef, type ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary"; size?: "sm" | "md";
}
export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variant = "default", size = "md", disabled, ...props }, ref) => (
    <button ref={ref} disabled={disabled}
      className={cn(
        "inline-flex items-center gap-2 font-mono uppercase tracking-[0.12em] border transition-colors",
        size === "sm" ? "px-3 py-1.5 text-[0.72rem]" : "px-5 py-2.5 text-[0.8rem]",
        variant === "primary"
          ? "bg-blueprint text-on-accent border-blueprint hover:bg-accent-hover hover:border-accent-hover"
          : "bg-transparent text-ink border-ink hover:bg-ink hover:text-bg",
        disabled && "opacity-50 cursor-not-allowed hover:bg-transparent hover:text-ink",
        className,
      )}
      {...props} />
  ),
);
Button.displayName = "Button";
```

- [ ] **Step 3: Write `components/ui/input.tsx`, `card.tsx`, `badge.tsx`**

```tsx
// input.tsx
import { cn } from "@/lib/utils";
import { forwardRef, type InputHTMLAttributes } from "react";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref}
      className={cn("w-full border border-ink bg-bg px-3 py-2 font-body text-ink",
        "focus:outline-none focus:border-blueprint placeholder:text-ink-mute", className)}
      {...props} />
  ),
);
Input.displayName = "Input";
```
```tsx
// card.tsx
import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("bg-surface border border-rule-soft p-6 transition-colors hover:border-blueprint", className)} {...props} />;
}
```
```tsx
// badge.tsx
import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";
export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("inline-flex items-center border border-ink px-2 py-0.5 font-mono text-[0.68rem] uppercase tracking-[0.1em]", className)} {...props} />;
}
```

- [ ] **Step 4: Write `app/(auth)/login/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(null); setLoading(true);
    try { await login(email, password); router.push("/dashboard"); }
    catch { setError("Invalid email or password."); }
    finally { setLoading(false); }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm border border-ink bg-surface p-8 shadow-hard space-y-5">
        <h1 className="text-4xl">ApplyPilot</h1>
        <p className="label">Sign in</p>
        {error && <p className="font-mono text-[0.8rem] text-[var(--warn)]">{error}</p>}
        <Input type="email" placeholder="you@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} required disabled={loading} />
        <Input type="password" placeholder="Password" value={password}
          onChange={(e) => setPassword(e.target.value)} required disabled={loading} />
        <Button type="submit" variant="primary" disabled={loading} className="w-full justify-center">
          {loading ? "Signing in…" : "Sign in"}
        </Button>
        <p className="font-mono text-[0.75rem] text-ink-soft">
          No account? <Link href="/signup" className="text-blueprint">Sign up</Link>
        </p>
      </form>
    </main>
  );
}
```

- [ ] **Step 5: Write `app/(auth)/signup/page.tsx`** (same pattern, calls `signup(email,password,name)`, has a name field, error copy "Could not create account — email may already be registered.", link to `/login`).

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signup } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [password, setPassword] = useState(""); const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(null); setLoading(true);
    try { await signup(email, password, name || undefined); router.push("/dashboard"); }
    catch { setError("Could not create account — email may already be registered."); }
    finally { setLoading(false); }
  }
  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm border border-ink bg-surface p-8 shadow-hard space-y-5">
        <h1 className="text-4xl">ApplyPilot</h1>
        <p className="label">Create account</p>
        {error && <p className="font-mono text-[0.8rem] text-[var(--warn)]">{error}</p>}
        <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} disabled={loading} />
        <Input type="email" placeholder="you@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} required disabled={loading} />
        <Input type="password" placeholder="Password (min 8 chars)" value={password}
          onChange={(e) => setPassword(e.target.value)} required minLength={8} disabled={loading} />
        <Button type="submit" variant="primary" disabled={loading} className="w-full justify-center">
          {loading ? "Creating…" : "Create account"}
        </Button>
        <p className="font-mono text-[0.75rem] text-ink-soft">
          Have an account? <Link href="/login" className="text-blueprint">Sign in</Link>
        </p>
      </form>
    </main>
  );
}
```

- [ ] **Step 6: Write `app/page.tsx`** (root redirect)

```tsx
import { redirect } from "next/navigation";
export default function Home() { redirect("/dashboard"); }
```

- [ ] **Step 7: Typecheck + build + manual round-trip**

Run: `cd frontend && npx tsc --noEmit && npx next build`. With backend running (`docker compose up -d`), `npm run dev`, visit `/signup`, create an account, confirm redirect to `/dashboard` (404 until B4 — acceptable here; verify network tab shows 201 + tokens persisted in `localStorage`).

- [ ] **Step 8: Commit**

```bash
git add frontend/app frontend/components/ui
git commit -m "feat(frontend): React Query providers, Blueprint UI primitives, auth pages"
```

---

### Task B4: Dashboard layout shell (sidebar + topnav, auth guard)

**Files:**
- Create: `app/(dashboard)/layout.tsx`, `components/shared/Sidebar.tsx`, `components/shared/TopNav.tsx`, `components/shared/PlanBadge.tsx`, `hooks/useMe.ts`
- Test: `tsc --noEmit` + manual: unauthenticated visit to `/dashboard` redirects to `/login`

**Interfaces:**
- Consumes: `getMe`, `useAuthStore`, `useUiStore`, `ThemeToggle`.
- Produces: dashboard shell with fixed sidebar (nav: Dashboard, Jobs, Applications, Settings), topnav with `PlanBadge` + `ThemeToggle` + logout; client-side guard redirecting to `/login` when no token / `getMe` fails; `useMe()` React Query hook.

- [ ] **Step 1: Write `hooks/useMe.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/lib/auth";
import type { User } from "@/types";
export function useMe() {
  return useQuery<User>({ queryKey: ["me"], queryFn: getMe, retry: false });
}
```

- [ ] **Step 2: Write `components/shared/Sidebar.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Briefcase, Send, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/applications", label: "Applications", icon: Send },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-[var(--sidebar-width)] shrink-0 border-r border-rule-soft bg-surface min-h-screen p-5">
      <div className="text-2xl mb-8" style={{ fontFamily: "var(--font-display)" }}>ApplyPilot</div>
      <nav className="space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={href} href={href}
              className={cn("flex items-center gap-3 px-3 py-2 font-mono text-[0.8rem] uppercase tracking-[0.08em] border border-transparent",
                active ? "bg-blueprint-tint border-blueprint text-ink" : "text-ink-soft hover:text-ink hover:border-rule-soft")}>
              <Icon size={16} /> {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 3: Write `components/shared/PlanBadge.tsx` and `TopNav.tsx`**

```tsx
// PlanBadge.tsx
import { Badge } from "@/components/ui/badge";
import type { Plan } from "@/types";
export function PlanBadge({ plan }: { plan: Plan }) {
  const color = plan === "unlimited" ? "border-blueprint text-blueprint"
    : plan === "pro" ? "border-ink text-ink" : "border-ink-mute text-ink-mute";
  return <Badge className={color}>{plan}</Badge>;
}
```
```tsx
// TopNav.tsx
"use client";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { PlanBadge } from "@/components/shared/PlanBadge";
import { logout } from "@/lib/auth";
import type { User } from "@/types";

export function TopNav({ user }: { user: User }) {
  const router = useRouter();
  return (
    <header className="h-[var(--header-height)] border-b border-rule-soft flex items-center justify-between px-6">
      <span className="label">{user.email}</span>
      <div className="flex items-center gap-3">
        <PlanBadge plan={user.plan} />
        <ThemeToggle />
        <button onClick={() => { logout(); router.push("/login"); }}
          aria-label="Log out" className="border border-ink p-2 hover:bg-ink hover:text-bg transition-colors">
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Write `app/(dashboard)/layout.tsx`** (guard + shell)

```tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/shared/Sidebar";
import { TopNav } from "@/components/shared/TopNav";
import { useMe } from "@/hooks/useMe";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, isError } = useMe();
  useEffect(() => { if (isError) router.replace("/login"); }, [isError, router]);
  if (isLoading) return <div className="p-10 font-mono text-ink-soft">Loading…</div>;
  if (!user) return null;
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 min-h-screen">
        <TopNav user={user} />
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Typecheck + build + manual guard check**

Run: `cd frontend && npx tsc --noEmit && npx next build`. Manual: clear `localStorage`, visit `/dashboard` → redirected to `/login`.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/\(dashboard\)/layout.tsx frontend/components/shared frontend/hooks/useMe.ts
git commit -m "feat(frontend): dashboard shell with sidebar, topnav, and auth guard"
```

---

### Task B5: Jobs feed + job detail (hooks, JobCard, JobFeed, JobFilters)

**Files:**
- Create: `hooks/useJobs.ts`, `components/jobs/{JobCard,JobFeed,JobFilters}.tsx`, `app/(dashboard)/jobs/page.tsx`, `app/(dashboard)/jobs/[id]/page.tsx`
- Test: `tsc --noEmit` + manual: seed a job via API, see it in feed, open detail, click "Create application"

**Interfaces:**
- Consumes: `api`, types `Job/JobList`, `Application`.
- Produces: `useJobs(params)` (React Query, keyed by filters/page), `useJob(id)`, `useCreateApplication()` mutation (`POST /applications`); `JobCard`, `JobFeed` (loading/error/empty/success), `JobFilters` (company/source/q); jobs list page + detail page with a "Create application" CTA that navigates to the new application.

- [ ] **Step 1: Write `hooks/useJobs.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Application, Job, JobList } from "@/types";

export interface JobQuery { company?: string; source?: string; q?: string; page?: number; page_size?: number; }

export function useJobs(params: JobQuery) {
  return useQuery<JobList>({
    queryKey: ["jobs", params],
    queryFn: async () => (await api.get<JobList>("/jobs", { params })).data,
  });
}
export function useJob(id: string) {
  return useQuery<Job>({ queryKey: ["job", id], queryFn: async () => (await api.get<Job>(`/jobs/${id}`)).data });
}
export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation<Application, Error, string>({
    mutationFn: async (jobId) => (await api.post<Application>("/applications", { job_id: jobId })).data,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["applications"] }); },
  });
}
```

- [ ] **Step 2: Write `components/jobs/JobCard.tsx`**

```tsx
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Job } from "@/types";

export function JobCard({ job }: { job: Job }) {
  return (
    <Link href={`/jobs/${job.id}`}>
      <Card className="shadow-hard hover:shadow-hard-lg">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-xl">{job.role}</h3>
            <p className="font-mono text-[0.8rem] text-ink-soft">{job.company}</p>
          </div>
          {job.match_score !== null && (
            <Badge className="border-blueprint text-blueprint">{Math.round(job.match_score * 100)}%</Badge>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[0.7rem] text-ink-mute uppercase">
          <span>{job.source}</span>
          {job.location && <span>· {job.location}</span>}
          {job.salary_range && <span>· {job.salary_range}</span>}
        </div>
      </Card>
    </Link>
  );
}
```

- [ ] **Step 3: Write `components/jobs/JobFilters.tsx` and `JobFeed.tsx`**

```tsx
// JobFilters.tsx
"use client";
import { Input } from "@/components/ui/input";
export interface Filters { q: string; source: string; }
export function JobFilters({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6">
      <Input placeholder="Search role or company" value={value.q}
        onChange={(e) => onChange({ ...value, q: e.target.value })} />
      <Input placeholder="Source (e.g. greenhouse)" value={value.source}
        onChange={(e) => onChange({ ...value, source: e.target.value })} />
    </div>
  );
}
```
```tsx
// JobFeed.tsx
"use client";
import { JobCard } from "@/components/jobs/JobCard";
import type { JobList } from "@/types";
export function JobFeed({ data, isLoading, isError }: { data?: JobList; isLoading: boolean; isError: boolean }) {
  if (isLoading) return <p className="font-mono text-ink-soft">Loading jobs…</p>;
  if (isError) return <p className="font-mono text-[var(--warn)]">Failed to load jobs.</p>;
  if (!data || data.items.length === 0) return <p className="font-mono text-ink-mute">No jobs yet.</p>;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.items.map((j) => <JobCard key={j.id} job={j} />)}
    </div>
  );
}
```

- [ ] **Step 4: Write `app/(dashboard)/jobs/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { JobFilters, type Filters } from "@/components/jobs/JobFilters";
import { JobFeed } from "@/components/jobs/JobFeed";
import { useJobs } from "@/hooks/useJobs";

export default function JobsPage() {
  const [filters, setFilters] = useState<Filters>({ q: "", source: "" });
  const { data, isLoading, isError } = useJobs({
    q: filters.q || undefined, source: filters.source || undefined, page: 1, page_size: 30,
  });
  return (
    <div>
      <h1 className="text-3xl mb-6">Jobs</h1>
      <JobFilters value={filters} onChange={setFilters} />
      <JobFeed data={data} isLoading={isLoading} isError={isError} />
    </div>
  );
}
```

- [ ] **Step 5: Write `app/(dashboard)/jobs/[id]/page.tsx`**

```tsx
"use client";
import { useParams, useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useJob, useCreateApplication } from "@/hooks/useJobs";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: job, isLoading, isError } = useJob(id);
  const create = useCreateApplication();
  if (isLoading) return <p className="font-mono text-ink-soft">Loading…</p>;
  if (isError || !job) return <p className="font-mono text-[var(--warn)]">Job not found.</p>;
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl">{job.role}</h1>
      <p className="font-mono text-ink-soft mb-6">{job.company}</p>
      <Card className="shadow-hard">
        <p className="label mb-2">Source</p>
        <p className="font-mono text-[0.85rem]">{job.source}</p>
        {job.jd_url && <a href={job.jd_url} className="block mt-4 text-blueprint font-mono text-[0.8rem]">View posting →</a>}
      </Card>
      <Button variant="primary" className="mt-6" disabled={create.isPending}
        onClick={async () => { const app = await create.mutateAsync(job.id); router.push(`/applications/${app.id}`); }}>
        {create.isPending ? "Creating…" : "Create application"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 6: Typecheck + build + manual**

Run: `cd frontend && npx tsc --noEmit && npx next build`. Seed a job:
`curl -X POST localhost:8000/jobs -H "Authorization: Bearer <token>" -H 'content-type: application/json' -d '{"source":"greenhouse","company":"Stripe","role":"SWE Intern"}'`. Confirm it appears at `/jobs`, opens at `/jobs/[id]`, and "Create application" navigates to the app detail.

- [ ] **Step 7: Commit**

```bash
git add frontend/hooks/useJobs.ts frontend/components/jobs "frontend/app/(dashboard)/jobs"
git commit -m "feat(frontend): jobs feed, filters, and detail with create-application CTA"
```

---

### Task B6: Applications kanban + table + detail; dashboard overview

**Files:**
- Create: `hooks/useApplications.ts`, `hooks/useDashboard.ts`, `components/applications/{ApplicationKanban,ApplicationTable,TimelineView}.tsx`, `components/dashboard/{StatsGrid,ReplyRateChart,ActivityFeed}.tsx`, `app/(dashboard)/applications/page.tsx`, `applications/[id]/page.tsx`, `app/(dashboard)/dashboard/page.tsx`, `app/(dashboard)/settings/page.tsx`, `hooks/useResumes.ts`
- Test: `tsc --noEmit` + manual end-to-end

**Interfaces:**
- Consumes: `api`, types.
- Produces: `useApplications(status?)`, `useApplication(id)`, `useUpdateApplication()` (PATCH status), `useDashboard()` (`GET /dashboard/stats`), `useResumes()`+`useUploadResume()`; kanban grouped by the 7 statuses with column move via PATCH; table view; detail timeline; dashboard StatsGrid + Recharts ReplyRateChart (status distribution) + ActivityFeed; settings page with resume upload (multipart).

- [ ] **Step 1: Write `hooks/useApplications.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Application, ApplicationStatus } from "@/types";

export function useApplications(status?: ApplicationStatus) {
  return useQuery<Application[]>({
    queryKey: ["applications", status ?? "all"],
    queryFn: async () => (await api.get<Application[]>("/applications", { params: status ? { status } : {} })).data,
  });
}
export function useApplication(id: string) {
  return useQuery<Application>({ queryKey: ["application", id],
    queryFn: async () => (await api.get<Application>(`/applications/${id}`)).data });
}
export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation<Application, Error, { id: string; status: ApplicationStatus }>({
    mutationFn: async ({ id, status }) => (await api.patch<Application>(`/applications/${id}`, { status })).data,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["applications"] }); },
  });
}
```

- [ ] **Step 2: Write `hooks/useDashboard.ts` and `hooks/useResumes.ts`**

```ts
// useDashboard.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";
export function useDashboard() {
  return useQuery<DashboardStats>({ queryKey: ["dashboard"],
    queryFn: async () => (await api.get<DashboardStats>("/dashboard/stats")).data });
}
```
```ts
// useResumes.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Resume } from "@/types";
export function useResumes() {
  return useQuery<Resume[]>({ queryKey: ["resumes"], queryFn: async () => (await api.get<Resume[]>("/resumes")).data });
}
export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation<Resume, Error, File>({
    mutationFn: async (file) => {
      const fd = new FormData(); fd.append("file", file);
      return (await api.post<Resume>("/resumes", fd, { headers: { "Content-Type": "multipart/form-data" } })).data;
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["resumes"] }); },
  });
}
```

- [ ] **Step 3: Write `components/applications/ApplicationTable.tsx` and `TimelineView.tsx`**

```tsx
// ApplicationTable.tsx
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Application } from "@/types";
export function ApplicationTable({ apps }: { apps: Application[] }) {
  return (
    <div className="overflow-x-auto border border-rule-soft">
      <table className="w-full font-mono text-[0.8rem]">
        <thead className="border-b border-ink text-left uppercase tracking-[0.08em]">
          <tr><th className="p-3">Role</th><th className="p-3">Company</th><th className="p-3">Status</th><th className="p-3">Created</th></tr>
        </thead>
        <tbody>
          {apps.map((a) => (
            <tr key={a.id} className="border-b border-rule-soft hover:bg-surface-hover">
              <td className="p-3"><Link href={`/applications/${a.id}`} className="text-blueprint">{a.job.role}</Link></td>
              <td className="p-3">{a.job.company}</td>
              <td className="p-3"><Badge>{a.status}</Badge></td>
              <td className="p-3 text-ink-mute">{new Date(a.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```
```tsx
// TimelineView.tsx
import type { Application } from "@/types";
export function TimelineView({ app }: { app: Application }) {
  const events: { label: string; at: string | null }[] = [
    { label: "Created", at: app.created_at },
    { label: "Sent", at: app.sent_at },
    { label: "Follow-up scheduled", at: app.follow_up_at },
    { label: "Replied", at: app.reply_at },
  ];
  return (
    <ul className="space-y-3">
      {events.filter((e) => e.at).map((e) => (
        <li key={e.label} className="flex items-center gap-3">
          <span className="w-3 h-3 bg-blueprint shrink-0" />
          <span className="font-mono text-[0.8rem]">{e.label}</span>
          <span className="font-mono text-[0.75rem] text-ink-mute">{new Date(e.at as string).toLocaleString()}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: Write `components/applications/ApplicationKanban.tsx`** (columns = 7 statuses; move via PATCH buttons — drag-drop deferred to a later phase to avoid an extra dependency in P1)

```tsx
"use client";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUpdateApplication } from "@/hooks/useApplications";
import type { Application, ApplicationStatus } from "@/types";

const COLUMNS: ApplicationStatus[] = ["pending", "generated", "sent", "opened", "replied", "rejected", "offer"];
const NEXT: Partial<Record<ApplicationStatus, ApplicationStatus>> = {
  pending: "generated", generated: "sent", sent: "opened", opened: "replied",
};

export function ApplicationKanban({ apps }: { apps: Application[] }) {
  const update = useUpdateApplication();
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map((col) => (
        <div key={col} className="min-w-[220px] flex-1">
          <p className="label mb-3">{col} ({apps.filter((a) => a.status === col).length})</p>
          <div className="space-y-3">
            {apps.filter((a) => a.status === col).map((a) => (
              <Card key={a.id} className="shadow-hard">
                <p className="font-mono text-[0.8rem]">{a.job.role}</p>
                <p className="font-mono text-[0.72rem] text-ink-soft">{a.job.company}</p>
                {NEXT[col] && (
                  <Button size="sm" className="mt-3" disabled={update.isPending}
                    onClick={() => update.mutate({ id: a.id, status: NEXT[col] as ApplicationStatus })}>
                    → {NEXT[col]}
                  </Button>
                )}
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Write `app/(dashboard)/applications/page.tsx`** (kanban/table toggle via Radix tabs or simple buttons)

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ApplicationKanban } from "@/components/applications/ApplicationKanban";
import { ApplicationTable } from "@/components/applications/ApplicationTable";
import { useApplications } from "@/hooks/useApplications";

export default function ApplicationsPage() {
  const [view, setView] = useState<"kanban" | "table">("kanban");
  const { data, isLoading, isError } = useApplications();
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl">Applications</h1>
        <div className="flex gap-2">
          <Button size="sm" variant={view === "kanban" ? "primary" : "default"} onClick={() => setView("kanban")}>Kanban</Button>
          <Button size="sm" variant={view === "table" ? "primary" : "default"} onClick={() => setView("table")}>Table</Button>
        </div>
      </div>
      {isLoading && <p className="font-mono text-ink-soft">Loading…</p>}
      {isError && <p className="font-mono text-[var(--warn)]">Failed to load applications.</p>}
      {data && data.length === 0 && <p className="font-mono text-ink-mute">No applications yet — create one from a job.</p>}
      {data && data.length > 0 && (view === "kanban" ? <ApplicationKanban apps={data} /> : <ApplicationTable apps={data} />)}
    </div>
  );
}
```

- [ ] **Step 6: Write `app/(dashboard)/applications/[id]/page.tsx`**

```tsx
"use client";
import { useParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TimelineView } from "@/components/applications/TimelineView";
import { useApplication } from "@/hooks/useApplications";

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: app, isLoading, isError } = useApplication(id);
  if (isLoading) return <p className="font-mono text-ink-soft">Loading…</p>;
  if (isError || !app) return <p className="font-mono text-[var(--warn)]">Application not found.</p>;
  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-3xl">{app.job.role}</h1><Badge>{app.status}</Badge>
      </div>
      <p className="font-mono text-ink-soft mb-6">{app.job.company}</p>
      <Card className="shadow-hard mb-6">
        <p className="label mb-2">Email subject</p>
        <p className="font-body">{app.email_subject ?? "— not generated yet (Phase 2) —"}</p>
        <p className="label mt-4 mb-2">Email body</p>
        <p className="font-body whitespace-pre-wrap">{app.email_body ?? "—"}</p>
      </Card>
      <Card className="shadow-hard">
        <p className="label mb-4">Timeline</p>
        <TimelineView app={app} />
      </Card>
    </div>
  );
}
```

- [ ] **Step 7: Write `components/dashboard/{StatsGrid,ReplyRateChart,ActivityFeed}.tsx`**

```tsx
// StatsGrid.tsx
import { Card } from "@/components/ui/card";
import type { DashboardStats } from "@/types";
export function StatsGrid({ stats }: { stats: DashboardStats }) {
  const cells = [
    { label: "Applications", value: stats.total_applications },
    { label: "Sent", value: stats.by_status["sent"] ?? 0 },
    { label: "Replied", value: stats.by_status["replied"] ?? 0 },
    { label: "Reply rate", value: `${Math.round(stats.reply_rate * 100)}%` },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
      {cells.map((c) => (
        <Card key={c.label} className="shadow-hard">
          <p className="label">{c.label}</p>
          <p className="text-4xl mt-2" style={{ fontFamily: "var(--font-display)" }}>{c.value}</p>
        </Card>
      ))}
    </div>
  );
}
```
```tsx
// ReplyRateChart.tsx
"use client";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Cell } from "recharts";
import type { DashboardStats } from "@/types";
export function ReplyRateChart({ stats }: { stats: DashboardStats }) {
  const data = Object.entries(stats.by_status).map(([status, count]) => ({ status, count }));
  if (data.length === 0) return <p className="font-mono text-ink-mute">No data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <XAxis dataKey="status" tick={{ fontFamily: "var(--font-mono)", fontSize: 11 }} />
        <YAxis allowDecimals={false} tick={{ fontFamily: "var(--font-mono)", fontSize: 11 }} />
        <Bar dataKey="count">{data.map((d) => <Cell key={d.status} fill="var(--blueprint)" />)}</Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```
```tsx
// ActivityFeed.tsx
import Link from "next/link";
import type { Application } from "@/types";
export function ActivityFeed({ apps }: { apps: Application[] }) {
  if (apps.length === 0) return <p className="font-mono text-ink-mute">No recent activity.</p>;
  return (
    <ul className="space-y-3">
      {apps.map((a) => (
        <li key={a.id} className="flex items-center gap-3 border-b border-rule-soft pb-2">
          <span className="w-2 h-2 bg-blueprint shrink-0" />
          <Link href={`/applications/${a.id}`} className="font-mono text-[0.8rem] text-blueprint">{a.job.role}</Link>
          <span className="font-mono text-[0.72rem] text-ink-mute">{a.job.company} · {a.status}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 8: Write `app/(dashboard)/dashboard/page.tsx`**

```tsx
"use client";
import { Card } from "@/components/ui/card";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { ReplyRateChart } from "@/components/dashboard/ReplyRateChart";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { useDashboard } from "@/hooks/useDashboard";

export default function DashboardPage() {
  const { data, isLoading, isError } = useDashboard();
  if (isLoading) return <p className="font-mono text-ink-soft">Loading…</p>;
  if (isError || !data) return <p className="font-mono text-[var(--warn)]">Failed to load dashboard.</p>;
  return (
    <div>
      <h1 className="text-3xl mb-6">Dashboard</h1>
      <StatsGrid stats={data} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-hard"><p className="label mb-4">Status distribution</p><ReplyRateChart stats={data} /></Card>
        <Card className="shadow-hard"><p className="label mb-4">Recent activity</p><ActivityFeed apps={data.recent} /></Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 9: Write `app/(dashboard)/settings/page.tsx`** (resume upload)

```tsx
"use client";
import { useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useResumes, useUploadResume } from "@/hooks/useResumes";

export default function SettingsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: resumes, isLoading } = useResumes();
  const upload = useUploadResume();
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl mb-6">Settings</h1>
      <Card className="shadow-hard">
        <p className="label mb-4">Resume</p>
        <input ref={inputRef} type="file" accept=".pdf,.doc,.docx" hidden
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); }} />
        <Button variant="primary" disabled={upload.isPending} onClick={() => inputRef.current?.click()}>
          {upload.isPending ? "Uploading…" : "Upload resume"}
        </Button>
        {upload.isError && <p className="font-mono text-[0.8rem] text-[var(--warn)] mt-3">Upload failed.</p>}
        <div className="mt-6 space-y-2">
          {isLoading && <p className="font-mono text-ink-soft">Loading…</p>}
          {resumes?.map((r) => (
            <p key={r.id} className="font-mono text-[0.8rem]">{r.filename}
              <span className="text-ink-mute"> · {new Date(r.created_at).toLocaleDateString()}</span></p>
          ))}
          {resumes && resumes.length === 0 && <p className="font-mono text-ink-mute">No resume uploaded.</p>}
        </div>
      </Card>
    </div>
  );
}
```

- [ ] **Step 10: Typecheck + build + manual end-to-end**

Run: `cd frontend && npx tsc --noEmit && npx next build`. Manual: log in → upload resume (Settings) → create application from a job → see it on the kanban → move it to "sent" → confirm dashboard stats update.

- [ ] **Step 11: Commit**

```bash
git add frontend/hooks frontend/components/applications frontend/components/dashboard "frontend/app/(dashboard)"
git commit -m "feat(frontend): applications kanban/table/detail, dashboard overview, settings resume upload"
```

---

### Task B7: Frontend Dockerfile + compose wiring + full-stack smoke test

**Files:**
- Create: `frontend/Dockerfile`, `frontend/.dockerignore`; Modify: `docker-compose.yml`, `frontend/next.config.ts` (standalone output)
- Test: `docker compose up` full stack; signup→dashboard works end-to-end in browser

**Interfaces:**
- Produces: `frontend` service in compose on :3000 talking to backend on :8000; the whole stack boots with one command.

- [ ] **Step 1: Set standalone output in `next.config.ts`**

```ts
import type { NextConfig } from "next";
const nextConfig: NextConfig = { reactStrictMode: true, output: "standalone" };
export default nextConfig;
```

- [ ] **Step 2: Write `frontend/Dockerfile`**

```dockerfile
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 3: Write `frontend/.dockerignore`**

```
node_modules
.next
.env.local
```

- [ ] **Step 4: Add `frontend` service to `docker-compose.yml`**

```yaml
  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports: ["3000:3000"]
    depends_on:
      backend: { condition: service_healthy }
```

> Note: `NEXT_PUBLIC_*` is inlined at build time; for a different API host, rebuild with
> the appropriate value. Document this in the README.

- [ ] **Step 5: Full-stack boot + smoke test**

Run:
```bash
docker compose build
docker compose up -d
sleep 20
curl -f http://localhost:8000/health && echo " ✓ backend"
curl -f http://localhost:3000 >/dev/null && echo " ✓ frontend"
```
Expected: both ✓. In a browser: visit `http://localhost:3000` → redirected to `/dashboard` → `/login`; sign up; land on dashboard; upload a resume; seed a job via curl; create an application; verify it appears. Then `docker compose down`.

- [ ] **Step 6: Commit**

```bash
git add frontend/Dockerfile frontend/.dockerignore frontend/next.config.ts docker-compose.yml
git commit -m "feat(frontend): Dockerfile + compose wiring for full-stack docker-compose up"
```

---

### Task B8: README + Phase 1 verification

**Files:**
- Create: `README.md`
- Test: run the documented quickstart from scratch

**Interfaces:**
- Produces: setup/run docs, ASCII architecture diagram, env var table, risk/compliance section (per design Section 10), and a "Phase 1 scope / what's next" section.

- [ ] **Step 1: Write `README.md`** with: project summary; ASCII architecture diagram (reuse design doc Section 3); prerequisites (Docker, Node 20, Python 3.12); **Quickstart** (`cp .env.example .env`, `docker compose up --build`, open `:3000`); env var table (every var from `.env.example` with description); local dev (backend `uvicorn`, frontend `npm run dev`); running tests (`docker compose run --rm backend pytest tests/ -q`; `cd frontend && npx tsc --noEmit`); **Risk & Compliance** section copied from design Section 10 (LinkedIn ToS, CAN-SPAM/GDPR, ATS auto-submit, third-party API terms); **Phase roadmap** (Phase 1 done; Phases 2–6 upcoming); **External credentials** table from design Section 11.

- [ ] **Step 2: Clean-room verification**

Run:
```bash
docker compose down -v
cp .env.example .env
docker compose up -d --build
sleep 25
curl -f http://localhost:8000/health && curl -f http://localhost:3000 >/dev/null && echo "✓ stack healthy"
docker compose run --rm backend python -m pytest tests/ -q
docker compose down
```
Expected: stack healthy; full backend suite passes.

- [ ] **Step 3: Run final placeholder/secret gates**

Run:
```bash
grep -rn "TODO\|FIXME\|placeholder\|NotImplemented" --include="*.py" --include="*.ts" --include="*.tsx" backend frontend || echo "✓ no TODOs"
grep -rn "sk-ant\|password123\|hardcoded" --include="*.py" --include="*.ts" --include="*.tsx" backend frontend || echo "✓ no secrets"
cd frontend && grep -rn ": any\b\|@ts-ignore" --include="*.ts" --include="*.tsx" . || echo "✓ no any/ts-ignore"
# No hardcoded colors in components: forbid color-baking Tailwind utilities and hex/rgb literals
# outside the single token file (app/globals.css).
grep -rn "text-white\|bg-white\|text-black\|bg-black\|#[0-9a-fA-F]\{3,6\}\|rgb(" \
  --include="*.tsx" --include="*.ts" components app | grep -v "globals.css" \
  || echo "✓ no hardcoded colors outside globals.css"
```
Expected: all four print their ✓ line. (Tailwind color-scale utilities like `text-red-500` are likewise disallowed — only the semantic tokens `bg`, `surface`, `ink*`, `rule*`, `blueprint*`, `accent-hover`, `on-accent`, `warn` may be used.)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README with quickstart, architecture, risk/compliance, roadmap"
```

---

## Self-Review

**1. Spec coverage (design doc → tasks):**
- Docker stack (PG+pgvector/Redis/MinIO/backend/frontend) → A1, A12, B7 ✓
- Migrations + pgvector + indexes + RLS scaffold → A4 ✓
- Models/config/logging → A1, A2, A3 ✓
- JWT auth (signup/login/refresh/me) → A5, A6 ✓
- Storage service + resume upload → A7 ✓
- Jobs CRUD/list/filter → A8 ✓
- Applications CRUD + status transitions → A9 ✓
- Dashboard stats → A10 ✓
- Rate limiting → A11 ✓
- Frontend shell + Blueprint design system → B1, B4 ✓
- Auth pages → B3 ✓; Jobs feed+detail → B5 ✓; Applications kanban/table/detail → B6 ✓; Dashboard overview → B6 ✓; Settings resume upload → B6 ✓
- `lib/api.ts` single client + JWT refresh → B2 ✓
- README + risk docs → B8 ✓
- **Deliberately deferred to later phases (documented):** AI generation (Phase 2), scraping (Phase 3), email/contacts (Phase 4), billing/plan_guard (Phase 5), form filler/feedback (Phase 6), drag-and-drop kanban, Google OAuth login. Plan_guard middleware and `email_accounts`/`follow_ups`/`agent_runs`/`contacts`/`feedback`/`usage_logs` endpoints are not built in P1 — their tables exist (A3) so later phases add routers without migrations.

**2. Placeholder scan:** No "TODO/implement later" in task code. Notes marked with `>` are clarifications, not deferrals of code. The application detail intentionally renders "not generated yet (Phase 2)" as user-facing copy — this is real UI, not a placeholder.

**3. Type consistency:** Backend `ApplicationStatus` enum values match frontend `ApplicationStatus` union and `NEXT`/`COLUMNS` arrays. `JobOut`/`Job`, `ApplicationOut`/`Application`, `DashboardStats` fields align across A8/A9/A10 and B2. `get_storage` dependency name matches between A7 service, router, and conftest override. `?status=` alias fix in A9 keeps the public param name consistent with B6's `useApplications` (`params: { status }`).

**4. Ambiguity check:** RLS in A4 is explicitly the documented Supabase-swap path with API-layer enforcement as the active mechanism (Global Constraints). `NEXT_PUBLIC_API_URL` build-time inlining caveat is called out in B7.

**5. No-hardcoded-color audit:** All component colors use semantic Tailwind tokens (`bg`, `surface`, `ink`, `rule`, `blueprint`, `accent-hover`, `on-accent`, `warn`, `blueprint-tint`) backed by CSS custom properties. Literal color values live only in the `:root`/`[data-theme="dark"]` blocks of `app/globals.css` (B1) — editing those blocks re-themes the entire app. The B8 grep gate enforces this. The primary button uses `text-on-accent` (not `text-white`); chart fills use `var(--blueprint)`; warnings use the `warn` token.
