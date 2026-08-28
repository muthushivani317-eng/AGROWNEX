"""Produce module constants (docs/DATABASE_SCHEMA.md → Produce domain).

The procurement lifecycle is deliberately *not* a marketplace lifecycle: there is
no "Sold" or "Reserved" transactional state. Offers move through a data-collection
lifecycle so verified harvest information can be planned for procurement.
"""

from __future__ import annotations

import os
import re
import unicodedata
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"
DEFAULT_CURRENCY = "INR"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection — absent means the deterministic mock (no external channel).
PROCUREMENT_PROVIDER = os.getenv("PROCUREMENT_PROVIDER", "")

# Harvest-window horizons (days) used by the deterministic engine.
WINDOW_WEEK_DAYS = 7
WINDOW_MONTH_DAYS = 30


class ProduceUnit(StrEnum):
    """Quantity units; convertible ones share a kilogram base for value estimates."""

    KG = "kg"
    QUINTAL = "quintal"
    TONNE = "tonne"
    BAG = "bag"  # non-standard weight → not convertible for value estimates


class ProduceCategory(StrEnum):
    GRAINS = "grains"
    PULSES = "pulses"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    SPICES = "spices"
    PLANTATION_CROPS = "plantation_crops"
    FLOWERS = "flowers"
    OTHER_PRODUCE = "other_produce"


class ProduceAvailabilityType(StrEnum):
    AVAILABLE_NOW = "available_now"
    UPCOMING_HARVEST = "upcoming_harvest"


# Public API contract (shared verbatim with mobile): categories are
# grains|pulses|vegetables|fruits|spices|plantation_crops|flowers|other_produce;
# availability is available_now|upcoming_harvest.
PRODUCE_TAXONOMY: dict[str, str] = {
    "paddy": ProduceCategory.GRAINS,
    "rice": ProduceCategory.GRAINS,
    "maize": ProduceCategory.GRAINS,
    "wheat": ProduceCategory.GRAINS,
    "ragi": ProduceCategory.GRAINS,
    "millet": ProduceCategory.GRAINS,
    "sorghum": ProduceCategory.GRAINS,
    "redgram": ProduceCategory.PULSES,
    "blackgram": ProduceCategory.PULSES,
    "greengram": ProduceCategory.PULSES,
    "chickpea": ProduceCategory.PULSES,
    "groundnut": ProduceCategory.PULSES,
    "tomato": ProduceCategory.VEGETABLES,
    "brinjal": ProduceCategory.VEGETABLES,
    "onion": ProduceCategory.VEGETABLES,
    "potato": ProduceCategory.VEGETABLES,
    "okra": ProduceCategory.VEGETABLES,
    "moringa": ProduceCategory.VEGETABLES,
    "banana": ProduceCategory.FRUITS,
    "mango": ProduceCategory.FRUITS,
    "guava": ProduceCategory.FRUITS,
    "papaya": ProduceCategory.FRUITS,
    "grapes": ProduceCategory.FRUITS,
    "chilli": ProduceCategory.SPICES,
    "turmeric": ProduceCategory.SPICES,
    "pepper": ProduceCategory.SPICES,
    "coriander": ProduceCategory.SPICES,
    "coconut": ProduceCategory.PLANTATION_CROPS,
    "sugarcane": ProduceCategory.PLANTATION_CROPS,
    "tea": ProduceCategory.PLANTATION_CROPS,
    "coffee": ProduceCategory.PLANTATION_CROPS,
    "jasmine": ProduceCategory.FLOWERS,
    "marigold": ProduceCategory.FLOWERS,
    "rose": ProduceCategory.FLOWERS,
}

_PROHIBITED_TERMS = {
    "seed", "seeds", "pesticide", "insecticide", "herbicide", "fungicide",
    "fertilizer", "fertiliser", "urea", "agrochemical", "medicine", "veterinary",
    "livestock", "cattle", "goat", "goats", "poultry", "tractor", "machinery", "equipment",
    "விதை", "பூச்சிக்கொல்லி", "உரம்", "மருந்து", "கால்நடை", "இயந்திரம்", "டிராக்டர்",
}


def normalize_product_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(re.sub(r"[^\w\u0b80-\u0bff]+", " ", normalized).split())


def prohibited_product_term(value: str) -> str | None:
    tokens = set(normalize_product_name(value).split())
    return next((term for term in _PROHIBITED_TERMS if term in tokens), None)


# Kilograms per unit for the convertible units (bag is intentionally absent).
UNIT_KG: dict[str, float] = {
    ProduceUnit.KG.value: 1.0,
    ProduceUnit.QUINTAL.value: 100.0,
    ProduceUnit.TONNE.value: 1000.0,
}


class ProduceGrade(StrEnum):
    """Expected grade of the harvest (self-declared; AI grading is future-ready)."""

    A = "a"
    B = "b"
    C = "c"
    FAQ = "faq"  # Fair Average Quality
    MIXED = "mixed"
    UNGRADED = "ungraded"


class QuantityProvenance(StrEnum):
    FARMER_REPORTED = "farmer_reported"
    SYSTEM_ESTIMATED = "system_estimated"
    VERIFIED = "verified"


class ProduceStatus(StrEnum):
    """Procurement data-collection lifecycle (never a transactional/sale state)."""

    DRAFT = "draft"  # saved but not submitted for procurement planning
    SUBMITTED = "submitted"  # harvest info submitted for procurement planning
    PLANNED = "planned"  # acknowledged into a procurement channel's plan
    HARVESTED = "harvested"  # harvest completed
    FULFILLED = "fulfilled"  # procurement handled off-app
    WITHDRAWN = "withdrawn"  # farmer withdrew the offer
    EXPIRED = "expired"  # harvest date passed with no action


# Statuses a farmer may set directly (the rest are system/provider driven).
FARMER_SETTABLE_STATUSES: frozenset[str] = frozenset(
    {
        ProduceStatus.DRAFT.value,
        ProduceStatus.SUBMITTED.value,
        ProduceStatus.HARVESTED.value,
        ProduceStatus.WITHDRAWN.value,
    }
)


class ProcurementChannel(StrEnum):
    """Where a submitted offer is routed. Only ``MOCK`` is active in V1."""

    MOCK = "mock"
    ENAM = "enam"
    FPO = "fpo"
    PRIVATE = "private"
    EXPORT = "export"
    ADMIN = "admin"


class HarvestWindow(StrEnum):
    """Deterministic bucket for how soon a harvest is due."""

    OVERDUE = "overdue"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    LATER = "later"
