# Disease detection backend contract

## Capability authority

`app/crop_runtime/crop_registry.json` is the only declarative crop/model
release registry. `ReadinessResolver` adds executable artifact and runtime
state. The authenticated `GET /api/v1/disease/capabilities` response combines
those facts with the user's server-side roles.

The success envelope's `data` is an object with `crops` and
`crop_identification`. Each crop exposes `visible`, `runtime_ready`,
`integrity_verified`, `adapter_available`, `user_authorized`, a lowercase
`release_scope` (`internal`, `pilot`, `general`, or `blocked`),
`supported_class_ids`, `prediction_kind`, field-validation status, and a
sanitized unavailable reason. It must not expose routes, paths, hashes,
temperatures, thresholds, credentials, or official accuracy claims.

Technical readiness never grants release authorization. General-farmer
inference remains blocked. Prediction endpoints continue to require exactly
one controlled role and a crop-confirmation receipt. Legacy joint inference
also requires an explicitly enabled, active field-test session.

Role eligibility is registry-driven and shared by capabilities and route
dependencies. Internal testers and KVK reviewers can access controlled
runtimes; pilot testers are eligible only where `pilot_inference_eligible` is
true. Technical readiness fields never mean that a particular user is
authorized; only `/disease/capabilities` publishes `user_authorized`.

## Error contract

HTTP errors use the standard envelope:

```json
{
  "success": false,
  "message": "The disease model is not available.",
  "error_code": "MODEL_RUNTIME_UNAVAILABLE",
  "errors": [],
  "timestamp": "...",
  "request_id": "..."
}
```

Stable model failure categories are `MODEL_ARTIFACT_MISSING`,
`MODEL_INTEGRITY_FAILURE`, and `MODEL_RUNTIME_UNAVAILABLE`. Authorization,
confirmation, invalid-image, low-quality, and out-of-domain codes remain
distinct. Private exception text is never returned.

An abstention or uncertain result is a valid model decision and can remain a
successful response. A missing, corrupt, or unloadable runtime is an
operational failure and returns HTTP 503.

## Readiness

`/readyz` checks general application infrastructure. `/ready` is the stricter
controlled-pilot readiness probe. It verifies the six disease runtimes, the
six-class crop-identity runtime, its safety artifact, and all required Python
inference packages. Results contain sanitized categories only.

Immutable technical checks are cached per process and prewarmed in a worker
thread during application startup. Role membership and field-test session state
are evaluated on every request and are never cached. Operators and tests can
explicitly invalidate technical state with `refresh_technical_readiness()` and
`refresh_model_inventory()`.

Run the same fail-closed inventory check locally or in CI with:

```text
python -m scripts.verify_model_inventory
```

The controlled-pilot container healthcheck targets `/ready`.
