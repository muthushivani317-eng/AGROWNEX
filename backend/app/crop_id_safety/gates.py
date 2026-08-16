from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

ARTIFACT_ROOT = (
    Path(__file__).resolve().parents[2] / "model_artifacts" / "safety_gates" / "crop_id_internal_v1"
)


class SafetyArtifactError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_safety_artifact(root: Path = ARTIFACT_ROOT) -> dict[str, Any]:
    config_path = root / "safety_config.json"
    manifest_path = root / "SHA256SUMS.json"
    if not config_path.is_file() or not manifest_path.is_file():
        raise SafetyArtifactError("SAFETY_ARTIFACT_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest != {"safety_config.json": sha256_file(config_path)}:
        raise SafetyArtifactError("SAFETY_ARTIFACT_INTEGRITY_FAILURE")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        config.get("scope") != "INTERNAL_ONLY"
        or config.get("general_farmer_release") != "BLOCKED"
        or config.get("official_field_validation") is not False
    ):
        raise SafetyArtifactError("SAFETY_POLICY_INVALID")
    return config


@dataclass(frozen=True)
class QualityResult:
    outcome: str
    reason_code: str | None
    metrics: dict[str, float]


def assess_quality(image: Image.Image, config: dict[str, Any]) -> QualityResult:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    width, height = rgb.size
    sample = np.asarray(rgb.resize((128, 128)), dtype=np.float32)
    gray = sample.mean(axis=2)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    texture = float(
        (np.abs(np.diff(gray, axis=1)).mean() + np.abs(np.diff(gray, axis=0)).mean()) / 2
    )
    near_white = float((gray >= 248).mean())
    near_black = float((gray <= 7).mean())
    histogram = np.histogram(gray, bins=32, range=(0, 256))[0].astype(float)
    probabilities = histogram / max(1.0, histogram.sum())
    entropy = float(-(probabilities * np.log2(np.maximum(probabilities, 1e-12))).sum())
    metrics = {
        "width": float(width),
        "height": float(height),
        "effective_pixels": float(width * height),
        "brightness": brightness,
        "contrast": contrast,
        "texture": texture,
        "entropy": entropy,
        "near_white_ratio": near_white,
        "near_black_ratio": near_black,
    }
    q = config["quality"]
    checks = [
        (min(width, height) < q["minimum_dimension"], "IMAGE_TOO_SMALL"),
        (width * height < q["minimum_effective_pixels"], "INSUFFICIENT_PIXELS"),
        (brightness <= q["minimum_brightness"], "EXTREME_DARKNESS"),
        (brightness >= q["maximum_brightness"], "EXTREME_BRIGHTNESS"),
        (near_black >= q["maximum_near_black_ratio"], "EXTREME_DARKNESS"),
        (near_white >= q["maximum_near_white_ratio"], "EXTREME_BRIGHTNESS"),
        (contrast < q["minimum_contrast"], "NEAR_UNIFORM_IMAGE"),
        (texture < q["minimum_texture"], "SEVERE_BLUR_OR_NO_DETAIL"),
        (texture > q["maximum_texture"], "NOISE_OR_COMPRESSION_ARTIFACT"),
    ]
    for failed, reason in checks:
        if failed:
            return QualityResult("LOW_QUALITY", reason, metrics)
    return QualityResult("QUALITY_ACCEPTABLE", None, metrics)


def assess_plant(image: Image.Image, config: dict[str, Any]) -> dict[str, Any]:
    array = np.asarray(image.convert("RGB").resize((128, 128)), dtype=np.float32) / 255
    maximum, minimum = array.max(2), array.min(2)
    saturation = (maximum - minimum) / np.maximum(maximum, 1e-6)
    green = (
        (array[:, :, 1] > array[:, :, 0] * 0.92)
        & (array[:, :, 1] > array[:, :, 2] * 0.92)
        & (saturation > 0.10)
    )
    green_fraction = float(green.mean())
    saturated_fraction = float((saturation > 0.10).mean())
    p = config["plant_heuristic"]
    if (
        green_fraction >= p["minimum_green_fraction"]
        and saturated_fraction >= p["minimum_saturated_fraction"]
    ):
        outcome = "PLANT"
    elif green_fraction <= p["non_plant_maximum_green_fraction"]:
        outcome = "NON_PLANT"
    else:
        outcome = "PLANT_UNCERTAIN"
    return {
        "outcome": outcome,
        "method": "CONSERVATIVE_COLOUR_TEXTURE_HEURISTIC",
        "green_fraction": green_fraction,
        "saturated_fraction": saturated_fraction,
    }


def assess_ood(plant_result: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    if plant_result["outcome"] == "NON_PLANT":
        return {"outcome": "UNSUPPORTED_CROP", "reason_code": "NON_PLANT"}
    # No independent crop-reference set exists. Refusing to guess is mandatory.
    return {
        "outcome": config["ood"]["default_outcome"],
        "reason_code": "INDEPENDENT_OOD_REFERENCE_UNAVAILABLE",
    }


def assess_ambiguity(runtime: Any, image: Image.Image) -> dict[str, Any]:
    original = runtime.predict(image)
    mirrored = runtime.predict(ImageOps.mirror(image))
    brighter = runtime.predict(ImageEnhance.Brightness(image).enhance(1.05))
    results = [original, mirrored, brighter]
    labels = {item.get("identified_crop") for item in results}
    stable = len(labels) == 1 and None not in labels
    accepted = all(item.get("status") == "identified" for item in results)
    return {
        "outcome": "IDENTITY_ACCEPTABLE_FOR_CONFIRMATION"
        if stable and accepted
        else "AMBIGUOUS_IMAGE",
        "transform_agreement": stable,
        "runtime_results": results,
    }


def public_quality(result: QualityResult) -> dict[str, Any]:
    return asdict(result)
