"""Disease module constants (docs/AI_PROMPTS.md, docs/SECURITY.md → file upload)."""
from __future__ import annotations

import os
from enum import StrEnum

# --- Vision provider: reuse the AI module's Gemini configuration (single source) ---
from app.modules.ai.constants import (  # noqa: F401 — re-exported for the vision client
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)

DEFAULT_LANGUAGE = "ta"

# --- Image quality gate (docs: blurry, dark, overexposed, too small) ---
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
MIN_DIMENSION_PX = 224
MIN_IMAGE_BYTES = 2 * 1024  # 2 KB
MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MB (docs/SECURITY.md → 10 MB, small margin)

# Pixel metrics are 0..1. These bands flag poor images before Gemini is called.
DARK_MAX_BRIGHTNESS = 0.20
OVEREXPOSED_MIN_BRIGHTNESS = 0.92
OVEREXPOSED_MAX_WHITE_RATIO = 0.35
BLUR_MIN_SHARPNESS = 0.10


class QualityIssue(StrEnum):
    MISSING = "missing"
    TOO_SMALL = "too_small"
    TOO_LARGE = "too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    CORRUPTED = "corrupted"
    BLURRY = "blurry"
    DARK = "dark"  # under-exposed
    OVEREXPOSED = "overexposed"


# Non-plant reject reasons returned by the vision provider (docs: STEP 2).
class RejectReason(StrEnum):
    HUMAN = "human"
    BUILDING = "building"
    ANIMAL = "animal"
    VEHICLE = "vehicle"
    SKY = "sky"
    SOIL = "soil"
    EMPTY = "empty"
    OTHER = "other"


class CaptureMethod(StrEnum):
    CAMERA = "camera"
    GALLERY = "gallery"


class Severity(StrEnum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


# --- Cloudflare R2 (S3-compatible). Never AWS S3 (docs: storage). ---
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "agrowai")
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL", "")
R2_REGION = "auto"
DISEASE_IMAGE_PREFIX = "disease"
