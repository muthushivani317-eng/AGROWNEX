"""Compatibility accessors backed exclusively by the crop runtime registry.

New API code should use :mod:`app.modules.disease.capability_service`, which
also combines authenticated roles with executable runtime readiness.
"""
from __future__ import annotations

from app.crop_runtime.registry import load_registry


def _legacy_view() -> dict[str, dict[str, object]]:
    registry = load_registry()
    return {
        entry.crop_id: {
            "crop": entry.crop_id,
            "visible_in_app": entry.crop_enabled,
            "dataset_verification_status": entry.field_validation_status,
            "disease_model_status": entry.model_status.value,
            "disease_model_available": entry.disease_detection_enabled,
            "nutrient_model_available": True,
            "satellite_support_available": True,
            "production_approved": False,
        }
        for entry in registry.document.crops
    }


CROP_CAPABILITIES = _legacy_view()


def normalize_crop_id(crop: str | None) -> str:
    """Return the registry's stable crop ID, retaining unknown IDs for rejection."""
    normalized = (crop or "").strip().casefold()
    try:
        return load_registry().normalize(normalized)
    except KeyError:
        return normalized


def disease_model_available(crop: str) -> bool:
    try:
        return load_registry().get(crop).disease_detection_enabled
    except KeyError:
        return False


def public_capabilities() -> list[dict[str, object]]:
    """Deprecated generic view; authenticated APIs use the capability service."""
    return list(CROP_CAPABILITIES.values())
