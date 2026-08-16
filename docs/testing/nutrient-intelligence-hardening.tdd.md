# Nutrient Intelligence hardening — TDD evidence

## Scope

Feature 5 only: safe recommendation gating, abstention presentation, structured provider errors, Tamil/English messages, and production credential/mock checks.

## RED

- Backend recommendation tests failed when visual-only and secondary findings produced nutrient-specific recommendations without corroboration.
- Mobile engine tests failed for the same unsafe recommendation behavior.
- New mobile error and presentation tests initially failed because structured provider/crop errors and abstained-result sanitization were not implemented.

## GREEN

- Backend nutrient suite: `42 passed`.
- Mobile nutrient and home-entry suites: `9 suites, 51 tests passed`.
- Mobile TypeScript typecheck: passed.
- Scoped backend Ruff: passed.
- Android `assembleKvkFieldTest`: passed after removal of the mobile environment key entry.

## Full regression evidence

- Backend: `1007 passed, 7 failed, 1 skipped`; the seven failures are outside Feature 5 and relate to unavailable ONNX disease-model dependencies/readiness.
- Mobile: `941 passed, 2 failed`; both failures are outside Feature 5 and are brittle source-text assertions in disease-result and notification tests.

## External validation limits

- No backend `GEMINI_API_KEY` or `GOOGLE_API_KEY` was available, so a real Gemini response was not validated.
- No authorized Android device was listed by ADB, so physical-device execution was not possible.
- No versioned expert-approval document is bound to the active nutrient policy; `expert_verified` remains false.
