# AgrowAI — Production Hardening Upgrade Report

_Senior-engineer pass against the instruction files in `agrow-ai/`._

## 0. Headline results

| Check | Before | After |
|-------|--------|-------|
| Backend `pytest backend/tests -q` | 514 passed | **559 passed** (+45) |
| Backend `ruff check app` | clean | **clean** |
| Mobile `npx tsc --noEmit` | clean | **clean** (untouched) |
| Mobile `npx jest` | 440 passed | **440 passed** (untouched) |

Work was committed phase-by-phase (backend commits in the root repo;
`agrow-ai/` is its own git repo — see §6). No secrets were hardcoded; no mock
provider can reach production silently; product rules were enforced, not bypassed.

## 1. Instruction reconciliation & merged plan

The task referenced **three** instruction files; only **two** exist:
`claude_code.md` (backend, Phases 1–6) and `claude_code_3.md` (mobile, Phases
A–F). **`claude_code_2.md` is absent** — see Blockers (§3). A third authoritative
source, `agrow-ai/CLAUDE.md` + `agrow-ai/docs/`, was also honored.

Merged, de-duplicated execution order (per the task's ordering rule — backend
security & AI first, then scalability/observability, then mobile, then QA):

1. **Group 1** — AI routing/cost (P1) + security (P2)  ✅ done
2. **Group 2** — scalability (P3) + observability (P4)  ✅ P4 done, P3 partial
3. **Group 3** — product & mobile (P5 + A–F)  ◐ documentation + honesty done; app UX deferred
4. **Group 4** — final QA (P6)  ◐ lint/tests green; cleanup partial

De-duplications applied: voice STT/TTS (P5 backend + Phase B) → one seam;
offline disease queue (P5 + Phase C) → once; Sentry (P4 backend + Phase F
frontend) → distinct targets; account deletion, notification deep-links,
mock-in-prod guard, README → once each.

## 2. Conflicts found & resolved (more-specific/later wins)

| Conflict | Resolution |
|----------|------------|
| Task says 3 files; 2 exist | Proceeded with the 2 present; `claude_code_2.md` documented as blocked. |
| `CLAUDE.md` "ChatGPT for reasoning / never Claude as app AI" & "Gemini 2.5 Pro" vs `claude_code.md` "chat → gemini-2.5-flash" | **Flash for chat, Pro for vision** — `AI_DECISION_MATRIX.md` already endorses it and the code cites it. No ChatGPT/Claude app dependency introduced. |
| `CLAUDE.md` lists **AWS S3** vs its own success-list + `.env.example` **Cloudflare R2** | **Cloudflare R2** (later/more-specific; matches finalized stack). |
| Phase ordering (`claude_code.md` 1–6 vs task's "security & AI first") | Task ordering; happens to match 1→2→3→4. |
| P3 "geo index on farm locations" vs actual GeoJSON-in-JSON storage | No PostGIS GiST applies; used the correct `(latitude, longitude)` composite index and noted it. |

## 3. Blockers & how they were handled

- **`claude_code_2.md` missing** — cannot execute unreadable instructions; its
  (likely backend/mobile) slice is unaddressed by definition. Recorded, not
  silently skipped.
- **Not a git repository** — required per-phase commits. Resolved by
  `git init` + a root `.gitignore` (excludes `node_modules`, `.venv`, `.expo`,
  `dist`, `__pycache__`), then a commit per phase. Discovered `agrow-ai/` is its
  **own** embedded git repo, so backend phases commit at root and mobile changes
  would commit inside `agrow-ai/`.
- **MSG91 vs Firebase OTP** — the spec says wire MSG91 "behind the existing auth
  seam… keep OTP hashing/pepper as-is," but the codebase delegates OTP *code
  generation* to Firebase on-device (backend row is audit/throttle, `otp_hash=None`).
  There is no server-side OTP-send seam to slot into. **Closest correct
  alternative implemented**: a tested `SMSProvider` seam with `MSG91Provider`
  (Tamil template, HTTP-mocked) + `MockSMSProvider` default, env-selected, with a
  missing key falling back to mock (never a silent fake send). Wiring it live
  needs server-side code generation + hashing (a larger change from the Firebase
  model) — deferred, see §5.

## 4. What was done, per phase

### Phase 1 — AI routing & cost control (commit `2d10a9a`)
Routing (Pro=vision, Flash=chat, env-driven), Flash→Pro fallback, and the INR
cost table already existed. **Added**: `token_usage` table (migration 0019) +
`TokenUsageRepository`; per-request recording (farmer/module/model/tokens/
latency/estimated INR) wired into the chat and disease-vision pipelines (mock
calls recorded as `is_sample`, 0 cost, never fabricated); `GET
/api/v1/admin/ai-costs` with per-model/per-module + daily/weekly aggregates;
`app/core/cache.py` shared Redis cache seam with graceful degradation, backing
the weather + market caches (`CACHE_BACKEND`). Diagnoses/chat never cached.
**Tests**: routing + fallback, cost recording + aggregation + window, cache.

### Phase 2 — Security & abuse protection (commit `2347df9`)
ASGI middleware: request-id, security headers (HSTS in prod, nosniff, DENY,
Referrer-Policy), 8MB body-size guard (413), Redis sliding-window rate limiter
(in-memory fallback, fails open) → 429 with a Tamil+English envelope, stricter on
`/auth`. Per-farmer daily AI quota (30 scans + 100 chats) via the token_usage
ledger → 429. Production boot guards (`validate_production`): refuse dev secret,
wildcard/empty CORS, or debug on; docs hidden unless `EXPOSE_DOCS`. `auth/sms.py`
MSG91 seam (§3). **Tests**: boot guards, middleware, SMS selection+send, quota.

### Phase 3 — Scalability & reliability (commit `4def63e`, **partial**)
**Done**: `/healthz` + `/readyz` (DB + Redis; 503 when not ready) at root;
DB pool settings (`pool_size`/`max_overflow`/`pool_timeout`); migration 0020 —
`(user_id, created_at)` composite indexes on disease_reports, ai_conversations,
notifications + `(latitude, longitude)` on farm_locations. **Tests**: liveness +
readiness matrix. **Deferred** (§5): ARQ worker, FCM provider + device tokens,
shared httpx client factory.

### Phase 4 — Observability & operations (commit `009230d`)
Structured JSON logs in prod (human-readable dev) with a scrubbing filter
(OTPs, phone middle-digits, Authorization tokens redacted). Optional Sentry
(no-op when unset/absent; `send_default_pii` off). `/metrics` Prometheus endpoint
behind `X-Metrics-Token` (request/error counters, latency sum, per-model AI-call
counter) via a dependency-free registry + middleware. Gemini-down errors made
Tamil-first (honest 503, no fabricated answers; disease writes nothing on
failure). `backend/RUNBOOK.md` (deploy, full env reference, rollback, "Gemini is
down" playbook) and `.github/workflows/ci.yml` (ruff, mypy-gradual,
pytest+coverage≥85, frontend tsc+jest). **Tests**: metrics auth/exposure, scrub,
Sentry no-op.

### Phase 5 / Group 4 — Product honesty & docs (this commit)
Root `README.md`: live-vs-seam table, mermaid architecture, quickstart, the five
product rules. Honest degradation path verified and made bilingual. This report.

## 5. Remaining known gaps (owner: next iteration)

Deferred deliberately — each needs running infrastructure or the full Expo UX
cycle to reach the "IS 9/10, not looks-like-it" bar this pass insisted on. None
were faked.

| Gap | Source | Why deferred |
|-----|--------|--------------|
| ARQ background worker (weather alerts, price refresh, retry dispatch) + compose service | P3 | Needs Redis broker + scheduled-job verification; pure job logic should be extracted and unit-tested first. |
| Real `FCMProvider` + device-token migration/endpoint | P3 | Needs Firebase Admin messaging + a device to verify delivery; provider seam exists (`notifications/provider.py`). |
| Shared httpx client factory | P3 | Optimization touching both AI providers; deferred to protect the green suite. |
| Full server-side MSG91 OTP (code gen + hashing + verify) | P2 | Would replace the working Firebase-on-device flow; seam delivered, live wiring is a larger auth change. |
| Voice STT/TTS backend (`/ai/voice`, Sarvam seam) + mobile mic/read-aloud | P5 / Phase B | New provider seams + audio upload + app recording; multi-day. |
| Mobile Phases A–F (home redesign, onboarding, offline queue, perf, retention, store readiness, in-app deletion UI) | `claude_code_3.md` | Large UX program on an already-working app (tsc clean, 440 jest green); each phase is its own reviewed slice. |
| `docs/` honesty audit annotations; `PERF_REPORT.md`, `BUILD.md`, `store/` | P5 / Phase D/F | Documentation deliverables tied to the mobile phases above. |
| Coverage gate value | P4/P6 | CI enforces `--cov-fail-under=85`; the actual % was not measured locally (pytest-cov not installed) — validate on first CI run and adjust if needed. |
| Repo cleanup (`repositories.py` vs `repository.py` naming; remove duplicated `agrow-ai/docker/`) | P6 | Cross-cutting renames; deferred to avoid churn during the security pass. |

## 6. Commits

```
009230d phase 4: JSON logging + Sentry, /metrics, secret scrubbing, RUNBOOK, CI
4def63e phase 3 (partial): readiness probes, connection pool, hot-path indexes
2347df9 phase 2: rate limiting, production boot guards, security middleware, MSG91 OTP seam
2d10a9a phase 1: AI token-usage ledger, /admin/ai-costs, Redis cache seam
b099be1 chore: baseline snapshot before production-hardening pass
```

## 7. Before/after by dimension

- **AI architecture** — routing existed; now every call is metered into a cost
  ledger with an admin dashboard, quota-protected, and cache-fronted for
  idempotent reads. Gemini-down degrades honestly in Tamil.
- **Security** — from open CORS/no rate limit/no boot guards to sliding-window
  limiting, per-farmer AI quotas, security headers, body-size limits, and a
  production that refuses to boot misconfigured.
- **Scalability** — added readiness probes, connection pooling, and hot-path
  composite indexes (worker + push remain).
- **Observability** — from print-style logs to structured JSON + secret
  scrubbing, `/metrics`, optional Sentry, a RUNBOOK, and CI.
- **Product honesty** — mocks self-identify and are prod-gated; errors are
  bilingual; no fabricated diagnoses/prices; the README states plainly what is
  live vs. seam-only.
