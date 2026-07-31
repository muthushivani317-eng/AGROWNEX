# Banana V3 Production Inference

Frozen hierarchical inference for Banana only:

1. validate and preprocess the image;
2. run the calibrated healthy gate;
3. apply the predicted healthy-gate class threshold;
4. return cautious healthy, or route accepted diseased evidence;
5. run the calibrated disease classifier;
6. apply the predicted disease class threshold;
7. return a localization key or abstain.

ONNX is preferred when its verified artifacts exist; PyTorch is the configured
fallback. Integrity failure never triggers silent fallback. Images are not
stored by default, logs exclude farmer identity and precise address, and
diagnosis is separate from agronomy advice.

This package is integrated for supervised field validation. It is not an
official Tamil Nadu field-accuracy claim and is not yet field validated.
Farmer never pays. No pesticide products or recommendations are returned.

## Required artifacts

Copy the two frozen checkpoints and two exported ONNX models into the exact
paths documented in `artifacts/manifests/artifact_manifest.json`, then rebuild
the manifest and checksum inventory using the bundle script.

## Commands

```powershell
python -m pytest app/banana_v3/tests -q
python scripts/export_banana_v3_onnx.py
python scripts/build_banana_v3_bundle.py
python scripts/verify_banana_v3_bundle.py banana_v3_production_bundle.zip
```
