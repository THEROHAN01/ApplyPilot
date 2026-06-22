# ApplyPilot — Database Schema

PostgreSQL 16 with the **pgvector** extension. Ten tables, defined as SQLAlchemy 2.0
declarative models under `backend/models/` and created by the single migration
`backend/alembic/versions/001_initial.py`. This document is generated from the actual
model modules.

**Global conventions**
- Every primary key is `id UUID` (default `uuid4()`, generated app-side).
- All `created_at` / `*_at` columns are `TIMESTAMP WITH TIME ZONE`. `created_at` defaults to `now()` server-side.
- All foreign keys to `users.id` / `jobs.id` / `applications.id` use `ON DELETE CASCADE`.
- Embedding columns are **`vector(1024)`** (pgvector) — sized for `BAAI/bge-large-en-v1.5`. **NULL throughout Phase 1**; populated in Phase 2/3.
- Tenant isolation is enforced at the API layer (`WHERE user_id = current_user.id`). RLS policies exist but are inert without Supabase roles (Section "RLS" below).

---

## Enums (Postgres named types)

| Type name | Values |
|-----------|--------|
| `plan_tier` | `free`, `pro`, `unlimited` |
| `application_status` | `pending`, `generated`, `sent`, `opened`, `replied`, `rejected`, `offer` |
| `email_provider` | `gmail`, `outlook` |
| `agent_run_status` | `queued`, `running`, `done`, `failed` |

---

## `users`
The application user with self-contained auth credentials and plan tier.

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `email` | varchar(320) | no | — | **unique**, indexed |
| `name` | varchar(200) | yes | — | |
| `avatar_url` | varchar(1000) | yes | — | |
| `password_hash` | varchar(255) | yes | — | bcrypt; nullable to allow future OAuth-only users |
| `plan` | `plan_tier` | no | `free` | |
| `stripe_customer_id` | varchar(255) | yes | — | set in Phase 5 |
| `created_at` | timestamptz | no | `now()` | |

- **Indexes:** PK on `id`; unique index on `email`.
- **Relationships:** has_many `resumes` (cascade delete-orphan), has_many `applications` (cascade delete-orphan).

## `resumes`
Uploaded resume file plus (future) parsed text and embedding.

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `filename` | varchar(500) | no | — | original upload name |
| `storage_url` | varchar(1000) | no | — | MinIO object URL |
| `storage_key` | varchar(1000) | yes | — | object key (used for deletion) |
| `parsed_text` | text | yes | — | NULL in Phase 1 (Phase 2 parsing) |
| `embedding` | **vector(1024)** | yes | — | NULL in Phase 1 |
| `created_at` | timestamptz | no | `now()` | |

- **Indexes:** PK; btree on `user_id`; **IVFFlat** `ix_resumes_embedding` on `embedding` (`vector_cosine_ops`, lists=100).
- **Relationships:** belongs_to `user`.

## `jobs`
A job posting. **Global** (no `user_id`) — shared across users.

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `source` | varchar(50) | no | — | board id, e.g. `greenhouse` |
| `company` | varchar(300) | no | — | |
| `role` | varchar(300) | no | — | |
| `jd_url` | varchar(1000) | yes | — | |
| `jd_text` | text | yes | — | |
| `jd_embedding` | **vector(1024)** | yes | — | NULL in Phase 1 |
| `location` | varchar(300) | yes | — | |
| `salary_range` | varchar(120) | yes | — | |
| `match_score` | float | yes | — | cosine match vs resume; NULL until Phase 2 |
| `posted_at` | timestamptz | yes | — | part of dedup key |
| `scraped_at` | timestamptz | no | `now()` | list ordering key |
| `status` | varchar(30) | no | `active` | free-form lifecycle string |

- **Indexes:** PK; **unique** `uq_job_dedup` on `(company, role, posted_at)`; **IVFFlat** `ix_jobs_jd_embedding` on `jd_embedding` (`vector_cosine_ops`, lists=100).
- **Relationships:** referenced by `applications` (no back-relationship declared on `Job`).
- **Note:** rows with NULL `posted_at` are not deduped (NULLs are distinct in a unique index).

## `applications`
A user's outreach/application for a specific job. The CRM's core record.

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `job_id` | UUID | no | — | FK → `jobs.id` (CASCADE), indexed |
| `status` | `application_status` | no | `pending` | |
| `email_subject` | varchar(500) | yes | — | filled by generator (Phase 2) |
| `email_body` | text | yes | — | |
| `cover_letter` | text | yes | — | |
| `linkedin_msg` | text | yes | — | |
| `recruiter_email` | varchar(320) | yes | — | from contact finder (Phase 4) |
| `recruiter_linkedin` | varchar(1000) | yes | — | |
| `sent_at` | timestamptz | yes | — | |
| `follow_up_at` | timestamptz | yes | — | |
| `reply_at` | timestamptz | yes | — | |
| `created_at` | timestamptz | no | `now()` | |

- **Indexes:** PK; btree on `user_id` and `job_id`; composite `ix_applications_user_status` on `(user_id, status)`.
- **Relationships:** belongs_to `user` (back_populates `applications`); belongs_to `job` (`lazy="selectin"`, eager-loaded for `ApplicationOut`).

## `contacts`
A discovered recruiter / hiring-manager contact. *(Model only — no router until Phase 4.)*

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `company` | varchar(300) | no | — | |
| `name` | varchar(200) | yes | — | |
| `title` | varchar(300) | yes | — | |
| `email` | varchar(320) | yes | — | |
| `linkedin_url` | varchar(1000) | yes | — | |
| `source` | varchar(100) | yes | — | discovery source |
| `verified` | boolean | no | `false` | SMTP-handshake verified |
| `created_at` | timestamptz | no | `now()` | |

- **Indexes:** PK; btree on `user_id`.

## `email_accounts`
OAuth-connected sending account; tokens stored encrypted (Fernet/AES-256). *(Model only — Phase 4.)*

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `provider` | `email_provider` | no | — | `gmail` / `outlook` |
| `access_token_enc` | text | yes | — | Fernet-encrypted at rest |
| `refresh_token_enc` | text | yes | — | Fernet-encrypted at rest |
| `email_address` | varchar(320) | no | — | |
| `connected_at` | timestamptz | no | `now()` | |

- **Indexes:** PK; btree on `user_id`.

## `follow_ups`
A scheduled or sent follow-up message for an application. *(Model only — Phase 4.)*

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `application_id` | UUID | no | — | FK → `applications.id` (CASCADE), indexed |
| `scheduled_at` | timestamptz | yes | — | |
| `sent_at` | timestamptz | yes | — | |
| `body` | text | yes | — | |
| `status` | varchar(30) | no | `scheduled` | |

- **Indexes:** PK; btree on `application_id`.
- **Note:** no direct `user_id` — owner is reached via `application_id`.

## `agent_runs`
A record of an agent / Celery task execution. The async-work ↔ UI contract. *(Model only — Phase 2.)*

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `task_type` | varchar(100) | no | — | e.g. `generate_email`, `scrape_jobs` |
| `status` | `agent_run_status` | no | `queued` | |
| `result_json` | JSONB | yes | — | task output |
| `error` | text | yes | — | failure detail |
| `started_at` | timestamptz | yes | — | |
| `finished_at` | timestamptz | yes | — | |
| `created_at` | timestamptz | no | `now()` | |

- **Indexes:** PK; btree on `user_id`.

## `feedback`
Thumbs rating + notes on a generated email. *(Model only — Phase 6.)*

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `application_id` | UUID | no | — | FK → `applications.id` (CASCADE), indexed |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `rating` | integer | no | — | thumbs up/down encoded as int |
| `notes` | text | yes | — | |
| `created_at` | timestamptz | no | `now()` | |

- **Indexes:** PK; btree on `application_id` and `user_id`.

## `usage_logs`
Per-user monthly action counters for plan enforcement / metering. *(Model only — Phase 5.)*

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | UUID | no | `uuid4` | PK |
| `user_id` | UUID | no | — | FK → `users.id` (CASCADE), indexed |
| `action` | varchar(100) | no | — | e.g. `generate`, `send` |
| `count` | integer | no | `0` | |
| `month_year` | varchar(7) | no | — | `YYYY-MM` bucket |

- **Indexes:** PK; btree on `user_id`.

---

## Index summary

| Index | Table | Definition |
|-------|-------|------------|
| (PK) | all | `id` |
| `users.email` unique | users | unique on `email` |
| `uq_job_dedup` | jobs | unique `(company, role, posted_at)` |
| `ix_resumes_embedding` | resumes | IVFFlat `embedding` `vector_cosine_ops` lists=100 |
| `ix_jobs_jd_embedding` | jobs | IVFFlat `jd_embedding` `vector_cosine_ops` lists=100 |
| `ix_applications_user_status` | applications | btree `(user_id, status)` |
| FK btree | resumes, applications, contacts, email_accounts, follow_ups, agent_runs, feedback, usage_logs | `user_id` / `application_id` / `job_id` |

> IVFFlat indexes only accelerate ANN search once rows have non-NULL embeddings
> (Phase 2/3). They are created up front so no migration is needed when embeddings arrive.

---

## Row-Level Security (RLS) — Supabase-swap path

`001_initial.py` enables RLS on all user-owned tables and creates an owner policy keyed
on a Postgres GUC, so the schema is ready to drop behind Supabase auth without a rewrite:

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
CREATE POLICY <table>_owner ON <table>
  USING (user_id::text = current_setting('app.current_user_id', true));
```

- Applied to: `resumes`, `jobs`, `applications`, `contacts`, `email_accounts`, `follow_ups`, `agent_runs`, `feedback`, `usage_logs`.
- **`follow_ups`** and **`jobs`** get RLS *enabled* but **no owner policy**: `follow_ups`
  has no `user_id` (filter via `application_id`), and `jobs` is global (no per-user owner).
  A permissive SELECT policy must be added for `jobs` if RLS is ever enforced.
- **Inert today:** without a Supabase auth role setting `app.current_user_id`, these
  policies do not restrict the app's DB role. The **active** isolation mechanism in this
  build is API-layer `user_id` filtering. Do not rely on RLS for tenancy in Phase 1.
