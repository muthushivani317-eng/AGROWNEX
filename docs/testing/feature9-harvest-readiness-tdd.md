# Feature 9 — Harvest Readiness TDD evidence

## Red

`python -m pytest tests/test_harvest_readiness_service.py -q` initially failed at collection because the verified readiness registry and service did not exist. The existing mobile fallback test then failed when the safety contract was made more explicit (`insufficient_data` versus `no_verified_readiness_rule`).

## Green

The focused backend suite verifies engine invocation, fail-closed empty-registry behavior, persistence, immutable history, idempotency, and ownership. The focused mobile suite verifies safe fallback and backend mapping without any generated harvest date.

## Safety boundary

The active verified criteria registry is empty. No crop readiness rule, threshold, or harvest date was added. Farmer confirmation can only follow an engine result that is awaiting confirmation, and it is stored as farmer-reported evidence rather than expert verification.
