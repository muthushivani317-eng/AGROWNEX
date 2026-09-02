"""Conservative, non-diagnostic image-quality/OOD checks before inference."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageSafetyResult:
    accepted: bool
    reason_code: str | None


def assess_image_safety(
    image: Image.Image, *, texture_policy: Literal["strict", "spatial"] = "strict"
) -> ImageSafetyResult:
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
    # Nearest-neighbour sampling preserves black/white synthetic blocks;
    # smoothing them first can make checkerboards look like natural edges.
    binary_sample = np.asarray(
        rgb.resize((128, 128), Image.Resampling.NEAREST), dtype=np.float32
    ).mean(axis=2)
    binary_pattern = float(
        ((binary_sample <= 7) | (binary_sample >= 248)).mean()
    ) >= 0.90
    if texture_policy == "spatial" and binary_pattern:
        return ImageSafetyResult(False, "SYNTHETIC_OR_NOISE_PATTERN")
    if texture > 15:
        if texture_policy != "spatial":
            return ImageSafetyResult(False, "SYNTHETIC_OR_NOISE_PATTERN")
        # Edge strength alone also describes detailed leaves and backgrounds.
        # Require weak spatial coherence before calling high texture noise.
        # This is a quality heuristic, not proof of plant identity or safety
        # to diagnose; downstream crop/content checks still apply.
        horizontal_correlation = float(np.corrcoef(
            gray[:, :-1].ravel(), gray[:, 1:].ravel()
        )[0, 1])
        vertical_correlation = float(np.corrcoef(
            gray[:-1, :].ravel(), gray[1:, :].ravel()
        )[0, 1])
        if (not np.isfinite(horizontal_correlation)
                or not np.isfinite(vertical_correlation)
                or min(horizontal_correlation, vertical_correlation) < 0.5):
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


def require_safe_image(
    image: Image.Image, *, texture_policy: Literal["strict", "spatial"] = "strict"
) -> None:
    result = assess_image_safety(image, texture_policy=texture_policy)
    if not result.accepted:
        raise UnsafeImageError(result.reason_code or "OUT_OF_DOMAIN_IMAGE")
