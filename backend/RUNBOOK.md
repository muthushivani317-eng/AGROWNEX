# AgrowAI Backend — Operations Runbook

Operational reference for deploying and running the AgrowAI FastAPI backend
(Python 3.12+, Postgres+PostGIS, Redis). Product rules (Tamil-first, no
fabricated data, farmer data ownership) are enforced in code — see
`docs/PRODUCT_RULES.md` and `UPGRADE_REPORT.md`.

## 1. Deploy

```bash
# 1. Install deps
pip install -r requirements.txt
# 2. Apply DB migrations (idempotent; safe to re-run)
alembic upgrade head
# 3. Boot (production refuses to start on unsafe config — see §5 boot guards)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Containerized: `docker compose up -d` (see `docker-compose.yml`). Run
`alembic upgrade head` as a release step before rolling new pods.

## 2. Health & readiness

| Probe | Path | Meaning |
|-------|------|---------|
| Liveness | `GET /healthz` | Process is up (no dependencies). |
| Readiness | `GET /readyz` | DB reachable; Redis reachable when `CACHE_BACKEND=redis`. 503 = do not route traffic. |
| Metrics | `GET /metrics` | Prometheus text; requires header `X-Metrics-Token: $METRICS_TOKEN`. |

## 3. Environment variables

Required-in-production means the app should not run without a real value; boot
guards (`Settings.validate_production`) hard-fail on the starred ones.

| Variable | Default | Required in prod |
|----------|---------|------------------|
| `ENVIRONMENT` | `development` | yes (`production`) |
| `DEBUG` | `true` | forced `false` in prod |
| `DATABASE_URL` | local asyncpg URL | yes |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT` | `10` / `20` / `30` | tune to load |
| `REDIS_URL` | `redis://localhost:6379/0` | yes if Redis features on |
| `CACHE_BACKEND` | `memory` | `redis` for multi-worker |
| `SESSION_SECRET` | dev default | **yes** ★ (boot fails on dev default) |
| `CORS_ORIGINS` | `["*"]` | **yes** ★ (explicit list; `*` fails boot) |
| `EXPOSE_DOCS` | `false` | optional (docs hidden in prod otherwise) |
| `RATE_LIMIT_DEFAULT` / `RATE_LIMIT_AUTH` / `RATE_LIMIT_WINDOW_SECONDS` | `100` / `10` / `60` | tune |
| `MAX_REQUEST_BODY_BYTES` | `8388608` (8MB) | tune |
| `AI_DAILY_DISEASE_QUOTA` / `AI_DAILY_CHAT_QUOTA` | `30` / `100` | tune |
| `ALLOW_MOCK_PROVIDERS` | `false` | keep `false` in prod |
| `GEMINI_API_KEY` | empty → mock provider | yes (else runs in mock mode) |
| `DATA_GOV_API_KEY` | empty → market provider unavailable | yes (live mandi prices) |
| `GEMINI_VISION_MODEL` / `GEMINI_CHAT_MODEL` | `gemini-2.5-pro` / `gemini-2.5-flash` | optional |
| `COST_*_INR_PER_1K` | published-price approximations | set to real contract |
| `FIREBASE_PROJECT_ID` / `FIREBASE_CREDENTIALS_JSON` | empty | yes (auth) |
| `R2_*` (Cloudflare R2) | empty | yes (image storage) |
| `OTP_PROVIDER` | `mock` | `msg91` for server-side SMS |
| `MSG91_AUTH_KEY` / `MSG91_SENDER_ID` / `MSG91_TEMPLATE_ID` | empty / `AGROAI` / empty | if `OTP_PROVIDER=msg91` |
| `SENTRY_DSN` | empty (no-op) | recommended |
| `LOG_JSON` | unset → JSON in prod | optional |
| `METRICS_TOKEN` | empty (`/metrics` closed) | recommended |

## 4. Rollback

1. Roll application image back to the previous tag.
2. If a migration must be reverted: `alembic downgrade -1` (every migration in
   this repo has a tested `downgrade`). Prefer forward-fixes for data safety.
3. Verify `GET /readyz` returns 200 and `GET /healthz` is 200 on the restored
   version before shifting traffic back.

## 5. Boot guards (production safety)

On startup in `ENVIRONMENT=production`, the app **refuses to boot** if:
- `SESSION_SECRET` is still the dev default,
- `CORS_ORIGINS` is empty or contains `*`,
- `DEBUG` is true.

This is intentional — a misconfigured production must fail loudly, not leak.

## 6. "What to do when Gemini is down"

The app is designed to **degrade to honest unavailability**, never to fabricate:

- Chat: the router tries Flash, escalates to Pro on empty responses, and on a
  hard outage raises `ai_unavailable` (HTTP 503) with a Tamil-first message.
- Disease: raises `disease_analysis_failed` (HTTP 503), Tamil-first; **no image
  is stored and no report is written** when analysis fails.
- No mock answer is silently returned in production (mock providers only run
  when `GEMINI_API_KEY` is unset, and `ALLOW_MOCK_PROVIDERS` gates them).
- Cached idempotent reads (weather/market) keep serving from Redis/last-good.

Operator actions: confirm `GEMINI_API_KEY`/quota with the provider, watch
`agrowai_ai_calls_total` and `agrowai_request_errors_total` in `/metrics`, and
check Sentry for `ai_unavailable` spikes. Farmers see an honest "try again"
message in Tamil; their photos are never lost (client-side retry queue).

## 7. "What to do when market prices are unavailable"

`GET /api/v1/market` returns `503` with error code
`market_data_unavailable` only when the live provider failed and no verified
stored price matches the request. A successful provider response with zero
matching records remains `200` with an empty list. Previously verified database
prices continue to be served and are labelled stale when their publication date
is old.

Operator actions:

1. Confirm `DATA_GOV_API_KEY` is present in the API service. The worker also
   needs the same valid key for scheduled market refresh jobs.
2. Inspect `market.provider` logs for `category`, upstream HTTP `status`,
   `latency_ms`, and attempt number. Logs deliberately exclude the API key,
   query payload, response body, and farmer identifiers.
3. A `401`, `403`, or `429` normally indicates an invalid/revoked key, provider
   permission, quota, or rate-limit problem. Transport errors and `5xx` statuses
   can be retried after the upstream service recovers.
4. After changing the key, redeploy the API and worker, then call a known crop
   and district query. Confirm a `200` response contains verified records before
   closing the incident.

## 8. Tests / CI

```bash
pytest backend/tests -q          # full suite
ruff check backend/app           # lint
```
CI runs ruff, pytest (with coverage), `tsc --noEmit`, and jest — see
`.github/workflows/ci.yml`.
