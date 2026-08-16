# Temporary Gemini crop identification — controlled beta

## Decision and scope

Gemini is a temporary crop-identification provider only. It must never diagnose disease or produce recommendations. Dedicated crop-ID training is deferred because the audited dataset is not defensible. General farmer release is blocked.

The canonical crop allowlist is `banana`, `paddy`, `cotton`, `groundnut`, `chilli`, and `redgram`. Provider output outside this set is rejected by a strict Pydantic schema. Display labels are never routing identifiers.

## Architecture

1. Authenticated controlled-tester role gate.
2. MIME, byte-size, decoded-format, pixel-count, corruption, dimensions, exposure and detail checks.
3. Temporary provider-assisted plant/non-plant/uncertain classification.
4. Schema-constrained Gemini crop identification, with uncertainty failing closed.
5. Server-created request bound to actor and SHA-256 of the uploaded image.
6. Mandatory farmer confirmation or explicit correction to one canonical crop.
7. Short-lived opaque confirmation receipt.
8. Disease endpoint validates receipt ownership, crop, image identity and expiry before dispatch.
9. Crop-specific frozen disease calibration and abstention remain unchanged.

The current confirmation store is process-local and expires after 15 minutes. Loss of state blocks inference. A shared durable/Redis-backed implementation, with atomic replay control across workers, is required before pilot deployment.

## Provider replacement guide

Implement `CropIdentificationProvider.identify(image, mime_type)` and `model_name`. Return only the internal `GeminiCropIdentification` JSON schema (the interface name is historical); never change the public API or disease receipt validation. A replacement requires provenance, calibration, OOD evaluation, parity tests, and explicit release approval.

## Feature and release gates

- `GENERAL_FARMER_RELEASE=NO` is enforced by server role dependencies, not mobile navigation.
- Only `internal_tester`, `pilot_tester`, and `kvk_reviewer` are accepted by the controlled endpoint.
- Chilli and Redgram remain restricted by their runtime registry and must not be enabled based on crop identification alone.
- Real farmer and Tamil Nadu field validation are separate release gates.

## Environment

Required server-only variables: `GEMINI_API_KEY`, `GEMINI_VISION_MODEL`, `GEMINI_BASE_URL`, `GEMINI_TIMEOUT_SECONDS`, and `GEMINI_MAX_RETRIES`. Secrets must never be placed in Expo public variables or logs. Retry count is capped at three by code. Provider configuration failure returns a safe 503 category.

Image safety defaults are 8 MiB maximum and 25 million decoded pixels. Existing conservative image-detail heuristics remain in `backend/app/image_safety.py`; moving all thresholds into typed settings is still required before pilot tuning.

## Privacy and auditability

Logs contain request ID, status, safe actor-recorded indicator, and timestamps. They do not contain raw images, API keys, authorization headers, phone numbers, prompts, or provider raw output. Any privacy/legal conclusion must be verified against official DPDP requirements.

## Recommendations

Crop ID creates no recommendation. Disease knowledge may render only after receipt validation, accepted calibrated disease inference, and source-backed content mapping. Any agricultural statement must be verified against an official source. Pesticide brands are prohibited.

## Data-collection handoff

Farmer corrections are audit events, not training labels. A future dedicated-model dataset requires explicit consent, expert review, licence/provenance, duplicate-family grouping, sealed evaluation, and source-diversity controls before any training.
