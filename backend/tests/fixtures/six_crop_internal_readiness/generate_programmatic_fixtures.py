"""Generate deterministic non-agricultural safety fixtures.

These files exercise decoding and image-safety gates only. They are not
agricultural evidence and must never be used to validate crop identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "generated"
SEED = 20260728


def _save(name: str, image: Image.Image, image_format: str = "PNG") -> None:
    path = GENERATED / name
    image.save(path, image_format)


def main() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    size = (224, 224)

    _save("all_black.png", Image.new("RGB", size, "black"))
    _save("all_white.png", Image.new("RGB", size, "white"))
    _save("solid_colour.png", Image.new("RGB", size, (40, 120, 190)))
    _save(
        "random_noise.png",
        Image.fromarray(rng.integers(0, 256, (224, 224, 3), dtype=np.uint8)),
    )
    checker = np.indices(size).sum(axis=0) % 2 * 255
    _save(
        "checkerboard.png",
        Image.fromarray(np.repeat(checker[:, :, None], 3, axis=2).astype(np.uint8)),
    )
    gradient = np.linspace(0, 255, 224, dtype=np.uint8)
    _save(
        "gradient.png",
        Image.fromarray(
            np.repeat(np.tile(gradient, (224, 1))[:, :, None], 3, axis=2)
        ),
    )
    _save("tiny.png", Image.new("RGB", (16, 16), (40, 110, 40)))
    texture = Image.fromarray(
        rng.integers(20, 220, (224, 224, 3), dtype=np.uint8)
    )
    _save("extreme_blur.png", texture.filter(ImageFilter.GaussianBlur(30)))
    _save("overexposed.png", Image.new("RGB", size, (253, 253, 253)))
    _save("underexposed.png", Image.new("RGB", size, (2, 2, 2)))

    screenshot = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(screenshot)
    for y in range(20, 200, 20):
        draw.rectangle((15, y, 190, y + 5), fill="black")
    _save("text_screenshot.png", screenshot)

    ui = Image.new("RGB", size, (242, 242, 242))
    draw = ImageDraw.Draw(ui)
    draw.rectangle((10, 10, 214, 45), fill=(25, 100, 180))
    for y in (65, 105, 145):
        draw.rectangle((20, y, 204, y + 24), outline=(40, 40, 40), width=2)
    _save("ui_like_screenshot.png", ui)

    shapes = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(shapes)
    draw.ellipse((15, 15, 100, 100), fill="red")
    draw.rectangle((120, 20, 210, 100), fill="blue")
    draw.polygon(((20, 210), (110, 115), (200, 210)), fill="yellow")
    _save("geometric_shapes.png", shapes)

    (GENERATED / "corrupt.jpg").write_bytes(b"not-a-jpeg")
    good_png = GENERATED / "gradient.png"
    (GENERATED / "truncated.png").write_bytes(good_png.read_bytes()[:40])
    (GENERATED / "unsupported.txt").write_text(
        "deterministic unsupported-format fixture\n", encoding="utf-8"
    )

    inventory = []
    for path in sorted(GENERATED.iterdir()):
        if path.name == "GENERATION_MANIFEST.json":
            continue
        inventory.append(
            {
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "seed": SEED,
                "dimensions": None
                if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}
                or path.name in {"corrupt.jpg", "truncated.png"}
                else list(Image.open(path).size),
                "purpose": "PROGRAMMATIC_INVALID",
            }
        )
    (GENERATED / "GENERATION_MANIFEST.json").write_text(
        json.dumps(
            {
                "generator": str(Path(__file__).name),
                "seed": SEED,
                "agricultural_evidence": False,
                "fixtures": inventory,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
