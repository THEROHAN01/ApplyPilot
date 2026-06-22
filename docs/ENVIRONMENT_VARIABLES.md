# ApplyPilot — Environment Variables

Every environment variable across backend and frontend. The **Phase 1 (live now)**
section reflects the actual fields in `backend/config.py` and the `.env.example` files.
The **AI provider** and **Phase 2+ feature key** sections document variables that the
corresponding phase will add to `config.py` — they are not read yet.

**How config is loaded**
- Backend: `backend/config.py` (pydantic-settings) reads from the process environment and
  an optional `.env`. Field names are lower-case; the env var is the UPPER-CASE form
  (e.g. field `database_url` ← `DATABASE_URL`).
- Under Docker Compose: the `backend` service loads `backend/.env.example` via `env_file:`
  and overrides `DATABASE_URL`/`REDIS_URL`/`S3_ENDPOINT` inline to the in-network hostnames
  (`db`, `redis`, `minio`). There is **no** root `.env` read by Compose.
- Frontend: only `NEXT_PUBLIC_*` vars are exposed to the browser, baked at `next build`.

---

## Phase 1 — live now (in `config.py`)

| Variable | Required | Default | Phase | Description | How to get |
|----------|----------|---------|-------|-------------|------------|
| `APP_ENV` | no | `development` | 1 | Runtime environment (`development`/`production`) | choose |
| `DATABASE_URL` | no* | `postgresql+psycopg2://applypilot:applypilot@db:5432/applypilot` | 1 | SQLAlchemy DSN. In-Docker uses host `db`; for host runs override to `…@localhost:5433/…` | from compose / your PG |
| `REDIS_URL` | no | `redis://redis:6379/0` | 1 | Redis for rate limiter (and Celery broker from Phase 2) | from compose / your Redis |
| `JWT_SECRET` | **prod** | `dev-only-insecure-change-me` | 1 | HS256 signing secret. **Must change for any non-local run.** | `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM` | no | `HS256` | 1 | JWT signing algorithm | fixed |
| `ACCESS_TOKEN_TTL_MIN` | no | `30` | 1 | Access-token lifetime (minutes) | choose |
| `REFRESH_TOKEN_TTL_DAYS` | no | `14` | 1 | Refresh-token lifetime (days) | choose |
| `S3_ENDPOINT` | no | `minio:9000` | 1 | S3/MinIO endpoint (host:port). In-Docker `minio:9000`; host runs `localhost:9000` | from compose |
| `S3_ACCESS_KEY` | no | `minioadmin` | 1 | MinIO/S3 access key | from MinIO |
| `S3_SECRET_KEY` | no | `minioadmin` | 1 | MinIO/S3 secret key | from MinIO |
| `S3_BUCKET` | no | `applypilot` | 1 | Bucket for resumes/artifacts | choose |
| `S3_SECURE` | no | `false` | 1 | `true` to use TLS on the S3 endpoint | choose |
| `FERNET_KEY` | no (Phase 4) | *(empty)* | 4 | Fernet/AES-256 key encrypting OAuth tokens at rest | `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `CORS_ORIGINS` | no | `http://localhost:3000` | 1 | Comma-separated allowed origins | your frontend origin(s) |
| `RATE_LIMIT_PER_MIN` | no | `120` | 1 | Max requests per identity per 60s | choose |

\* `DATABASE_URL` has a working default for Docker; for host-side dev/tests you must set
it to `…@localhost:5433/…` (Postgres is published on host port **5433**).

### Frontend

| Variable | Required | Default | Phase | Description | How to get |
|----------|----------|---------|-------|-------------|------------|
| `NEXT_PUBLIC_API_URL` | no | `http://localhost:8000` | 1 | Backend base URL. **Baked into the image at `next build`** — set as a build arg for non-localhost deploys | your API origin |

---

## AI provider layer (Phase 2 — to be added to `config.py`)

Switching providers is one line: change `AI_PROVIDER`. Only the variables for the
selected provider need to be set.

| Variable | Required | Default | Phase | Description | How to get |
|----------|----------|---------|-------|-------------|------------|
| `AI_PROVIDER` | no | `sarvam` | 2 | Active provider: `sarvam` \| `anthropic` \| `openai` \| `ollama` | choose |
| `SARVAM_API_KEY` | when `sarvam` | — | 2 | Sarvam AI subscription key (`api_subscription_key`) | dashboard.sarvam.ai |
| `SARVAM_MODEL` | no | `sarvam-105b` | 2 | Sarvam model id (`sarvam-105b` or `sarvam-30b`) | choose |
| `ANTHROPIC_API_KEY` | when `anthropic` | — | 6 | Claude API key (vision tasks / form-fill) | console.anthropic.com |
| `ANTHROPIC_MODEL` | no | `claude-sonnet-4-6` | 6 | Anthropic model id | choose |
| `OPENAI_API_KEY` | when `openai` | — | optional | OpenAI key (fallback/comparison provider) | platform.openai.com |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | optional | OpenAI model id | choose |
| `OPENAI_BASE_URL` | no | `https://api.openai.com/v1` | optional | Override for OpenAI-compatible gateways | your gateway |
| `OLLAMA_BASE_URL` | no | `http://localhost:11434` | optional | Local Ollama endpoint (zero data egress dev) | local install |
| `OLLAMA_MODEL` | no | `llama3.1` | optional | Local model id | `ollama pull` |

See `docs/AI_PROVIDER_LAYER.md` for the contract and the add-a-provider guide.

---

## Phase 4–5 feature keys (to be added when the phase lands)

| Variable | Required | Phase | Description | Missing-key behaviour |
|----------|----------|-------|-------------|-----------------------|
| `SERPAPI_KEY` | when contact finder used | 4 | SerpAPI key for recruiter search | disable contact finder |
| `HUNTER_API_KEY` | optional | 4 | Hunter.io email discovery | fall back to pattern guessing |
| `GMAIL_CLIENT_ID` | when Gmail send used | 4 | Google OAuth 2.0 client id | disable email send |
| `GMAIL_CLIENT_SECRET` | when Gmail send used | 4 | Google OAuth 2.0 client secret | disable email send |
| `STRIPE_SECRET_KEY` | when billing enabled | 5 | Stripe secret key | disable billing endpoints |
| `STRIPE_WEBHOOK_SECRET` | when billing enabled | 5 | Stripe webhook signing secret | reject webhooks |

All missing **optional** keys return `503 {"error":"feature_unavailable","reason":"api_key_not_configured"}` — never a crash.

---

## Minimum to run Phase 1

Nothing. `docker compose up` works with the committed defaults and no secrets. For a
non-local deploy, set at least: a strong `JWT_SECRET`, real `DATABASE_URL`/`REDIS_URL`,
real S3 credentials, and a correct `NEXT_PUBLIC_API_URL` (build arg) + `CORS_ORIGINS`.
