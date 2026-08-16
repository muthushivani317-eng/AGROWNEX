# Banana V3 Field Collection Protocol

## 1. Purpose

This protocol defines how to collect realistic, expert-reviewable banana leaf images that can support improved cross-farm and cross-device generalization. It governs data collection and quality control only. It is not a diagnosis protocol and does not provide pesticide advice.

Banana V2 remains frozen as a research baseline and must not be modified. External benchmark images are not approved for training. No result produced from this collection may be described as Tamil Nadu field accuracy without a separate, valid field evaluation.

## 2. Scope

The collection categories are:

- `banana__cordana_leaf_spot`
- `banana__pestalotiopsis_leaf_spot`
- `banana__sigatoka_leaf_spot`
- `banana__healthy`
- `banana__uncertain_or_mixed_symptoms`

These are collection and review categories, not collector-assigned final diagnoses. Disease definitions and agricultural interpretations must carry this instruction: **Verify against official source or qualified plant-pathology expert.**

## 3. Roles and responsibilities

- **Field collector:** obtains consent, assigns identifiers, captures original images, and records observations without inventing labels.
- **Farmer or farm representative:** voluntarily permits the agreed uses and may decline participation.
- **Data manager:** safeguards files and consent records, creates checksums, checks metadata, and manages quarantine.
- **Plant-pathology reviewer:** reviews evidence independently, records label status, confidence, decision, and rationale.
- **Split custodian:** pre-assigns dataset roles and enforces group-aware leakage controls.
- **Sealed-test custodian:** restricts sealed-test access, verifies the lock, and records the one-time evaluation.

One person may hold multiple roles, but access to sealed-test images and labels must remain restricted and auditable.

## 4. Consent and farmer protection

- Participation is voluntary and the farmer never pays.
- Refusal must not reduce or affect access to AgrowAI.
- Collect only data needed for the agreed operation. Do not collect an exact personal address unless operationally necessary.
- Use coded farm identifiers; never place a farmer name in an image or hierarchy identifier.
- Do not publish identifiable farmer images without explicit permission.
- Record permissions separately for training, internal research, publication, and sealed testing.
- Permit withdrawal before dataset freezing where operationally possible, and record any withdrawal request.
- Store consent records separately from public image folders.

## 5. Collection unit hierarchy

Use this hierarchy:

1. `district_code` — coded district, format `TN_<DISTRICT_SHORT_CODE>`.
2. `farm_code` — coded farm, format `TN_<DISTRICT_SHORT_CODE>_FARM_<4 DIGITS>`.
3. `visit_id` — one collection visit, format `<farm_code>_VISIT_<YYYYMMDD>_<2 DIGITS>`.
4. `plant_id` — one plant during the visit, format `<visit_id>_PLANT_<3 DIGITS>`.
5. `leaf_id` — one leaf on the plant, format `<plant_id>_LEAF_<3 DIGITS>`.
6. `capture_group_id` — strongly related images from one leaf and capture sequence, format `<leaf_id>_CAPTURE_<2 DIGITS>`.
7. `image_id` — unique image identifier, format `BAN_V3_<8 DIGITS>`.

All related images from one leaf must use one `capture_group_id`. Identifiers must not contain the farmer's name.

## 6. Required photo sequence per leaf

Capture:

1. `full_plant_view` — show the entire plant and visible distribution of symptoms.
2. `full_leaf_front` — show the complete front surface and leaf margins.
3. `symptom_closeup` — sharply show symptom and lesion boundaries without losing context.
4. `leaf_back_view_when_relevant` — show the corresponding lower surface when informative.
5. `environmental_context` — show non-identifying growing context around the plant.

Optional views are `second_symptom_closeup`, `scale_reference_view`, `stem_or_pseudostem_view`, and `uncertain_context_view`.

For every photo:

- Prefer natural light; avoid strong shadows and glare.
- Do not use filters, beauty mode, screenshots, or WhatsApp-compressed copies.
- Retain the original file and do not crop before ingestion.
- Keep fingers away from symptoms and lesion boundaries.
- Avoid heavy digital zoom.
- Use one plain scale reference only when appropriate.
- Do not include pesticide packets, labels, or branded products in the frame.

## 7. Image quality requirements

The symptom region must be visible where symptoms are claimed; focus must be acceptable; motion blur, overexposure, and underexposure must not prevent review. The image must be unique, unedited, correctly oriented, and framed so the leaf occupies enough of the image. Preserve original metadata where possible.

Assign one decision:

- `PASS` — usable without a material warning.
- `PASS_WITH_WARNING` — usable, with a recorded limitation.
- `RECAPTURE_REQUIRED` — a replacement should be collected.
- `EXCLUDE` — unusable or unsafe for the intended role.

## 8. Disease and symptom observations

Record observations without forcing a diagnosis:

- crop confirmation; banana variety if known; plant age or growth stage;
- leaf position and upper or lower leaf surface;
- lesion shape, colour, halo, distribution, edge involvement, and vein alignment;
- symptom severity and wet or dry appearance;
- mixed symptoms, pest signs, possible nutrient deficiency, or environmental damage;
- symptom progression if known.

Field collectors must not invent a disease label. **Verify against official source or qualified plant-pathology expert.**

## 9. Expert label workflow

**Stage A — field provisional observation:** the collector records visible evidence and may select an explicitly provisional category.

**Stage B — expert-reviewed label:** a qualified reviewer evaluates the complete evidence independently.

Allowed label statuses:

- `UNREVIEWED`
- `EXPERT_CONFIRMED`
- `EXPERT_PROVISIONAL`
- `LABEL_DISAGREEMENT`
- `UNCERTAIN`
- `MULTIPLE_DISEASES_POSSIBLE`
- `NOT_VISUALLY_DIAGNOSABLE`
- `NON_DISEASE_DAMAGE`

Allowed final decisions:

- `KEEP`
- `RELABEL`
- `EXCLUDE`
- `UNCERTAIN`
- `MULTIPLE_DISEASES_POSSIBLE`
- `EXPERT_REVIEW_ONLY`

A corrected label must record reviewer name, organization, review date, confidence, and notes. Model output must never serve as ground truth.

## 10. Dataset role assignment

- `training_candidate` — may become training data only after consent, quality, leakage, and expert gates pass.
- `development_validation_candidate` — reserved for model-development validation.
- `calibration_candidate` — reserved for post-training calibration.
- `sealed_field_test_candidate` — locked evaluation data, inaccessible to model development.
- `expert_review_only` — retained for review but not model fitting or evaluation.

Assign roles before model training begins. A `capture_group_id` cannot appear in multiple roles. A farm visit should normally stay in one role unless a documented higher-level grouping policy prevents leakage. Exact and near duplicates must remain in one role.

Lock sealed field-test candidates before development. They must never be used for training, augmentation development, model selection, debugging, threshold selection, calibration, label-policy tuning, preprocessing tuning, or architecture selection. Never move them into training after poor results.

## 11. Leakage prevention

Check exact SHA-256 duplicates, perceptual duplicates, bursts, renamed copies, cropped or edited copies, common leaf, common plant, common farm visit, common video-frame source, and photographer sequences. Group-aware splitting is mandatory. All images from the same leaf, plant, capture session, or strongly related group must remain in the same dataset role and final split.

## 12. Sealed field-test rules

- Store sealed data separately with restricted access.
- Hide labels from model developers where practical.
- Do not open it until the model, preprocessing, temperature, and thresholds are frozen.
- Record the evaluation timestamp and checksums.
- Do not tune after evaluation.
- A failure requires a new model version and a new sealed test set; the original result remains immutable.

## 13. Directory structure

```text
banana_v3_field_data/
  incoming/
    <district_code>/
      <farm_code>/
        <visit_id>/
          <plant_id>/
            <leaf_id>/
              <capture_group_id>/
  quarantine/
  approved/
  expert_review/
  excluded/
  sealed_field_test/
  manifests/
  checksums/
  consent_records/
```

Do not store consent forms inside public image folders.

## 14. File naming

Use:

```text
<image_id>__<capture_group_id>__<view_type>.<extension>
```

Example:

```text
BAN_V3_00000001__TN_TUT_FARM_0001_VISIT_20260726_01_PLANT_001_LEAF_001_CAPTURE_01__symptom_closeup.jpg
```

Preserve the original filename in metadata.

## 15. Collection workflow

1. Obtain consent.
2. Create farm and visit codes.
3. Confirm the crop.
4. Identify the plant and leaf.
5. Assign the capture group.
6. Take the required photo sequence.
7. Record field observations.
8. Assign a provisional dataset role.
9. Upload original files.
10. Generate checksums.
11. Run quality review.
12. Run duplicate review.
13. Send the complete group for expert review.
14. Approve, relabel, exclude, or retain as uncertain.
15. Lock sealed-test records.

## 16. Quality-control checkpoints

- ingestion check;
- metadata completeness check;
- image readability check;
- exact and perceptual duplicate checks;
- label consistency check;
- consent check;
- role leakage check;
- expert-review completeness check;
- sealed-test lock check.

Each checkpoint must have a recorded result, reviewer or process identity, and timestamp.

## 17. Rejection reasons

- `NO_CONSENT`
- `WRONG_CROP`
- `IMAGE_UNREADABLE`
- `SEVERE_BLUR`
- `EXTREME_EXPOSURE`
- `SYMPTOM_NOT_VISIBLE`
- `DUPLICATE_EXACT`
- `DUPLICATE_NEAR`
- `SCREENSHOT_OR_COMPRESSED_COPY`
- `EDITED_IMAGE`
- `LABEL_UNCERTAIN`
- `MULTIPLE_DISEASES`
- `NON_DISEASE_DAMAGE`
- `METADATA_INCOMPLETE`
- `SPLIT_LEAKAGE_RISK`
- `PERSONAL_PRIVACY_RISK`
- `OTHER`

## 18. Minimum collection diversity

Seek diversity across districts, farms, banana varieties, devices, photographers, lighting, backgrounds, symptom stages, leaf positions, and seasons where available. Numeric targets must be defined later from expert review and actual data availability; none are asserted here.

## 19. Security and privacy

Use coded farms, restricted consent records, role-based access, checksum tracking, backups, and an audit trail. Do not expose exact coordinates publicly by default. Store the sealed test read-only and restrict access to its custodian.

## 20. Completion criteria

A collection batch is complete only when consent is valid, metadata is complete, files are readable, checksums exist, duplicate and quality statuses are recorded, expert status is recorded, a dataset role is assigned, leakage checks pass, and the sealed-test lock is applied where relevant.

## 21. Limitations

- Public-dataset accuracy does not equal Tamil Nadu field accuracy.
- Image-only classification may be insufficient.
- Visually overlapping diseases may require symptom questions and expert review.
- Labels and definitions must be verified: **Verify against official source or qualified plant-pathology expert.**
- This protocol does not create a Banana V3 training plan.
