# Model Availability Policy

A registry status is not sufficient to enable farmer diagnosis. Runtime integrity and deployment authorization are separate gates.

A frozen runtime may be integrity-verified when its status is `FROZEN_RUNTIME_READY`, even when disease detection remains disabled. Inference is available only when:

- the crop is enabled;
- disease detection is enabled;
- status is `FROZEN_RUNTIME_READY`;
- every required artifact exists;
- `SHA256SUMS.txt` verifies every runtime input;
- the class map is contiguous;
- the path is crop-specific and contains no sealed-test material.

Any failure returns or records `MODEL_NOT_AVAILABLE`. There is no cross-crop fallback and no manual bypass. Abstention remains a valid safe outcome and must not expose an unsupported class.

Readiness reports declared model status, complete local bundle presence, local
integrity verification, and inference authorization as separate facts. A Drive
or Colab result does not prove that the configured local bundle exists.

Redgram currently has declared status `FROZEN_RUNTIME_READY`, but
`disease_detection_enabled=false` because its provisional evaluation did not
meet the deployment gate. Until its complete local contract is present and
verified, `local_runtime_ready=false`; regardless of bundle state,
`inference_authorized=false`. Its runtime must not be invoked through a disease
prediction endpoint, and the consumed provisional test must never be reopened
by application runtime.
