# Controlled-beta crop-identification pre-change audit

Audit timestamp: `2026-08-03T19:38:24Z`

This is the immutable pre-change baseline. It distinguishes code presence from an end-to-end, server-enforced safety control.

| Component | Exists | Connected | Tested | Production-ready | Evidence |
|---|---:|---:|---:|---:|---|
| Image corruption check | Yes | Yes | Yes | Partial | `backend/app/gemini_crop_identification/router.py::_validated_image`; `backend/tests/test_gemini_crop_identification.py::test_invalid_upload_never_reaches_provider` |
| File type validation | Yes | Yes | Yes | Partial | MIME allowlist in `_validated_image`; content is decoded independently, but stable reason codes differ from the requested registry |
| File size validation | Yes | Yes | No | Partial | `MAX_IMAGE_BYTES=12_000_000`; no focused boundary test found |
| Minimum image resolution | Yes | Yes | Yes | Partial | `backend/app/image_safety.py::assess_image_safety`; threshold is hard-coded |
| Blur detection | Partial | Yes | Partial | No | Texture heuristic exists but is not a documented/configurable blur metric |
| Brightness/exposure check | Yes | Yes | Yes | Partial | Brightness and near-black/white heuristics exist; hard-coded thresholds and non-standard reason codes |
| Plant/non-plant validation | Temporary | Yes | Partial | No | Gemini contract can return `non_plant`; no independently validated detector exists |
| Gemini crop-ID client | Yes | Yes | Mocked | Partial | `GeminiCropIdentificationProvider`; no real-provider evidence |
| Six-crop constrained output | Yes | Yes | Yes | Partial | Pydantic literals and parser allowlist; provider request lacks an explicit response JSON schema |
| Unsupported-crop handling | Yes | Yes | Yes | Partial | Parser maps arbitrary crop names to uncertainty |
| Crop-ID confidence or uncertainty | Yes | Yes | Yes | No | Gemini self-reported confidence is treated as numeric confidence without declaring its source |
| Farmer confirmation UI | Yes | Local only | Partial | No | `DiseaseScreen` confirmation state is client-local and not bound to the server request |
| Farmer rejection path | Yes | Local only | Partial | No | Manual crop correction exists, but no server audit of original result/correction |
| Requested-crop mismatch handling | Partial | Separate legacy path | Yes | No | Dedicated runtime compares requested crop; Gemini receipt is not consumed by disease routing |
| Disease-model routing | Yes | Yes | Yes | Partial | Banana and legacy adapters exist; routing is not bound to Gemini request identity |
| Model version logging | Partial | Partial | Partial | No | Dedicated route logs model metadata; Gemini-to-disease chain has no joined audit record |
| Disease calibration | Yes | Runtime-specific | Yes | Partial | Frozen runtime policies exist; not re-audited or modified here |
| Disease abstention | Yes | Runtime-specific | Yes | Partial | Runtime-specific abstention exists; not bound to Gemini confirmation receipt |
| Tamil result rendering | Partial | Partial | Partial | No | Several controlled-beta strings are English-only; human-reviewed Tamil is incomplete |
| English result rendering | Yes | Yes | Partial | Partial | Mobile controlled-beta states render English guidance |
| Internal tester restriction | Yes | Yes | Yes | Partial | `ControlledTester` enforces internal/pilot/KVK roles server-side |
| General farmer release blocked | Yes | Yes | Yes | Partial | Backend role gate blocks general farmers; mobile feature defaults need explicit audit |
| Unit tests | Yes | N/A | Mocked | Partial | Gemini parser/upload and image safety unit tests exist |
| Backend integration tests | Partial | Partial | Mocked | No | Upload-to-provider ASGI test exists; no confirmation-to-disease integration |
| Mobile tests | Yes | Partial | Mocked | No | API and Disease screen tests exist; no server-bound receipt test |
| Real-device E2E proof | No | No | No | No | No current physical-device evidence for this controlled-beta flow |

## Pre-change blockers

1. The public crop-ID response is not the required auditable contract (no request ID, bilingual structured reason, confidence source, provider model/version, quality/plant check objects, or timestamp).
2. Gemini output is JSON-validated after receipt, but the request does not use the provider's strongest response-schema constraint.
3. Provider retry/rate-limit/timeout mapping is incomplete.
4. Image thresholds are hard-coded and decompression-bomb handling/resource limits are incomplete.
5. Farmer confirmation and correction are client-only; neither is bound to authenticated ownership, image identity, expiry, or original request ID.
6. Disease routing does not consume a server-validated crop-identification confirmation.
7. The separate dedicated crop-identity router is registered even though the controlled-beta decision says Gemini is primary and dedicated crop ID is deferred.
8. No real Gemini, emulator, production API, or physical-device E2E evidence is available for this audit.

## Initial implementation plan

1. Harden and version the Gemini response/provider contract and image gate without changing model artifacts.
2. Add a server-side confirmation/correction receipt boundary with ownership, image hash, expiry and replay protection.
3. Make the mobile flow confirm through the server and retain the resulting receipt before disease routing.
4. Keep all disease inference fail closed until the receipt is actually enforced by the relevant disease endpoint; do not present a local Boolean as sufficient proof.
5. Add focused backend/mobile/security tests and documentation, then run complete validation suites and review the final diff.
