"""Unit tests for the image-quality gate (pure, no deps)."""
from __future__ import annotations

from app.modules.disease.constants import MIN_IMAGE_BYTES
from app.modules.disease.quality import (
    QualityMetrics,
    assess_quality,
    read_dimensions,
)


def make_png(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


def make_jpeg(width: int, height: int) -> bytes:
    return (
        b"\xff\xd8\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x00" * 8
    )


def test_read_dimensions_png_and_jpeg():
    assert read_dimensions(make_png(320, 240)) == (320, 240)
    assert read_dimensions(make_jpeg(300, 200)) == (300, 200)
    assert read_dimensions(b"not an image") == (None, None)


def _ok_metrics(**over) -> QualityMetrics:
    base = dict(
        file_size=MIN_IMAGE_BYTES + 1000,
        mime_type="image/jpeg",
        width=400,
        height=400,
        corrupted=False,
    )
    base.update(over)
    return QualityMetrics(**base)


def test_accepts_a_good_image():
    assert assess_quality(_ok_metrics()).acceptable is True


def test_flags_missing_and_size_and_type():
    assert assess_quality(QualityMetrics(file_size=0)).issues == ["missing"]
    assert "too_small" in assess_quality(_ok_metrics(file_size=10)).issues
    assert "too_large" in assess_quality(_ok_metrics(file_size=50_000_000)).issues
    assert "unsupported_type" in assess_quality(_ok_metrics(mime_type="image/gif")).issues


def test_flags_low_resolution_and_corrupted():
    assert "too_small" in assess_quality(_ok_metrics(width=100, height=400)).issues
    assert "corrupted" in assess_quality(_ok_metrics(corrupted=True)).issues


def test_flags_blur_darkness_and_overexposure():
    assert "blurry" in assess_quality(_ok_metrics(sharpness=0.02)).issues
    assert "dark" in assess_quality(_ok_metrics(brightness=0.05)).issues
    assert "overexposed" in assess_quality(_ok_metrics(brightness=0.97)).issues
    assert "overexposed" in assess_quality(_ok_metrics(overexposed_ratio=0.6)).issues


def test_pixel_checks_skipped_when_metrics_absent():
    # brightness/sharpness None (Pillow unavailable) ⇒ no blur/dark flags.
    result = assess_quality(_ok_metrics(brightness=None, sharpness=None))
    assert result.acceptable is True
