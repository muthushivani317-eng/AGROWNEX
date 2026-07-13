"""Growth module constants (docs/DATABASE_SCHEMA.md → Crop Growth).

Reuses the Disease module's Cloudflare R2 configuration and image-quality gate,
and the AI module's Gemini configuration — a single source of truth, no
duplication (docs/PRODUCT_RULES.md → no duplicate code).
"""
from __future__ import annotations

from enum import StrEnum

# --- Vision provider: reuse the AI module's Gemini configuration ---
from app.modules.ai.constants import (  # noqa: F401 — re-exported for the growth client
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)

# --- Object storage: reuse the Disease module's Cloudflare R2 configuration ---
from app.modules.disease.constants import (  # noqa: F401 — re-exported for storage
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET,
    R2_PUBLIC_BASE_URL,
    R2_REGION,
    R2_SECRET_ACCESS_KEY,
)

DEFAULT_LANGUAGE = "ta"

# R2 key prefix for growth photos (kept separate from disease/{...}).
GROWTH_IMAGE_PREFIX = "growth"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# A monitoring "week" for the Week 1 → Week 2 → … timeline.
DAYS_PER_WEEK = 7


class GrowthStage(StrEnum):
    """Estimated crop growth stage (docs/DATABASE_SCHEMA.md → growth_stages)."""

    GERMINATION = "germination"
    SEEDLING = "seedling"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    MATURITY = "maturity"
    HARVEST = "harvest"
    UNKNOWN = "unknown"


class PlantVigor(StrEnum):
    """Overall plant vigour observed in the photo."""

    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# Re-export the shared capture method so callers don't import across modules
# inconsistently (docs: reuse, no duplication).
from app.modules.disease.constants import CaptureMethod  # noqa: E402,F401
