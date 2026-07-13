"""Nutrient Deficiency AI constants (docs/PRODUCT_RULES.md → never fabricate).

The Nutrient Analysis Engine reasons about *visible* nutrient deficiencies using
transparent, standard plant-nutrition symptomology, and corroborates the visual
finding with Soil / Satellite / Weather signals. Thresholds are explicit so results
are reproducible. When the evidence is insufficient the deficiency is reported as
``not_confirmed`` — never invented — and a soil/tissue test is advised. All
recommendations are *generic* localization codes; no commercial fertilizer brand is
ever recommended.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection — absent means Gemini vision when a key is set, else the mock.
NUTRIENT_PROVIDER = os.getenv("NUTRIENT_PROVIDER", "")

# Images share the same Cloudflare R2 pipeline as the Disease module (reused).
NUTRIENT_IMAGE_PREFIX = "nutrient"


class NutrientProviderName(StrEnum):
    """The visual-analysis backends. Gemini in V1; future CV models plug in here."""

    GEMINI = "gemini"
    MOCK = "mock"
    YOLO = "yolo"                 # future — YOLO nutrient model
    EFFICIENTNET = "efficientnet"  # future
    CONVNEXT = "convnext"        # future
    TENSORRT = "tensorrt"        # future — custom TensorRT model
    ONNX = "onnx"                # future — ONNX Runtime
    ENSEMBLE = "ensemble"        # future — hybrid AI ensemble


class Nutrient(StrEnum):
    """Every deficiency the module supports (docs: SUPPORTED DEFICIENCIES)."""

    NITROGEN = "nitrogen"
    PHOSPHORUS = "phosphorus"
    POTASSIUM = "potassium"
    SULPHUR = "sulphur"
    CALCIUM = "calcium"
    MAGNESIUM = "magnesium"
    IRON = "iron"
    ZINC = "zinc"
    BORON = "boron"
    COPPER = "copper"
    MANGANESE = "manganese"
    MOLYBDENUM = "molybdenum"
    CHLORINE = "chlorine"


# Nutrient groupings (mobility drives which leaves show symptoms first — reference
# knowledge only, never used to fabricate a finding).
MACRO_NUTRIENTS: frozenset[str] = frozenset(
    {Nutrient.NITROGEN.value, Nutrient.PHOSPHORUS.value, Nutrient.POTASSIUM.value}
)
SECONDARY_NUTRIENTS: frozenset[str] = frozenset(
    {Nutrient.SULPHUR.value, Nutrient.CALCIUM.value, Nutrient.MAGNESIUM.value}
)
MICRO_NUTRIENTS: frozenset[str] = frozenset(
    {
        Nutrient.IRON.value,
        Nutrient.ZINC.value,
        Nutrient.BORON.value,
        Nutrient.COPPER.value,
        Nutrient.MANGANESE.value,
        Nutrient.MOLYBDENUM.value,
        Nutrient.CHLORINE.value,
    }
)

# Nutrient → the Soil Engine parameter that corroborates a macro deficiency.
SOIL_MACRO_PARAM: dict[str, str] = {
    Nutrient.NITROGEN.value: "nitrogen",
    Nutrient.PHOSPHORUS.value: "phosphorus",
    Nutrient.POTASSIUM.value: "potassium",
}
# Micronutrients the Soil Health Card measures (DTPA) — a soil deficiency here is
# strong corroboration of the visual finding.
SOIL_MICRO_ELEMENTS: frozenset[str] = frozenset(
    {"zinc", "iron", "manganese", "copper", "boron"}
)


class DeficiencyStatus(StrEnum):
    CONFIRMED = "confirmed"          # strong visual + corroboration
    POSSIBLE = "possible"            # visible signs, not yet corroborated
    NOT_CONFIRMED = "not_confirmed"  # insufficient evidence — never invented


class Severity(StrEnum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class AffectedArea(StrEnum):
    NONE = "none"
    SPOTS = "spots"
    PATCHES = "patches"
    SCATTERED = "scattered"
    WIDESPREAD = "widespread"
    WHOLE_FIELD = "whole_field"
    UNKNOWN = "unknown"


class VisibleSymptom(StrEnum):
    """The leaf-symptom vocabulary the engine evaluates (docs: ANALYSIS ENGINE).

    Codes only — the Tamil-first client renders ``nutrient.symptom.<value>``.
    """

    YELLOWING = "yellowing"
    INTERVEINAL_CHLOROSIS = "interveinal_chlorosis"
    VEIN_YELLOWING = "vein_yellowing"
    PURPLING = "purpling"
    LEAF_EDGE_SCORCH = "leaf_edge_scorch"
    LEAF_TIP_NECROSIS = "leaf_tip_necrosis"
    NECROSIS = "necrosis"
    SPOTS = "spots"
    LEAF_CURL = "leaf_curl"
    STUNTED_LEAF = "stunted_leaf"
    PALE_LEAF = "pale_leaf"
    OLDER_LEAF_FIRST = "older_leaf_first"
    YOUNGER_LEAF_FIRST = "younger_leaf_first"
    DEFORMED_GROWTH = "deformed_growth"


ALL_SYMPTOMS: frozenset[str] = frozenset(s.value for s in VisibleSymptom)


class RecommendationCategory(StrEnum):
    NUTRIENT = "nutrient"
    TEST = "test"
    EXPERT = "expert"
    MONITOR = "monitor"
    GENERAL = "general"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReportStatus(StrEnum):
    ANALYZED = "analyzed"
    REJECTED = "rejected"


SEVERITY_ORDER: dict[str, int] = {
    Severity.NONE.value: 0,
    Severity.MILD.value: 1,
    Severity.MODERATE.value: 2,
    Severity.SEVERE.value: 3,
}

# --------------------------------------------------------------------------- #
# Confidence thresholds (transparent + tunable).
# --------------------------------------------------------------------------- #
# Visual/adjusted confidence (0-100) → deficiency status.
CONFIDENCE_CONFIRM = 75   # at/above this AND corroborated → confirmed
CONFIDENCE_POSSIBLE = 50  # at/above this → possible; below → not_confirmed

# Corroboration adjustments applied by the engine (points).
CORROBORATION_BOOST = 12       # a supporting soil/satellite/weather signal
STRONG_SOIL_BOOST = 18         # soil directly measures this nutrient as low
CONTRADICTION_PENALTY = 15     # soil measures this nutrient as sufficient/high
DISEASE_CONFLICT_PENALTY = 20  # a recent high-confidence disease on the same farm

CONFIDENCE_MIN = 0
CONFIDENCE_MAX = 99  # a visual finding is never reported as 100% certain
