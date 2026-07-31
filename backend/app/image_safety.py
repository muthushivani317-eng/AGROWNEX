"""Conservative, non-diagnostic image-quality/OOD checks before inference."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageSafetyResult:
    accepted: bool
    reason_code: str | None


def assess_image_safety(image: Image.Image) -> ImageSafetyResult:
    """Reject obvious invalid/synthetic inputs; this does not verify crop identity."""
    rgb = image.convert("RGB")
    if min(rgb.size) < 96:
        return ImageSafetyResult(False, "IMAGE_TOO_SMALL")
    sample = np.asarray(rgb.resize((128, 128)), dtype=np.float32)
    gray = sample.mean(axis=2)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    horizontal = float(np.abs(np.diff(gray, axis=1)).mean())
    vertical = float(np.abs(np.diff(gray, axis=0)).mean())
    texture = (horizontal + vertical) / 2
    near_white = float((gray >= 248).mean())
    near_black = float((gray <= 7).mean())

    if brightness <= 10 or near_black >= 0.97:
        return ImageSafetyResult(False, "EXTREME_DARKNESS")
    if brightness >= 245 or near_white >= 0.97:
        return ImageSafetyResult(False, "EXTREME_BRIGHTNESS")
    if contrast < 2:
        return ImageSafetyResult(False, "NEAR_UNIFORM_IMAGE")
    if texture > 15:
        return ImageSafetyResult(False, "SYNTHETIC_OR_NOISE_PATTERN")
    if texture < 0.75:
        return ImageSafetyResult(False, "INSUFFICIENT_DETAIL")
    if brightness >= 190 and near_white >= 0.70 and texture >= 2:
        return ImageSafetyResult(False, "SCREENSHOT_LIKE_IMAGE")
    return ImageSafetyResult(True, None)


class UnsafeImageError(ValueError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def require_safe_image(image: Image.Image) -> None:
    result = assess_image_safety(image)
    if not result.accepted:
        raise UnsafeImageError(result.reason_code or "OUT_OF_DOMAIN_IMAGE")
