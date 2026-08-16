"""Scheme module constants (docs/DATABASE_SCHEMA.md → Government domain).

Verified schemes only (docs/PRODUCT_RULES.md rule 4). The eligibility engine is
deterministic and rule-based — no AI in V1 — so recommendations are transparent
and explainable.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Sentinel meaning "no constraint" in a scheme's structured rule lists.
ANY = "all"

SOURCE_MOCK = "mock"
# Hand-curated, individually-verified static snapshot of real official scheme
# data (app/modules/schemes/curated_data.py) -- not a live government API, but
# real sourced and dated content, not a fabrication (2026-08 pre-release audit
# follow-up: see curated_data.py's module docstring for why).
SOURCE_CURATED = "curated_verified"
# Future providers read a source key from the environment; absent → mock.
SCHEME_PROVIDER = os.getenv("SCHEME_PROVIDER", "")

# A scheme is "recommended" when the farmer scores at least this (0-100).
RECOMMENDED_SCORE_THRESHOLD = int(os.getenv("SCHEME_RECOMMENDED_THRESHOLD", "70"))
# Fallback: always surface at least this many top eligible schemes as recommended.
RECOMMENDED_MIN_COUNT = 3


class SchemeCategory(StrEnum):
    """Master categories (docs/DATABASE_SCHEMA.md → scheme_categories)."""

    INSURANCE = "insurance"
    SUBSIDY = "subsidy"
    LOAN = "loan"
    EQUIPMENT = "equipment"
    SEEDS = "seeds"
    IRRIGATION = "irrigation"
    ORGANIC = "organic_farming"
    INCOME_SUPPORT = "income_support"
    OTHER = "other"


class FarmerCategory(StrEnum):
    """Land-holding class — the Indian operational-holding classification."""

    MARGINAL = "marginal"  # < 1 ha
    SMALL = "small"  # 1–2 ha
    SEMI_MEDIUM = "semi_medium"  # 2–4 ha
    MEDIUM = "medium"  # 4–10 ha
    LARGE = "large"  # > 10 ha


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    # All hard checks pass, but some farmer data is missing to be certain.
    LIKELY = "likely_eligible"
    NOT_ELIGIBLE = "not_eligible"


class SchemeStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class SchemeTab(StrEnum):
    ELIGIBLE = "eligible"
    RECOMMENDED = "recommended"
    ALL = "all"
    BOOKMARKED = "bookmarked"


class DocumentType(StrEnum):
    AADHAAR = "aadhaar"
    LAND_TENURE_PROOF = "land_tenure_proof"
    BANK_PASSBOOK = "bank_passbook"
    PHOTOGRAPH = "photograph"
    INCOME_CERTIFICATE = "income_certificate"
    SOWING_CERTIFICATE = "sowing_certificate"
    SERVICE_CONNECTION = "service_connection"
    WATER_SOURCE_PROOF = "water_source_proof"
    OTHER = "other"


# Maps every exact document_name currently used across scheme records to its
# canonical type. Add new entries whenever a provider introduces a new name.
DOCUMENT_TYPE_ALIASES: dict[str, DocumentType] = {
    "Aadhaar card": DocumentType.AADHAAR,
    "Identity proof (Aadhaar/Voter ID)": DocumentType.AADHAAR,
    "Land ownership records": DocumentType.LAND_TENURE_PROOF,
    "Land ownership documents": DocumentType.LAND_TENURE_PROOF,
    "Land records": DocumentType.LAND_TENURE_PROOF,
    "Land records / tenancy proof": DocumentType.LAND_TENURE_PROOF,
    "Bank account passbook": DocumentType.BANK_PASSBOOK,
    "Bank passbook": DocumentType.BANK_PASSBOOK,
    "Passport-size photograph": DocumentType.PHOTOGRAPH,
    "Income certificate": DocumentType.INCOME_CERTIFICATE,
    "Sowing certificate": DocumentType.SOWING_CERTIFICATE,
    "Agricultural service connection number": DocumentType.SERVICE_CONNECTION,
    "Water source proof": DocumentType.WATER_SOURCE_PROOF,
}


def classify_document(name: str) -> DocumentType:
    return DOCUMENT_TYPE_ALIASES.get(name, DocumentType.OTHER)


# Farmer-category thresholds in hectares (upper bound, exclusive except LARGE).
FARMER_CATEGORY_BOUNDS: tuple[tuple[FarmerCategory, float], ...] = (
    (FarmerCategory.MARGINAL, 1.0),
    (FarmerCategory.SMALL, 2.0),
    (FarmerCategory.SEMI_MEDIUM, 4.0),
    (FarmerCategory.MEDIUM, 10.0),
)


def derive_farmer_category(land_hectares: float | None) -> FarmerCategory | None:
    """Classify a holding by size (marginal/small/…); ``None`` if land unknown."""
    if land_hectares is None or land_hectares <= 0:
        return None
    for category, upper in FARMER_CATEGORY_BOUNDS:
        if land_hectares < upper:
            return category
    return FarmerCategory.LARGE
