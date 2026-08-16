# AgrowAI internal-testing feature audit

Generated: 2026-08-06T17:24:37.575Z

- Required features represented: 20
- Mobile routes represented: 70
- Backend router capabilities represented: 30
- Internal-testing profile: production HTTPS/Firebase checks enforced; developer mocks disabled.
- Safety gates: crop confirmation, confidence/calibration/abstention, and restricted-crop labels preserved.

## Feature results

- **Language Selection** — /(auth)/language — VISIBLE_AND_REACHABLE
- **Phone Authentication** — /(auth)/login — VISIBLE_AND_REACHABLE
- **OTP Verification** — /(auth)/otp — VISIBLE_AND_REACHABLE
- **Farmer Profile** — /(tabs)/profile — VISIBLE_AND_REACHABLE
- **Farm Registration** — /farm/new — VISIBLE_AND_REACHABLE
- **Home Dashboard** — /(tabs) — VISIBLE_AND_REACHABLE
- **AI Chat** — /(tabs)/ai — VISIBLE_AND_REACHABLE
- **Crop Identification** — /plant-identifier — VISIBLE_AND_REACHABLE
- **Farmer Crop Confirmation** — /disease — VISIBLE_AND_REACHABLE
- **Disease Detection** — /disease — VISIBLE_AND_REACHABLE
- **Nutrient Deficiency** — /nutrient — FUNCTIONAL_BACKEND_PROVIDER
- **Weather** — /weather — VISIBLE_AND_REACHABLE
- **Crop Calendar** — /calendar — VISIBLE_AND_REACHABLE
- **Market Prices** — /(tabs)/market — VISIBLE_AND_REACHABLE
- **Government Schemes** — /schemes — VISIBLE_AND_REACHABLE
- **Sell Produce** — /produce — VISIBLE_AND_REACHABLE
- **Notifications** — /notifications — VISIBLE_AND_REACHABLE
- **Settings** — /profile/account — VISIBLE_AND_REACHABLE
- **Language Switching** — /profile/account — VISIBLE_AND_REACHABLE
- **Logout** — /profile/account — VISIBLE_AND_REACHABLE

## Material findings

- `localStandalone` is not the internal-testing variant because it intentionally supports loopback HTTP.
- `internalTesting` is the non-debuggable Android build type; its Expo profile is `internal_testing`.
- Nutrient Deficiency selects `apiNutrientProvider` when production Firebase/backend configuration is present. Analyze has no client mock fallback; read operations may use cached prior reports on network errors.
- Chilli and Redgram remain `RESTRICTED_INTERNAL_TESTING_ONLY` and use restricted backend adapters.
- Strict APK string inspection still finds generic loopback/test strings in bundled framework/development code. Runtime configuration is production-only and fail-closed, but this prevents claiming zero raw references.
