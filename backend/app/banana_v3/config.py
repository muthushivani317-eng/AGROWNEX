"""Immutable Banana V3 runtime configuration."""
from __future__ import annotations

import os
from pathlib import Path

MODEL_VERSION = "banana-v3.0.0"
BUNDLE_VERSION = "banana-v3-production-bundle-1"
PACKAGE_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = PACKAGE_ROOT / "artifacts"
LOG_ROOT = Path(os.getenv("BANANA_V3_LOG_DIR", PACKAGE_ROOT / "logs"))
MAX_UPLOAD_BYTES = int(os.getenv("BANANA_V3_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MIN_IMAGE_SIDE = 64
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
RUNTIME_PREFERENCE = os.getenv("BANANA_V3_RUNTIME", "auto").lower()

HEALTHY_CLASSES = {"banana__healthy": 0, "banana__diseased": 1}
DISEASE_CLASSES = {
    "banana__cordana_leaf_spot": 0,
    "banana__pestalotiopsis_leaf_spot": 1,
    "banana__sigatoka_leaf_spot": 2,
}
HEALTHY_TEMPERATURE = 2.090103190616
DISEASE_TEMPERATURE = 0.823204678118
HEALTHY_THRESHOLDS = {
    "banana__healthy": {"confidence": 0.65, "margin": 0.30},
    "banana__diseased": {"confidence": 0.50, "margin": 0.00},
}
DISEASE_THRESHOLDS = {
    "banana__cordana_leaf_spot": {"confidence": 0.34, "margin": 0.86},
    "banana__pestalotiopsis_leaf_spot": {"confidence": 0.34, "margin": 0.88},
    "banana__sigatoka_leaf_spot": {"confidence": 0.34, "margin": 0.00},
}
EXPECTED_CHECKPOINT_HASHES = {
    "checkpoints/healthy_gate_best.pt": "838d40714ba6c43ec2e6c5eb4af1c895a7f739ab46e7ee38d58d50cd55e01e98",
    "checkpoints/disease_classifier_best.pt": "056b97c4faca32356ad6e1ac8b3d7f6166952a9a149ab518d41fdadd798e467e",
}
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
