import io

from app.modules.lcc.analyzer import (
    analyze_leaf_image,
    delta_e_cie76,
    srgb_to_lab,
)
from PIL import Image, ImageDraw


def _photo(colour: tuple[int, int, int], *, size: int = 500, leaf_fraction: float = 0.7) -> bytes:
    image = Image.new("RGB", (size, size), (235, 235, 235))
    draw = ImageDraw.Draw(image)
    margin = int(size * (1 - leaf_fraction) / 2)
    draw.ellipse((margin, size // 8, size - margin, size * 7 // 8), fill=colour)
    # Leaf-like veins provide real edges; a flat colour card should fail the blur guard.
    for x in range(margin + 10, size - margin, 16):
        lighter = tuple(min(255, value + 12) for value in colour)
        draw.line((size // 2, size // 2, x, size // 5), fill=lighter, width=2)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=92)
    return output.getvalue()


def test_lab_conversion_and_delta_e_are_deterministic() -> None:
    lab = srgb_to_lab((125, 162, 65))
    assert 60 < lab[0] < 70
    assert delta_e_cie76(lab, lab) == 0


def test_matches_a_reference_panel_without_external_ai() -> None:
    result = analyze_leaf_image(_photo((75, 132, 59)))
    assert result.abstained is False
    assert result.panel_number == 4
    assert result.nitrogen_status == "borderline"


def test_abstains_when_too_little_green_is_visible() -> None:
    result = analyze_leaf_image(_photo((75, 132, 59), leaf_fraction=0.15))
    assert result.abstained is True
    assert result.quality_issue == "too_little_leaf"


def test_abstains_for_dark_photo() -> None:
    result = analyze_leaf_image(_photo((25, 42, 18)))
    assert result.abstained is True
    assert result.quality_issue in {"too_dark", "too_little_leaf"}


def test_rejects_non_image_bytes() -> None:
    result = analyze_leaf_image(b"not an image")
    assert result.abstained is True
    assert result.quality_issue == "invalid_image"
