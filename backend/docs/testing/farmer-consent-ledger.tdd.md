# Farmer consent ledger — TDD evidence

## Source plan

The journeys and guarantees were derived from the approved Phase 1 farmer-release plan in the Codex task. No external plan file was used.

## User journeys

- As a farmer, I can grant or withdraw each optional processing purpose independently.
- As a farmer, I can see the current decision and the exact notice version recorded for it.
- As an administrator, I can see a farmer's current consent summary without receiving private evidence metadata.
- As the business, I can prove consent events were appended, not rewritten, and reject ambiguous duplicate requests.

## RED and GREEN evidence

| Stage | Command | Result |
|---|---|---|
| Initial RED | `.venv\\Scripts\\python.exe -m pytest tests\\test_consent_flow.py tests\\test_admin_flow.py -q` | Collection failed as intended because `app.modules.consents` did not exist. |
| Hardening RED | `.venv\\Scripts\\python.exe -m pytest tests\\test_consent_flow.py -q` | Collection failed as intended because the new `UserConsentState` allocator contract did not exist. |
| Final GREEN | `.venv\\Scripts\\python.exe -m pytest tests\\test_consent_flow.py tests\\test_admin_flow.py -q` | `18 passed`; only pytest cache permission warnings. |
| Static checks | Scoped Ruff check for changed consent, admin, router, migration, and test files | `All checks passed`. |
| App contract | Backend import plus consent-route assertion | `APP_IMPORT_AND_ROUTE_PASS`. |
| Migration graph | `alembic heads` | `c8b4f7a21d09 (head)`. |

## Test specification

| # | Guarantee | Test target | Type | Result |
|---|---|---|---|---|
| 1 | Optional purposes default to denied and required service processing is not mutable consent | `tests/test_consent_flow.py` | Integration | PASS |
| 2 | Grant and withdrawal append versioned history while current state uses the latest event | `tests/test_consent_flow.py` | Integration | PASS |
| 3 | Reusing an idempotency key for the opposite decision is rejected | `tests/test_consent_flow.py` | Service/integration | PASS |
| 4 | Notice version, locale, purpose text, hash, and channel are resolved from the server registry | `tests/test_consent_flow.py` | Unit/integration | PASS |
| 5 | ORM update and delete attempts against consent evidence are rejected | `tests/test_consent_flow.py` | Security/integration | PASS |
| 6 | Farmer and admin responses exclude arbitrary evidence metadata | `tests/test_consent_flow.py`, `tests/test_admin_flow.py` | API integration | PASS |
| 7 | Admin farmer-detail access retains existing permission checks and audit behavior | `tests/test_admin_flow.py` | Authorization integration | PASS |

## Coverage and known gaps

`pytest-cov` is not installed in the backend environment, so a numeric coverage report could not be produced. Every public consent service and API behavior in this slice is exercised by the targeted integration suite.

Before production deployment, run the migration and direct-SQL immutability checks on PostgreSQL, plus multi-session concurrency tests for first-row creation, distinct keys, identical replay, and opposite-decision replay. English and Tamil notice wording also requires privacy/legal approval; the code binds decisions to exact versioned text and hashes but does not constitute that approval.

## Merge evidence

No RED/GREEN checkpoint commits were created because the parent feature workflow requires explicit user approval at its pre-commit gate. This document preserves the RED/GREEN evidence for the eventual conventional commit.
