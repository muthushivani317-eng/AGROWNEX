# Crop-stage tracking — TDD evidence

## Journeys

- A farmer sees an explicit unavailable state when no verified crop-stage pack exists.
- A farmer can confirm a server suggestion or separately report/correct the observed stage.
- A network-failed report is retained as pending and retried with the same idempotency key.
- A stale version produces a visible conflict instead of overwriting server state.
- History preserves whether an entry was a farmer confirmation or correction.

## RED → GREEN

| Guarantee | RED evidence | GREEN evidence |
|---|---|---|
| Client cannot forge registry verification | New backend test failed because `StageTrackingService` had no server registry dependency and trusted client evidence | Empty server registry overrides forged client fields with `NO_VERIFIED_STAGE_MODEL` |
| Correction payload cannot self-assert expert/registry verification | Mobile workflow test initially failed because transition and offline modules did not exist | API test verifies `expert_reviewed=false`, `registry_verified=false`, and farmer-selection evidence |
| Offline actions survive and replay idempotently | Queue module missing at RED | Queue/replay tests pass and remove records only after server success |

## Validation

- Focused backend Growth/stage tests: 24 passed.
- Focused mobile Growth/Calendar/Home tests: 52 passed.
- TypeScript typecheck: passed.
- Scoped Ruff and Prettier: passed.
- Full backend: 1014 passed, 7 unrelated disease/ONNX failures, 1 skipped.
- Full mobile: 952 passed, 2 unrelated brittle source-text failures.
- Android KVK field-test build: passed.

## Safety and remaining external state

- Active verified crop-stage pack count remains zero; no agricultural durations were added.
- Farmer confirmation/correction remains farmer-reported evidence and never sets expert review.
- No authorized ADB device was available for physical validation.
