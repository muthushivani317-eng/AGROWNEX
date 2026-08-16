"""Explicit opt-in live Gemini validation; never runs as part of pytest."""
from __future__ import annotations

import argparse
import asyncio
import mimetypes
from pathlib import Path

from app.plant_identifier.provider import get_plant_identifier_provider
from app.plant_identifier.service import parse_plant_identification


async def main(image_path: Path) -> None:
    mime = mimetypes.guess_type(image_path.name)[0]
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise SystemExit("Unsupported image type")
    provider = get_plant_identifier_provider()
    image = await asyncio.to_thread(image_path.read_bytes)
    raw = await provider.identify(image, mime, "en", None)
    result = parse_plant_identification(raw)
    print({
        "status": result.status,
        "schema_valid": True,
        "informational_only": result.informational_only,
        "used_for_disease_routing": result.used_for_disease_routing,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--allow-live-provider", action="store_true")
    args = parser.parse_args()
    if not args.allow_live_provider:
        raise SystemExit("Live provider access requires --allow-live-provider")
    asyncio.run(main(args.image))
