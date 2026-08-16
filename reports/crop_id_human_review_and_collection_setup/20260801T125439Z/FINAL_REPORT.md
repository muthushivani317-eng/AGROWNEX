# Crop-ID human review and collection setup

The operational review and privacy-safe local collection packages are ready.
No image or agricultural recommendation was approved, and training remains blocked.

- `CHILLI_REVIEW_TOOL=READY_FOR_INTERNAL_REVIEW`
- `REDGRAM_REVIEW_TOOL=READY_FOR_INTERNAL_REVIEW_DATA_INSUFFICIENT`
- `NON_PLANT_COLLECTION_PACKAGE=READY_NO_DATA_COLLECTED`
- `UNKNOWN_CROP_COLLECTION_PACKAGE=READY_NO_DATA_COLLECTED`
- `FOUR_CROP_GAP_ANALYSIS=COMPLETE_COLLECTION_REQUIRED`
- `RECOMMENDATION_REVIEW_TOOL=READY_HUMAN_APPROVAL_REQUIRED`
- `APPROVED_CHILLI_IMAGES=0`
- `APPROVED_REDGRAM_IMAGES=0`
- `APPROVED_UNKNOWN_CROP_IMAGES=0`
- `APPROVED_NON_PLANT_IMAGES=0`
- `TRAINING_READINESS=NOT_READY`

Frozen models and sealed test sets were not accessed or modified. No training,
calibration, deployment, APK build, staging, commit, or push was performed.
