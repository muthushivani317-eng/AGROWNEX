import pytest
from app.modules.nutrient.crops import (
    normalize_nutrient_crop,
    normalize_observed_nutrient_crop,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Sugarcane", "sugarcane"),
        ("sugar cane", "sugarcane"),
        ("Rice", "paddy"),
        ("Red-Gram", "red gram"),
        ("நெல்", "நெல்"),
    ],
)
def test_normalize_nutrient_crop(value, expected) -> None:
    assert normalize_nutrient_crop(value) == expected


@pytest.mark.parametrize("value", ["", "   ", "paddy<script>", "crop/../../x", "x" * 81])
def test_normalize_nutrient_crop_rejects_invalid_values(value) -> None:
    with pytest.raises(ValueError):
        normalize_nutrient_crop(value)


def test_observed_crop_allows_parenthesized_scientific_name() -> None:
    assert normalize_observed_nutrient_crop("Sugarcane (Saccharum officinarum)") == "sugarcane"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Banana plant", "banana"),
        ("banana tree", "banana"),
        ("Banana Plant (Musa spp.)", "banana"),
        ("Paddy crop", "paddy"),
        ("Sugarcane", "sugarcane"),
    ],
)
def test_observed_crop_strips_generic_descriptor_suffix(value, expected) -> None:
    assert normalize_observed_nutrient_crop(value) == expected


def test_observed_crop_does_not_strip_a_bare_generic_word() -> None:
    # "tree" alone stays "tree" -- we only drop a trailing descriptor when it
    # follows an actual crop name, never strip down to nothing.
    assert normalize_observed_nutrient_crop("Tree") == "tree"
