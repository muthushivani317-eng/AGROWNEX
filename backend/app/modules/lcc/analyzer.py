"""Deterministic Leaf Colour Chart matching without an AI or network service.

The palette is an approximate digital representation of the commonly used
four-panel (2-5) LCC. A phone photo cannot reproduce a printed chart exactly,
so poor or ambiguous inputs fail closed rather than producing a panel guess.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass

from PIL import Image, ImageFilter, UnidentifiedImageError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MIN_DIMENSION = 240
MAX_ANALYSIS_SIDE = 900

# AgrowAI v1 digital reference palette (sRGB), panels 2 through 5.
LCC_REFERENCE_RGB: dict[int, tuple[int, int, int]] = {
    2: (174, 190, 75),
    3: (125, 162, 65),
    4: (75, 132, 59),
    5: (39, 94, 52),
}


@dataclass(frozen=True)
class LccAnalysis:
    abstained: bool
    quality_issue: str | None
    panel_number: int | None
    nitrogen_status: str
    average_lab: tuple[float, float, float] | None
    color_distance: float | None
    leaf_pixel_ratio: float
    brightness: float
    sharpness: float


def srgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert an sRGB triplet (0..255) to CIE L*a*b* using D65 white."""
    channels = []
    for value in rgb:
        channel = value / 255.0
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    red, green, blue = channels
    x = (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883

    delta = 6 / 29

    def f(value: float) -> float:
        return value ** (1 / 3) if value > delta**3 else value / (3 * delta**2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e_cie76(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(first, second, strict=True)))


REFERENCE_LAB = {panel: srgb_to_lab(rgb) for panel, rgb in LCC_REFERENCE_RGB.items()}


def _abstain(
    issue: str,
    *,
    ratio: float = 0.0,
    brightness: float = 0.0,
    sharpness: float = 0.0,
) -> LccAnalysis:
    return LccAnalysis(True, issue, None, "abstained", None, None, ratio, brightness, sharpness)


def analyze_leaf_image(image_bytes: bytes) -> LccAnalysis:
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        return _abstain("invalid_image")
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.verify()
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        return _abstain("invalid_image")

    if min(image.size) < MIN_DIMENSION:
        return _abstain("image_too_small")
    image.thumbnail((MAX_ANALYSIS_SIDE, MAX_ANALYSIS_SIDE), Image.Resampling.LANCZOS)
    pixels = list(image.get_flattened_data())
    leaf_pixels: list[tuple[int, int, int]] = []
    leaf_indexes: list[int] = []
    for index, (red, green, blue) in enumerate(pixels):
        maximum, minimum = max(red, green, blue), min(red, green, blue)
        saturation = 0 if maximum == 0 else (maximum - minimum) / maximum
        # Includes pale yellow-green panels while rejecting grey/brown soil and sky.
        if green >= red * 0.82 and green >= blue * 1.12 and saturation >= 0.18 and green >= 38:
            leaf_pixels.append((red, green, blue))
            leaf_indexes.append(index)

    ratio = len(leaf_pixels) / len(pixels)
    if ratio < 0.12:
        return _abstain("too_little_leaf", ratio=ratio)

    average_rgb = tuple(
        sum(pixel[channel] for pixel in leaf_pixels) / len(leaf_pixels)
        for channel in range(3)
    )
    brightness = 0.2126 * average_rgb[0] + 0.7152 * average_rgb[1] + 0.0722 * average_rgb[2]
    if brightness < 48:
        return _abstain("too_dark", ratio=ratio, brightness=brightness)
    if brightness > 225:
        return _abstain("overexposed", ratio=ratio, brightness=brightness)

    edge = image.convert("L").filter(ImageFilter.FIND_EDGES)
    all_edge_values = list(edge.get_flattened_data())
    edge_values = [all_edge_values[index] for index in leaf_indexes]
    sharpness = 0.0
    if edge_values:
        mean = sum(edge_values) / len(edge_values)
        sharpness = sum((value - mean) ** 2 for value in edge_values) / len(edge_values)
    if sharpness < 18:
        return _abstain("too_blurry", ratio=ratio, brightness=brightness, sharpness=sharpness)

    average_lab = srgb_to_lab(average_rgb)
    ranked = sorted(
        (delta_e_cie76(average_lab, lab), panel)
        for panel, lab in REFERENCE_LAB.items()
    )
    best_distance, panel = ranked[0]
    if best_distance > 34 or ranked[1][0] - best_distance < 1.5:
        return _abstain("ambiguous_colour", ratio=ratio, brightness=brightness, sharpness=sharpness)
    status = "deficient" if panel <= 3 else "borderline" if panel == 4 else "sufficient"
    return LccAnalysis(
        False,
        None,
        panel,
        status,
        tuple(round(value, 2) for value in average_lab),
        round(best_distance, 2),
        round(ratio, 4),
        round(brightness, 2),
        round(sharpness, 2),
    )
