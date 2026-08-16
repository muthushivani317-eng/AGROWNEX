# Disease Pipeline Audit

The code preserves the required fail-closed order: image selection, quality check, crop identification, explicit crop confirmation, crop capability/model guard, inference and abstention/result rendering. Unsupported crops do not proceed.

Repairs in this pass:

- crop-identification network failure has a real Retry action using the already selected image;
- internal translation marker removed;
- raw crop-ID confidence percentage removed from farmer UI;
- no model, threshold, temperature or capability was changed.

The supplied device failure “Crop identification could not connect” is not resolved as a production fact because authenticated device and Railway evidence could not be captured. `CROP_IDENTIFICATION=FAIL`; `DISEASE_INFERENCE=BLOCKED`.
