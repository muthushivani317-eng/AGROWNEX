"""Process-local cache of immutable technical model readiness.

Roles and field-test session state are intentionally excluded.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .readiness import CropReadiness, ReadinessResolver
from .registry import load_registry

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _build_snapshot() -> dict[str, CropReadiness]:
    registry = load_registry()
    resolver = ReadinessResolver(registry, BACKEND_ROOT)
    return {
        entry.crop_id: resolver.resolve(entry.crop_id)
        for entry in registry.document.crops
    }


@lru_cache(maxsize=1)
def get_technical_readiness() -> dict[str, CropReadiness]:
    return _build_snapshot()


def refresh_technical_readiness() -> None:
    get_technical_readiness.cache_clear()
