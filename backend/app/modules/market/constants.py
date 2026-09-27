"""Market module constants (docs/DATABASE_SCHEMA.md → Market, docs/PRODUCT_RULES.md).

Prices come only from verified sources (docs/PRODUCT_RULES.md → government data
is never fabricated). Provider configuration is read from the environment so a
paid/state provider can be swapped in without code changes.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# --- Cache (docs/API_CONTRACT.md → Market Prices cache 15 minutes; Redis-ready) ---
MARKET_CACHE_TTL_SECONDS = int(os.getenv("MARKET_CACHE_TTL_SECONDS", str(15 * 60)))

# --- Open Government (data.gov.in) / Agmarknet provider ---
# Resource: "Current Daily Price of Various Commodities from Various Markets (Mandi)".
# The API key is issued per-account at data.gov.in and must stay server-side.
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
DATA_GOV_BASE_URL = os.getenv(
    "DATA_GOV_BASE_URL", "https://api.data.gov.in/resource"
)
AGMARKNET_RESOURCE_ID = os.getenv(
    "AGMARKNET_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070"
)
AGMARKNET_TIMEOUT_SECONDS = float(os.getenv("AGMARKNET_TIMEOUT_SECONDS", "8"))
AGMARKNET_MAX_RETRIES = int(os.getenv("AGMARKNET_MAX_RETRIES", "3"))
# Cap the number of records pulled per upstream call (bounded, paginated client-side).
AGMARKNET_FETCH_LIMIT = int(os.getenv("AGMARKNET_FETCH_LIMIT", "500"))
# Optional second official data.gov.in resource tried when the primary fails
# (same Agmarknet source, different dataset). Empty = disabled.
AGMARKNET_BACKUP_RESOURCE_ID = os.getenv("AGMARKNET_BACKUP_RESOURCE_ID", "").strip()

# --- Background state-wide sync (worker only; never on a farmer's request) ---
# data.gov.in is often slow or briefly down, so the worker pulls every price for
# these states on a schedule with a generous timeout/retry budget and the app
# serves the stored copy (last good prices, with their market date).
MARKET_SYNC_STATES = tuple(
    s.strip() for s in os.getenv("MARKET_SYNC_STATES", "Tamil Nadu").split(",") if s.strip()
)
AGMARKNET_SYNC_TIMEOUT_SECONDS = float(os.getenv("AGMARKNET_SYNC_TIMEOUT_SECONDS", "45"))
AGMARKNET_SYNC_MAX_RETRIES = int(os.getenv("AGMARKNET_SYNC_MAX_RETRIES", "5"))
AGMARKNET_SYNC_MAX_PAGES = int(os.getenv("AGMARKNET_SYNC_MAX_PAGES", "20"))

# Number of days of history returned by GET /market/history by default.
DEFAULT_HISTORY_DAYS = 30
MAX_HISTORY_DAYS = 365

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

SOURCE_AGMARKNET = "agmarknet"
SOURCE_MOCK = "mock"


class CommodityCategory(StrEnum):
    """Broad commodity grouping shown on cards and used for search facets."""

    CEREAL = "cereal"
    PULSE = "pulse"
    OILSEED = "oilseed"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    SPICE = "spice"
    CASH_CROP = "cash_crop"
    OTHER = "other"


class PriceUnit(StrEnum):
    """Unit the min/max/modal prices are quoted in."""

    QUINTAL = "quintal"  # Agmarknet default: ₹ per quintal (100 kg)
    KG = "kg"
    TONNE = "tonne"


class MarketSearchType(StrEnum):
    """Facet returned by GET /market/search."""

    CROP = "crop"
    MARKET = "market"
    DISTRICT = "district"
    STATE = "state"


class LocationStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


# Commodity name (lowercased) → category. Best-effort classification of the free-text
# commodity returned by Agmarknet; unknown commodities fall back to OTHER.
COMMODITY_CATEGORY_MAP: dict[str, CommodityCategory] = {
    "paddy": CommodityCategory.CEREAL,
    "rice": CommodityCategory.CEREAL,
    "wheat": CommodityCategory.CEREAL,
    "maize": CommodityCategory.CEREAL,
    "jowar": CommodityCategory.CEREAL,
    "bajra": CommodityCategory.CEREAL,
    "ragi": CommodityCategory.CEREAL,
    "bengal gram": CommodityCategory.PULSE,
    "black gram": CommodityCategory.PULSE,
    "green gram": CommodityCategory.PULSE,
    "red gram": CommodityCategory.PULSE,
    "arhar": CommodityCategory.PULSE,
    "tur": CommodityCategory.PULSE,
    "groundnut": CommodityCategory.OILSEED,
    "soyabean": CommodityCategory.OILSEED,
    "sunflower": CommodityCategory.OILSEED,
    "sesamum": CommodityCategory.OILSEED,
    "castor seed": CommodityCategory.OILSEED,
    "tomato": CommodityCategory.VEGETABLE,
    "onion": CommodityCategory.VEGETABLE,
    "potato": CommodityCategory.VEGETABLE,
    "brinjal": CommodityCategory.VEGETABLE,
    "cabbage": CommodityCategory.VEGETABLE,
    "cauliflower": CommodityCategory.VEGETABLE,
    "banana": CommodityCategory.FRUIT,
    "mango": CommodityCategory.FRUIT,
    "grapes": CommodityCategory.FRUIT,
    "chilli": CommodityCategory.SPICE,
    "turmeric": CommodityCategory.SPICE,
    "coriander": CommodityCategory.SPICE,
    "cotton": CommodityCategory.CASH_CROP,
    "sugarcane": CommodityCategory.CASH_CROP,
}


def classify_commodity(commodity: str) -> CommodityCategory:
    return COMMODITY_CATEGORY_MAP.get(
        commodity.strip().lower(), CommodityCategory.OTHER
    )
