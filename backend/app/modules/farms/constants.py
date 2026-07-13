"""Farm module constants (docs/DATABASE_SCHEMA.md → Farm domain)."""
from __future__ import annotations

from enum import StrEnum


class FarmStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    HARVESTED = "harvested"
    ARCHIVED = "archived"


class SoilType(StrEnum):
    ALLUVIAL = "alluvial"
    BLACK = "black"
    RED = "red"
    LATERITE = "laterite"
    SANDY = "sandy"
    CLAY = "clay"
    LOAMY = "loamy"
    SILT = "silt"


class IrrigationType(StrEnum):
    RAINFED = "rainfed"
    CANAL = "canal"
    BOREWELL = "borewell"
    OPEN_WELL = "open_well"
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    TANK = "tank"


class WaterSource(StrEnum):
    RAIN = "rain"
    RIVER = "river"
    CANAL = "canal"
    BOREWELL = "borewell"
    OPEN_WELL = "open_well"
    POND = "pond"
    TANK = "tank"


class AreaSource(StrEnum):
    """Whether the farm area is computed from the boundary or entered by hand."""

    AUTO = "auto"
    MANUAL = "manual"


class LocationSource(StrEnum):
    GPS = "gps"
    MANUAL = "manual"


class BoundarySource(StrEnum):
    DRAWN = "drawn"
    GPS = "gps"
    IMPORTED = "imported"


# Pagination (docs/API_CONTRACT.md → PAGINATION).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Farm media limits (docs/SECURITY.md → File upload).
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
