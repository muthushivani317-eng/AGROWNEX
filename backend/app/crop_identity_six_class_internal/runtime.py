from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = (
    Path(__file__).resolve().parents[2]
    / "model_artifacts"
    / "frozen_runtime"
    / "crop_identity_six_class_internal_v1"
)
CLASSES = ["banana", "paddy", "cotton", "groundnut", "chilli", "redgram"]


class IntegrityError(RuntimeError):
    pass


def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def verify(root: Path = ROOT):
    manifest = root / "SHA256SUMS.json"
    if not manifest.is_file():
        raise IntegrityError("HASH_MANIFEST_MISSING")
    expected = json.loads(manifest.read_text(encoding="utf-8"))
    required = {
        "model.pt",
        "runtime_config.json",
        "class_order.json",
        "calibration.json",
        "abstention_thresholds.json",
        "dataset_hashes.json",
        "rollback.json",
    }
    if not required <= set(expected):
        raise IntegrityError("REQUIRED_ARTIFACT_MISSING_FROM_MANIFEST")
    for name, value in expected.items():
        path = root / name
        if not path.is_file() or digest(path) != value:
            raise IntegrityError("ARTIFACT_INTEGRITY_FAILURE:" + name)
    cfg = json.loads((root / "runtime_config.json").read_text(encoding="utf-8"))
    if (
        cfg.get("class_order") != CLASSES
        or cfg.get("general_farmer_release") != "BLOCKED"
        or cfg.get("official_accuracy_claim") is not False
        or cfg.get("farmer_confirmation_required") is not True
    ):
        raise IntegrityError("RUNTIME_POLICY_INVALID")
    return cfg


class Runtime:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self._model = None
        self._cfg = None
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            if self._model is not None:
                return
            self._cfg = verify(self.root)
            import torch
            from torch import nn
            from torchvision.models import mobilenet_v3_small

            m = mobilenet_v3_small(weights=None)
            m.classifier[3] = nn.Linear(m.classifier[3].in_features, 6)
            ck = torch.load(self.root / "model.pt", map_location="cpu", weights_only=False)
            m.load_state_dict(ck["model_state_dict"], strict=True)
            self._model = m.eval()

    def predict(self, image: Image.Image):
        self.load()
        import torch

        assert self._cfg is not None and self._model is not None
        c = self._cfg["preprocessing"]
        im = ImageOps.exif_transpose(image).convert("RGB")
        scale = c["resize"] / min(im.size)
        im = im.resize(
            (round(im.width * scale), round(im.height * scale)), Image.Resampling.BILINEAR
        )
        left = (im.width - c["center_crop"]) // 2
        top = (im.height - c["center_crop"]) // 2
        im = im.crop((left, top, left + c["center_crop"], top + c["center_crop"]))
        x = np.asarray(im, dtype=np.float32) / 255
        x = (x - np.array(c["mean"], dtype=np.float32)) / np.array(c["std"], dtype=np.float32)
        x = torch.from_numpy(np.transpose(x, (2, 0, 1))[None].copy())
        with torch.inference_mode():
            p = torch.softmax(self._model(x)[0] / self._cfg["temperature"], 0)
        order = p.argsort(descending=True)
        confidence = float(p[order[0]])
        margin = confidence - float(p[order[1]])
        accepted = (
            confidence >= self._cfg["confidence_threshold"]
            and margin >= self._cfg["margin_threshold"]
        )
        calibrated_probabilities = {
            crop: float(p[index]) for index, crop in enumerate(CLASSES)
        }
        return {
            "status": "identified" if accepted else "uncertain",
            "identified_crop": CLASSES[int(order[0])] if accepted else None,
            "confidence": confidence if accepted else None,
            "calibrated_probabilities": calibrated_probabilities,
            "margin": margin,
            "farmer_confirmation_required": True,
            "reason_code": "CROP_MATCH" if accepted else "CROP_IDENTITY_UNCERTAIN",
            "scope": "INTERNAL_ONLY",
            "official_accuracy_claim": False,
            "general_farmer_release": "BLOCKED",
        }

    def health(self):
        try:
            verify(self.root)
            return {
                "status": "ready_internal_only",
                "classes": CLASSES,
                "farmer_confirmation_required": True,
                "official_accuracy_claim": False,
                "general_farmer_release": "BLOCKED",
            }
        except Exception as e:
            return {
                "status": "not_ready",
                "error_category": type(e).__name__,
                "official_accuracy_claim": False,
                "general_farmer_release": "BLOCKED",
            }


runtime = Runtime()
