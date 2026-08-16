# Banana V3 Hierarchical Architecture

## 1. Objective

Banana V3 must preserve specific disease diagnosis while reducing false exact diagnoses caused by domain shift and overlapping visual symptoms. The system is not allowed to output an exact disease solely because one class has the largest probability.

The frozen Banana V2 research baseline demonstrated strong internal validation but weak transfer to the already-opened 424-image diagnostic benchmark. Banana V3 therefore uses explicit gates, calibration, symptom verification, class-specific thresholds, and abstention. It does not permanently merge the three disease classes.

Known frozen comparison facts supplied by the project:

- architecture: MobileNetV3 Small;
- internal development Top-1: `0.940789`;
- internal development macro F1: `0.932385`;
- calibration temperature: `2.420216`;
- frozen margin threshold: `0.90`;
- checkpoint SHA-256: `5c4678d46c8b5e195a6df1ebc326533e1d783250f48891ef1c90b35a48a711a0`;
- final split SHA-256: `e147450c1448fc19bce970c6f007d7cbe1b84b86ad5e05539288aa705fc5ab4f`;
- external diagnostic benchmark Top-1: `0.483491`;
- external macro F1: `0.406266`;
- external accepted accuracy: `0.522449`;
- Cordana recall: `0.11`;
- Pestalotiopsis recall: `0.008547`;
- many Cordana and Pestalotiopsis images were predicted as Sigatoka;
- status: `RESEARCH_BASELINE_NOT_FOR_FARMER_DEPLOYMENT`.

The approved Banana V2 dataset contains `3037` images: Cordana `162`, Healthy `727`, Pestalotiopsis `172`, and Sigatoka `1976`. Its grouped split contains training `2126`, development validation `456`, and calibration `455`. These are source facts, not Banana V3 results. The Banana V3 expert-review package exists, but its expert review is not formally complete and is not approved ground truth.

## 2. Scope

Supported crop:

- `banana`

Supported final classes:

- `banana__healthy`
- `banana__cordana_leaf_spot`
- `banana__pestalotiopsis_leaf_spot`
- `banana__sigatoka_leaf_spot`

Supported non-final states:

- `banana__image_unusable`
- `banana__uncertain_disease`
- `banana__mixed_or_non_diagnostic_symptoms`
- `banana__crop_mismatch`
- `banana__requires_more_information`

Any disease definition or symptom interpretation must carry: **Verify against official source or qualified plant-pathology expert.**

## 3. Full inference flow

```text
Input image
  → crop confirmation
  → image quality gate
  → healthy-versus-diseased gate
  → disease-specific classifier
  → calibrated probabilities
  → symptom-question verification
  → class-specific decision policy
  → exact disease or abstention
```

1. **Input image:** accept one original image and its permitted technical metadata.
2. **Crop confirmation:** ensure that the request is intended for banana.
3. **Image quality gate:** determine whether the evidence is usable.
4. **Healthy-versus-diseased gate:** route accepted evidence without issuing a disease diagnosis.
5. **Disease-specific classifier:** rank Cordana, Pestalotiopsis, and Sigatoka only for accepted diseased cases.
6. **Calibrated probabilities:** apply the separately frozen temperature for the relevant model.
7. **Symptom-question verification:** compare structured answers with reviewed knowledge without treating questions as ground truth.
8. **Class-specific decision policy:** enforce the predicted class's frozen confidence, margin, conflict, and mixed-symptom rules.
9. **Exact disease or abstention:** return a cautious final state and audit reason.

## 4. Stage 0: Crop confirmation

Purpose:

- confirm that the image is intended to show a banana plant or leaf;
- reject obvious wrong-crop inputs;
- avoid forcing a banana diagnosis on unrelated images.

For the V3 baseline, crop confirmation may initially come from user selection. An optional crop-image classifier may be added later only as a separate ablation. The current training scope must not expand to multi-crop classification.

Outputs:

- `crop_confirmed`
- `crop_mismatch`
- `crop_uncertain`

## 5. Stage 1: Image quality gate

Detect or record:

- severe blur;
- extreme overexposure or underexposure;
- symptom region too small;
- leaf mostly occluded;
- screenshot or heavy compression;
- edited image;
- non-leaf image;
- multiple leaves with no clear target;
- background-dominant image;
- duplicate or near-duplicate input;
- unsupported orientation or corrupted file.

Required output:

- `usable`
- `usable_with_warning`
- `recapture_required`
- `reject`

The first baseline may use deterministic checks. A learned quality model is optional later. Image-quality detection is a gate, not the disease classifier.

## 6. Stage 2: Healthy versus diseased gate

Classes:

- `banana__healthy`
- `banana__diseased`

This binary routing stage prevents direct disease classification when evidence of disease is uncertain. It is not the final diagnosis.

- If healthy is accepted, return healthy only when its calibrated probability and margin meet the frozen healthy-gate policy; otherwise request more information or return uncertainty.
- If diseased is accepted, route to the disease-specific stage.
- If neither route is accepted, abstain or request another image.

## 7. Stage 3: Specific disease classifier

Classes:

- `banana__cordana_leaf_spot`
- `banana__pestalotiopsis_leaf_spot`
- `banana__sigatoka_leaf_spot`

The classifier runs only after quality acceptance and a diseased decision from Stage 2. It must use calibrated probabilities, Top-1 confidence, Top-1 minus Top-2 margin, class-specific thresholds, symptom-question agreement, and conflict detection. One global threshold alone is prohibited.

## 8. Stage 4: Symptom-question verification

Structured fields:

- `lesion_shape`
- `lesion_colour`
- `yellow_halo_present`
- `lesion_distribution`
- `vein_alignment`
- `leaf_edge_involvement`
- `upper_or_lower_surface`
- `symptom_stage`
- `wet_or_dry_appearance`
- `symptom_progression`
- `mixed_symptoms_possible`
- `pest_signs_present`
- `nutrient_deficiency_possible`
- `environmental_damage_possible`

Symptom questions support the model but do not replace verified plant-pathology knowledge. Every symptom-to-disease rule must state: **Verify against official source or qualified plant-pathology expert.**

## 9. Stage 5: Final decision engine

Allowed outputs:

- `banana__healthy`
- `banana__cordana_leaf_spot`
- `banana__pestalotiopsis_leaf_spot`
- `banana__sigatoka_leaf_spot`
- `banana__uncertain_disease`
- `banana__mixed_or_non_diagnostic_symptoms`
- `banana__image_unusable`
- `banana__crop_mismatch`
- `banana__requires_more_information`

An exact disease may be returned only when crop is confirmed, quality passes, the diseased gate accepts, class-specific confidence and margin thresholds pass, symptoms do not contradict the prediction, and neither a mixed-disease nor non-diagnostic flag is active.

## 10. Hierarchical training components

- **A. Quality gate:** deterministic baseline checks and reason codes.
- **B. Healthy-versus-diseased model:** binary MobileNetV3 Small.
- **C. Three-class disease model:** Cordana, Pestalotiopsis, and Sigatoka MobileNetV3 Small.
- **D. Calibration layer per model:** independently fitted scalar temperatures.
- **E. Decision-policy layer:** frozen routing, thresholds, conflicts, and abstention.
- **F. Symptom-question schema:** generic structured evidence with missing states.
- **G. Logging and audit layer:** versions, decisions, reason codes, and permitted checksums.

Not every component must be a neural network.

## 11. Model architecture baseline

Use MobileNetV3 Small as the first baseline for both the healthy-versus-diseased gate and the three-class disease classifier. This is consistent with the frozen Banana V2 baseline, supports controlled comparison, and remains suitable for mobile-oriented deployment. A larger model is not assumed to perform better and may be tested only as a later ablation.

## 12. Preprocessing

- RGB conversion;
- EXIF transpose;
- resize the shorter side to 256;
- center crop to 224 for evaluation;
- document the training crop separately;
- ImageNet mean `[0.485, 0.456, 0.406]`;
- ImageNet standard deviation `[0.229, 0.224, 0.225]`;
- `float32`, `NCHW`;
- no test-time augmentation in the baseline.

## 13. Data flow diagram

```text
Image + user crop selection
        │
        ├─ crop mismatch/uncertain ───────────────→ abstain
        ▼
Deterministic quality checks
        ├─ reject/recapture ─────────────────────→ image unusable
        ▼
Healthy gate → calibrated probabilities
        ├─ accepted healthy ─────────────────────→ cautious healthy
        ├─ uncertain ────────────────────────────→ more information
        ▼ accepted diseased
Disease classifier → calibrated probabilities
        ▼
Class-specific confidence + margin
        ▼
Symptom agreement/conflict + mixed-symptom check
        ├─ fail/conflict/mixed ──────────────────→ abstain
        ▼
Likely specific disease + internal audit record
```

## 14. Failure handling

- **Low confidence:** abstain with `ABSTAIN_DISEASE_LOW_CONFIDENCE`.
- **Low margin:** abstain with `ABSTAIN_DISEASE_LOW_MARGIN`.
- **Gate disagreement:** request more information or return model disagreement.
- **Model-symptom disagreement:** do not expose an exact disease.
- **Crop mismatch:** return `banana__crop_mismatch`.
- **Poor quality:** request recapture or return `banana__image_unusable`.
- **Multiple disease suspicion:** return `banana__mixed_or_non_diagnostic_symptoms`.
- **Unsupported pattern:** return `banana__requires_more_information`.
- **Backend failure:** return a safe runtime-error response without a diagnosis.

## 15. Deployment restrictions

- Banana V3 is not approved until its components and policy are frozen and validly tested.
- No Tamil Nadu field-accuracy claim is allowed without a new sealed, expert-reviewed field test.
- Do not promote or recommend pesticide brands.
- Farmer never pays.
- Exact disease names must not be shown after abstention.
- Every response must record model versions and uncertainty status internally.
- The opened external benchmark is diagnostic only and is excluded from all fitting and selection.

## 16. Versioning

- `banana_v3_quality_gate_v1`
- `banana_v3_healthy_gate_v1`
- `banana_v3_disease_classifier_v1`
- `banana_v3_decision_policy_v1`
- `banana_v3_runtime_bundle_v1`

Banana V1, Banana V2, and all frozen Banana V2 artifacts remain unchanged.
