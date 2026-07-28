# Multi-Crop Infrastructure Test Report

This report covers model-independent registry, runtime-integrity, API availability, and mobile fail-closed behavior. It does not contain model metrics and is not an accuracy claim.

Validation commands:

```text
python -m pytest tests/test_crop_runtime_registry.py -q
npx jest features/multiCropDiagnosis/__tests__/cropRegistry.test.ts --runInBand
npx tsc --noEmit
```

## Results

- Focused backend crop-runtime tests: 11 passed.
- Complete backend suite: 650 passed, 1 skipped.
- Focused mobile crop-registry tests: 4 passed.
- Complete Jest suite: 625 passed across 99 suites.
- TypeScript: passed.
- Python compile validation: passed.

The backend emitted one existing Starlette/httpx deprecation warning. Jest emitted existing intentional auth/logging messages. Neither caused a test failure.

Redgram follow-up coverage proves:

- registry status is `FROZEN_RUNTIME_READY`;
- disease detection remains disabled;
- frozen-runtime integrity can be verified independently;
- inference authorization still fails closed;
- there is no Banana or Chilli fallback;
- public responses retain the limitation and redact internal paths;
- consumed provisional-test paths are rejected before filesystem access.

No model was loaded or trained, and no sealed or consumed provisional-test file was accessed.
