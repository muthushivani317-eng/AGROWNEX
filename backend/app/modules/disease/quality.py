"""Image quality gate (docs: Image Quality Validation).

Poor images are never sent to Gemini. Dimension parsing and the rule engine are
pure and dependency-free (unit-tested). Pixel metrics (brightness, blur,
overexposure) use Pillow when available and are skipped gracefully otherwise, so
the module never hard-depends on an image library.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.modules.disease.constants import (
    ALLOWED_MIME_TYPES,
    BLUR_MIN_SHARPNESS,
    DARK_MAX_BRIGHTNESS,
    MAX_IMAGE_BYTES,
    MIN_DIMENSION_PX,
    MIN_IMAGE_BYTES,
    OVEREXPOSED_MAX_WHITE_RATIO,
    OVEREXPOSED_MIN_BRIGHTNESS,
    QualityIssue,
)

logger = get_logger("disease.quality")

_JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}


@dataclass
class QualityMetrics:
    file_size: int
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    brightness: float | None = None  # 0..1 mean luminance
    overexposed_ratio: float | None = None  # 0..1 fraction of near-white pixels
    sharpness: float | None = None  # 0..1, higher = sharper
    corrupted: bool | None = None


@dataclass
class QualityResult:
    acceptable: bool
    issues: list[str] = field(default_factory=list)


def read_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Parse image width/height from PNG or JPEG headers (pure, no deps)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return width, height
    if data[:2] == b"\xff\xd8":
        return _jpeg_dimensions(data)
    return None, None


def _jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    i = 2
    size = len(data)
    while i + 9 < size:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xD8 or marker == 0xD9 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        if marker in _JPEG_SOF_MARKERS:
            height = int.from_bytes(data[i + 5 : i + 7], "big")
            width = int.from_bytes(data[i + 7 : i + 9], "big")
            return width, height
        i += 2 + length
    return None, None


def _pillow_metrics(
    data: bytes,
) -> tuple[float | None, float | None, float | None]:
    """(brightness, overexposed_ratio, sharpness) via Pillow, or None if absent."""
    try:
        import io

        from PIL import Image, ImageFilter, ImageStat
    except Exception:  # Pillow not installed — skip pixel checks.
        return None, None, None
    try:
        with Image.open(io.BytesIO(data)) as image:
            gray = image.convert("L")
            brightness = ImageStat.Stat(gray).mean[0] / 255.0
            histogram = gray.histogram()
            total = sum(histogram) or 1
            white = sum(histogram[245:])
            overexposed_ratio = white / total
            edges = gray.filter(ImageFilter.FIND_EDGES)
            variance = ImageStat.Stat(edges).var[0]
            sharpness = min(1.0, variance / 2000.0)
        return brightness, overexposed_ratio, sharpness
    except Exception:
        logger.info("pillow metrics failed; skipping pixel checks")
        return None, None, None


def detect_corrupted(
    data: bytes, mime_type: str | None, width: int | None
) -> bool | None:
    """True if the image cannot be decoded; None when undecidable (no Pillow)."""
    try:
        import io

        from PIL import Image
    except Exception:
        # Fallback: a JPEG/PNG we can normally parse but couldn't ⇒ bad header.
        if mime_type in ("image/jpeg", "image/png") and width is None:
            return True
        return None
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        return False
    except Exception:
        return True


def extract_metrics(data: bytes, mime_type: str | None) -> QualityMetrics:
    width, height = read_dimensions(data)
    brightness, overexposed_ratio, sharpness = _pillow_metrics(data)
    return QualityMetrics(
        file_size=len(data),
        mime_type=mime_type,
        width=width,
        height=height,
        brightness=brightness,
        overexposed_ratio=overexposed_ratio,
        sharpness=sharpness,
        corrupted=detect_corrupted(data, mime_type, width),
    )


def assess_quality(metrics: QualityMetrics) -> QualityResult:
    """Deterministic rule engine — pure and fully unit-tested."""
    if metrics.file_size <= 0:
        return QualityResult(acceptable=False, issues=[QualityIssue.MISSING.value])

    issues: list[QualityIssue] = []

    if metrics.mime_type and metrics.mime_type not in ALLOWED_MIME_TYPES:
        issues.append(QualityIssue.UNSUPPORTED_TYPE)
    if metrics.corrupted:
        issues.append(QualityIssue.CORRUPTED)
    if metrics.file_size < MIN_IMAGE_BYTES:
        issues.append(QualityIssue.TOO_SMALL)
    elif metrics.file_size > MAX_IMAGE_BYTES:
        issues.append(QualityIssue.TOO_LARGE)

    if metrics.width is not None and metrics.height is not None:
        if min(metrics.width, metrics.height) < MIN_DIMENSION_PX:
            issues.append(QualityIssue.TOO_SMALL)

    if metrics.sharpness is not None and metrics.sharpness < BLUR_MIN_SHARPNESS:
        issues.append(QualityIssue.BLURRY)

    if metrics.brightness is not None:
        if metrics.brightness < DARK_MAX_BRIGHTNESS:
            issues.append(QualityIssue.DARK)
        elif metrics.brightness > OVEREXPOSED_MIN_BRIGHTNESS:
            issues.append(QualityIssue.OVEREXPOSED)
    if (
        metrics.overexposed_ratio is not None
        and metrics.overexposed_ratio > OVEREXPOSED_MAX_WHITE_RATIO
    ):
        issues.append(QualityIssue.OVEREXPOSED)

    # De-duplicate while preserving order.
    unique = list(dict.fromkeys(issue.value for issue in issues))
    return QualityResult(acceptable=not unique, issues=unique)
