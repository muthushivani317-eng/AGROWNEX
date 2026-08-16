# AgrowAI temporary crop-identification controlled-beta audit

## 1. Final status

```text
CROP_IDENTIFICATION_AUDIT=PARTIAL
TEMP_GEMINI_CROP_ID_IMPLEMENTATION=PARTIAL
IMAGE_QUALITY_GATE=PARTIAL
PLANT_NON_PLANT_GATE=PARTIAL
FARMER_CONFIRMATION_FLOW=PARTIAL
REQUESTED_CROP_VALIDATION=PASS
DISEASE_MODEL_ROUTING=PARTIAL
GENERAL_FARMER_RELEASE=BLOCKED
REAL_GEMINI_VALIDATION=NOT_RUN
PHYSICAL_DEVICE_E2E=NOT_RUN
READY_FOR_INTERNAL_TESTING=NO
READY_FOR_PILOT_TESTING=NO
READY_FOR_GENERAL_FARMER_RELEASE=NO
```

## 2. Executive conclusion

A controlled-role Gemini endpoint, conservative image heuristics, six-crop parsing and a photo-first mobile screen existed. They were not a complete safety chain: provider output was not schema-constrained at request time, the response lacked audit fields, confirmation was a client Boolean, disease routing did not consume the crop-ID request, and a deferred dedicated crop-ID router remained registered.

The repair adds a strict provider/public contract, schema-constrained Gemini request, bounded retries, content-aware image checks, actor/image/crop/expiry-bound one-time receipts, server confirmation/correction, mobile receipt handling, and receipt enforcement in Banana, legacy Paddy/Cotton/Groundnut, and restricted Chilli/Redgram routes. The separate dedicated crop-ID router was unregistered; its artifacts were not modified.

The result remains partial because the receipt store is process-local, Tamil text is intentionally a human-review placeholder, several image thresholds remain hard-coded, no independent validated plant detector exists, and no real Gemini or physical-device E2E run was available.

## 3. Pre-change audit matrix

The full timestamped matrix and evidence are in `PRE_CHANGE_AUDIT.md`. Summary:

| Component | Exists | Connected | Tested | Production-ready | Evidence |
|---|---:|---:|---:|---:|---|
| Image corruption check | Yes | Yes | Yes | Partial | `_validated_image`; focused upload tests |
| File type validation | Yes | Yes | Yes | Partial | MIME plus decoded-format equality |
| File size validation | Yes | Yes | Yes | Partial | 8 MiB bounded read |
| Minimum image resolution | Yes | Yes | Yes | Partial | `assess_image_safety` |
| Blur detection | Partial | Yes | Yes | No | conservative detail heuristic, not validated blur model |
| Brightness/exposure check | Yes | Yes | Yes | Partial | dark/overexposed heuristics |
| Plant/non-plant validation | Temporary | Yes | Mocked | No | provider-assisted outcome, explicitly labelled temporary |
| Gemini crop-ID client | Yes | Yes | Mocked | Partial | adapter and strict response JSON schema |
| Six-crop constrained output | Yes | Yes | Yes | Partial | Pydantic literal and mobile parser |
| Unsupported-crop handling | Yes | Yes | Yes | Partial | `unsupported`/null crop fails closed |
| Crop-ID confidence or uncertainty | Yes | Yes | Yes | Partial | nullable self-report with explicit source |
| Farmer confirmation UI | Yes | Yes | Yes | Partial | server confirmation and opaque receipt; process-local state |
| Farmer rejection path | Yes | Yes | Yes | Partial | explicit correction source; no training-label use |
| Requested-crop mismatch handling | Yes | Yes | Yes | Partial | receipt validates actor/crop/image/expiry/replay |
| Disease-model routing | Yes | Yes | Yes | Partial | receipt enforced; no live model E2E in this audit |
| Model version logging | Yes | Partial | Partial | Partial | runtime-specific metadata; joined durable audit absent |
| Disease calibration | Existing | Yes | Existing | Partial | frozen policies unchanged |
| Disease abstention | Existing | Yes | Existing | Partial | frozen policies unchanged |
| Tamil result rendering | Partial | Partial | Partial | No | untranslated text remains `HUMAN_TRANSLATION_REVIEW_REQUIRED` |
| English result rendering | Yes | Yes | Yes | Partial | controlled-beta states render |
| Internal tester restriction | Yes | Yes | Yes | Partial | `ControlledTester` server dependency |
| General farmer release blocked | Yes | Yes | Yes | Partial | receipt issuance requires controlled role |
| Unit tests | Yes | N/A | Yes | Partial | focused suites pass |
| Backend integration tests | Yes | Yes | Mocked | Partial | ASGI upload/confirm and route safety tests |
| Mobile tests | Yes | Yes | Mocked | Partial | 749 tests pass |
| Real-device E2E proof | No | No | No | No | not run |

## 4. Files changed

- `backend/app/gemini_crop_identification/{schemas,service,provider,prompt,router,confirmation}.py`: strict contracts, provider hardening, image gate, receipt lifecycle.
- `backend/app/api/v1/router.py`: unregister deferred dedicated crop-ID router; keep temporary Gemini router.
- `backend/app/{banana_v3,legacy_joint,restricted_crops}/api_router.py`: enforce receipt ownership/crop/image/expiry/replay before inference.
- `backend/tests/test_gemini_crop_identification.py`, `test_crop_ood_api.py`, `test_crop_domain_gate.py`, `test_restricted_crop_e2e.py`: contract, confirmation, safety and route tests.
- `backend/.env.crop-id-emulator.example`: documented provider variables without secrets.
- `agrow-ai/features/cropIdentification/*`: strict mobile contract and confirmation API.
- `agrow-ai/features/disease/screens/DiseaseScreen.tsx`: photo-first Gemini flow and server confirmation receipt.
- `agrow-ai/features/multiCropDiagnosis/{adapters,types}.ts` and tests: require/pass receipt.
- `agrow-ai/features/bananaV3/{bananaV3Api,screens/BananaDiseaseDetectionScreen}.tsx`: require/pass receipt without changing model behaviour.
- `docs/crop_identification/*CONTROLLED_BETA*`, `TEMPORARY_*`, `CROP_ID_REASON_CODES.md`: architecture, API, environment, reason codes, provider replacement, validation, limitations, rollback and data handoff.
- `reports/crop_identification_controlled_beta_audit/20260803T193824Z/*`: immutable pre-change audit and final report.

The worktree contained many unrelated pre-existing changes and untracked files. They were preserved and not attributed to this task.

## 5. Architecture implemented

Quality decoding precedes Gemini; the provider-assisted plant outcome and crop result share one strict schema. Free-form crop names and extra keys are rejected. Farmer confirmation/correction creates an opaque 15-minute receipt bound to actor, SHA-256 image identity and canonical crop. A receipt is one-time and disease endpoints validate it before runtime dispatch. Provider errors map to safe categories, retries are capped, prompt injection is explicitly ignored, raw provider output is not returned, and secrets/raw images are not logged. Controlled tester authorization remains server-side. Crop ID never renders recommendations; frozen disease calibration, abstention and recommendation safety are unchanged.

## 6. Supported-crop runtime status

| Crop | Crop ID enabled | Farmer confirmation | Disease runtime loadable | Disease route enabled | Final status |
|---|---:|---:|---:|---:|---|
| Banana | Yes | Required | Evidence says yes | Controlled receipt only | Internal validation required |
| Paddy | Yes | Required | Legacy joint runtime | Controlled receipt only | Internal validation required |
| Cotton | Yes | Required | Legacy joint runtime | Controlled receipt only | Internal validation required |
| Groundnut | Yes | Required | Legacy joint runtime | Controlled receipt only | Internal validation required |
| Chilli | Yes | Required | Restricted runtime evidence | Restricted testers only | General farmer disabled |
| Redgram | Yes | Required | Restricted runtime evidence | Restricted testers only | General farmer disabled; leaf spot forced abstain |

## 7. Tests executed

- `pytest ...test_gemini... test_image_safety... test_crop_ood... test_crop_domain_gate... test_restricted_crop_e2e... test_legacy_joint...`: 43 passed, 0 failed, 0 skipped.
- Full backend `pytest backend/tests`: 816 passed, 4 failed, 1 skipped, 27 setup errors. The task-related crop-domain expectation was corrected afterward and passes focused validation. Remaining failures/errors are unrelated recommendation/growth assertions, inaccessible Redgram artifact path, and sandbox-denied pytest temp directories. This is not reported as a green full suite.
- Focused Jest: 37 passed initially; final relevant adapter/API/screen suites pass.
- Full Jest `--runInBand --no-cache --silent`: 117 suites, 749 tests passed; 0 failed, 0 skipped.
- TypeScript `tsc --noEmit`: pass.
- Ruff on all changed backend/task tests: pass.
- Secret scan: pass.

## 8. Build validation

- Backend import: pass, FastAPI initialized in test mode with 183 routes.
- Mobile TypeScript: pass.
- Mobile full tests: 749/749 pass.
- Expo Doctor: 19/20; existing `react-native-gesture-handler` version mismatch (`~3.1.0` expected, `2.32.0` found).
- Production Android JS export: pass, 4,701 modules, Hermes bundle generated. No Gemini secret identifier/provider URL found in output scan.
- Android APK: not built; the requested build-or-production-bundle gate was satisfied by Expo production export.

## 9. Security and fail-closed validation

Strict schemas reject arbitrary crops, disease labels, malformed JSON and extra provider keys. Controlled roles gate request creation and confirmation. Confirmation validates ownership, canonical crop, image hash, expiry and one-time use; forged/missing tokens stop before model inference. Mobile adapters refuse a local confirmation Boolean without a server receipt. Unsupported/non-plant/uncertain results cannot automatically reach disease inference. No raw token, image, API key, internal path or raw provider internals are returned or logged.

## 10. Real validation status

- Mocked Gemini tests: PASS (not an accuracy claim).
- Real Gemini API tests: NOT_RUN; no live credential/provider call was made.
- Emulator tests: NOT_RUN for this final flow.
- Physical-device tests: NOT_RUN.
- Production API tests: NOT_RUN.

## 11. Remaining blockers

1. Replace process-local confirmation storage with shared durable state and atomic replay protection before multi-worker pilot deployment.
2. Complete human-reviewed Tamil strings; placeholders are intentionally not fabricated.
3. Validate/tune documented quality thresholds with approved evidence and move all remaining heuristics to typed configuration.
4. Execute real Gemini tests and the controlled physical-device matrix.
5. Resolve Expo dependency mismatch.
6. Resolve unrelated full-backend failures and sandbox/file-permission errors, then obtain a completely green full backend suite.
7. Review restricted Chilli/Redgram route policy against registry `disease_detection_enabled=false`; do not interpret restricted internal access as farmer enablement.

## 12. Exact next actions

1. Internal testing: shared receipt store, reviewed Tamil, green complete backend suite, real Gemini smoke test, then controlled Android E2E for all fail-closed cases.
2. Pilot testing: production-like security/privacy review, KVK/plant-pathology review, signed test protocol, monitoring/rollback and explicit per-runtime approval.
3. Dedicated replacement: collect consented, licensed, diverse, duplicate-controlled data; seal evaluation; train only after a new approval audit; implement the existing provider interface.
4. General farmer release: remain blocked until field evidence, privacy/safety approval, operational monitoring and explicit release authorization exist.

## 13. Final declaration

```text
DEDICATED_CROP_ID_TRAINING_STARTED=NO
GEMINI_USED_ONLY_FOR_TEMPORARY_CROP_IDENTIFICATION=YES
FARMER_CONFIRMATION_REQUIRED=YES
GEMINI_DISEASE_DIAGNOSIS_ALLOWED=NO
GENERAL_FARMER_RELEASE_ALLOWED=NO
UNVERIFIED_ACCURACY_CLAIMS_MADE=NO
```
