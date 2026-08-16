# Feature 10 — Action Verification TDD evidence

## Journeys

- A farmer opens a stable source-linked action, reports done/not done/deferred, optionally adds a note, and sees the server-saved status and append-only history.
- A disconnected farmer sees an explicit pending-sync state; replay uses the same idempotency key.
- Another farmer cannot read or update the action, and stale versions fail with a conflict.

## RED

- `python -m pytest tests/test_action_verification_service.py tests/test_action_verification_api_contract.py -q` failed because the service schemas/API did not exist.
- `npx jest features/actionVerification/__tests__/api.test.ts --runInBand` failed because the mobile API mapper did not exist.

## GREEN

- Focused backend tests cover workflow semantics, evidence consent, persistence, ownership, idempotency, history, and router registration.
- Focused mobile tests cover safe status wording, API mapping, Home entry, and route registration.

## Safety boundary

`farmer_reported_done` is workflow completion only. No API or UI state declares agronomic success. Evidence bytes are validated when supplied but are not persisted until a protected evidence-storage adapter is connected; the current UI therefore does not offer photo upload.
