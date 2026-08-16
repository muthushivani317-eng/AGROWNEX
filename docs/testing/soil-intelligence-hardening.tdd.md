# Soil Intelligence hardening — TDD evidence

## Scope and journeys

Derived from the Feature 6 request: farmers must see the source of every soil value;
production must never substitute local/mock remote data; missing remote capability must
be explicit; owned-farm boundaries are required; and numeric values retain units.

## RED → GREEN evidence

| Guarantee | RED evidence | GREEN evidence |
|---|---|---|
| Production without a real soil provider fails closed | Backend provider test could not import an unavailable provider | Focused backend suite passes with `UnavailableSoilProvider` |
| Production mobile does not select the local provider | Provider safety test resolved a local dashboard instead of rejecting | Mobile provider safety test passes with `remote_estimation_unavailable` |
| API provenance reaches mobile domain data | Mapper returned no `indicatorEvidence` | Mapper test passes with evidence, status, unit, and laboratory-equivalent flag preserved |
| Every numeric parameter has unit metadata | pH evidence unit was the empty string | Evidence test passes with `pH` and no empty parameter units |
| Remote requests never invent an AOI or result | `SoilService.remote_estimation` did not exist | Service test passes: owned verified AOI plus unavailable provider returns zero estimates |

## Validation

- Focused backend: 33 passed before final truth-class addition.
- Focused mobile/home: 36 passed; TypeScript typecheck passed.
- Full backend: 1011 passed, 7 unrelated disease/ONNX failures, 1 skipped.
- Full mobile: 949 passed, 2 unrelated brittle source-text failures.
- Android KVK field-test build: passed.
- Physical device: not run; ADB listed no authorized device.

## Known external gaps

- No real remote-soil provider adapter or credentials are installed, so real remote data
  is not validated. The runtime returns an explicit unavailable state.
- No expert-approval record is bound to the soil recommendation rules.
