"""Secret-safe configuration readiness for satellite image generation."""

from __future__ import annotations

import os


def _present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def satellite_readiness() -> dict[str, bool | list[str]]:
    provider = _present("COPERNICUS_CLIENT_ID") and _present("COPERNICUS_CLIENT_SECRET")
    storage = all(
        _present(name)
        for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
    )
    public_delivery = _present("R2_PUBLIC_BASE_URL")
    queue = _present("REDIS_URL")
    states = {
        "provider": provider,
        "storage": storage,
        "public_delivery": public_delivery,
        "queue": queue,
    }
    return {
        "provider_configured": provider,
        "storage_configured": storage,
        "public_delivery_configured": public_delivery,
        "queue_configured": queue,
        "ready_for_image_generation": all(states.values()),
        "missing_components": [name for name, configured in states.items() if not configured],
    }
