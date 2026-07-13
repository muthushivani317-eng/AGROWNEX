# 🚀 AgrowAI Backend (FastAPI)

Foundation skeleton for the AgrowAI API. Implements the production architecture
from `../agrow-ai/docs/BACKEND_ARCHITECTURE.md`, `API_CONTRACT.md`,
`DATABASE_SCHEMA.md`, and `SECURITY.md` — **no business features yet**.

## Stack

FastAPI · Python 3.12+ · SQLAlchemy 2 (async) · PostgreSQL + PostGIS · Redis ·
Alembic · Firebase Admin (JWT) · Docker.

## What's in this skeleton

- **Layered clean architecture** — `API → Service → Repository → DB`. Routes
  never run SQL; repositories never call AI.
- **Standard envelope** — every response matches `API_CONTRACT.md`
  (`{ success, message, data, timestamp, request_id }`) via `schemas/response.py`
  and the global handlers in `api/errors.py`.
- **Config & logging** — env-driven `core/config.py`, structured `core/logging.py`
  (never logs secrets/OTP).
- **Auth** — Firebase ID-token verification (`core/security.py`), a working
  `users` domain (model → repository → service → router) with `/auth/login`,
  `/auth/profile`, `/auth/logout`, and DI in `modules/auth/dependencies.py`.
- **Database** — async engine/session (`core/database.py`), base mixins (UUID PK,
  timestamps, soft delete), Alembic migrations (initial `users` table).
- **Health** — `/api/v1/health` (liveness) and `/api/v1/health/ready` (DB check).
- **Ops** — `docker-compose.yml` (Postgres+PostGIS, Redis, API), `Dockerfile`,
  `pyproject.toml` (ruff + black), tests.

## Structure

```
app/
  core/        config · database · logging · security · exceptions
  schemas/     response envelope
  shared/      base_model (mixins) · base_repository
  api/
    errors.py  global exception handlers
    v1/        router · health
  modules/
    auth/      models · schemas · repository · service · dependencies · router
  main.py      app factory
migrations/    alembic env + versions
tests/         smoke tests
```

## Getting started

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env

# With Docker (Postgres + Redis + API):
docker compose up --build

# Or run the API directly (needs a reachable Postgres):
alembic upgrade head
uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs

## Quality

```bash
ruff check app
black --check app
pytest
```

## Next

Feature phases add the remaining domain modules (farmer, farm, crop, disease,
weather, market, schemes, produce, notifications, AI router) — each following
the same module layout and the schema in `DATABASE_SCHEMA.md`.
