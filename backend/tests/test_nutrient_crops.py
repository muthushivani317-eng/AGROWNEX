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
