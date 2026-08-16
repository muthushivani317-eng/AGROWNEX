# Final Evidence Report

The highest valid outcome is `BLOCKED_INSUFFICIENT_DATA_AND_HUMAN_REVIEW`.

The repository already contains a reproducible, checksummed four-class public-dataset crop-ID baseline and controlled backend path. It cannot be promoted or expanded by inference: Chilli, Redgram, unknown-crop and non-plant approved data are absent from the runtime, non-plant rejection is unproven, and the existing test reports high source-shortcut risk. The consumed provisional test was not reopened.

The recommendation architecture is correctly fail-closed, but no record has completed disease-specific factual approval and Tamil approval. All agricultural content remains subject to `VERIFY AGAINST OFFICIAL SOURCE`. Privacy/legal conclusions remain `VERIFY AGAINST OFFICIAL DPDP REQUIREMENTS`.

No dataset was downloaded, no model was trained, no sealed images were opened, no runtime was changed, no deployment was attempted, and no APK was built.

## Required status matrix

```text
DATA_ACQUISITION=INCOMPLETE
DATASET_REVIEW=FOUR_CLASS_CONDITIONAL_ONLY
DATASET_READY=NO
TRAINING=EIGHT_CLASS_NOT_STARTED
CALIBRATION=EXISTING_FOUR_CLASS_ONLY
PROVISIONAL_TEST=EXISTING_FOUR_CLASS_CONSUMED_DO_NOT_REOPEN
RUNTIME_PACKAGE=FOUR_CLASS_RESTRICTED_ONLY
BACKEND_INTEGRATION=CONTROLLED_TESTER_ONLY
MOBILE_INTEGRATION=PRESENT_UNVERIFIED
RAILWAY_DEPLOYMENT=MANUAL_ACCESS_REQUIRED
LIVE_E2E=NOT_RUN
LAPTOP_OFF_TEST=NOT_RUN
FARMER_RELEASE_READINESS=NO
```

```text
SOURCE_COLLECTION=PARTIAL
SOURCE_AUTHORITY_REVIEW=HUMAN_REVIEW_REQUIRED
DISEASE_LABEL_MAPPING=PARTIAL
SYMPTOM_REVIEW=NOT_PROVEN_COMPLETE
IMMEDIATE_ACTION_REVIEW=NOT_PROVEN_COMPLETE
PREVENTION_REVIEW=NOT_PROVEN_COMPLETE
BIOLOGICAL_CULTURAL_REVIEW=NOT_PROVEN_COMPLETE
CHEMICAL_REVIEW=BLOCKED_VERIFY_AGAINST_OFFICIAL_SOURCE
TAMIL_REVIEW=NOT_PROVEN_COMPLETE
RUNTIME_DATABASE=NOT_BUILT
BACKEND_INTEGRATION=FAIL_CLOSED_SCAFFOLD_ONLY
MOBILE_INTEGRATION=PRESENT_UNVERIFIED
LIVE_E2E=NOT_RUN
FARMER_RELEASE_READINESS=NO
```

## Per-crop summary

| Crop | Crop-ID | Disease runtime | Recommendation | Farmer eligible | Primary blockers |
|---|---|---|---|---|---|
| Banana | Four-class provisional | Available, field validation in progress | 5 packets, 0 approved | No | Shortcut risk, recommendation/Tamil approval |
| Paddy | Four-class provisional | Local legacy evidence present; registry stale | 4 packets, 0 approved | No | Registry reconciliation, recommendation/Tamil approval |
| Cotton | Four-class provisional | Local legacy evidence present; registry stale | 3 packets, 0 approved | No | Registry reconciliation, source shortcut, approvals |
| Groundnut | Four-class provisional | Local legacy evidence present; registry stale | 2 packets, 0 approved | No | Registry reconciliation, approvals |
| Chilli | Missing from crop-ID | Restricted runtime, farmer disabled | 0 packets | No | Crop-ID data, expert review, Tamil review |
| Redgram | Missing from crop-ID | Restricted runtime, farmer disabled | 0 packets | No | Crop-ID data, expert review, Tamil review |
