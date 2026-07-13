"""Farmer module constants (docs/DATABASE_SCHEMA.md → Farmer domain)."""
from __future__ import annotations

from enum import StrEnum


class Theme(StrEnum):
    """Appearance preference (docs/DESIGN_SYSTEM.md → Light/Dark/Auto)."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class PreferredUnits(StrEnum):
    METRIC = "metric"
    IMPERIAL = "imperial"


# Languages supported in V1 (docs/AGROWAI_MASTER_SPEC.md → Language strategy).
SUPPORTED_LANGUAGES: tuple[str, ...] = ("ta", "en")
DEFAULT_LANGUAGE = "ta"

# Regex shared by every schema that accepts a language code.
LANGUAGE_PATTERN = "^(ta|en)$"

# The profile table stores a primary + secondary crop, so the preferred-crop
# list is capped at two persisted values (docs/DATABASE_SCHEMA.md → farmer_profiles).
MAX_PERSISTED_CROPS = 2
