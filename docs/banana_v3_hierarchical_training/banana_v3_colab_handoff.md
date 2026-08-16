# Banana V3 Colab Handoff

## 1. Purpose

This file is the exact bridge from Codex planning to Colab implementation. It authorizes no training by itself and does not change Banana V1, Banana V2, or any frozen artifact.

## 2. Required existing inputs

Use repository-to-Drive placeholders until the exact synchronized path is confirmed:

- approved Banana V2 manifest: `<DRIVE_SYNC_ROOT>/banana_v2/approved_manifest.csv`
- final grouped split manifest: `<DRIVE_SYNC_ROOT>/banana_v2/final_grouped_split_manifest.csv`
- BananaLSD training package if source extraction is required: `<DRIVE_SYNC_ROOT>/source_packages/banana_lsd.zip`
- Source 2 extraction manifest: `<DRIVE_SYNC_ROOT>/source_manifests/source_2_extraction_manifest.csv`
- Banana V2 frozen runtime, reference only: `<DRIVE_SYNC_ROOT>/banana_v2/frozen_runtime/`
- Banana V3 class mapping: `<DRIVE_SYNC_ROOT>/banana_v3/banana_v3_class_mapping.json`
- Banana V3 stage configuration: `<DRIVE_SYNC_ROOT>/banana_v3/banana_v3_stage_config.json`
- Banana V3 symptom schema: `<DRIVE_SYNC_ROOT>/banana_v3/banana_v3_symptom_schema.json`

The opened 424-image benchmark must remain separate and must not enter any derived fitting manifest.

## 3. Required new Colab output directories

```text
/content/drive/MyDrive/AgrowAI_V1/training_outputs/banana_v3_hierarchical/
  healthy_gate/
  disease_classifier/
  hierarchical_reports/
  frozen_runtime/
  logs/
```

Do not overwrite or reuse Banana V2 output paths.

## 4. Colab execution order

1. **Cell 1:** mount Drive and run environment checks.
2. **Cell 2:** load manifests and verify hashes.
3. **Cell 3:** resolve image paths.
4. **Cell 4:** derive the healthy-gate manifest.
5. **Cell 5:** derive the disease-classifier manifest.
6. **Cell 6:** verify counts and group preservation.
7. **Cell 7:** create transforms and datasets.
8. **Cell 8:** create safe data loaders with `num_workers=0` initially.
9. **Cell 9:** train the healthy gate.
10. **Cell 10:** evaluate the healthy gate on development.
11. **Cell 11:** fit the healthy-gate temperature on calibration.
12. **Cell 12:** select healthy-gate thresholds.
13. **Cell 13:** train the disease classifier.
14. **Cell 14:** evaluate the disease classifier on development.
15. **Cell 15:** fit the disease-classifier temperature on calibration.
16. **Cell 16:** select class-specific disease thresholds.
17. **Cell 17:** simulate the full hierarchical flow.
18. **Cell 18:** freeze the runtime.
19. **Cell 19:** run the already-opened diagnostic benchmark once, after freeze only.
20. **Cell 20:** generate final reports.

## 5. Required Colab assertions

- Source manifest row count equals `3037`.
- Source split row count equals `3037`.
- No external benchmark path appears in either derived manifest.
- No capture group crosses splits.
- No exact hash crosses splits.
- No unsupported class is present.
- Healthy is excluded from the disease-classifier manifest.
- No V2 output path is used as a V3 output.
- Calibration is not used for training.
- Development is not used for training.
- External benchmark is not used before freeze.
- The 424-image benchmark remains blocked from training, model selection, calibration, threshold selection, preprocessing tuning, architecture selection, and debugging.

## 6. Required final Colab tokens

- `BANANA_V3_MANIFESTS_READY`
- `BANANA_V3_HEALTHY_GATE_TRAINING_COMPLETE`
- `BANANA_V3_HEALTHY_GATE_CALIBRATION_COMPLETE`
- `BANANA_V3_DISEASE_CLASSIFIER_TRAINING_COMPLETE`
- `BANANA_V3_DISEASE_CALIBRATION_COMPLETE`
- `BANANA_V3_HIERARCHICAL_SIMULATION_COMPLETE`
- `BANANA_V3_FROZEN_RUNTIME_COMPLETE`
- `BANANA_V3_DIAGNOSTIC_EXTERNAL_EVALUATION_COMPLETE`

## 7. First Colab task

The first Colab task after this Codex phase is:

> Load the approved Banana V2 manifest and final grouped split, then derive two leakage-safe Banana V3 manifests without changing any split assignment.

No external benchmark image is approved for training. MobileNetV3 Small is the baseline for both trained stages. Farmer never pays. Do not promote or recommend pesticide brands. Any agricultural interpretation must state: **Verify against official source or qualified plant-pathology expert.**
