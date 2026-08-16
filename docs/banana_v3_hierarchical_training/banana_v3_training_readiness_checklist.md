# Banana V3 Training Readiness Checklist

## Repository safety

- [ ] Banana V1 unchanged.
- [ ] Banana V2 unchanged.
- [ ] Frozen V2 artifacts unchanged.
- [ ] Opened external benchmark excluded from fitting and selection.
- [ ] No opened benchmark image copied to training.

## Data readiness

- [ ] Approved manifest exists.
- [ ] Final grouped split exists.
- [ ] Source paths resolve.
- [ ] Exact duplicates checked.
- [ ] Perceptual duplicates checked.
- [ ] Capture groups preserved.
- [ ] Unsupported classes absent.
- [ ] Healthy images present.
- [ ] All three disease classes present.
- [ ] No Panama class.
- [ ] Dataset licence and provenance reviewed: **Verify dataset licence and provenance against official source.**

## Binary gate readiness

- [ ] Mapping verified.
- [ ] Derived counts calculated from manifests.
- [ ] Class weights calculated from training only.
- [ ] Loaders created.
- [ ] One batch inspected safely.

## Disease classifier readiness

- [ ] Healthy excluded.
- [ ] Cordana, Pestalotiopsis, and Sigatoka classes verified.
- [ ] Derived counts calculated.
- [ ] Class weights calculated from training only.
- [ ] Loaders created.
- [ ] One batch inspected safely.

## Training configuration

- [ ] Seed recorded.
- [ ] Device recorded.
- [ ] Environment recorded.
- [ ] Output directories are new.
- [ ] V2 output is not reused.
- [ ] Checkpoint names fixed.
- [ ] Early stopping configured.
- [ ] Metrics configured.

## Calibration

- [ ] Separate calibration split used.
- [ ] No calibration leakage.
- [ ] Separate temperatures planned.
- [ ] Argmax-change check planned.

## Thresholds

- [ ] No threshold preselected.
- [ ] Class-specific threshold analysis planned.
- [ ] Opened external benchmark excluded from threshold selection.

## Freeze

- [ ] Freeze receipt planned.
- [ ] Checksums planned.
- [ ] Runtime bundle planned.

## Deployment block

- [ ] No deployment before freeze.
- [ ] No deployment before valid evaluation.
- [ ] No Tamil Nadu field-accuracy claim.
- [ ] No pesticide-brand promotion or recommendation.
- [ ] Farmer never pays.
- [ ] Symptom and disease definitions remain subject to: **Verify against official source or qualified plant-pathology expert.**

`TRAINING_READY = true` only when every required item is checked.
