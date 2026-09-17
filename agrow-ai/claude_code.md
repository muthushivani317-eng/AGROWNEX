# AgrowAI — Production Hardening & Upgrade Prompt (for Claude Code)

Copy everything below this line into Claude Code, run from the repo root
(the folder containing `backend/` and `agrow-ai/`).

---

You are the senior engineer on AgrowAI — an AI agricultural assistant for
small farmers in South Tamil Nadu (Tamil-first, distributed via KVK
Thoothukudi). The repo has a FastAPI backend (`backend/`, Python 3.12+,
Postgres+PostGIS, Redis, Firebase auth, Alembic, ~21 modules following a
router → service → repository → provider pattern with Protocol-based
provider seams) and an Expo React Native app (`agrow-ai/`, expo-router,
i18next with ta/en locales, zustand, react-query).

Your mission: raise this codebase from "strong foundation with gaps" to
genuinely production-grade — the kind of code that scores 9+/10 on an
independent engineering review because it IS 9+/10, not because it looks
like it. Work in the phases below, IN ORDER. After each phase: run
`pytest backend/tests -q`, fix anything you broke, write new tests for
what you added, and commit with a clear message before moving on.

## Non-negotiable product rules (never violate, enforce in code and prompts)
1. Never recommend commercial pesticide brands; always warn about banned
   pesticides (maintain the banned list in one constants file).
2. If the AI is not confident, it says so (`needs_expert_review=true`,
   lowered confidence). Never fabricate a diagnosis, price, or forecast.
3. Tamil-first: every farmer-facing string exists in `ta` and `en`;
   Tamil is the default.
4. Farmer photos and data belong to the farmer: no third-party sharing,
   signed URLs for images, deletion endpoint must actually delete.
5. Mock providers must always self-identify (`provider="mock"`,
   `is_sample=true`) and must never be selectable when
   `ENVIRONMENT=production` — add a startup guard that refuses to boot
   production with any mock provider active unless explicitly
   allow-listed via `ALLOW_MOCK_PROVIDERS`.

## PHASE 1 — AI model routing & cost control (Pro for vision, Flash for chat)
- In `backend/app/modules/ai/` and `backend/app/modules/disease/`:
  introduce per-task model selection. Disease image diagnosis stays on
  `gemini-2.5-pro` (env `GEMINI_VISION_MODEL`). Conversational chat moves
  to `gemini-2.5-flash` (env `GEMINI_CHAT_MODEL`). Keep the existing
  provider Protocol; just parameterize model per call site. Do not
  hardcode — everything via env with sane defaults.
- Add automatic fallback: if Flash returns an empty/unparseable response
  twice, retry once on Pro, log the escalation.
- Add a `token_usage` table (migration) recording per-request: farmer_id,
  module, model, input/output tokens, latency_ms, and estimated cost in
  INR (cost table in constants, env-overridable). Expose an admin
  endpoint `/api/v1/admin/ai-costs` with daily/weekly aggregates per
  model and per module.
- Add Redis response caching for idempotent AI-adjacent reads (weather
  bundles, market prices) with sensible TTLs; never cache disease
  diagnoses or personalized chat.
- Tests: model-routing unit tests, fallback test, cost-recording test.

## PHASE 2 — Security & abuse protection
- Implement real rate limiting as ASGI middleware backed by Redis
  (sliding window). Use the existing `rate_limit_default` and
  `rate_limit_auth` settings in `app/core/config.py`, plus a stricter
  per-farmer daily quota for AI endpoints (`AI_DAILY_QUOTA`, default 30
  disease scans + 100 chat messages/day) so one script can't drain the
  Gemini budget. Return 429 with a Tamil+English error body.
- Production config hardening in `app/core/config.py`: when
  `is_production` — `debug` forced False, `cors_origins` must be an
  explicit list (boot failure if `*`), docs/openapi URLs disabled unless
  `EXPOSE_DOCS=true`, `session_secret` must not equal the dev default
  (boot failure otherwise).
- Add security headers middleware (HSTS, X-Content-Type-Options,
  X-Frame-Options), request-ID middleware, and body-size limits
  (reject >8MB uploads before reading into memory).
- Wire a real SMS OTP provider behind the existing auth seam: implement
  `MSG91Provider` (env-configured) alongside the mock; template the OTP
  message in Tamil. Keep OTP hashing/pepper logic as-is.
- Tests: rate-limit middleware tests, production-boot-guard tests, OTP
  provider selection tests (mock the HTTP layer, no real network).

## PHASE 3 — Scalability & reliability
- Add a background worker using ARQ (Redis-based, async, lightweight):
  jobs for (a) weather alert evaluation per registered farm on a
  schedule, (b) market price refresh, (c) notification dispatch retries.
  Include the worker in `docker-compose.yml` as a separate service.
- Replace the mock notification provider default with a real
  `FCMProvider` (Firebase Cloud Messaging via the already-initialised
  Admin SDK) selected by `NOTIFICATION_PROVIDER=fcm`. Store device push
  tokens (new migration + endpoint `POST /api/v1/notifications/devices`).
  Notification content localized ta/en.
- Database: add missing indexes for the hottest query paths (farmer_id +
  created_at on reports/chats/notifications; geo index on farm
  locations). Add Alembic migration. Add connection-pool settings
  (pool_size, max_overflow) to config.
- Add `/healthz` (liveness) and `/readyz` (checks DB + Redis) endpoints.
- Graceful timeouts: global httpx client factory with shared limits
  instead of creating a new AsyncClient per request in
  `ai/provider.py` and `disease/vision.py`.
- Tests: worker job unit tests (pure logic extracted), readiness probe
  test, FCM provider selection test.

## PHASE 4 — Observability & operations
- Integrate structured JSON logging in production (keep human-readable
  in dev) and Sentry (env `SENTRY_DSN`, no-op when unset). Never log
  tokens, OTPs, phone numbers in full, or image bytes.
- Add Prometheus metrics endpoint `/metrics` (request latency histogram
  per route, AI call counter per model, error counter). Guard behind an
  internal token.
- Add a GitHub Actions CI workflow: ruff, mypy (tolerate gradual
  typing), pytest with coverage gate ≥85% on `backend/app`, and a
  frontend job running `tsc --noEmit` and jest. CI must pass.
- Write `backend/RUNBOOK.md`: deploy steps, env var reference (every
  variable, its default, and whether required in production), rollback,
  and "what to do when Gemini is down" (the app degrades to honest
  unavailability messages in Tamil — verify this path works and test it).

## PHASE 5 — Product vision alignment (make the claims true)
- Tamil voice input in the app: add `expo-av` recording in the AI chat
  screen (`agrow-ai/features/ai/`), upload audio to a new backend
  endpoint `POST /api/v1/ai/voice` which transcribes via a provider seam
  (`STTProvider` Protocol: `SarvamSTTProvider` for Tamil, plus mock),
  then routes the transcript through the existing chat service. Reply is
  shown as Tamil text; add optional TTS playback behind the same seam
  pattern (`TTSProvider`). All env-configured, mock by default in dev.
- Update the disease result screen to always surface: confidence,
  `needs_expert_review` banner (with a "consult expert" deep link to the
  experts module), and the banned-pesticide warning styling.
- Add an in-app "offline notice + retry queue" for disease photo uploads
  (queue in MMKV, flush on reconnect) — farmers have patchy networks.
- Audit `docs/` so every claim matches reality: mark satellite, soil,
  nutrient, schemes, experts-marketplace as "provider seam ready, not
  yet live" wherever they're described. Honesty is a feature.
- Add `README.md` at repo root: what's live, what's seam-only,
  architecture diagram (mermaid), quickstart, and the five product rules
  above. External reviewers read the README first — it must be accurate,
  specific, and complete.

## PHASE 6 — Final quality pass
- Delete `__pycache__`, `.venv`, `.expo`, `dist`, and the duplicated
  `agrow-ai/docker/` backend copy from version control; add/extend
  `.gitignore`.
- Normalize `repositories.py` vs `repository.py` naming (pick one,
  update imports).
- Run ruff + mypy across backend; fix findings. Run `tsc --noEmit` on
  the frontend; fix findings.
- Ensure `pytest backend/tests -q` passes 100% and coverage ≥85%.
- Produce `UPGRADE_REPORT.md` summarizing every change, the before/after
  on each dimension (AI architecture, security, scalability,
  observability, product honesty), and remaining known gaps with owners.

Work autonomously through all phases. Prefer small, reviewed commits per
phase. Never introduce a hardcoded secret. Never let a mock reach
production silently. When a decision is ambiguous, choose the option
that best protects a farmer's crop, money, and data — in that order.