# AgrowAI Authenticated App Release-Blocker Audit

## Decision

`READY_FOR_TESTING=NO`

The code-level stop-ship repair improved Home, Nutrient Deficiency gating, AI composer visibility, Add Farm error visibility, Disease retry/copy, scheme/market warnings, Plant Identifier copy and raw translation fallback. Automated validation and a standalone arm64 release build pass. The required Android device was not connected, so physical UI validation and authenticated production API validation could not be performed. The prior Crop Identification and Plant Identifier failures therefore remain unresolved release blockers.

## Changes completed

- Home split into prioritized Quick Actions and More Services with deterministic two-column sizing.
- Nutrient Deficiency added and routed to a controlled unavailable screen; no fake analysis.
- AI composer given explicit release-native layout and visibility styles.
- Add Farm shows location permission/unavailable retry states, hides exact coordinates and explains disabled submit.
- Disease crop-ID failure now has a real retry; internal marker/raw confidence removed.
- Plant Identifier internal review marker removed with safe English fallback.
- Scheme percentage hidden; scheme and market official-source warnings added.
- Translation runtime cannot render an unresolved dotted key; recommendation Tamil-review enum leakage removed.
- No disease model, checkpoint, threshold, temperature, capability, OTP flow or backend logic was changed.

## Validation

- Full Jest: 117/117 suites, 746/746 tests PASS.
- TypeScript: PASS.
- Expo Doctor: 20/20 PASS.
- Android production JS export: PASS, 4,701 modules.
- Standalone non-debuggable arm64 release: PASS.
- APK SHA-256: `673bc3c8354d36d5271ca132bda9727f6dcc6ec8afb647f9eef2e5bbbb342219`.
- Physical device: NOT RUN (`RZCY80YM62A` absent from ADB).
- Authenticated production requests: NOT RUN.

## Required status fields

HOME_LAYOUT=AUTOMATED_PASS_PHYSICAL_PENDING
NUTRIENT_DEFICIENCY_CARD=PASS_CONTROLLED_UNAVAILABLE
AI_COMPOSER=AUTOMATED_PASS_PHYSICAL_PENDING
AI_BACKEND_MESSAGE=NOT_RUN
ADD_FARM_UI=PARTIAL_PHYSICAL_PENDING
GPS_PERMISSION=NOT_RUN
GPS_LOCATION=NOT_RUN
MAP_BOUNDARY=NOT_RUN
FARM_SUBMISSION=NOT_RUN
DISEASE_CAPTURE=NOT_RUN
CROP_IDENTIFICATION=FAIL_NOT_REVALIDATED
DISEASE_INFERENCE=BLOCKED_BY_CROP_IDENTIFICATION
WEATHER=NOT_RUN
CROP_CALENDAR=NOT_RUN
GROWTH_MONITOR=NOT_RUN
MARKET_PRICES=WARNING_ADDED_PHYSICAL_PENDING
SCHEME_TABS=AUTOMATED_PRESENT_PHYSICAL_PENDING
SCHEME_SOURCE_WARNING=PASS
SELL_PRODUCE=NOT_RUN
NOTIFICATIONS=NOT_RUN
PLANT_IDENTIFIER=FAIL_NOT_REVALIDATED
SOIL_INTELLIGENCE=NOT_RUN
PROFILE=NOT_RUN
PROFILE_SETUP=NOT_RUN
RAW_TRANSLATION_KEYS=STATIC_PASS_PHYSICAL_PENDING
FEATURE_NAVIGATION=AUTOMATED_PASS_PHYSICAL_PENDING
RELEASE_BUILD=PASS
PHYSICAL_DEVICE_REGRESSION=NOT_RUN_DEVICE_UNAVAILABLE
READY_FOR_TESTING=NO
FARMER_RELEASE_READINESS=NO

Nothing was staged, committed or pushed.
