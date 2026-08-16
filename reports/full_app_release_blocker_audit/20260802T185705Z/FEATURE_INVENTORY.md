# AgrowAI Authenticated Feature Inventory

Baseline frozen at `2026-08-02T18:57:05Z`. Baseline standalone release APK SHA-256: `47a5ef077a6b684ba77ab421285b3d1550548b806e9c4a729e9bd2310287f04b`. The mobile worktree already contained 126 changed/untracked status entries; none were deleted or reset. All device and production states remain `NOT_VALIDATED` unless direct evidence is recorded below.

| Feature | Visible Home label | Expected pathname | Physical route | Backend endpoint(s), relative to `/api/v1` | Auth | Farm | Profile | Current UI state | Current functional state | Real-device status | Known blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Home | Home | `/(tabs)` | `app/(tabs)/index.tsx` | dashboard composes feature queries | Yes | No | Yes | Partially repaired light layout | Route loop fixed | Not revalidated after repair | Full dashboard/device regression pending |
| AI Assistant | AI Assistant | `/ai` | `app/(tabs)/ai.tsx` | `POST /ai/chat`; `GET/DELETE /ai/history[...]` | Yes | No | Yes | Composer repair exists but device evidence absent | Provider implemented | FAIL in supplied evidence | Composer/message/backend production validation required |
| Disease Detection | Disease Detection | `/disease` | `app/disease/index.tsx` | `POST /disease/analyze`; crop-specific runtime routes are separately capability-gated | Yes | Crop confirmation | Yes | Capture workflow exists | Multi-stage production path unresolved | FAIL | Crop-identification connection failure; no bypass permitted |
| Weather | Weather | `/weather` | `app/weather.tsx` | `GET /weather` | Yes | Location/farm context | Yes | Implemented | Provider implemented | NOT_VALIDATED | Real location, offline and production response unverified |
| Add Farm | Add Farm | `/farm/new` | `app/farm/new.tsx` | `POST /farms`; boundary `PUT /farms/{id}/boundary` | Yes | Creates farm | Yes | Long form with reported usability defects | Submission provider implemented | FAIL | GPS/map/form hierarchy/raw key/disabled-state defects |
| Crop Calendar | Crop Calendar | `/calendar` | `app/calendar/index.tsx` | `/calendar`, `/calendar/generate`, `/calendar/summary`, `/calendar/events/{id}` | Yes | Yes | Yes | Implemented | Provider implemented | NOT_VALIDATED | No release-device or production evidence |
| Growth Monitor | Growth Monitor | `/growth` | `app/growth/index.tsx` | `/growth/upload`, `/growth/history`, `/growth/timeline`, `/growth/latest` | Yes | Yes | Yes | Implemented | Provider implemented | NOT_VALIDATED | Upload and rendering not physically validated |
| Market Prices | Market Prices | `/market` | `app/(tabs)/market.tsx` | `/market`, `/market/history`, `/market/search`, `/market/favourites` | Yes | No | Yes | Implemented | Provider implemented | NOT_VALIDATED | Current-source warning and production data verification pending |
| Government Schemes | Govt Schemes | `/schemes` | `app/schemes/index.tsx` | `/schemes`, `/schemes/eligible`, `/schemes/recommended`, `/schemes/bookmarks` | Yes | Contextual | Yes | Reported concatenated tabs/crowded cards | Provider implemented | FAIL | Provisional facts need warning; tabs and cards unusable |
| Sell Produce | Sell Produce | `/produce` | `app/produce/index.tsx` | `/produce`, `/produce/upcoming`, `/produce/history` | Yes | Yes | Yes | Implemented | Provider implemented | NOT_VALIDATED | Form/API/device evidence missing |
| Notifications | Notifications | `/notifications` | `app/notifications/index.tsx` | `/notifications`, `/notifications/unread`, `/notifications/read-all`, preferences | Yes | No | Yes | Implemented | Provider implemented | NOT_VALIDATED | Device and production validation missing |
| Plant Identifier | Plant Identifier | `/plant-identifier` | `app/plant-identifier/index.tsx` | feature-specific identification service (audit pending) | Yes | No | Yes | Internal placeholder leaked | Service unavailable in evidence | FAIL | Raw `HUMAN_TAMIL_REVIEW_REQUIRED`; endpoint/provider audit required |
| Soil Intelligence | Soil Intelligence | `/soil` | `app/soil/index.tsx` | `/soil`, `/soil/latest`, `/soil/history`, `/soil/recommendation`, `/soil/report` | Yes | Yes | Yes | Implemented | Provider implemented | NOT_VALIDATED | Evidence/source and production/device validation missing |
| Nutrient Deficiency | Missing from Home | `/nutrient` | `app/nutrient/index.tsx` | `/nutrient/analyze`, `/nutrient/history`, `/nutrient/latest`, `/nutrient/recommendations` | Yes | Likely | Yes | Physical screen exists, Home registration absent | Client exists; evidence/model status not proven | FAIL | Must remain controlled unavailable unless evidence pipeline is verified |
| Farm tab | Farm | `/(tabs)/farm` | `app/(tabs)/farm.tsx` | `/farms` | Yes | No | Yes | Partially repaired | Provider implemented | NOT_VALIDATED | Full list/detail navigation and production validation pending |
| Profile | Profile | `/(tabs)/profile` | `app/(tabs)/profile.tsx` | `/farmers/me`, `/farmers/languages`, `/farmers/preferences` | Yes | No | Yes | Partially repaired | Provider implemented | NOT_VALIDATED | Device visual/API validation pending |
| Profile edit | Edit Profile | `/profile/edit` | `app/profile/edit.tsx` | `PUT /farmers/me`; languages/preferences | Yes | No | Yes | Implemented | Provider implemented | NOT_VALIDATED | Device submission evidence pending |
| Profile setup | Complete Profile | `/complete-profile` | `app/(auth)/complete-profile.tsx` | `/farmers/me`, languages | Auth bootstrap | No | No | Partially repaired | Provider implemented | NOT_VALIDATED | Clean-login setup regression pending |

## Environment inventory

Statically referenced public keys: `EXPO_PUBLIC_API_BASE_URL`, `EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL`, `EXPO_PUBLIC_APP_ENV`, `EXPO_PUBLIC_API_TIMEOUT_MS`, Firebase API/auth-domain/project/storage/messaging/app IDs, Google client IDs, `EXPO_PUBLIC_ADMIN_ALLOWLIST`, session timeouts, upload endpoint, and Mapbox token. Values and secrets are intentionally not recorded here.

## Initial decision

`READY_FOR_TESTING=NO`. Route existence and automated tests alone are not feature acceptance. Production API and physical standalone-release validation remain mandatory.
