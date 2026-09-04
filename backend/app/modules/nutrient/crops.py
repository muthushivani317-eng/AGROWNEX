"""Crop-name handling for nutrient image analysis.

Nutrient analysis is model-driven and is not limited to the disease classifier's
fixed class registry.  Crop names still need deterministic normalization so request,
farm, and observed-image values can be compared safely.
"""

from __future__ import annotations

import re
import unicodedata

_MAX_CROP_NAME_LENGTH = 80
_ALIASES = {
    "rice": "paddy",
    "paddy rice": "paddy",
    "sugar cane": "sugarcane",
}
_SEPARATORS = frozenset({" ", "-", "_", "'", "’"})
# The vision model sometimes appends a generic botanical word to an otherwise
# correct crop name (e.g. "banana plant" instead of "banana"). Stripped only from
# the *observed* value below so a wording difference is never treated as a
# different crop than the one the farmer/farm actually selected.
_GENERIC_SUFFIXES = frozenset(
    {
        "plant",
        "plants",
        "tree",
        "trees",
        "crop",
        "crops",
        "leaf",
        "leaves",
        "sapling",
        "saplings",
        "seedling",
        "seedlings",
        "shrub",
        "shrubs",
        "vine",
        "vines",
        "sprout",
        "sprouts",
    }
)


def normalize_nutrient_crop(value: str) -> str:
    """Return a comparable crop identifier without imposing a fixed crop list.

    The farm crop and provider observation are data, not prompts or code.  We allow
    international letter names plus ordinary word separators, while rejecting empty,
    excessively long, or control/punctuation-heavy values.
    """

    text = unicodedata.normalize("NFKC", value or "").strip()
    if not text or len(text) > _MAX_CROP_NAME_LENGTH:
        raise ValueError("invalid crop name")
    if any(
        not (unicodedata.category(char)[0] in {"L", "M"} or char in _SEPARATORS) for char in text
    ):
        raise ValueError("invalid crop name")

    normalized = " ".join(text.replace("_", " ").replace("-", " ").casefold().split())
    if not normalized or not any(char.isalpha() for char in normalized):
        raise ValueError("invalid crop name")
    return _ALIASES.get(normalized, normalized)


def normalize_observed_nutrient_crop(value: str) -> str:
    """Normalize model output, tolerating a parenthesized scientific name and a
    trailing generic descriptor word (the model sometimes says "banana plant"
    where "banana" was meant -- same crop, not a mismatch).
    """
    common_name = re.sub(r"\s*\([^()]{1,80}\)\s*$", "", value or "")
    normalized = normalize_nutrient_crop(common_name)
    words = normalized.split(" ")
    while len(words) > 1 and words[-1] in _GENERIC_SUFFIXES:
        words.pop()
    return " ".join(words)
