# AgrowAI — Task Board

## ✅ Phase 0 — Foundation

Status: **Complete**

Project architecture, navigation, theme (DESIGN_SYSTEM), Tamil-first localization,
reusable `Ag*` UI kit, state management (Zustand + React Query), API client,
MMKV + SQLite storage, FastAPI backend skeleton (layered API → service →
repository → DB), and quality gates.

## ✅ Phase 1 — Authentication Module

Status: **Complete**

Frontend

- Branded animated **Splash** + native splash gate.
- **Language selection** (Tamil default) as the first-run step.
- **Onboarding** carousel.
- **Phone OTP login** (Firebase) with resend countdown and validation.
- **Google Sign-In** (expo-auth-session → Firebase credential) with mock fallback.
- **Apple Sign-In** (expo-apple-authentication, hashed nonce) with mock fallback.
- **Secure session**: tokens in encrypted MMKV, user in MMKV.
- **Auto login** on cold start; **token refresh**; **session expiry + idle timeout**
  (`useSessionGuard`); 401 → refresh → retry in the API client.
- **Logout** (clears session + query cache).
- **Authentication guards** (`useProtectedRoute`, entry redirect).
- **Profile setup**: photo picker (`AgAvatar` + expo-image-picker), preferred
  language, name, district, block, village, experience, preferred crops.
- **RBAC prep**: `role` on the user model.

Backend (`/backend`)

- Endpoints (docs/API_CONTRACT.md): `/auth/otp/send`, `/auth/otp/verify`,
  `/auth/google`, `/auth/apple`, `/auth/refresh`, `/auth/profile` (GET + PUT),
  `/auth/profile/details`, `/auth/logout`.
- **Firebase JWT** verification (docs/SECURITY.md); server session management:
  refresh-token rotation (hashed, single-use), user sessions, login history,
  OTP audit + rate-limiting.
- **RBAC** tables seeded (roles/permissions/role_permissions/user_roles); default
  `farmer` role assigned on user creation.
- **Profile** tables (farmer_profiles, farmer_preferences, farmer_languages).
- Repository pattern + service layer + FastAPI DI + Pydantic + SQLAlchemy +
  Alembic migration (`0002_auth_profile_tables`).

Database tables added (auth + profile only): otp_requests, refresh_tokens,
user_sessions, login_history, roles, permissions, role_permissions, user_roles,
farmer_profiles, farmer_preferences, farmer_languages.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 22 passed · `expo export --platform android` bundles.
- Backend: `ruff` clean · `pytest` 20 passed · Alembic revision graph valid.

## ✅ Phase 2 — Farmer Profile Module

Status: **Complete**

Backend (`/backend`, new `app/modules/farmers`)

- Endpoints (docs/API_CONTRACT.md → FARMER MODULE): `/farmers/me` (GET + PUT),
  `/farmers/preferences` (GET + PUT), `/farmers/languages` (GET + PUT).
- Repository → Service → API layering with FastAPI DI; reuses the existing
  `farmer_profiles` / `farmer_preferences` / `farmer_languages` tables and models
  (no new migration). Authentication was not modified — the current-user
  dependency is imported from the auth module.
- `PUT /farmers/me` upserts the profile and seeds the preference + default-language
  rows; `PUT /farmers/preferences` is a partial patch; `PUT /farmers/languages`
  replaces the language set, enforces exactly one default, and syncs the profile's
  primary language. `ProfileNotFoundError` (reused) → 404 when no profile exists.

Frontend (`features/profile`)

- **View Profile** (identity header, location, farming, account entry) with
  loading (skeleton), error+retry, and empty (set-up) states.
- **Edit Profile**: avatar upload, preferred language, district, block, village,
  farming experience, preferred crops — React Hook Form + reused Zod schema.
- **Avatar upload** via a swappable upload service (real AWS S3 when
  `EXPO_PUBLIC_S3_UPLOAD_ENDPOINT` is set, local mock otherwise).
- **Account Settings**: contact, appearance/language (reused toggles), and
  notification / voice / units preferences persisted via `/farmers/preferences`.
- Swappable **profile provider** (`api` ↔ `local`) mirroring the auth provider:
  persists to the encrypted MMKV auth store locally and to the backend when
  configured. Offline edits are saved locally and queued in the SQLite outbox.
- Tamil-first, dark/light, accessible; routes `profile/edit` + `profile/account`.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 32 passed (7 suites).
- Backend: `ruff check` clean · `pytest` 35 passed.

## ✅ Phase 3 — Farm Registration Module

Status: **Complete**

The core spatial module. Multiple farms per farmer, each with GPS location,
GeoJSON boundary, computed area, crop/soil/irrigation attributes, images and
status. Every future module (weather, AI, disease, calendar, market, growth)
builds on this data.

Backend (`/backend`, new `app/modules/farms`)

- Tables (migration `0003_farm_tables`): `farms`, `farm_locations`,
  `farm_boundaries`, `farm_media`. Repository → Service → API layering; the
  current-user dependency is reused from auth (authentication unchanged).
- Endpoints (docs/API_CONTRACT.md → FARM MODULE): `GET/POST /farms`,
  `GET/PUT/DELETE /farms/{id}` (soft delete), `GET/PUT /farms/{id}/boundary`,
  `GET/POST /farms/{id}/images`. Paginated + filterable list (status, district,
  crop, search); ownership-scoped.
- Geometry stored as **GeoJSON** (JSONB on Postgres — PostGIS-compatible via
  `ST_GeomFromGeoJSON`); a geodesic `geo.py` computes area/perimeter/centroid
  server-side, so it works without a live PostGIS/SpatiaLite backend. Validation:
  GPS bounds, polygon (≥3 points, closed, in-range), duplicate farm name (409),
  required fields, manual-area override.

Frontend (`features/farm`)

- **Farm List** (filter chips, pull-to-refresh, empty/loading/error states, FAB),
  **Add/Edit Farm** (RHF + Zod), **Farm Details**, **Boundary Editor**, **Farm
  Gallery**.
- **Mapbox** map via the Static Images API (raster backdrop; grid fallback with
  no token) + an SVG/gesture **polygon editor**: pan-under-crosshair drop points,
  undo/clear, GPS recenter (`expo-location`), live geodesic **area** in ha/acres.
- Swappable **farm provider** (`api` ↔ `local`) mirroring auth/profile. **Offline**:
  local MMKV mirror, an outbox queue, reconnect sync, and last-write-wins
  **conflict resolution**. Reuses the shared image upload service (S3/local) for
  farm photos.
- Routes: `(tabs)/farm`, `farm/new`, `farm/[id]`, `farm/[id]/edit`,
  `farm/[id]/boundary`, `farm/[id]/gallery`. Tamil-first, dark/light, accessible.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 66 passed (14 suites).
- Backend: `ruff check` clean · `pytest` 55 passed.

## ✅ Phase 4 — Weather Intelligence Module

Status: **Complete**

The primary weather data source for the Home Dashboard, AI Chat, Crop Calendar,
Disease Detection and Notifications. Uses each farm's GPS via Open-Meteo
(docs/PRODUCT_RULES.md rule 5).

Backend (`/backend`, new `app/modules/weather`)

- Endpoints (docs/API_CONTRACT.md → WEATHER): `GET /weather` (bundle),
  `GET /weather/current`, `GET /weather/forecast` (24h hourly + 7-day daily),
  `GET /weather/alerts` (insights). Each accepts `farm_id` (coords resolved from
  the farm, ownership-scoped) or explicit `latitude`/`longitude`.
- **Repository → Service → API** with the farm-coordinate lookup reused from the
  farms module (no completed module modified, no new DB table). **Cache layer**
  (in-process TTL, 5 min, coordinate-keyed; Redis-ready). Open-Meteo **client**
  with timeout + bounded **retries**; provider is injectable so the service is
  tested with a fake (no network).
- Pure `parser.py` (current + hourly-24 + daily-7, WMO code → condition) and a
  deterministic, rule-based `insights.py`: irrigation, spraying, heat-stress,
  heavy-rain, wind and field-work advice with transparent thresholds (no runtime
  AI). Insights carry a `code`+`params` for the client to localize, plus English
  text for AI/notifications.

Frontend (`features/weather`)

- **Weather Screen** with **Farm Selector** (switch between the farmer's farms),
  **Weather Card** (current), **metrics** (humidity, wind, UV, rain, sunrise/
  sunset), **Hourly (24h)** and **Weekly (7-day)** forecasts, and **Weather
  Alerts** (localized rule-based insights). Loading/empty/error/offline states;
  prompts to add a location when a farm has no GPS. Route: `/weather`.
- Swappable **weather provider** (`api` ↔ deterministic mock) + **offline MMKV
  cache** fallback; React Query **background refresh** (interval + on-reconnect),
  5-min stale time matching the backend cache. Tamil-first, dark/light, accessible.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 73 passed (17 suites).
- Backend: `ruff check` clean · `pytest` 70 passed.

## ✅ Phase 5 — Home Dashboard Module

Status: **Complete**

The primary post-login screen. Frontend-only — it composes the existing Auth,
Farm and Weather modules (no backend changes; no completed module modified).

Frontend (`features/home`)

- **Top section**: greeting + farmer name + **live clock** + avatar, with a
  **quick farm switcher** (reuses the weather `FarmSelector`; the selected farm is
  shared with the Weather screen via the persisted selection).
- **Weather widget** (reuses the Weather module): temperature, condition, rain
  probability, top **today's advice** insight, and an **alert badge**; taps
  through to the Weather screen. Prompts to add a location when the farm has none.
- **Today's farm** card (crop, area, growth-stage placeholder until Growth
  Monitor, last-updated) → Farm Details.
- **Today's tasks**: deterministic **rule-based** checklist derived from the
  weather insights + a weekday rotation (irrigate, inspect, spray delay, weed,
  fertilizer, drainage, heat) with local check-off.
- **Quick actions**: AI Assistant, Disease Detection, Add Farm, Market Prices,
  Sell Produce (unbuilt targets show "coming soon").
- **Recent activity** derived from real data only (recent farms, profile setup,
  active weather alert) with relative timestamps — no fabricated events.
- **Offline**: cached farm + weather data via the existing MMKV caches; React
  Query **background refresh** + pull-to-refresh; **skeleton** loading and retry.
- Tamil-first, dark/light, accessible; premium staggered entering animations
  (UI-thread Reanimated). Rendered by the existing home tab (`(tabs)/index`).

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 86 passed (20 suites).
- Backend: `ruff check` clean · `pytest` 70 passed (unchanged).

## ✅ Phase 6 — AI Chat Module

Status: **Complete**

A conversational farming assistant. Single AI provider: **Google Gemini 2.5 Pro**
(finalized stack; supersedes the docs' ChatGPT references). Tamil-first,
context-aware and safety-validated.

Backend (`/backend`, new `app/modules/ai`)

- Tables (migration `0004_ai_chat_tables`): `ai_conversations`, `ai_messages`
  (user-scoped; optional `farm_id`). Repository → Service → API; the current-user
  dependency is reused from auth (no completed module modified).
- Endpoints (docs/API_CONTRACT.md → AI CHAT): `POST /ai/chat`, `GET /ai/history`
  (paginated), `GET /ai/history/{id}`, `DELETE /ai/history/{id}` (soft delete).
  (Voice/image chat are deferred to their own modules.)
- **AI router pipeline** (docs/AI_DECISION_MATRIX, AI_PROMPTS): context/farm-memory
  builder (reuses profile + farm, best-effort weather) → system prompt (safety +
  Tamil-first + response format) → **Gemini** provider → response validator →
  persist. Provider is an injectable `GeminiClient` (httpx REST + retries) with a
  deterministic **mock** when no `GEMINI_API_KEY`; tested with a fake (no network).
  API keys stay server-side (docs/SECURITY.md).

Frontend (`features/ai`)

- **Chat screen** (AI tab): message list with farmer/assistant bubbles, animated
  **typing indicator**, starter **suggestion chips**, docked composer, new-chat +
  history actions. **History screen** (`/ai/history`) with open/delete.
- Swappable **AI provider** (`api` ↔ local): the local provider persists
  conversations in MMKV and answers with the deterministic mock, so the assistant
  and history **work offline / in dev** without a backend or key.
- Reuses the persisted **farm selection** for context and the current language for
  replies. Tamil-first, dark/light, accessible; `KeyboardAvoidingView` composer.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 95 passed (23 suites).
- Backend: `ruff check` clean · `pytest` 84 passed.

## ✅ Phase 7 — Disease Detection Module

Status: **Complete**

> **Current architecture (supersedes the original Phase 7 implementation):** the
> unrestricted Gemini disease-analysis route was removed on July 31, 2026. Gemini
> may identify a crop/plant, but must not diagnose disease or generate treatment.
> Disease diagnosis is fail-closed: the six supported crops use their dedicated
> ONNX/PyTorch classifiers, and accepted results obtain guidance only from the
> verified disease registry. Unsupported crops return a clear not-supported result.

Backend (`/backend`, new `app/modules/disease`)

- Table (migration `0005_disease_reports`): consolidated, user/farm-scoped
  `disease_reports` history. Current diagnoses are persisted by the crop-specific
  services with explicit TEST MODE markers where required.
- Pipeline: photo quality gate → six-class crop identification → farmer
  confirmation → crop-specific classifier → confidence/abstention policy →
  verified-registry guidance. No generative fallback exists.
- Active families: Banana V3; legacy-joint paddy/cotton/groundnut; restricted
  Chilli/Redgram. History endpoints remain `GET /disease/history`,
  `GET /disease/{id}`, and `DELETE /disease/{id}`.

Frontend (`features/disease`)

- **Detect** screen (camera + gallery via `expo-image-picker`), **client-side
  quality pre-check** with localized guidance before upload, analyzing state;
  **Detail** screen (image, crop+confidence, disease, severity, expert-review flag,
  confidence meter, symptoms/causes/actions/prevention, Tamil explanation, weather
  snapshot); **History** screen.
- The unified photo-first flow is reachable from the Home "Disease Detection"
  quick action and fails closed when the crop or disease class is unsupported.
  Tamil-first, dark/light, accessible; loading / skeleton / error states.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 107 passed (26 suites).
- Backend: `ruff check` clean · `pytest` 103 passed.

## ✅ Phase 8 — Crop Calendar Module

Status: **Complete**

Deterministic, **rule-based** farming schedule (no AI in V1) generated from each
farm's crop, sowing date, season (derived) and irrigation type. At read time it
**reuses the Weather module's insights** to annotate tasks with advisories (delay
irrigation on heavy rain, delay spraying on strong wind, recommend irrigation in
extreme heat) — no weather logic is duplicated. Generation is behind a provider
seam so future AI can adjust schedules with no frontend change.

Backend (`/backend`, new `app/modules/calendar`)

- Table (migration `0006_crop_calendar_events`): `crop_calendar_events`
  (user/farm-scoped, reserved `crop_session_id`; stores code, activity type,
  title/description, scheduled date, priority, status, growth stage, weather
  dependency, reminder metadata). Repository → Service → API; reuses auth's
  current-user, the **farm repository** (ownership) and the **weather service**.
- Deterministic core: `schedules.py` (predefined per-crop templates covering all
  12 activity types — generic + paddy), pure `generator.py` (dates each activity
  from the sowing date; rainfed farms de-emphasise irrigation tasks; season
  derived from the sowing month), pure `weather_adjuster.py` (maps reused weather
  insight codes → advisory per task). Regeneration replaces the pending plan but
  keeps completed history. Endpoints (docs/API_CONTRACT.md → CROP CALENDAR):
  `POST /calendar/generate`, `GET /calendar`, `GET /calendar/today`,
  `GET /calendar/upcoming`, `GET /calendar/completed`, `GET /calendar/missed`,
  `GET /calendar/summary`, `GET /calendar/{farm_id}`, `PUT /calendar/events/{id}`.

Frontend (`features/calendar`)

- **Calendar** screen: farm switcher, season **progress indicator**, view tabs
  (Today / Upcoming / Timeline / Month / Completed), **month grid** with activity
  markers, crop filter, expandable **task cards** (localized by code, priority
  badge, weather advisory), inline complete/undo, pull-to-refresh. Loading /
  skeleton / empty / error states; Tamil-first; dark/light; accessible.
- Swappable **calendar provider** (`api` ↔ local deterministic generator + MMKV)
  so the calendar works offline / in dev; **offline task completion** falls back
  to the existing SQLite outbox. Reachable from the Home "Crop Calendar" quick
  action. Reminder metadata is prepared for future FCM (no push scheduled in V1).

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 124 passed (29 suites).
- Backend: `ruff check` clean · `pytest` 131 passed.

## ✅ Phase 9 — Market Prices Module

Status: **Complete**

Verified mandi prices for farmers. External price sources sit behind a
``MarketPriceProvider`` abstraction so the initial Open Government / Agmarknet
provider can be replaced later (eNAM, state APIs, local admin, paid feeds) with
no change to the service, API or frontend. Prices come only from verified sources
(docs/PRODUCT_RULES.md → market data is never fabricated).

Backend (`/backend`, new `app/modules/market`)

- Tables (migration `0007_market_tables`): `market_locations`, `market_prices`,
  `market_price_history`, `market_favourites`. Commodity/variety are stored as
  text (no crops master exists yet; the verified source returns free-text
  commodities). Repository → Service → API layering; the current-user dependency
  is reused from auth (no completed module modified).
- **Provider abstraction**: `MarketPriceProvider` Protocol + `AgmarknetProvider`
  (data.gov.in daily mandi prices, httpx with timeout + bounded retries, injectable)
  and a deterministic `MockMarketProvider` used when no `DATA_GOV_API_KEY` is set.
  A pure `parse_agmarknet_record` normalizer + best-effort commodity → category
  classification. API keys stay server-side (docs/SECURITY.md).
- **Caching** (in-process TTL, 15 min, query-keyed; Redis-ready) + **offline
  fallback**: on a provider timeout/failure the service serves the last prices
  stored in the DB rather than erroring. Every fetch persists current prices and
  appends daily **history** (idempotent upserts). `refresh()` is the same path
  with the cache bypassed — the hook a **background scheduler** calls.
- Endpoints (docs/API_CONTRACT.md → MARKET): `GET /market` (filter by
  crop/district/state/market + paginate), `GET /market/today`,
  `GET /market/history`, `GET /market/search` (crop/market/district/state facets),
  `GET/POST /market/favourites`, `DELETE /market/favourites/{id}`. Global response
  envelope throughout; no SQL in routes.

Frontend (`features/market`)

- **Market Prices screen** (Market tab): live **search** (crop / market / district
  / state suggestions → typed filter chip), view tabs **All / Today / Nearby /
  Favourites**, pull-to-refresh, **price cards** (crop, market, district, min/max/
  **modal** price, unit, category badge, updated-time, favourite star), inline
  favourite toggle. "Nearby" reuses the selected farm's district (weather
  `useSelectedFarm`). Loading skeleton, empty, error-retry and offline states;
  Tamil-first, dark/light, accessible.
- Swappable **market provider** (`api` ↔ local): the local provider serves the
  same deterministic sample prices + MMKV favourites so the screen works offline /
  in dev. The API provider mirrors each fetch to an MMKV **offline cache** and
  falls back to it on network failure. React Query staleTime matches the backend
  15-min cache.

Database tables added: market_locations, market_prices, market_price_history,
market_favourites.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 145 passed (32 suites).
- Backend: `ruff check` clean · `pytest` 156 passed · Alembic revision graph valid.

## ✅ Phase 10 — Crop Growth Monitor Module

Status: **Complete**

Farmers upload crop photos over time and view the full growth history (Week 1 →
Week N). The AI analysis sits behind a ``GrowthAnalysisProvider`` abstraction so
future models (YOLO, nutrient-deficiency, pest, growth-stage) can replace Gemini
with **no change to the service, API or frontend**. Heavily reuses the Disease
Detection pipeline (image quality gate, Cloudflare R2 storage, Gemini client
shape), the AI context builder, the farm repository and the weather snapshot.

Backend (`/backend`, new `app/modules/growth`)

- Tables (migration `0008_crop_growth_tables`): `crop_growth_sessions`,
  `crop_growth_images`, `crop_growth_analysis` (nullable `disease_result` /
  `nutrient_result` reserved for future models), `crop_growth_timelines`.
  Repository → Service → API; current-user reused from auth (no completed module
  modified). Commodity/stage/vigour stored as stable codes (Tamil-first UI).
- **Provider abstraction**: `GrowthAnalysisProvider` Protocol + `GeminiGrowthProvider`
  (Gemini 2.5 Pro vision, httpx, timeout + retry + one parse-retry, injectable) and
  a deterministic `MockGrowthProvider` used when no `GEMINI_API_KEY`. Pure
  `parse_growth_analysis` validator. A `NutrientProvider` seam (default
  `NullNutrientProvider` → returns None, never fabricates) provides the nutrient
  future seam. Growth does not invoke a generative disease-diagnosis fallback.
  Centralized growth prompt (`prompts.py`).
- Upload pipeline: reused deterministic **quality gate** (poor images never reach
  the model) → growth analysis **comparing against the previous week** → store
  image in **Cloudflare R2** (`growth/…` prefix) →
  persist image + analysis + a **timeline entry** (week number + health delta +
  risk level) → roll up the session. Verified **weather snapshot** stored per photo.
- Endpoints (docs/API_CONTRACT.md → CROP GROWTH): `POST /growth/upload`,
  `GET /growth/history` (paginated, filterable), `GET /growth/timeline`,
  `GET /growth/latest`, `GET /growth/session/{id}`, `DELETE /growth/image/{id}`.
  Global response envelope; no SQL in routes.

Frontend (`features/growth`)

- **Crop Growth Monitor screen** (reachable from the Home "Growth Monitor" quick
  action): **camera + gallery** upload (reuses the Disease module's picker +
  client quality pre-check), view tabs **Timeline / History / Compare**, a
  **Week 1 → Week N timeline** (connector rail, per-week photo, stage/risk badges,
  health delta ↑/↓, AI observations), **history** cards, **growth comparison**
  (first vs latest), full-screen **image viewer**, pull-to-refresh, loading
  skeleton, empty/error-retry and offline states. Tamil-first, dark/light, a11y.
- Swappable **growth provider** (`api` ↔ local): the local provider serves the
  same deterministic mock analysis + MMKV sessions/images so the monitor and
  timeline work offline / in dev; the API provider mirrors history to an MMKV
  **offline cache** and falls back to it on network failure.

Database tables added: crop_growth_sessions, crop_growth_images,
crop_growth_analysis, crop_growth_timelines.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 168 passed (35 suites).
- Backend: `ruff check` clean · `pytest` 180 passed · Alembic revision graph valid.

## ✅ Phase 11 — Government Scheme Recommendation Engine

Status: **Complete**

Not a scheme-listing app — an intelligent, deterministic **eligibility engine**.
Verified schemes are stored behind a ``GovernmentSchemeProvider`` abstraction and
matched against each farmer's profile + farm to produce eligible schemes ranked
by a transparent score. Flow: Repository → Service → **Eligibility Engine** →
Provider → API → Frontend. No business logic in routers. Schemes come only from
verified sources (docs/PRODUCT_RULES.md rule 4) — never fabricated. Rule-based,
no AI in V1, so every verdict is explainable.

Backend (`/backend`, new `app/modules/schemes`)

- Tables (migration `0009_scheme_tables`): `government_schemes` (verified schemes
  with descriptive fields **and** structured eligibility rules — states/districts/
  crops/farmer-categories/land bounds/income ceiling), `scheme_documents`
  (required-document checklist), `scheme_bookmarks` (user-scoped). Repository →
  Service → API; current-user reused from auth; the farmer context reuses the
  **profile** and **farm** repositories (no completed module modified).
- **Provider abstraction**: `GovernmentSchemeProvider` Protocol + a
  `MockSchemeProvider` seeded with real, verified central + Tamil Nadu programmes
  (PM-KISAN, PMFBY, KCC, Soil Health Card, PM-KUSUM, TN free electricity, TN drip
  subsidy, NFSM-Pulses) and their real eligibility rules. `get_default_provider`
  selects it; future providers (Tamil Nadu portal, Central APIs, Admin Portal,
  Scraper) implement the same Protocol with no change to the service/engine/API/
  frontend. Idempotent seed-on-first-use (upsert by slug).
- **Eligibility Engine** (`engine.py`) — pure, deterministic, fully unit-tested:
  classifies each scheme (eligible / likely-eligible / not-eligible), assigns a
  transparent 0-100 relevance score (targeted matches raise it, unknown farmer
  data lowers it), and ranks (eligible first, then score, then soonest deadline).
  Farmer category is derived from the operational holding (marginal…large).
- Endpoints (docs/API_CONTRACT.md → GOVERNMENT SCHEMES): `GET /schemes` (all,
  filter + paginate), `GET /schemes/eligible` (ranked + context), `GET
  /schemes/recommended`, `GET /schemes/bookmarks`, `POST /schemes/bookmarks`,
  `DELETE /schemes/bookmarks/{id}`, `GET /schemes/{id}` (full detail + the
  farmer's eligibility, documents and steps). Global response envelope; no SQL in
  routes.

Frontend (`features/schemes`)

- **Government Schemes screen** (reachable from the Home "Govt Schemes" quick
  action): view tabs **Eligible / Recommended / All / Bookmarked**, farm switcher
  (reused weather `FarmSelector`) driving the eligibility context, a "matched to"
  context banner, **search + category filters** (All tab), and **AgSchemeCard**
  (category/state badges, description, eligibility meter, department, deadline
  countdown, bookmark). **Scheme Detail**: eligibility meter + matched/to-confirm/
  unmet criteria breakdown, benefits, who-is-eligible, deadline, **documents
  checklist**, **application steps**, official-website button (in-app browser),
  verified-source footer, bookmark. Loading skeletons, empty/error/offline states.
- Swappable **scheme provider** (`api` ↔ local): the local provider runs a
  faithful client-side mirror of the eligibility engine over the same verified
  sample schemes + MMKV bookmarks, so the engine and screens work offline / in
  dev; the API provider mirrors lists to an MMKV **offline cache** and falls back
  to it on network failure. Tamil-first, dark/light, accessible.

Database tables added: government_schemes, scheme_documents, scheme_bookmarks.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 197 passed (38 suites) ·
  `expo export --platform android` bundles.
- Backend: `ruff check` clean · `pytest` 222 passed · Alembic revision graph
  valid (single head `0009_scheme_tables`).

## ✅ Phase 12 — Sell My Produce (Procurement Intelligence) Module

Status: **Complete**

NOT a marketplace — farmers do not sell inside the app and no transactions
happen here. The module collects **verified future-harvest information** for
procurement planning. Flow: Repository → Service → **Procurement Engine** →
Provider → API → Frontend. Market prices come only from verified sources (reused
from the Market module) and are never fabricated; buyers are never fabricated.

Backend (`/backend`, new `app/modules/produce`)

- Tables (migration `0010_produce_tables`): `produce_offers` (farmer+farm scoped
  harvest facts, a nullable **verified** market-price snapshot, and reserved
  future-ready columns — `crop_session_id`, `ai_grade`, `buyer_match`,
  `logistics`, `procurement_channel` — so buyer matching / auctions / procurement
  AI / demand prediction / warehouse / cold storage / transport / export need no
  schema redesign), `offer_images`, `offer_status_history`, `buyer_interest`
  (future-ready, unused in V1). Repository → Service → API; current-user, the
  **farm repository** (ownership + location defaults) and the **market
  repository** (verified price snapshot) are reused (no completed module modified).
- **Procurement Engine** (`engine.py`) — pure, deterministic, fully unit-tested:
  days-to-harvest, harvest-window bucket (overdue/this-week/this-month/later),
  quantity → kg normalization, and estimated market value (only when a verified
  price reference exists) + estimated asking value. No fabrication.
- **Provider abstraction**: `ProduceProvider` Protocol + `MockProduceProvider`
  (acknowledges a submitted offer for procurement planning, returns **no**
  fabricated buyers). Future providers (eNAM, FPO, private buyers, export
  companies, admin portal) implement the same Protocol via `get_default_provider`
  with no frontend change.
- Endpoints (docs/API_CONTRACT.md → PRODUCE): `GET/POST /produce`,
  `GET /produce/upcoming`, `GET /produce/history`, `GET/PUT/DELETE /produce/{id}`,
  `POST /produce/{id}/images`. All authenticated; global response envelope; no SQL
  in routes. Validation: quantity > 0, harvest date ≥ today, crop required, farm
  ownership, farmer-settable status transitions only.

Frontend (`features/produce`)

- **Produce List** (tabs All / Upcoming / History, FAB, offline banner, reused
  `AgProduceCard` with harvest-window badge + estimated value), **Create** &
  **Edit** (shared `ProduceForm`: farm selector, crop/unit/grade dropdowns, quick
  harvest-date chips, asking price, notes, **photo upload** via the shared upload
  service), **Details** (photo gallery + add photo, procurement insight with the
  verified price reference, status-history timeline, edit/delete, "no sales in the
  app" note), dedicated **Upcoming Harvest** and **History** screens. Reachable
  from the Home "Sell Produce" quick action.
- Swappable **produce provider** (`api` ↔ local): the local provider runs a
  faithful client-side mirror of the procurement engine over MMKV-stored offers.
  **Offline support + background sync + retry**: mutations that fail offline are
  queued in an MMKV **outbox** and replayed on reconnect (`useProduceSync`); the
  API provider mirrors lists to an offline cache and falls back on network error.
  Loading skeletons, empty/error/offline states; Tamil-first, dark/light, a11y.

Database tables added: produce_offers, offer_images, offer_status_history,
buyer_interest.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 232 passed (42 suites) ·
  `expo export --platform android` bundles.
- Backend: `ruff check` clean · `pytest` 253 passed · Alembic revision graph
  valid (single head `0010_produce_tables`).

> Note: per the module brief this is procurement intelligence, so the tables are
> named `produce_offers` / `offer_images` / `offer_status_history` /
> `buyer_interest` (the reframed, future-ready equivalents of the docs'
> `produce_listings` family) — no marketplace/transaction tables were built.

## ✅ Phase 13 — Notifications & Smart Alerts Module

Status: **Complete**

The **event center** of AgrowAI — not just push notifications. A centralized,
deterministic notification **engine** receives events from every completed module
(weather, disease, calendar, growth, market, schemes, produce, AI), applies a
transparent rule table (no AI) to classify severity/priority, stores them
permanently (docs: notifications are never permanently deleted → "delete" =
*dismiss*), and delivers them through a ``NotificationProvider`` abstraction
(in-app now; FCM / OneSignal / SMS / WhatsApp / Email later) with no frontend
change. Titles/messages are stored as localization keys + a payload so the
Tamil-first client renders them. Flow: Repository → Service → **Notification
Engine** → Provider → API → Frontend. No completed module was modified — sources
are read through their own repositories/services.

Backend (`/backend`, `app/modules/notifications`)

- Tables (migration `0011_notification_tables`): `notifications`,
  `notification_preferences`, `notification_delivery_log`, `notification_templates`
  (the rule table materialized + seeded from `constants.RULES`), and
  `future_notification_queue` (scheduled alerts promoted when due). Repository →
  Service → API; current-user reused from auth.
- **Deterministic engine** (`engine.py`, pure + fully unit-tested): resolves each
  `CandidateEvent` against the rule table → a `NotificationDraft` (localization
  keys, severity, priority, resolved deep-link route, expiry). **Pure collectors**
  (`collectors.py`) — one per source — turn each module's data into candidates
  from transparent thresholds (heavy rain / disease ≥90% / task tomorrow / scheme
  closing / price move ≥5% / harvest ≤7d / stale growth / AI silence). **Sources**
  (`sources.py`) read each completed module's repository/service, each guarded so
  one failing source (or the weather network) never breaks generation.
- Sync pass is idempotent + **deduplicated** (unique `(user, dedup_key)`),
  **preference-gated** (per-module opt-outs + a minimum-severity gate), parks
  future alerts in the queue and **promotes** due ones, then **delivers** via the
  injectable provider and audits every attempt. `MockNotificationProvider`
  delivers in-app and marks external channels *skipped* (never claims sent).
- Endpoints (docs/API_CONTRACT.md → NOTIFICATIONS): `GET /notifications` (filter by
  module/severity/unread + paginate), `GET /notifications/unread`,
  `PUT /notifications/{id}/read`, `PUT /notifications/read-all`,
  `DELETE /notifications/{id}` (dismiss), `GET /notifications/preferences`,
  `PUT /notifications/preferences`. Global envelope; no SQL in routes.

Frontend (`features/notifications`)

- **Notification Center** (reached from the new Home header **bell + unread
  badge**): filter chips by **module** and **severity**, **mark-read** on open,
  **mark-all-read**, pull-to-refresh, loading skeleton / empty / error / offline
  states. **Detail** screen (full message, source, severity, deep link to the
  originating module, dismiss). **Preferences** screen (per-module opt-outs,
  delivery channels, minimum-severity gate).
- Swappable **provider** (`api` ↔ local): the local provider runs a faithful
  client-side **rule-engine mirror** (`rules.ts` + `notificationSamples.ts`) over
  MMKV so the center works offline / in dev; the API provider mirrors lists/unread/
  preferences to an MMKV **offline cache** and falls back on network error.
  **Offline + retry**: read/dismiss/read-all actions that fail offline are queued
  in an MMKV **outbox** and replayed on reconnect (`useNotificationSync`).
  Tamil-first (48 rule strings + UI, both locales), dark/light, accessible.

Database tables added: notifications, notification_preferences,
notification_delivery_log, notification_templates, future_notification_queue.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 252 passed (46 suites) ·
  `expo export --platform android` bundles.
- Backend: `ruff check` clean · `pytest` 290 passed · Alembic revision graph
  valid (single head `0011_notification_tables`).

## ✅ Phase 14 — Expert Connect Module

Status: **Complete**

A structured farmer↔verified-expert **consultation platform** — NOT a public chat
room. Every question is a tracked consultation with an **immutable** conversation
timeline, **deterministic assignment** to a verified expert desk (TNAU / KVK /
Government / Kisan Call Centre) and a logged status history. Flow: Repository →
Service → **Expert Engine** → Provider → API → Frontend. Built future-ready so
WhatsApp, live chat, video, email and AI-assisted replies join behind the provider
seam with no frontend change. Experts never modify farmer data; no expert opinion
is ever fabricated (docs/PRODUCT_RULES.md).

Backend (`/backend`, `app/modules/experts`)

- Tables (migration `0012_expert_tables`): `experts`, `expert_specializations`,
  `expert_availability`, `consultations`, `consultation_messages`,
  `consultation_attachments`, `consultation_status_history`. Repository → Service →
  API; current-user reused from auth; farm ownership + district reuse the **farm
  repository**; farmer language/district reuse the **profile repository**.
- **Expert Engine** (`engine.py`, pure + unit-tested): transparent match score
  (category / crop / district / language / verified / availability, load penalty),
  deterministic assignment (tie-break by id), and the consultation status-transition
  rules (farmer may only resolve/cancel; terminal states locked).
- **Provider abstraction**: `ExpertProvider` Protocol + `MockExpertProvider` that
  **seeds real institutional desks** (TNAU Agri-Tech Advisory, TNAU Plant Health
  Clinic, KVK Farm Advisory, Kisan Call Centre, State Agriculture Officer) and
  **acknowledges** an assigned consultation with a *system* message only — no
  fabricated agronomic replies. `get_default_provider` selects it; future channels
  (WhatsApp / live chat / video / email / AI) implement the same Protocol.
- Lifecycle: create → auto-assign → system acknowledgement → farmer replies (append
  only; status moves to the expert) → resolve/cancel. Every status change logged.
- Endpoints: `GET /experts`, `GET /experts/{id}`, `POST /consultations`,
  `GET /consultations` (+ `/pending`, `/history`), `GET /consultations/{id}`,
  `POST /consultations/{id}/reply`, `POST /consultations/{id}/attachments`,
  `PUT /consultations/{id}/status`. Global envelope; no SQL in routes.
- **Notification reuse** (additive, no migration to notification tables): the
  Notification engine gained an `experts` module + rules + a pure collector + a
  guarded source, so an assigned/replied/resolved consultation surfaces as a
  notification.

Frontend (`features/experts`)

- **Experts List** (category filter), **Expert Profile** (specializations, coverage,
  call / official-site, "ask this expert"), **Create Consultation** (crop → topic →
  photos → description, reused upload service; voice reserved), **Consultation
  Detail** (immutable **conversation timeline** with farmer/expert/system bubbles,
  reply composer, add-photo, **attachment viewer**, resolve/cancel), a
  consultations **hub** (All / Pending / History tabs), dedicated **Pending** and
  **Resolved History** screens. Reached from the new Home "Ask an Expert" quick
  action. Loading skeletons, empty/error/offline states; Tamil-first, dark/light,
  accessible.
- Swappable **provider** (`api` ↔ local): the local provider runs a faithful
  client-side mirror of the seeded desks + assignment engine + lifecycle over MMKV,
  so Expert Connect works offline / in dev; the API provider mirrors lists to an
  MMKV **offline cache** and falls back on network error. **Offline + retry**:
  reply/attachment/status actions that fail offline are queued in an MMKV outbox and
  replayed on reconnect (`useExpertSync`).

Database tables added: experts, expert_specializations, expert_availability,
consultations, consultation_messages, consultation_attachments,
consultation_status_history.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 277 passed (50 suites) ·
  `expo export --platform android` bundles.
- Backend: `ruff check` clean · `pytest` 322 passed · Alembic revision graph valid
  (single head `0012_expert_tables`).

## ✅ Phase 15 — Soil Intelligence Module

Status: **Complete**

A deterministic **Soil Engine** turns farmer-provided (or future lab / government /
satellite / Gemini-OCR) soil values into *generic* agronomic advice only — never a
commercial fertilizer brand, and never a fabricated value: unknown parameters stay
`null` and are surfaced honestly as "not available" (docs/PRODUCT_RULES.md). Flow:
Repository → Service → **Soil Engine** → Provider → API → Frontend. Future data
sources join behind the provider seam with no frontend change.

Backend (`/backend`, `app/modules/soil`)

- Tables (migration `0013_soil_tables`): `soil_profiles`, `soil_reports`,
  `soil_test_results`, `soil_recommendations`, `soil_history`. Repository → Service
  → API; current-user + farm ownership reuse auth and the farm repository.
- **Soil Engine** (`engine.py`, pure + unit-tested): classifies pH / organic carbon
  / N / P / K / salinity / micronutrients against the **Soil Health Card** rating
  bands (transparent, verifiable thresholds) and emits generic recommendations as
  localization codes (+ the measured value). No brands, no AI.
- **Provider abstraction**: `SoilProvider` Protocol + `MockSoilProvider` that
  returns **nothing** (no fabricated location soil, no fabricated OCR) — the farmer's
  values are the only source of truth in V1. Future providers (government datasets,
  laboratory APIs, satellite soil layers, Gemini OCR) implement the same Protocol.
- Report submission merges values into the farm's soil profile (a new measured value
  overrides; others are retained — never invented), stores generic recommendations,
  and appends a trend snapshot. The dashboard states "no data" honestly when a farm
  has no soil test, offering only farmer-registered soil-type baseline guidance.
- Endpoints: `GET /soil` (dashboard), `GET /soil/latest`, `GET /soil/history`,
  `GET /soil/recommendation`, `POST /soil/report`. Global envelope; no SQL in routes.
- **Notification reuse** (additive, no migration to notification tables): a `soil`
  module + rules + collector + guarded source, so a processed report surfaces as a
  notification and a deficiency raises a warning alert.

Frontend (`features/soil`)

- **Soil Dashboard** (reused weather `FarmSelector`), **Soil Health Card** (each
  parameter with value + rating chip, or a clear "not available"), **Upload Soil
  Report** (Soil Health Card values + optional photo via the reused upload service),
  **Soil History** (value trend), **Recommendations** (generic, no brands). Reached
  from the new Home "Soil Intelligence" quick action. Loading skeletons, empty/error
  states, retry, offline banner; Tamil-first, dark/light, accessible.
- Swappable **provider** (`api` ↔ local): the local provider runs a faithful client
  mirror of the Soil Engine over MMKV, so soil insights work offline / in dev; the API
  provider mirrors the dashboard/history to an MMKV **offline cache** and falls back
  on network error. **Offline + retry**: a report submitted offline is queued in an
  MMKV outbox and replayed on reconnect (`useSoilSync`).

Database tables added: soil_profiles, soil_reports, soil_test_results,
soil_recommendations, soil_history.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 300 passed (54 suites) ·
  `expo export --platform android` bundles.
- Backend: `ruff check` clean · `pytest` 346 passed · Alembic revision graph valid
  (single head `0013_soil_tables`).

## ✅ Phase 16 — Satellite Intelligence Module

Status: **Complete**

Professional farm monitoring over **free Sentinel-2** imagery. Vegetation indices
(NDVI, NDRE, EVI, NDMI) and their health / stress / moisture classifications use
**transparent, standard remote-sensing formulas and thresholds**, so results are
reproducible — never fabricated. When a usable scene is genuinely unavailable
(no farm polygon, cloud cover, acquisition delay, provider issue, or no imagery)
the session is an honest "Not Available" with a reason, never invented values
(docs/PRODUCT_RULES.md). Flow: Repository → Service → **Satellite Engine** +
**Alert Engine** → Provider → API → Frontend. Future imagery sources (Sentinel Hub,
Copernicus, Planet, Maxar, Earth Engine, drone/thermal) join behind the provider
seam with no frontend change.

Backend (`/backend`, `app/modules/satellite`) — already complete; this phase added
the frontend + its tests (no completed backend code regenerated).

- Tables (migration `0014_satellite_tables`): `satellite_sessions`,
  `satellite_images`, `satellite_indices`, `satellite_alerts`, `satellite_history`.
- **Satellite Engine** (pure): computes the four indices from reflectance bands and
  classifies vegetation health (NDVI bands), moisture (NDMI bands), trend + stress
  (NDVI deltas), with a cloud-derived confidence. **Alert Engine** (pure): emits
  generic localization-code alerts (cloud obstruction, rapid/abnormal NDVI drop,
  vegetation decline, low vigor, moisture stress, uneven field, missing imagery).
- **Provider abstraction**: `SatelliteProvider` Protocol + a Sentinel seam (honest
  "Not Available" until credentials wired) + a deterministic, clearly-flagged mock.
- Endpoints: `GET /satellite` (dashboard), `GET /satellite/latest`,
  `GET /satellite/history`, `GET /satellite/timeline`, `GET /satellite/indices`,
  `GET /satellite/alerts`, `POST /satellite/refresh`. Global envelope; no SQL in
  routes; authenticated; paginated history.
- **Notification reuse** (additive): satellite events surface via the notification
  engine (no completed module modified).

Frontend (`features/satellite`)

- **Satellite Dashboard** (reused weather `FarmSelector`): sample-data notice, honest
  no-polygon / not-available states, **Latest scene** card (image viewer, or an honest
  "no imagery preview"), **Vegetation Health** card (health / stress / moisture +
  trend, never fabricated), **Index gauges** (NDVI / NDRE / EVI / NDMI mean bars),
  **Comparison view** (first vs latest), alerts preview, **Refresh** + **Timeline**.
- **Stress Alerts** screen and **Historical Timeline** screen (weekly / monthly
  aggregation, `TimelineChart`). Routes: `app/satellite/{index,alerts,timeline}`;
  reached from the Home "Satellite" quick action.
- Swappable **provider** (`api` ↔ local): the local provider runs a faithful client
  mirror of the Satellite + Alert engines over MMKV (deterministic **sample** data,
  clearly flagged `isSample`, **no** fabricated imagery), so monitoring works offline
  / in dev; the API provider mirrors dashboard / history / timeline to an MMKV
  **offline cache** and falls back on network error. **Offline + retry**: a refresh
  requested offline is queued in an MMKV outbox and replayed on reconnect
  (`useSatelliteSync`). React Query for all server state, skeleton loading, empty /
  error / retry / offline states, accessibility labels, Tamil-first (`satellite`
  namespace, en + ta parity), dark / light.
- **Tests added** (`features/satellite/__tests__`): `satelliteEngine.test.ts` (index
  math, classifications, confidence, alert rules — 20 assertions), `satelliteMapper`
  (envelope → domain, honest nulls), `localSatelliteProvider` (sample sessions,
  honest unavailable states, history / timeline / alerts), `satelliteSync` (offline
  detection, outbox drain / retain / poison-drop). 35 tests across 4 suites.

Database tables added: satellite_sessions, satellite_images, satellite_indices,
satellite_alerts, satellite_history.

Quality gates (all green)

- Frontend: `tsc --noEmit` clean · `jest` 335 passed (58 suites, +35 satellite) ·
  `expo export --platform android` bundles.
- Backend: `ruff check` clean · `pytest` 377 passed · Alembic head
  `0014_satellite_tables`.

## ✅ Phase 17 — Nutrient Deficiency AI Module

Status: **Complete**

Identifies **visible nutrient deficiencies** from a crop-leaf photo and corroborates
the finding with the existing **Soil**, **Satellite** and **Weather** Intelligence.
This is NOT disease detection — it reasons about nutrition. A deficiency is **never
fabricated**: when the evidence is insufficient the verdict is an honest
**"Not Confirmed"** and a soil / tissue test is advised (docs/PRODUCT_RULES.md).
Flow: Repository → Service → **Nutrient Analysis Engine** → Provider → API → Frontend.
Reuses the Disease image pipeline (quality gate + R2 storage) and the AI Gemini
config — no duplication.

Backend (`/backend`, `app/modules/nutrient`)

- Tables (migration `0015_nutrient_tables`): `nutrient_reports`, `nutrient_analysis`,
  `nutrient_symptoms`, `nutrient_recommendations`, `nutrient_history`.
- **Provider abstraction**: `NutrientProvider` Protocol + `GeminiNutrientProvider`
  (vision, parse-retry) + deterministic `MockNutrientProvider`. Future CV models
  (YOLO / EfficientNet / ConvNeXt / TensorRT / ONNX / ensemble) plug in here with no
  frontend change. The provider only *observes*; the engine decides the verdict.
- **Nutrient Analysis Engine** (`engine.py`, pure + unit-tested): combines the visual
  observation with transparent Soil / Satellite / Weather signals →
  `confirmed` / `possible` / `not_confirmed` with an adjusted, capped (≤ 99) confidence;
  emits *generic* localization-code recommendations (no brands). Never overrides
  another module's diagnosis without evidence — a recent high-confidence disease
  lowers certainty and asks for an expert.
- Pure `parser.py` (lenient about "nothing conclusive", strict about validity — unknown
  nutrients/symptoms are dropped, never trusted). Service gathers references via each
  module's own repository/service (guarded — one failing is never fatal) and reuses
  the Disease quality gate + R2 storage.
- Endpoints: `POST /nutrient/analyze`, `GET /nutrient/history`, `GET /nutrient/latest`,
  `GET /nutrient/recommendations`, `GET /nutrient/report/{id}`. Authenticated;
  paginated history; global envelope; no SQL in routes.
- **Notification reuse** (additive, no notif-table migration): a `nutrient` module +
  rules (`deficiency_detected`, `test_recommended`) + pure `collect_nutrient` + a
  guarded `_collect_nutrient` source.

Frontend (`features/nutrient`)

- **Nutrient Analysis** screen (camera/gallery upload reusing the Disease picker +
  quality gate; farm selector; analysis progress), **Result** screen (verdict card
  with status + confidence meter, symptom list, **evidence** card showing the
  Soil/Satellite/Weather cross-check, generic recommendations, soil-test / expert
  CTAs, disclaimer), **History** screen (past analyses + first-vs-latest comparison).
  Routes `app/nutrient/{index,[id],history}`; Home "Nutrients" quick action.
- Swappable **provider** (`api` ↔ local): the local provider runs a faithful client
  mirror of the engine over MMKV (offline findings are honestly "possible", never a
  fabricated "confirmed"); the API provider mirrors history/latest/report to an MMKV
  **offline cache** and falls back on network error. **Offline + retry**: an analysis
  requested offline is queued in an MMKV outbox and replayed on reconnect
  (`useNutrientSync`). React Query, skeleton/empty/error/retry/offline states,
  accessibility, Tamil-first (`nutrient` namespace, en + ta parity), dark/light.
- Also extended the completed Notifications frontend (added `nutrient` to
  `NotificationModuleKey` + label + filter + `Leaf` icon + `notifications.moduleNutrient`
  + `notifications.rules.nutrient.*`).
- **Tests added** (`features/nutrient/__tests__`): `nutrientEngine` (corroboration,
  thresholds, generic recs), `nutrientMapper`, `localNutrientProvider`, `nutrientSync`.

Database tables added: nutrient_reports, nutrient_analysis, nutrient_symptoms,
nutrient_recommendations, nutrient_history.

Nutrient deficiencies implemented (13): nitrogen, phosphorus, potassium, sulphur,
calcium, magnesium, iron, zinc, boron, copper, manganese, molybdenum, chlorine —
plus an honest "Not Confirmed" when evidence is insufficient.

Quality gates (all green)

- Backend: `ruff check` clean · `pytest` 412 passed · Alembic head
  `0015_nutrient_tables`.
- Frontend: `tsc --noEmit` clean · `jest` 365 passed (62 suites, +30 nutrient) ·
  `expo export --platform android` bundles.

## ✅ Phase 18 — Crop Intelligence Engine Module

Status: **Complete**

The **central intelligence layer** of AgrowAI. It performs **no detection of its own** —
it aggregates the outputs of every agricultural module (Disease, Nutrient, Soil,
Satellite, Weather, Growth, Calendar, Expert) into a single farm-health assessment:
per-module health sub-scores, an **overall health score**, an **overall risk** level,
transparent **priority issues** and prioritized **generic recommendations**. A missing
module is **never fabricated** — it is excluded from the score and lowers the
**confidence** instead (docs/PRODUCT_RULES.md). Every weight/threshold is transparent
and reproducible. Flow: Repository → Service → **Engine → Decision → Recommendation** →
API → Frontend. Source-module data is only **read** (through each module's own
repository/service) — never overwritten.

Backend (`/backend`, `app/modules/intelligence`)

- Tables (migration `0016_intelligence_tables`): `crop_intelligence_reports`,
  `crop_health_scores`, `crop_risk_scores`, `crop_recommendations`,
  `crop_decision_history`.
- **Pure engines** (no I/O, fully unit-tested): `engine.py` (weight-normalized health
  scoring over the modules present + coverage/confidence blend), `decision.py` (ranked
  priority issues + cross-module risk escalation), `recommendation.py` (top-5 generic
  localization-code recommendations — treat a confident disease first, vigor decline
  with healthy leaves → inspect irrigation, heavy-rain + disease → preventive advisory).
- **Signals + Sources**: `signals.py` (normalized pure inputs) and `sources.py` (the I/O
  boundary — each `_read_*` adapter reads one module through its **own** repository and
  is **guarded**, so one module failing never breaks generation; weather is best-effort).
- Endpoints: `GET /intelligence` (dashboard), `GET /intelligence/latest`,
  `GET /intelligence/history` (paginated trend), `GET /intelligence/report/{id}`,
  `POST /intelligence/refresh`. Authenticated; owner-scoped; global envelope; no SQL in
  routes.
- **Notification reuse** (additive, no notif-table migration): an `intelligence` module +
  rules (`critical_risk`, `high_risk`) + pure `collect_intelligence` collector + a
  guarded `_collect_intelligence` source — a high/critical overall risk surfaces as an
  alert.

Frontend (`features/intelligence`)

- **Dashboard** screen (farm selector; **health-score visualization** — overall score +
  risk badge + **confidence meter** + per-module sub-score bars; **priority issues**;
  **recommendation timeline**; **risk timeline** = health/risk trend), **History** screen
  (decision trend + risk timeline), **Report** screen (a full saved report). Routes
  `app/intelligence/{index,history,[id]}`; Home "Farm Health" quick action.
- Swappable **provider** (`api` ↔ local): the API provider mirrors dashboard/history/
  reports to an MMKV **offline cache** and falls back on network error; the **local
  provider** runs a faithful **client mirror of the engine** (`intelligenceEngine.ts`)
  and **guardedly aggregates** the sibling Nutrient/Satellite MMKV stores — offline
  findings are honestly flagged `isSample`, never a fabricated verdict. **Offline +
  retry**: a refresh requested offline is queued in an MMKV outbox and replayed on
  reconnect (`useIntelligenceSync`). React Query, skeleton/empty/error/retry/offline
  states, accessibility, Tamil-first (`intelligence` namespace, en + ta parity),
  dark/light. **API mappers** (`intelligenceMapper.ts`) convert the envelope.
- Extended the completed Notifications frontend (added `intelligence` to
  `NotificationModuleKey` + label + filter + `Brain` icon + `notifications.moduleIntelligence`
  + `notifications.rules.intelligence.*`).
- **Tests added** (`features/intelligence/__tests__`, +32): `intelligenceEngine`
  (health/decision/recommendation), `intelligenceMapper`, `localIntelligenceProvider`
  (offline aggregation), `intelligenceSync`.

Backend tests added (`/backend/tests`, +62): `test_intelligence_engine`,
`test_intelligence_decision`, `test_intelligence_recommendation`,
`test_intelligence_flow` (service + repository), `test_intelligence_notifications`.

Database tables added: crop_intelligence_reports, crop_health_scores, crop_risk_scores,
crop_recommendations, crop_decision_history.

API endpoints: `GET /intelligence`, `GET /intelligence/latest`,
`GET /intelligence/history`, `GET /intelligence/report/{id}`, `POST /intelligence/refresh`.

Quality gates (all green)

- Backend: `ruff check` clean · `pytest` 474 passed (+62) · Alembic head
  `0016_intelligence_tables`.
- Frontend: `tsc --noEmit` clean · `jest` 397 passed (66 suites, +32 intelligence) ·
  `expo export --platform android` bundles.

## ✅ Phase 19 — AI Memory (Farm Memory Engine) Module

Status: **Complete**

A long-term **Farm Memory Engine** — NOT a chat history. A structured, deterministic
agricultural memory that continuously learns from a farm over months and years by
reading structured events from every existing module (Disease, Growth, Weather,
Satellite, Soil, Nutrient, Schemes, Market, Experts, AI Chat, Produce). The engine
merges duplicate events, assigns importance, generates seasonal & yearly summaries and
links related memories — and **never fabricates history** (docs/PRODUCT_RULES.md).
Historical memories are **immutable**; rebuild is idempotent. Reserved embedding/vector
fields (`memory_embeddings`) so future vector search / embeddings / RAG / additional AI
providers plug in behind the same seam with no redesign. Flow: Repository → Service →
**Memory Engine** → Sources → API → Frontend. Source-module data is only **read**
(through each module's own repository, guarded) — never overwritten.

Backend (`/backend`, `app/modules/memory`)

- Tables (migration `0017_memory_tables`): `farm_memories` (canonical, immutable
  memory: farmer/farm, source_module, event_type, localization `summary` + params,
  confidence, importance (+score), observed/inferred, season, season_year, crop,
  location, dedup_key, occurred_at, **reserved** embedding_ref/embedding_model),
  `memory_events` (raw events that back a memory — duplicates roll up), `memory_embeddings`
  (RESERVED for vector search — no vector written in V1), `memory_tags`, `memory_summaries`
  (season + year), `memory_links` (follows / relates / resolves — a future knowledge graph).
- **Pure engine** (`engine.py`, fully unit-tested): `merge_drafts` (collapse duplicate
  events, strongest leads), `select_new` (immutable-history idempotency), `generate_summaries`
  (seasonal + yearly counts, dominant source, top importance), `link_memories` (deterministic
  follows/relates/resolves). Pure `collectors.py` (one deterministic event builder per source,
  transparent importance rules, observed-vs-inferred) + `signals.py` (draft + stable dedup key).
  `sources.py` is the I/O boundary — each guarded `_read_*` reads one module through its **own
  repository** (weather best-effort behind a flag) and never fabricates a draft.
- Season derivation (`season_for_month` / `season_year`) is transparent + reproducible
  (Tamil-Nadu Kharif/Rabi/Summer; Rabi Jan/Feb roll into the prior agricultural year).
- Endpoints (docs: brief): `GET /memory` (dashboard — recent + latest summary),
  `GET /memory/latest`, `GET /memory/history` (paginated + filter by
  source/season/crop/importance + `q` search), `GET /memory/summary` (season + year
  bundle), `GET /memory/{id}` (a memory + its links), `POST /memory/rebuild`. Authenticated;
  owner-scoped; global envelope; no SQL in routes.

Frontend (`features/memory`)

- **Memory Dashboard** (farm selector; sample notice; latest **season/year summary**;
  **recent timeline**; Rebuild / Timeline / Summaries actions), **Memory Timeline**
  (filter chips by source + importance, text search, vertical timeline with importance
  badges + observed/inferred + confidence + relative time), **Season & Year Summaries**,
  **Memory Detail** (full record + tags + **related-memory links** you can follow). Routes
  `app/memory/{index,history,summary,[id]}`; Home "Farm Memory" quick action (History icon).
- Swappable **provider** (`api` ↔ local): the API provider mirrors dashboard/history/summary/
  detail to an MMKV **offline cache** and falls back on network error; the **local provider**
  runs a faithful **client mirror of the engine** (`memoryEngine.ts`) and **guardedly
  aggregates** the sibling Nutrient/Satellite MMKV stores — offline memories flagged
  `isSample`, never a fabricated record. **Offline + retry**: a rebuild requested offline is
  queued in an MMKV outbox and replayed on reconnect (`useMemorySync`). React Query,
  skeleton/empty/error/retry/offline states, accessibility, Tamil-first (`memory` namespace,
  en + ta parity), dark/light.
- **Tests added** — backend (`tests/test_memory_engine.py` +16, `tests/test_memory_flow.py`
  +6): season derivation, collectors, dedup/merge, immutable-history selection, seasonal/yearly
  summaries, follows/relates/resolves links; integration rebuild (empty→honest, learns from
  Disease+Soil, persists memories/events/summaries/links, dashboard/latest/history/summary/detail,
  idempotent + immutable, ownership isolation). Frontend (`features/memory/__tests__` +22):
  `memoryEngine`, `memoryMapper`, `localMemoryProvider` (offline aggregation), `memorySync`.

Database tables added: farm_memories, memory_events, memory_embeddings, memory_tags,
memory_summaries, memory_links.

API endpoints: `GET /memory`, `GET /memory/latest`, `GET /memory/history`,
`GET /memory/summary`, `GET /memory/{id}`, `POST /memory/rebuild`.

Quality gates (all green)

- Backend: `ruff check` clean · `pytest` 496 passed (+22) · Alembic head `0017_memory_tables`.
- Frontend: `tsc --noEmit` clean · `jest` 419 passed (70 suites, +22 memory) ·
  `expo export --platform android` bundles.

## ✅ Admin Dashboard — COMPLETE

The AgrowAI **team** platform (NOT a farmer interface): operational visibility across
every module plus farmer management, procurement, AI monitoring, analytics, broadcasts
and an immutable audit trail. Read-only over farmer data (no direct modification),
role-based (RBAC, least privilege), and every admin action is audited. Flow:
Repository → Service → **Admin Engine** → Provider → API → Frontend.

- **Backend** `app/modules/admin`:
  - **RBAC** (`constants.py`) — transparent role→permission grants for 5 roles
    (super_admin, district_manager, procurement_manager, agriculture_officer,
    customer_support) over 9 granular permissions; a new role/permission is a data
    change, never a redesign. `AdminRole`/`AdminPermission`/`AuditAction`/
    `ProcurementStatus`/`BroadcastTargetType`/`BroadcastScheduleType` enums.
  - **Pure Admin Engine** (`engine.py`, unit-tested, no I/O) — dashboard overview cards
    in documented order (honest nulls) + procurement analytics (village/crop/season
    splits + monthly quantity trend) **reusing** the Produce `to_kilograms` normalizer
    and the Memory `season_for_month` helper (no duplication).
  - **Read-only aggregation** (`metrics.py`, `queries.py`) — every cross-module query is
    guarded so one failing module never breaks the dashboard; untracked metrics (model
    latency, API failures) stay `None` — surfaced honestly, never fabricated.
  - **Provider seam** (`provider.py`) — `BroadcastProvider` Protocol +
    `NotificationBroadcastProvider` (delivers a broadcast by **reusing the Notifications
    engine** — no duplicate delivery code) + `MockBroadcastProvider` (tests). Future FCM
    / SMS / WhatsApp / Email channels plug in with no service change.
  - **Service** (`service.py`) — enforces RBAC, **audits every action**, aggregates via
    the engine; the only writes are admin-domain rows. Procurement status is derived from
    the **immutable audit trail** (last `procurement_status_changed`) — no farmer table
    is ever mutated. `seed.py` idempotently seeds roles/permissions/widgets and
    `ensure_admin` bootstraps the first Super Admin.
  - **API** (`router.py`, thin) — `GET /admin/me`, `/admin/dashboard`, `/admin/farmers`,
    `/admin/farmers/{id}`, `/admin/analytics`, `/admin/procurement`,
    `PUT /admin/procurement/{offer_id}/status`, `/admin/ai`, `/admin/notifications`,
    `POST /admin/broadcast`, `GET`/`POST /admin/announcements`, `/admin/audit`. Every
    endpoint resolves an active admin context (captures client IP for the audit) and is
    permission-checked in the service.
- **Frontend** `features/admin` (routes `app/admin/{index,farmers/index,farmers/[id],
  procurement,analytics,ai,broadcast,audit}`; team-only entry point gated in the Profile
  screen via `useAdminMe`): swappable provider (api ↔ local — the local provider serves a
  deterministic sample dataset flagged `isSample`, computes procurement analytics with a
  faithful client mirror of the engine, and persists status changes / broadcasts to MMKV
  with a local audit trail). **React Query hooks** (`useAdmin.ts`). Screens: Dashboard
  (overview tiles + pipeline + nav), Farmer Management (search + directory), Farmer Detail
  (profile + farms + activity), Procurement (analytics + status pipeline), AI Monitoring
  (metrics + honest “not tracked”), Analytics (real distributions), Broadcast (compose +
  history), Audit Logs (filterable immutable trail). Skeleton/empty/error/offline/
  access-denied states, accessibility, Tamil-first (`admin` namespace, en + ta parity),
  dark/light.
- **Tests added** — backend (`tests/test_admin_engine.py` +9, `tests/test_admin_flow.py`
  +9): overview order/nulls, procurement bucket/season/trend + unknown handling, RBAC
  grants; integration RBAC (non-admin / suspended / least-privilege denial), dashboard +
  audit, analytics distributions, AI honest-null, farmer directory search + detail,
  procurement status change audited + reflected, immediate vs scheduled broadcast,
  announcements. Frontend (`features/admin/__tests__` +21): `procurementAnalytics`,
  `adminMapper`, `localAdminProvider`, `adminMeta`.

Database tables added: admin_roles, admin_permissions, admin_users, broadcast_messages,
system_announcements, audit_logs, dashboard_widgets, dashboard_preferences.

Quality gates (all green)

- Backend: `ruff check` clean · `pytest` 514 passed (+18) · Alembic head `0018_admin_tables`.
- Frontend: `tsc --noEmit` clean · `jest` 440 passed (74 suites, +21 admin) ·
  `expo export --platform android` bundles.

## ⏭️ Next (not started)

- All MASTER_SPEC V1 feature modules are complete.

> Do not begin the next module until instructed.
