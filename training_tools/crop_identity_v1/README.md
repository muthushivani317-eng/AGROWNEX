# Four-crop MobileNetV3 Small baseline

Status: `PUBLIC_DATASET_PROVISIONAL`.

Run in a GPU Colab/runtime after uploading the repository and approved manifest:

```bash
python -m training_tools.crop_identity_v1.train \
  --manifest crop_identity_dataset_v1/manifests/split_manifest.json \
  --data-root /content/drive/MyDrive/AgrowAI_V1/knowledge_base \
  --output-dir training_runs/crop_identity_mobilenetv3_small_v1
```

The script refuses CPU execution. Checkpoint selection uses development
validation macro F1. Class imbalance is handled with class-weighted
cross-entropy; evaluation loaders remain naturally distributed.

Do not access `provisional_test` until development evaluation, shortcut
diagnostics, calibration, abstention selection, and the pre-test freeze record
are complete.
