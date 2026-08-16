# AgrowAI Model Factual Data Report

Audit date: 2026-08-07  
Scope searched: repository source plus `agrowai_autonomous_pipeline/EVIDENCE/`, `backend/model_artifacts/`, `backend/app/banana_v3/artifacts/`, `training_tools/`, `datasets/`, `docs/`, `reports/`, and model evaluation/configuration JSON, CSV and Markdown artifacts.

This is an evidence report only. No recommendation or estimated metric is included. `NOT FOUND` means no repository artifact containing that requested datum was found. “Provisional test” and “sealed test” retain the repository’s terminology and are not relabeled as official or field validation.

## 1. Banana V3 — healthy gate and disease classifier

### 1.1 Model card / config

| Field | Exact repository value | Evidence |
|---|---|---|
| Model version | `banana-v3.0.0` | `backend/app/banana_v3/artifacts/runtime/banana_v3_runtime_config.json` |
| Bundle version | `banana-v3-production-bundle-1` | same file |
| Healthy-gate architecture/identifier | `banana_v3_healthy_gate_mobilenetv3_small_v1` | same file |
| Disease-classifier architecture/identifier | `banana_v3_disease_classifier_mobilenetv3_small_v1` | same file |
| Runtime | `onnx_then_pytorch` | same file |
| Input | NCHW, float32, `[null, 3, 224, 224]`; RGB; shorter side 256; center crop 224×224; ImageNet mean/std | same file |
| Healthy-gate classes | `banana__healthy`, `banana__diseased` | `runtime/class_mappings.json` |
| Disease classes | `banana__cordana_leaf_spot`, `banana__pestalotiopsis_leaf_spot`, `banana__sigatoka_leaf_spot` | same file |
| Training dataset total | **NOT FOUND** | No dataset-size receipt exists in the frozen Banana V3 bundle or matching report tree. |
| Training per-class counts | **NOT FOUND** | Same search result. |
| Train/val/test split method | **NOT FOUND** | No split manifest or report tied to the frozen checkpoint hashes was found. |
| Plant/farm/field grouping | **NOT FOUND** | No such grouping field was found. |
| Deployment status | `PRODUCTION_INTEGRATED_FIELD_VALIDATION_IN_PROGRESS` | `runtime/banana_v3_runtime_config.json` |
| Field validation | `IN_PROGRESS` | same file and `runtime/model_lineage.json` |
| Official Tamil Nadu field accuracy claim | `false` | same files |

Checkpoint hashes:

- Healthy gate: `838d40714ba6c43ec2e6c5eb4af1c895a7f739ab46e7ee38d58d50cd55e01e98`.
- Disease classifier: `056b97c4faca32356ad6e1ac8b3d7f6166952a9a149ab518d41fdadd798e467e`.

### 1.2 Evaluation metrics

| Requested metric | Exact value |
|---|---|
| Held-out test overall accuracy — healthy gate | **NOT FOUND** |
| Held-out test overall accuracy — disease classifier | **NOT FOUND** |
| Held-out test per-class precision/recall/F1 | **NOT FOUND** |
| Held-out test confusion matrix | **NOT FOUND** |
| Held-out test abstention count/rate | **NOT FOUND** |
| Internal replay result | `NOT_RECORDED_IN_THIS_PACKAGE` (`runtime/model_lineage.json`) |

Calibration and frozen thresholds:

| Stage/class | Temperature | Confidence threshold | Margin threshold |
|---|---:|---:|---:|
| Healthy gate — `banana__healthy` | 2.090103190616 | 0.65 | 0.30 |
| Healthy gate — `banana__diseased` | 2.090103190616 | 0.50 | 0.00 |
| Disease — `banana__cordana_leaf_spot` | 0.823204678118 | 0.34 | 0.86 |
| Disease — `banana__pestalotiopsis_leaf_spot` | 0.823204678118 | 0.34 | 0.88 |
| Disease — `banana__sigatoka_leaf_spot` | 0.823204678118 | 0.34 | 0.00 |

Sources: `artifacts/calibration/*_temperature.json` and `artifacts/thresholds/*_selected_thresholds.json`.

Field-validation-specific results:

- Dates: **NOT FOUND**.
- Sample size: **NOT FOUND**.
- Ground-truth labeler/reviewer: **NOT FOUND**.
- Results: **NOT FOUND**.
- Only status found: `field_validation_status: "IN_PROGRESS"`.

### 1.3 Known gaps — exact artifact text

Exact status text:

> `"field_validation_status": "IN_PROGRESS"`

> `"deployment_status": "PRODUCTION_INTEGRATED_FIELD_VALIDATION_IN_PROGRESS"`

> `"official_tamil_nadu_field_accuracy_claim": false`

> `"internal_replay_status": "NOT_RECORDED_IN_THIS_PACKAGE"`

No Banana-V3-specific `phase_summary.md`, `blockers.md`, or `next_actions.md` was found under `agrowai_autonomous_pipeline/EVIDENCE/`. Banana is mentioned in the 6-class crop-identity evidence listed in §7; those references concern crop identity, not the Banana V3 disease models.

### 1.4 Runtime gate code

- Score calibration and threshold decision: `backend/app/banana_v3/decision_engine.py:28-43`.
- Accepted decision-code mapping: `backend/app/banana_v3/decision_engine.py:57+`.
- Healthy gate must accept before further action: `backend/app/banana_v3/inference_service.py:101-109`.
- Disease acceptance/abstention and follow-up/human-review flags: `backend/app/banana_v3/inference_service.py:109-136`.
- Frozen fallback thresholds duplicated as runtime defaults: `backend/app/banana_v3/config.py:26-32`.

## 2. Chilli restricted classifier

### 2.1 Model card / config

| Field | Exact value | Evidence |
|---|---|---|
| Runtime/model | `chilli_mobilenetv3_small_v1_restricted` / `chilli_mobilenetv3_small_v1` | `config/runtime_config.json` |
| Architecture | `mobilenet_v3_small` | same file |
| Checkpoint epoch/hash | 5 / `adab7c3eefa009b78e1c9d335fc088d74b5f2b456eb7196950da385ed761ec26` | same file |
| Frozen timestamp | `20260730T132857Z` | same file |
| Original readable images | 1,856 | `receipts/dataset_summary_final.json` |
| Excluded images | 653 | same file |
| Cleaned/training-pool images | 1,203 | same file |
| `chilli__bacterial_spot` | 147 | same file |
| `chilli__cercospora_leaf_spot` | 175 | same file |
| `chilli__leaf_curl_virus` | 423 | same file |
| `chilli__healthy` | 458 | same file |

Split counts:

| Split | Total | bacterial spot | cercospora | leaf curl virus | healthy |
|---|---:|---:|---:|---:|---:|
| Training | 843 | 103 | 123 | 296 | 321 |
| Development validation | 180 | 22 | 26 | 63 | 69 |
| Calibration | 91 | 11 | 13 | 33 | 34 |
| Provisional test | 89 | 11 | 13 | 31 | 34 |

Split method: seed `41212`, target proportions 0.70/0.15/0.075/0.075. Integrity evidence reports path overlap 0, SHA overlap 0 and **duplicate-family overlap 0**. Therefore the recorded grouping unit is duplicate family, not independent plant/farm/field. Plant-level split: **NOT FOUND**. Farm/field-level split: **NOT FOUND**.

Release flags from `policy/RESTRICTED_RUNTIME_POLICY.json`:

- `runtime_status: "RESTRICTED_FAIL_CLOSED_RUNTIME"`.
- `public_dataset_provisional_result: true`.
- `field_validation_completed: false`.
- `farmer_accuracy_claim_allowed: false`.
- `official_accuracy_claim_allowed: false`.
- `expert_verified_claim_allowed: false`.

### 2.2 Provisional held-out evaluation

Evaluation: `ONE_TIME_PROVISIONAL_TEST_COMPLETE`, timestamp `20260730T132433Z`, sample count 89.

- Accuracy: **0.9775280898876404**.
- Macro F1: **0.9621175523349437**.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `chilli__bacterial_spot` | 1.0 | 0.8181818181818182 | 0.9 | 11 |
| `chilli__cercospora_leaf_spot` | 0.9285714285714286 | 1.0 | 0.9629629629629629 | 13 |
| `chilli__healthy` | 0.9714285714285714 | 1.0 | 0.9855072463768116 | 34 |
| `chilli__leaf_curl_virus` | 1.0 | 1.0 | 1.0 | 31 |

Confusion matrix; row/column order: bacterial spot, cercospora, healthy, leaf curl virus:

```text
[[ 9, 1, 1, 0],
 [ 0,13, 0, 0],
 [ 0, 0,34, 0],
 [ 0, 0, 0,31]]
```

Calibration:

- Method: temperature scaling.
- Temperature: `1.0000321865081787`.
- Calibration samples: 91.
- Accuracy before/after: `0.989010989010989` / `0.989010989010989`.
- NLL before/after: `0.010529522262500205` / `0.010529509445049115`.
- ECE-15 before/after: `0.006105986270275745` / `0.006105931250603645`.
- Multiclass Brier before/after: `0.007521154866448731` / `0.007521087914845194`.

Abstention policy:

- Confidence ≥ `0.99` **AND** margin ≥ `0.99`; otherwise abstain.
- Test accepted: 87; abstained: 2; coverage `0.9775280898876404`.
- Test abstention rate: **2/89 = 0.02247191011235955 = 2.247191011235955%**.
- Accepted accuracy: `1.0`; accepted errors: 0.

Field validation: `field_validated: false`; dates, field sample count, labeler and results: **NOT FOUND**.

### 2.3 Known gaps — exact policy text

> `"public_dataset_provisional_result": true`

> `"field_validation_completed": false`

> `"tamil_nadu_accuracy_claim_allowed": false`

> `"farmer_accuracy_claim_allowed": false`

> `"official_accuracy_claim_allowed": false`

Chilli appears in the 6-class crop-identity EVIDENCE files summarized in §7, but no chilli-classifier-specific phase summary/blocker/next-action file was found.

### 2.4 Runtime gate code

- Packaged frozen logic: `backend/model_artifacts/frozen_runtime/chilli_mobilenetv3_small_v1_restricted/runtime/restricted_runtime.py`.
- API sanitation and fail-closed non-finite/error mapping: `backend/app/restricted_crops/api_router.py:51-82,141-156`.
- Policy fields used by the registered restricted runtime come from `policy/RESTRICTED_RUNTIME_POLICY.json`.

## 3. Redgram V2 restricted classifier

### 3.1 Model card / config

| Field | Exact value | Evidence |
|---|---|---|
| Runtime/model | `redgram_mobilenetv3_small_v1_restricted` / `redgram_mobilenetv3_small_v1` | `config/runtime_config.json` |
| Architecture | `mobilenet_v3_small` | same file |
| Checkpoint epoch/hash | 11 / `5b95e1658f6bb0d83a3cef8b455533599482d102b86a326f184477f214269e72` | receipts/policy |
| Frozen timestamp | `20260730T112949Z` | runtime config |
| Original readable images | 973 | `receipts/dataset_summary_final.json` |
| Excluded images | 276 | same file |
| Cleaned images | 697 | same file |
| `redgram__healthy` | 195 | same file |
| `redgram__leaf_spot` | 269 | same file |
| `redgram__sterility_mosaic` | 233 | same file |

Split counts:

| Split | Total | healthy | leaf spot | sterility mosaic |
|---|---:|---:|---:|---:|
| Training | 487 | 136 | 188 | 163 |
| Development validation | 105 | 29 | 41 | 35 |
| Calibration | 53 | 15 | 20 | 18 |
| Provisional test | 52 | 15 | 20 | 17 |

Split method: seed `41212`; 0.70/0.15/0.075/0.075; path overlap 0, SHA overlap 0, duplicate-family overlap 0. Independent plant/farm/field split: **NOT FOUND**.

Release flags:

- `status: "RESTRICTED_FAIL_CLOSED_RUNTIME"`.
- `three_class_automatic_diagnosis_ready: false`.
- `leaf_spot_automatic_acceptance_enabled: false`.
- `field_validated: false`.
- `farmer_accuracy_claim_allowed: false`.
- `official_accuracy_claim_allowed: false`.

### 3.2 Provisional held-out evaluation

Evaluation timestamp `20260730T112549Z`, sample count 52.

- Accuracy: **0.8653846153846154**.
- Macro F1: **0.8674317856269433**.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `redgram__healthy` | 1.0 | 0.9333333333333333 | 0.9655172413793104 | 15 |
| `redgram__leaf_spot` | 0.7407407407407407 | 1.0 | 0.851063829787234 | 20 |
| `redgram__sterility_mosaic` | 1.0 | 0.6470588235294118 | 0.7857142857142857 | 17 |

Confusion matrix; order healthy, leaf spot, sterility mosaic:

```text
[[14,1, 0],
 [ 0,20,0],
 [ 0,6,11]]
```

Calibration:

- Temperature `3.1163787841796875`; samples 53.
- Accuracy before/after: `0.9245283018867925` / `0.9245283018867925`.
- NLL before/after: `0.5050756021776911` / `0.25510837453020363`.
- ECE-15 before/after: `0.07917298573367998` / `0.0377901871249361`.
- Brier before/after: `0.15009366646747677` / `0.14202755080297094`.

Class policy:

- Healthy: confidence ≥ 0.4, margin ≥ 0.0.
- Leaf spot: `ALWAYS_ABSTAIN`.
- Sterility mosaic: confidence ≥ 0.4, margin ≥ 0.0.
- Test accepted: 25; abstained: 27; coverage `0.4807692307692308`.
- Test abstention rate: **27/52 = 0.5192307692307693 = 51.92307692307693%**.
- Accepted accuracy `1.0`; accepted errors 0.

Field validation: false. Dates, field sample count, labeler and results: **NOT FOUND**.

### 3.3 Known gaps — exact policy text

> `"three_class_automatic_diagnosis_ready": false`

> `"leaf_spot_automatic_acceptance_enabled": false`

> `"abstention_code": "REDGRAM_LEAF_SPOT_AUTOMATIC_ACCEPTANCE_DISABLED"`

> `"field_validated": false`

> `"official_accuracy_claim_allowed": false`

Redgram appears in 6-class crop-identity evidence (§7); no Redgram-V2-classifier-specific phase summary/blocker/next-action file was found.

### 3.4 Runtime gate code

- Current Redgram V2 score/margin gate: `backend/app/redgram_v2/runtime.py:89-113`.
- Packaged restricted classifier policy/runtime: `backend/model_artifacts/frozen_runtime/redgram_mobilenetv3_small_v1_restricted/runtime/restricted_runtime.py`.
- Unified restricted API output sanitation: `backend/app/restricted_crops/api_router.py:51-82`.

## 4. Legacy joint classifier — paddy, cotton, groundnut

### 4.1 Model card / config

| Field | Exact value |
|---|---|
| Bundle/version | `legacy_joint_v1_crop_constrained` |
| Architecture | `mobilenetv3_small` |
| Checkpoint epoch | 6 |
| Checkpoint hash | `f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117` |
| Output classes | 9 |
| Paddy classes | `paddy_healthy`, `rice_blast`, `rice_brown_leaf_spot`, `rice_tungro` |
| Cotton classes | `cotton_fusarium_wilt`, `cotton_healthy`, `cotton_verticillium_wilt` |
| Groundnut classes | `groundnut_healthy`, `groundnut_rust` |
| Training dataset total/per class | **NOT FOUND** |
| Train/val/test split counts | **NOT FOUND** |
| Split method/unit | **NOT FOUND**; a split-manifest hash/path is recorded, but the manifest itself is not present in the repository bundle. |
| Farm/field grouping | **NOT FOUND** |

The lineage records `development_used_for_reporting_only: true`, `calibration_used_for_temperature_and_threshold_selection: true`, `provisional_test_used: false`, and `model_weights_modified: false`.

Release/integration flags in `reports/crop_constrained_recalibration_decision.json`:

- `decision: "READY_FOR_BACKEND_INTEGRATION"`.
- `app_enablement_allowed: false`.
- `backend_integration_performed: false` (historical bundle decision artifact; current source later integrates routes).
- `provisional_test_opened: false`.

### 4.2 Evaluation metrics

Held-out/provisional test:

- Overall test accuracy: **NOT FOUND**.
- Test per-class precision/recall/F1: **NOT FOUND**.
- Test confusion matrix: **NOT FOUND**.
- Test abstention rate: **NOT FOUND**.

Development-only metrics found:

#### Paddy — development, 1,096 samples

Macro F1 all predictions: `0.8691918644860013`.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `paddy_healthy` | 0.9292035398230089 | 0.8898305084745762 | 0.9090909090909091 | 236 |
| `rice_blast` | 0.8412698412698413 | 0.803030303030303 | 0.8217054263565892 | 198 |
| `rice_brown_leaf_spot` | 0.8096590909090909 | 0.8742331288343558 | 0.8407079646017699 | 326 |
| `rice_tungro` | 0.9148936170212766 | 0.8958333333333334 | 0.9052631578947369 | 336 |

Development confusion matrix: **NOT FOUND**.

#### Cotton — development, 116 samples

Macro F1: `1.0`; all three classes precision/recall/F1 `1.0`; supports 47/26/43. Confusion matrix: **NOT FOUND**.

#### Groundnut — development, 108 samples

Macro F1: `1.0`; both classes precision/recall/F1 `1.0`; supports 90/18. Confusion matrix: **NOT FOUND**.

Calibration/abstention:

| Crop | Calibration n | Temperature | Confidence | Margin | Accepted | Abstained | Coverage | Accepted accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Paddy | 548 | 1.185621730465097 | 0.75 | 0.0 | 455 | 93 | 0.8302919708029197 | 0.9494505494505494 |
| Cotton | 59 | 0.11945409775578275 | 0.5 | 0.0 | 59 | 0 | 1.0 | 1.0 |
| Groundnut | 53 | 0.5215946352798655 | 0.5 | 0.0 | 53 | 0 | 1.0 | 1.0 |

These abstention figures are calibration-set results, not held-out test results. Paddy calibration abstention rate is `93/548 = 0.1697080291970803 = 16.97080291970803%`; cotton and groundnut are 0%.

Field validation dates/sample/labelers/results: **NOT FOUND**.

### 4.3 Known gaps — exact artifact text

> `Provisional-test material was not opened or used.`

> `Development subsets were used only for development-labelled reporting.`

> `"app_enablement_allowed": false`

> `"provisional_test_opened": false`

No legacy-joint-specific `phase_summary.md`, `blockers.md`, or `next_actions.md` was found under EVIDENCE.

### 4.4 Runtime gate and routing code

- Crop-constrained logits and crop threshold loading: `backend/app/legacy_joint/runtime.py:40-80`.
- Confidence, margin and accept/abstain decision: `backend/app/legacy_joint/runtime.py:127-137`.
- Reported thresholds: `backend/app/legacy_joint/runtime.py:149-156`.
- Routing policy requires `explicit_user_crop_confirmation`, sets `ai_crop_verification: false`, and restricts logits to the confirmed crop before calibration/softmax (`runtime/crop_routing_policy.json`).

## 5. Crop identity model — 4-class

### 5.1 Model card / config

| Field | Exact value |
|---|---|
| Model | `crop_identity_mobilenetv3_small_v1` |
| Version | `v1` |
| Architecture | `mobilenet_v3_small` |
| Pretraining | `torchvision IMAGENET1K_V1` |
| Classes | banana, paddy, cotton, groundnut |
| Approved dataset total | 8,246 |
| Banana | 762 |
| Paddy | 6,212 |
| Cotton | 660 |
| Groundnut | 612 |

Split counts:

| Split | banana | paddy | cotton | groundnut | Total |
|---|---:|---:|---:|---:|---:|
| Training | 534 | 4,348 | 462 | 428 | 5,772 |
| Development validation | 114 | 932 | 99 | 92 | 1,237 |
| Calibration | 57 | 466 | 50 | 46 | 619 |
| Provisional test | 57 | 466 | 49 | 46 | 618 |

Split evidence: random seed `20260729`; `family_leakage: 0`, `reserved_leakage: 0`, `sha_leakage: 0`. The recorded grouping is duplicate family/image hash, not plant/farm/field. Plant/farm/field grouping: **NOT FOUND**.

Release flags:

- `field_validation_status: "PUBLIC_DATASET_PROVISIONAL"`.
- `official_accuracy_claim: false`.
- `general_farmer_inference_authorized: false`.
- `non_plant_rejection_proven: false`.
- `shortcut_risk: "HIGH"` in evaluation files.

### 5.2 Provisional held-out evaluation

Provisional test samples: 618.

- Top-1 accuracy: **1.0**.
- Macro F1: **1.0**.
- Balanced accuracy: **1.0**.
- ECE: `0.001161447842605412`.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| banana | 1.0 | 1.0 | 1.0 | 57 |
| paddy | 1.0 | 1.0 | 1.0 | 466 |
| cotton | 1.0 | 1.0 | 1.0 | 49 |
| groundnut | 1.0 | 1.0 | 1.0 | 46 |

Confusion matrix; order banana, paddy, cotton, groundnut:

```text
[[57,  0, 0, 0],
 [ 0,466, 0, 0],
 [ 0,  0,49, 0],
 [ 0,  0, 0,46]]
```

Calibration/abstention:

- Temperature `0.2968480513819703`.
- NLL `0.00046743001439608634` → `1.943766095282724e-08`.
- ECE `0.00046563148498535156` → `0.0`.
- Class thresholds all 0.5; fallback 0.5; margin threshold 1.0; entropy threshold `2.3740658328108566e-09`.
- Test accepted 592; abstained 26; coverage `0.9579288025889967`; accepted accuracy `1.0`.
- Abstention rate: **26/618 = 0.04207119741100324 = 4.207119741100324%**.

Field validation: `PUBLIC_DATASET_PROVISIONAL`; dates/sample/labelers/field results: **NOT FOUND**.

### 5.3 Known gaps — exact artifact text

> `"shortcut_risk": "HIGH"`

> `"field_validation_status": "PUBLIC_DATASET_PROVISIONAL"`

> `"general_farmer_inference_authorized": false`

> `"non_plant_rejection_proven": false`

The EVIDENCE crop-ID phase summaries and generic blockers relevant to this model are in §7.

### 5.4 Runtime code

- Artifact status/integrity requirements: `backend/app/crop_identity/artifacts.py:151-197`.
- Confidence, top-two margin, entropy, requested-crop match and abstention: `backend/app/crop_identity/runtime.py:139-159`.
- Returned threshold metadata: `backend/app/crop_identity/runtime.py:167-188`.
- Pipeline quality/identity fail-closed decisions: `backend/app/crop_identity/pipeline.py:33-62`.

## 6. Crop identity model — 6-class internal

### 6.1 Model card / config

| Field | Exact value |
|---|---|
| Model ID | `crop_id_six_class_internal_v1` |
| Version | `1.0.0-internal` |
| Architecture | `mobilenet_v3_small` |
| Model SHA-256 | `61dab083068bfdee463111c154cff0c22cf52fe9a7afc97bab2382e802fd4e97` |
| Classes | banana, paddy, cotton, groundnut, chilli, redgram |
| Input preprocessing | resize 184, center crop 160, ImageNet mean/std |
| Total images | 19,174 |
| Banana | 1,289 |
| Paddy | 7,684 |
| Cotton | 1,322 |
| Groundnut | 1,720 |
| Chilli | 6,306 |
| Redgram | 853 |

Split counts:

| Crop | Train | Validation | Calibration | Sealed test | Total |
|---|---:|---:|---:|---:|---:|
| Banana | 902 | 193 | 65 | 129 | 1,289 |
| Paddy | 5,379 | 1,153 | 384 | 768 | 7,684 |
| Cotton | 926 | 198 | 66 | 132 | 1,322 |
| Groundnut | 1,204 | 258 | 86 | 172 | 1,720 |
| Chilli | 4,414 | 946 | 315 | 631 | 6,306 |
| Redgram | 597 | 128 | 43 | 85 | 853 |

Split method: grouped split with path, SHA and family leakage all zero (`split_integrity.json`). Family counts are recorded separately. This is a duplicate/group-family split, not demonstrated independent plant/farm/field splitting. Plant/farm/field grouping: **NOT FOUND**.

Release flags in `runtime_config.json`:

- `farmer_confirmation_required: true`.
- `general_farmer_release: "BLOCKED"`.
- `official_accuracy_claim: false`.
- `acceptance: "PARTIAL_RESTRICTED_INTERNAL_ONLY"`.
- `banana_data_quality: "LIMITED"`.
- `licence_and_identity: "PROVISIONAL_INTERNAL_USE_ONLY"`.

### 6.2 One-time sealed-test metrics

Sealed-test sample count: 1,917; access count 1.

- Accuracy: **0.9968701004981995**.
- Balanced accuracy: **0.9939873218536377**.
- Macro precision: **0.9940356612205505**.
- Macro recall: **0.9939873218536377**.
- Macro F1: **0.9940066337585449**.
- Top-2 accuracy: **1.0**.
- NLL: `0.013156399130821228`.
- ECE: `0.0024598716081527527`.
- Brier: `0.00469653494656086`.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| banana | 1.0 | 0.9922480583190918 | 0.9961089491844177 | 129 |
| paddy | 1.0 | 1.0 | 1.0 | 768 |
| cotton | 0.9849624037742615 | 0.9924242496490479 | 0.9886792302131653 | 132 |
| groundnut | 0.9941860437393188 | 0.9941860437393188 | 0.9941860437393188 | 172 |
| chilli | 0.996830403804779 | 0.996830403804779 | 0.996830403804779 | 631 |
| redgram | 0.9882352948188782 | 0.9882352948188782 | 0.9882352948188782 | 85 |

Confusion matrix; row/column order banana, paddy, cotton, groundnut, chilli, redgram:

```text
[[128,  0,  0,  0,  1, 0],
 [  0,768,  0,  0,  0, 0],
 [  0,  0,131,  0,  1, 0],
 [  0,  0,  0,171,  0, 1],
 [  0,  0,  2,  0,629, 0],
 [  0,  0,  0,  1,  0,84]]
```

Calibration/abstention:

- Calibration rows: 959.
- Temperature `0.25`.
- NLL `0.053813643753528595` → `0.002303415909409523`.
- ECE `0.048537557071540505` → `0.0017082175763789564`.
- Multiclass Brier after: `0.0014071156037971377`.
- Confidence threshold 0.5; margin threshold 0.0.
- Sealed test accepted 1,917; abstained 0; coverage 1.0; accepted errors 6.
- Sealed-test abstention rate: **0/1917 = 0%**.
- Separate safety evaluation: all 600 readable excluded records accepted; false-accept rate 100% (`EVIDENCE/.../safety_report.md`, `blockers.md`).

Field validation:

- `FIELD_VALIDATION_STATUS.json`: workflow ready true, complete false, status `DATA_COLLECTION_PENDING`.
- Planned districts: Thoothukudi, Tirunelveli, Kanyakumari.
- Completed field-validation date: **NOT FOUND**.
- Field sample size: **NOT FOUND**.
- Ground-truth labeler: **NOT FOUND**.
- Field results: **NOT FOUND**.

### 6.3 Known gaps — exact evidence text

> `PARTIAL_RESTRICTED_INTERNAL_ONLY`

> `Safety false-accept rate on selected excluded evidence: 100%.`

> `No independent unsupported-crop/non-plant benchmark.`

> `High dataset-source shortcut risk.`

> `Banana quality limited.`

> `Cotton third-party provenance unresolved.`

> `Expert botanical approval absent.`

> `Field validation absent.`

### 6.4 Runtime code and non-routing behavior

- Integrity and load checks: `backend/app/crop_identity_six_class_internal/runtime.py:42+`.
- Confidence/margin accept decision: `backend/app/crop_identity_six_class_internal/runtime.py:105-116`.
- Image quality gate: `backend/app/crop_identity_six_class_internal/router.py:42-65` and `backend/app/crop_id_safety/gates.py:50-150`.
- OOD v2 remains fail-closed because prototypes/thresholds are absent: `backend/app/crop_id_safety/v2.py:48-56`.
- Confirmation endpoint deliberately reports `disease_routing_authorized: false`; mobile contract: `agrow-ai/features/cropIdentification/internalSixClassApi.ts:15-16`.

## 7. EVIDENCE phase summaries, blockers and next actions mentioning the requested models

This is the complete matching set found among files named `phase_summary.md`, `blockers.md`, or `next_actions.md` under `agrowai_autonomous_pipeline/EVIDENCE/`.

| File | Factual summary |
|---|---|
| `06_DEDUPLICATION_AND_LEAKAGE_CONTROL/phase_summary.md` | Phase blocked; core artifact cannot be produced from accepted inputs; no gate bypassed; farmer confirmation required and general release blocked. |
| `07_CROP_ID_DATASET_BUILD/phase_summary.md` | Crop-ID dataset build blocked for the same accepted-input reason; general release false. |
| `08_CROP_ID_TRAINING/phase_summary.md` | Crop-ID training blocked; core artifact cannot truthfully be produced. |
| `09_CROP_ID_EVALUATION_CALIBRATION/phase_summary.md` | Crop-ID evaluation/calibration blocked; general release false. |
| `10_CROP_ID_RUNTIME_PACKAGING/phase_summary.md` | Crop-ID runtime packaging blocked; no gate bypassed. |
| `11_CROP_ID_BACKEND_INTEGRATION/phase_summary.md` | Backend integration partial; local work attempted, external validation/human approval/evidence still open; general release blocked. |
| `CROP_ID_DATASET_APPROVAL_PACKAGE/blockers.md` | Exact blocker: `CROP_ID_ACCEPTED_DATA_MISSING`; training and split generation blocked. |
| `CROP_ID_EMERGENCY_INTERNAL_SIX_CLASS/blockers.md` | 100% false acceptance on excluded evidence; no independent negative benchmark; shortcut risk; limited Banana; unresolved Cotton provenance; no botanical/field validation; Android/device/E2E incomplete at that timestamp. |
| `CROP_ID_EMERGENCY_INTERNAL_SIX_CLASS/next_actions.md` | Lists source-diverse data, provenance/count resolution, independent OOD gate, new calibration policy without reopening sealed test, Android/device E2E, botanical and field review. |
| `CROP_ID_FINAL_INTERNAL_COMPLETION/blockers.md` | Safety fitting blocked by supported-crop counts Banana 0, Cotton 0, Paddy 1, Redgram 1, Chilli 4, Groundnut 6; no defensible prototype/threshold/v2 safety runtime; no authorized device/production credential. |
| `CROP_ID_FINAL_INTERNAL_COMPLETION/next_actions.md` | Preserve frozen manifests; acquire independently sourced records, recheck grouping, and only then fit/freeze safety artifacts and perform one-time final safety evaluation. |
| `CROP_ID_IDENTITY_SCREENING/blockers.md` | Manual crop-identity review and founder decision required. |
| `CROP_ID_INDEPENDENT_SAFETY_DATASET_AND_OOD_V2/blockers.md` | Frozen 6-class classifier unchanged; sealed test not accessed; only 3 accepted records, unbalanced categories, legal/privacy review pending; prototypes/thresholds/evaluation blocked. |
| `CROP_ID_INDEPENDENT_SAFETY_DATASET_AND_OOD_V2/next_actions.md` | Resume official acquisition; human-review licenses/privacy; require multiple sources/families; freeze/final-evaluate once; create new v2 package without modifying classifier. |
| `CROP_ID_SAFETY_DATASET_AND_OOD_V2_COMPLETION/blockers.md` | Classifier unchanged; 56 payloads pending, zero accepted images, no group-safe split/prototypes/thresholds/final evaluation; classifier invocation disabled. |
| `CROP_ID_SAFETY_DATASET_AND_OOD_V2_COMPLETION/next_actions.md` | Download/review records, acquire missing categories, audit overlap, then freeze/fit/open final evaluation once. |
| `CROP_ID_SOURCE_ACQUISITION/next_actions.md` | Human decisions required on licensing, crop identity, privacy, duplicate/augmentation families and exclusions before splitting/training. |

No matching disease-classifier-specific phase summary/blocker/next-action documents were found for Banana V3, chilli restricted, Redgram V2, or legacy joint. References to Banana/Chilli/Redgram in the table above concern the 6-class crop-identity/safety-data program.

## 8. Shared infrastructure trace

### 8.1 Disease confidence/abstention/margin/OOD gates

| Runtime | Exact source location |
|---|---|
| Banana V3 | `backend/app/banana_v3/decision_engine.py:28-43`; orchestration `inference_service.py:101-136` |
| Chilli restricted | frozen package `backend/model_artifacts/frozen_runtime/chilli_mobilenetv3_small_v1_restricted/runtime/restricted_runtime.py`; API fail-closed mapping `backend/app/restricted_crops/api_router.py:51-82` |
| Redgram restricted | `backend/app/redgram_v2/runtime.py:89-113` plus frozen package runtime |
| Legacy joint | `backend/app/legacy_joint/runtime.py:127-137` |
| 4-class crop identity | `backend/app/crop_identity/runtime.py:139-159` |
| 6-class crop identity | `backend/app/crop_identity_six_class_internal/runtime.py:105-116` |
| Image quality / transform agreement / OOD | `backend/app/crop_id_safety/gates.py:50-150`; fail-closed OOD v2 `backend/app/crop_id_safety/v2.py:48-56` |
| Deprecated generic disease orchestrator | crop compatibility, confidence and margin checks at `backend/app/modules/disease/ml_runtime/orchestrator.py:65-97` |

### 8.2 Treatment-recommendation fail-closed logic

- Context-level fail closed: `backend/app/knowledge/recommendations/service.py:40-41` returns `RECOMMENDATION_BLOCKED_DISEASE_UNCERTAIN` when disease abstained, confidence failed or model label is absent.
- Strict review-aware retrieval boundary: `backend/app/knowledge/recommendations/review_service.py:20-27,34-84` blocks uncertain/mismatched crop, unregistered labels, healthy cases, missing calibrated threshold, low confidence, pending disease mapping, unresolved source conflict and missing official citation.
- The same service continues with Tamil/English review checks after line 84; it does not infer approvals.

### 8.3 Crop identity → disease routing

Current automatic use: **NOT FOUND / explicitly disabled for the internal 6-class model**.

The repository implements this sequence:

1. Crop identity returns a suggestion or uncertainty.
2. Farmer confirmation is required.
3. The internal 6-class confirmation contract returns `disease_routing_authorized: false` (`agrow-ai/features/cropIdentification/internalSixClassApi.ts:15-16`).
4. Disease requests use an explicit selected/user-confirmed crop. The legacy bundle’s `crop_routing_policy.json` says `routing_input: "explicit_user_crop_confirmation"` and `ai_crop_verification: false`.
5. Mobile crop-specific adapters call fixed endpoints: Banana V3; chilli/redgram restricted endpoints; paddy/cotton/groundnut legacy crop-specific endpoints (`agrow-ai/features/multiCropDiagnosis/adapters.ts`; route behavior is asserted in `__tests__/adapters.test.ts:23-125`).
6. Response parsing requires `crop_identity_source: "user_confirmed_not_ai_verified"` (`agrow-ai/features/multiCropDiagnosis/responseParser.ts:57-125`).

Therefore no evidence was found that a raw crop-identity model output directly or autonomously routes an image into a disease classifier.
