# Disease-Risk Alerts TDD evidence

The requested farmer journey is Home → current farm risk → persisted detail/history. The workflow must remain non-diagnostic and must not execute unverified rule packs.

| Guarantee | Test evidence | Result |
|---|---|---|
| Required authenticated API routes are mounted | `backend/tests/test_disease_risk_api_contract.py` | PASS |
| No verified pack produces a persisted, idempotent, non-alerting unavailable result | `backend/tests/test_disease_risk_api_contract.py` | PASS |
| Cross-user farm and alert reads are rejected | `backend/tests/test_disease_risk_api_contract.py` | PASS |
| Verified-rule engine and notification collector remain fail-closed | `backend/tests/test_disease_risk_engine.py`, `backend/tests/test_disease_risk_notifications.py` | PASS |
| Home entry, Expo routes and backend API paths exist | `agrow-ai/features/diseaseRisk/__tests__/integrationContract.test.ts` | PASS |
| Mobile mapping and Home route matrix remain valid | `agrow-ai/features/diseaseRisk/__tests__/mapper.test.ts`, `agrow-ai/features/home/__tests__/routeMatrix.test.ts` | PASS |

RED evidence: the initial focused run failed 2 backend and 2 mobile tests because the API, status, Home entry, routes and mobile API did not exist.

GREEN evidence: related backend validation passed 63 tests, final disease-risk/notification validation passed 49 tests, and final mobile validation passed 12 tests. TypeScript, scoped Ruff and scoped Prettier passed.

Known repository-wide gaps: full backend remains at 7 failures due unavailable ONNX/runtime readiness; full mobile remains at 3 unrelated stale contract failures. Android signing and an authorized ADB device are unavailable. Active verified agricultural rule-pack count is zero.
