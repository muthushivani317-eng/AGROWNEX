# AgrowAI Complete Technical Audit

Audit date: 2026-08-07  
Scope: first-party mobile, Android, backend, model-runtime, migration, localization, test, build and deployment source. Generated dependencies/build outputs and binary datasets were inventoried but not treated as source modules. Several dataset/model directories returned Windows access-denied errors; conclusions about executable application behavior come from the readable runtime manifests and code. The requested roadmap features 5–28 were not supplied—the prompt contains a placeholder—so the gap table uses repository-discovered product modules and explicitly avoids inventing roadmap requirements.

## 1. Executive Summary

- AgrowAI is an Expo/React Native Android application backed by a large Python FastAPI service. It is not a native Kotlin Activity/Fragment application and it is not a WhatsApp bot.
- The strongest live paths are authenticated backend APIs, Gemini text chat, Open-Meteo weather, Agmarknet market prices, and server-side image classifiers. WhatsApp, Tamil speech input/output, external expert channels and several notification channels are future seams or UI settings only.
- AI is mixed: Google Gemini 2.5 Flash/Pro is called over HTTPS, while custom MobileNetV3 models run server-side through ONNX Runtime or PyTorch. No model runs inside the Android APK.
- Disease/crop runtimes are unusually safety-conscious: confidence gates, abstention, image-quality checks, artifact hashes and farmer confirmation exist. Several crop-identity and restricted-crop manifests explicitly block general farmer release.
- Architecture is a consistent feature-module/provider pattern in mobile and Router → Service → Repository → Provider in backend. Overall consistency: 8/10. Duplication among legacy, V2, V3 and restricted model routers is the main architectural drag.
- Offline support is meaningful on mobile through MMKV mirrors/outboxes and cached weather/history, but it is uneven: live AI, fresh market/weather and server inference still require connectivity.
- No production secret was found hardcoded in the inspected source. Firebase client identifiers are configuration, not server secrets; real Gemini, database, Firebase Admin and data.gov credentials are environment-driven. The backend intentionally contains insecure development defaults but refuses them in production.
- The most important release risks are debug-keystore signing for release-derived APKs, incomplete field validation of ML models, mock-provider behavior outside production, absent real voice/WhatsApp delivery, and an omitted product roadmap that prevents a faithful feature 5–28 comparison.

## 2. Project Inventory

### Structure and modules

| Area | Important paths | Responsibility |
|---|---|---|
| Mobile routing | `agrow-ai/app/` | Expo Router file-based navigation and auth/application layouts |
| Mobile features | `agrow-ai/features/` | `admin`, `ai`, `auth`, `bananaV3`, `calendar`, `cropIdentification`, `diagnosisTransport`, `diagnosisWorkflow`, `disease`, `experts`, `farm`, `founderTesting`, `growth`, `home`, `intelligence`, `market`, `memory`, `multiCropDiagnosis`, `notifications`, `nutrient`, `plantIdentifier`, `produce`, `profile`, `satellite`, `schemes`, `soil`, `startup`, `weather` |
| Shared mobile | `components/`, `config/`, `hooks/`, `lib/`, `providers/`, `services/`, `stores/`, `theme/`, `types/`, `utils/` | Design system, configuration, API client, persistence and shared state |
| Android shell | `agrow-ai/android/` | React Native/Expo Gradle application, Hermes and native dependency autolinking |
| Backend entry/core | `backend/app/main.py`, `backend/app/core/`, `backend/app/api/` | FastAPI lifecycle, middleware, configuration, authentication, API composition |
| Backend business modules | `backend/app/modules/` | Admin, AI, auth, calendar, disease, experts, farmers, farms, growth, intelligence, market, memory, notifications, nutrient, produce, satellite, schemes, soil, weather |
| ML runtimes | `backend/app/banana_v3/`, `crop_identity*`, `legacy_joint/`, `redgram_v2/`, `restricted_crops/`, `plant_identifier/`, `gemini_crop_identification/` | Cloud vision and frozen ONNX/PyTorch classifiers, safety gates and API boundaries |
| Database | `backend/migrations/versions/` | 24 Alembic revisions covering users through device tokens and controlled tester roles |
| Training/evidence | `training_tools/`, `datasets/`, `crop_identity_dataset_v1/`, `model_artifacts/`, `recommendation_knowledge/`, `agrowai_autonomous_pipeline/` | Model training, frozen artifacts, data provenance and evidence; not Android runtime code |

### Architecture assessment

Mobile uses feature-oriented Clean-ish architecture: screens/hooks call a provider interface, which selects API or local implementations; DTO mappers and MMKV storage are kept behind feature services. Zustand handles client state, React Query handles server state, Expo Router handles navigation. Backend is consistently layered Router → Service → Repository → SQLAlchemy/Provider, visible for example in weather (`backend/app/modules/weather/router.py`, `service.py`, `repository.py`, `provider.py`) and AI (`backend/app/modules/ai/router.py`, `service.py:57-143`, `repositories.py`, `provider.py`). This is closer to modular Clean Architecture than MVVM/MVC. Consistency is **8/10**; parallel legacy/model-generation routers and occasional deterministic local providers duplicate domain behavior.

### Direct mobile/Android dependencies

All direct dependencies from `agrow-ai/package.json`:

- Expo/React Native platform: `expo`, `react`, `react-dom`, `react-native`, `react-native-web`, `expo-router`, `expo-constants`, `expo-linking`, `expo-status-bar`, `expo-splash-screen`, `expo-build-properties`.
- UI/native interaction: `@expo/vector-icons`, `lucide-react-native`, `@gorhom/bottom-sheet`, `react-native-gesture-handler`, `react-native-reanimated`, `react-native-worklets`, `react-native-screens`, `react-native-safe-area-context`, `react-native-svg`, `react-native-css-interop`, `expo-haptics`, `expo-symbols`, `expo-image`, `expo-font`, Inter and Noto Sans Tamil font packages.
- Device/media/location: `expo-image-picker`, `expo-file-system`, `expo-location`, `expo-localization`, `expo-web-browser`.
- Auth/security: `@react-native-firebase/app`, `@react-native-firebase/auth`, `expo-secure-store`, `expo-auth-session`, `expo-apple-authentication`, `expo-crypto`.
- Data/state: `axios`, `@tanstack/react-query`, `zustand`, `react-native-mmkv`, `@react-native-async-storage/async-storage`, `expo-sqlite`, `dayjs`.
- Forms/validation/i18n: `react-hook-form`, `@hookform/resolvers`, `zod`, `i18next`, `react-i18next`.
- Styling/utilities: `clsx`, `tailwind-merge`; dev tooling: Jest presets/types, TypeScript, Prettier, NativeWind and Tailwind CSS.
- Android Gradle adds React Android, Hermes (or JSC fallback), Google Services, and optional Fresco GIF/WebP modules (`agrow-ai/android/app/build.gradle:188-209`).

### Backend dependencies

`backend/requirements.txt` pins FastAPI/Uvicorn, Pydantic Settings, async SQLAlchemy/asyncpg/Alembic/GeoAlchemy2, Redis/ARQ, Firebase Admin, multipart and HTTPX, Sentry, Pillow, PyTorch/Torchvision, NumPy, ONNX/ONNX Runtime, JSON Schema, and pytest/pytest-asyncio/Ruff/Black/aiosqlite for development and tests.

### Platform versions

- Built configuration: minSdk **24**, targetSdk **36**, compileSdk **36**, build tools **36.0.0** (confirmed by the Gradle build output; Gradle refers to Expo root ext values at `android/app/build.gradle:88-94`).
- React Native **0.86.2**, Expo SDK **57**, Hermes enabled and New Architecture enabled (`android/gradle.properties`).
- Kotlin **2.1.20** in the resolved build; Android builds on the Java toolchain required by current React Native/Gradle (Java 17 runtime expected, but no first-party `sourceCompatibility` pin is present).
- Backend requires Python **>=3.12** (`backend/pyproject.toml`).

## 3. AI Models & Data Flow

### Integrated models

| Model/provider | Runtime and call site | Purpose | Input → output |
|---|---|---|---|
| Gemini 2.5 Flash | Cloud REST, `backend/app/modules/ai/provider.py:57-137,156-195` | Farmer chat; Pro fallback after blank/failure | System instruction + text history + message JSON → generated text and token metadata |
| Gemini 2.5 Pro | Cloud REST; chat fallback above and vision constants | Complex/fallback chat and vision identification | Text and/or base64 image parts → structured/generated response |
| Gemini crop identification | Cloud, `backend/app/gemini_crop_identification/router.py:112-168` and provider/schema modules | Plant/crop recognition with confirmation | Multipart image → localized crop candidates, confidence/quality/confirmation contract |
| Gemini plant identifier | Cloud, `backend/app/plant_identifier/router.py:80+` | General plant identification | Image → plant identity/alternatives and localized fields |
| Legacy joint crop-constrained classifier | Server ONNX, `backend/app/legacy_joint/`; artifact `model_opset17.onnx` | Paddy/cotton/groundnut disease classification | RGB image tensor → calibrated crop-constrained class scores/abstention |
| Banana V3 healthy gate | Server ONNX then PyTorch fallback; `banana_v3/inference_service.py` | Healthy vs diseased gate | NCHW float32 `[N,3,224,224]` → gated result |
| Banana V3 disease classifier | Same runtime | Banana disease class | Same normalized tensor → calibrated class and confidence/abstention |
| Chilli restricted MobileNetV3-small | Server PyTorch restricted runtime | Chilli disease classification | 224×224 normalized RGB → restricted accepted/abstained/error contract |
| Redgram restricted MobileNetV3-small | Server PyTorch restricted runtime | Redgram disease classification | 224×224 normalized RGB → restricted accepted/abstained/error contract |
| Crop identity MobileNetV3-small v1 | Server PyTorch; public inference blocked | Four-crop identity | 224 RGB → banana/paddy/cotton/groundnut probabilities |
| Six-class crop identity internal v1 | Server PyTorch, `crop_identity_six_class_internal/runtime.py:75-104` | Internal identity for banana/paddy/cotton/groundnut/chilli/redgram | 160 crop after resize → temperature-scaled probabilities + required confirmation |

No TensorFlow Lite model is embedded in the APK. Model manifests explicitly say Banana field validation is in progress and crop identity general farmer release is blocked.

### Prompt design

The main prompt is in `backend/app/modules/ai/prompts.py:5-48`: farmer-specific role, non-fabrication, supplied-context-only behavior, pesticide/brand safety, no yield guarantees, <200-word structure, Tamil-only or English-only directive, and farm/weather context. `AIService.chat` assembles profile, farm, best-effort Open-Meteo context, bounded history and the current message (`service.py:75-124`), validates output, records tokens/latency and persists the conversation.

### Four requested feature traces

**a. Crop disease detection.** Mobile selects/picks a photo, uses the crop registry and diagnosis transport, and posts multipart data through the authenticated Axios client. Backend `modules/disease/router.py:44-177` validates the request and routes to crop-specific runtime/safety gates. Frozen image preprocessing produces normalized tensors; ONNX/PyTorch returns scores; temperature/confidence/margin/quality/OOD gates can abstain. A diagnosis record is persisted and verified recommendation retrieval is separately fail-closed. Tamil presentation is localization/knowledge-record driven, not produced by an on-device Tamil model. Multiple generations coexist, so the precise path depends on crop capability.

**b. Daily market/mandi price.** Mobile `features/market/services/apiMarketProvider.ts` calls `/market`, `/market/today`, `/market/history`, search and favourites. Backend `market/provider.py:129-195` calls the data.gov.in Agmarknet resource with API key, filters, bounded retries and timeout. `parse_agmarknet_record` normalizes commodity, variety, market, district, min/max/modal price, date and ₹/quintal (`provider.py:99-126`). Results are cached/persisted; without a key, development uses deterministic mock rows (`provider.py:198-273`). This is not price prediction or AI.

**c. Weather alerts.** Coordinates come from a farm or query. Backend calls `https://api.open-meteo.com/v1/forecast` with current/hourly/daily fields (`weather/provider.py:36-87`), parses WMO values and derives deterministic irrigation, spraying, heat, rain, wind and field-work insights (`weather/insights.py`). Redis/in-memory cache TTL is five minutes. Mobile React Query refreshes every 15 minutes and falls back to MMKV cache (`features/weather/hooks/useWeather.ts:17-34`). Notification channel abstractions exist, but this trace does not prove background OS push delivery for every weather insight.

**d. Tamil voice messages.** **Not live.** Microphone permission and preference/UI text exist, but backend AI router explicitly says voice/image chat are deferred (`backend/app/modules/ai/router.py:7`), and the UI says voice notes are coming soon (`localization/locales/en.ts:1001`). There is no STT engine, NLU voice pipeline or TTS implementation to trace.

### WhatsApp

This is an in-app assistant with WhatsApp mentioned only as a future expert/notification channel. No Twilio SDK, Meta Cloud API client, webhook verification or WhatsApp Business credentials/routes were found. Backend provider comments explicitly describe WhatsApp as future (`modules/notifications/provider.py:4-5`, `modules/experts/provider.py:13`); therefore branding the current product “WhatsApp-based” is technically inaccurate.

## 4. Backend & Data Architecture

### Server and API boundaries

FastAPI boots from `backend/app/main.py:47-97`; production configuration is fail-fast, docs can be hidden, and middleware provides trusted-host enforcement, request IDs, rate limits, body-size limits, security headers, CORS and metrics. Mobile uses one Axios instance with the configured HTTPS `/api/v1` base, Firebase bearer tokens, refresh-once behavior and bounded retries (`agrow-ai/services/apiClient.ts`).

Major internal API groups are auth, farmers/preferences/languages, farms/media/boundaries, AI chat/history, disease/crop models, weather, market, calendar, schemes, produce, notifications/devices, growth, soil, satellite, nutrient, intelligence, memory, experts and admin. Model-specific endpoints include Banana V3, restricted chilli/redgram, crop identity, plant identifier and Gemini crop identification. Protected routes use Firebase bearer authentication; `verify_id_token` verifies signature/audience/issuer/expiry and revocation (`backend/app/core/security.py:68-116`).

External APIs/services:

- Google Gemini `.../v1beta/models/{model}:generateContent`, API key retained on backend (`ai/provider.py:95-105`).
- Open-Meteo `/v1/forecast`, no secret (`weather/provider.py:64-74`).
- data.gov.in/Agmarknet resource API, `api-key` query parameter (`market/provider.py:149-175`).
- Firebase Auth on Android and Firebase Admin token verification/FCM on backend.
- MSG91 is a configured future/server OTP seam; Android production phone SMS is Firebase (`core/config.py:108-115`).
- Sentry is optional/lazy backend observability. Media upload uses a configured HTTPS upload endpoint; it fails closed in release profiles if absent.

### Databases and schemas

Remote persistence is PostgreSQL through async SQLAlchemy; PostGIS support is installed for farm location/boundary data. Redis supplies shared TTL cache and ARQ background work. The 24 migration files define users/profiles/languages/preferences, farms/locations/boundaries/media, AI conversations/messages/token usage, disease reports, calendar events, market prices/favourites, growth images/analysis, schemes/bookmarks, produce offers/interests, notifications/preferences/delivery/device tokens, expert consultations/messages/attachments, soil reports/profiles, satellite sessions/indices/alerts, nutrient reports, intelligence reports, memory records, admin roles/audits/broadcasts, indexes, and controlled tester/reviewer roles.

Mobile persistence uses multiple MMKV feature stores for offline mirrors, outboxes, cached histories and preferences; encrypted MMKV/SecureStore protects auth-related state; AsyncStorage supports selected framework/state use; Expo SQLite is installed and registered but MMKV is the dominant first-party store. The founder test store is physically separate (`features/founderTesting/internalTestStorage.ts:5`).

### Tamil and offline behavior

Tamil is implemented with i18next/react-i18next and full `localization/locales/ta.ts`/`en.ts` resources plus Noto Sans Tamil. Gemini is prompted to reply in simple spoken Tamil (`prompts.py:31-37`). There is no translation API or dedicated Tamil-trained local model.

Offline behavior includes MMKV mirrors for farms, disease, weather, market-adjacent screens, calendar, notifications, schemes, growth, soil, satellite, nutrient, intelligence, memory, produce and experts. React Query manages stale/refetch behavior. This provides cached reads and some offline mutations, but new AI inference, identity/disease server inference and fresh public data remain online-only.

## 5. Code Quality & Risk Findings

| Severity | Finding | Evidence and consequence |
|---|---|---|
| **Critical** | Release-derived variants use the debug signing key | `android/app/build.gradle:103-125` assigns `signingConfigs.debug` to `release`, `localStandalone`, and `internalTesting`. Fine for internal APKs, unacceptable for farmer production distribution. Create a protected release keystore and CI signing flow before production. |
| **High** | Several ML runtimes are not authorized for farmer claims | Banana config says field validation in progress; crop-identity configs say official accuracy false/general release blocked; chilli/redgram are restricted. UI/API must preserve those gates and avoid diagnosis claims. |
| **High** | Product description overstates live channels | No WhatsApp/STT/TTS implementation exists. Claiming a WhatsApp/voice product now creates operational and trust risk. |
| **High** | Development mock providers return plausible agricultural/market/chat data | `ai/provider.py:198-226` and `market/provider.py:198-273`. Production fail-fast controls are good (`core/config.py:137-172`), but every deployment must set production environment correctly; otherwise sample content may look real. |
| **Medium** | Parallel inference generations increase routing and maintenance risk | `legacy_joint`, `banana_v3`, `restricted_crops`, `redgram_v2`, `crop_identity*`, and model-boundary routers overlap. A single capability registry/router should own production selection. |
| **Medium** | AI output validation is primarily textual safety, not evidence grounding | Prompt prohibits fabrication and `validate_response` checks shape, but chat remains generative. Agricultural recommendations should cite approved knowledge records and separate verified facts from model prose. |
| **Medium** | Offline behavior is broad but inconsistent | Many feature providers cache/read locally, while AI and image inference need backend. Network loss can leave stale information without a universal timestamp/confidence banner. |
| **Medium** | Upload trust boundary needs server-side magic-byte and malware controls | Mobile constrains picker behavior and backend caps request size, but content-type/decoded-image checks must remain mandatory at every upload endpoint. |
| **Medium** | Java toolchain is implicit | Gradle source has no explicit first-party Java compatibility/toolchain pin, weakening reproducibility across developer machines. |
| **Low** | No first-party TODO/FIXME debt surfaced in executable source | The only scan hit was an integrity string in `package-lock.json`; however, comments describe many “future” providers, which are product gaps rather than TODO markers. |
| **Low** | Some Tamil appeared mojibake in PowerShell output | Files may be valid UTF-8 and the console may be decoding incorrectly. Add localization encoding/render snapshots to prevent genuine corruption. |

No hardcoded production Gemini key, Firebase Admin credential, database password or session secret was found. `DEV_SESSION_SECRET` and localhost DB/Redis defaults are deliberate development values, and `validate_production()` rejects them. Firebase `google-services.json` contains client configuration, which is not equivalent to an Admin private key, but Firebase rules/API restrictions still matter.

Error handling is generally good: HTTP providers use timeouts, bounded exponential retry and stable domain errors; mobile retries transient requests and handles 401 refresh once; weather context is best-effort; cached reads support degradation; ML paths can abstain. Crash risks remain around large/invalid images and configuration drift, but body/image limits and startup model loading reduce them.

Tests are substantial rather than absent: 123 mobile test-related files and 102 backend Python test files were enumerated. The latest validated run passed 120 Jest suites/764 tests and 872 backend tests with one skip. That is strong regression volume, although no coverage percentage was established and real-device/UI accessibility tests remain outstanding.

UI/UX strengths include Tamil-first localization, large reusable controls, clear loading/error/empty components, image confirmation and explicit diagnosis states. Weaknesses for low-literacy users are the absent real voice flow, text-heavy advanced modules, many navigation destinations, and insufficient proof of TalkBack/large-font/one-handed field testing.

## 6. Roadmap Gap Analysis

The requested “features 5–28” list was not pasted. The following is therefore a repository capability gap table—not a claim about the missing roadmap numbering.

| Discovered capability | State | Existing reusable infrastructure / gap |
|---|---|---|
| AI farmer chat | Implemented online | Gemini provider, persistence, quotas, context and Tamil prompt; needs grounded citations |
| Crop disease diagnosis | Implemented with crop-dependent gates | Reuse image transport, safety gates and knowledge service; field validation remains crop-specific |
| Crop/plant identification | Internal/restricted + Gemini path | Confirmation UI and model registry reusable; general-release model safety is blocked |
| Daily market prices | Implemented API + dev mock | Agmarknet provider/cache/favourites reusable; freshness/source labeling should be prominent |
| Weather/spray insights | Implemented deterministic API pipeline | Open-Meteo/parser/insight/cache reusable for alerts; background delivery proof incomplete |
| Tamil localization | Implemented | Full locale resources/font; voice is not implemented |
| Tamil voice messages | Placeholder/unbuilt | Microphone permission, preference and UI labels only; requires STT/TTS/audio transport |
| WhatsApp integration | Unbuilt | Notification/expert provider interfaces can accept a future verified Meta adapter/webhook |
| Push/SMS/email/voice delivery | Partly scaffolded | Preferences, device tokens and provider seam exist; each real external channel needs implementation |
| Farm/soil/growth/calendar | Implemented module scaffolding/API/local mirrors | Can feed AI context and proactive advice once evidence and sync policies mature |
| Satellite/nutrient/intelligence/memory | Implemented modules, mixed deterministic/sample/provider state | Shared farm identity, storage and dashboards reusable; verify upstream data and claims |
| Expert connection | In-app consultation implemented; external channels future | Consultation/message schema reusable for WhatsApp/video/email |
| Schemes/produce marketplace | Implemented modules | Auth, localization, bookmarks/offers reusable; source verification/moderation required |
| Pest outbreak/community alerts | Not a distinct live pipeline | Could reuse diagnosis aggregation, geospatial farms, notifications and admin broadcast after privacy-preserving design |
| Price prediction | Unbuilt | Market history exists, but no predictive model; do not label current daily prices as forecasts |

## 7. Prioritized Recommendations

| Item | Effort | Impact | Priority |
|---|---:|---:|---:|
| Replace debug release signing with CI-held production keystore; retain internal key only for internalTesting | Medium | Critical security/distribution | P0 |
| Keep blocked/restricted ML flags enforced end-to-end; complete independent South-Tamil-Nadu field validation per crop | Major | Farmer safety | P0 |
| Consolidate all disease/identity runtime selection behind one versioned capability registry and envelope | Medium | Reliability/maintainability | P0 |
| Ground agricultural answers in reviewed knowledge records with citations, uncertainty and escalation—not prompt rules alone | Major | Safety/trust | P0 |
| Implement explicit stale/source/time badges across every cached weather/market/diagnosis view | Quick | Offline trust | P1 |
| Build Tamil voice as a resilient push-to-talk state machine: on-device VAD/compression, resumable upload, Tamil STT, constrained intent, spoken summary with replay/speed controls | Major | Accessibility | P1 |
| Conduct TalkBack, 200% font, sunlight, low-end-phone and one-handed Tamil usability sessions with farmers | Medium | Adoption | P1 |
| Add unified offline sync/outbox policy with conflict handling, per-record freshness and network-quality telemetry | Major | Rural reliability | P1 |
| Add magic-byte/decode/image-bomb checks and retention/deletion policy at every photo boundary | Medium | Privacy/security | P1 |
| Pin Java toolchain and dependency manager; enforce frozen installs and audit gates in CI | Quick | Reproducibility | P1 |
| Implement WhatsApp only through Meta Cloud API with signed webhook verification, consent, templates, opt-out and idempotency | Major | Channel reach | P2 |
| Reduce Gemini cost by keeping Flash for normal chat, truncating history, caching stable context and using Pro only on measured escalation | Quick | Cost | P2 |
| Partition model/AI telemetry by anonymous farmer/crop cohort and monitor abstention, drift, latency and cost | Medium | Scale/model governance | P2 |

Cost illustration: at an assumed 20 farmer turns/day, 1,000 input and 300 output tokens/turn, monthly consumption is 0.6M input + 0.18M output tokens per farmer. Apply the current Gemini 2.5 Flash prices from Google’s official pricing page to those volumes before budgeting; token logs already exist (`AIService` records input/output tokens), so replace assumptions with p50/p95 production data. This excludes image inference, retries, taxes and infrastructure.

Scaling from pilot to thousands/day should use stateless FastAPI replicas, PostgreSQL pool sizing, Redis shared cache/rate limiting, ARQ workers for slow jobs, object storage for media, idempotency keys, model worker isolation, per-farmer quotas, structured tracing and SLOs. Keep ML artifacts immutable and hash-verified as the Banana bundle already demonstrates.

## 8. Elite Feature Ideas

1. **Tamil “field walk” coach:** a hands-free sequence that requests wide/close leaf photos, reads back capture-quality feedback in Tamil, asks one symptom question at a time, and produces an abstaining evidence card. It can reuse image-quality gates, diagnosis workflow, localization and future STT/TTS.
2. **Hyperlocal anonymous crop-health radar:** aggregate only high-confidence, consented diagnoses into coarse village grids and warn nearby farmers of emerging patterns without exposing individual farms. Reuse geospatial farms, diagnosis events, admin broadcasts and notifications; enforce k-anonymity and minimum sample thresholds.
3. **Action-window planner:** combine verified weather spray windows, the farmer’s crop calendar, cached market data and reviewed disease guidance into three simple Tamil cards—“do now / wait / ask an expert”—with offline snapshots and spoken playback. This reuses existing deterministic modules and avoids inventing a new model.

