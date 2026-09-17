# Organic mobile foundation

The feature keeps transport DTOs in `services/organicMapper.ts`; screens and hooks use camel-case domain types only.

Assumed API contract:

- `GET /farms/{farm_id}/organic-profile` returns the profile or 404 when it has not been created.
- `PUT /farms/{farm_id}/organic-profile` is an upsert and receives an `Idempotency-Key` header.
- `GET /organic-logbook/entries?farm_id={farm_id}` returns an array ordered newest first.
- `POST /organic-logbook/entries` accepts `practice_code`, `input_reference`, `quantity_unit`, `note`, `action_workflow_id`, and `idempotency_key`.
- All responses use the app's standard `{ success, data }` envelope.
- `GET /farms/{farm_id}/organic-plan` returns source-reviewed disease, soil, calendar, weather and satellite actions. Satellite actions are always rendered as scouting-only, regardless of payload wording.

The plan bundle is the mobile adapter for capabilities 2, 4, 5, 11 and 12. It intentionally renders no fallback agronomy when the server has no applicable content. Produce traceability optionally accepts `organic_classification` and `organic_claim_verification`; a `certified_organic` classification is rejected unless verification is `verified`.

Farm mode is not certification. The first slice does not allow certification editing or display a certification badge. Cache and outbox keys are scoped to the authenticated account for shared-device safety.

## Admin certification boundary

The mobile admin console is role-gated, but it has no certification-review API/provider contract. Review remains backend/admin-web only in this phase; mobile never exposes a non-functional approval control or lets a farmer self-verify. Mobile review requires server-enforced admin list/detail/decision endpoints, protected document access, and immutable audit metadata.

`EXPO_PUBLIC_AGROWAI_ORGANIC_ENABLED=false` hides the farm entry point and redirects the organic dashboard. Plans are cached per authenticated account for offline reading; profile and logbook writes use the account-scoped outbox.
