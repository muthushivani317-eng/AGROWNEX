from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from .readiness import ReadinessResolver
from .registry import load_registry
from .resolver import ModelNotAvailableError, RuntimeIntegrityError, RuntimeResolver
from .schemas import CropRegistryEntry, ModelAvailabilityStatus

router = APIRouter(tags=["crop-runtime"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolver() -> RuntimeResolver:
    return RuntimeResolver(load_registry(), Path(__file__).resolve().parents[2])


def build_model_status(
    entry: CropRegistryEntry,
    resolver: RuntimeResolver,
) -> dict[str, object]:
    bundle_present = False
    integrity_verified = False
    integrity = "NOT_APPLICABLE"
    if entry.model_status == ModelAvailabilityStatus.FROZEN_RUNTIME_READY:
        bundle_present = resolver.bundle_presence(entry.crop_id)
        if not bundle_present:
            integrity = "LOCAL_RUNTIME_BUNDLE_MISSING"
        else:
            try:
                resolver.verify_integrity(entry.crop_id)
                integrity_verified = True
                integrity = "VERIFIED"
            except (ModelNotAvailableError, RuntimeIntegrityError):
                integrity = "FAILED_CLOSED"

    local_runtime_ready = bundle_present and integrity_verified
    inference_authorized = (
        entry.crop_enabled
        and entry.disease_detection_enabled
        and entry.model_status == ModelAvailabilityStatus.FROZEN_RUNTIME_READY
        and local_runtime_ready
    )
    return {
        "crop_id": entry.crop_id,
        "declared_status": entry.model_status.value,
        "model_status": entry.model_status.value,
        "local_runtime_bundle_present": bundle_present,
        "local_integrity_verified": integrity_verified,
        "local_runtime_ready": local_runtime_ready,
        "integrity_status": integrity,
        "pilot_inference_eligible": entry.pilot_inference_eligible,
        "disease_detection_enabled": entry.disease_detection_enabled,
        "general_farmer_inference_authorized": (
            entry.general_farmer_inference_authorized is True
        ),
        "inference_authorized": inference_authorized,
        "field_validation_status": entry.field_validation_status,
        "official_accuracy_claim": False,
    }


@router.get("/crops")
async def list_crops():
    registry = load_registry()
    readiness = ReadinessResolver(registry, PROJECT_ROOT)
    return [
        {
            **registry.public(entry.crop_id).model_dump(mode="json"),
            **readiness.resolve(entry.crop_id).public_dict(),
        }
        for entry in registry.document.crops
    ]


@router.get("/crops/{crop_id}")
async def get_crop(crop_id: str):
    try:
        registry = load_registry()
        entry = registry.get(crop_id)
        return {
            **registry.public(entry.crop_id).model_dump(mode="json"),
            **ReadinessResolver(registry, PROJECT_ROOT)
            .resolve(entry.crop_id)
            .public_dict(),
        }
    except KeyError as exc:
        raise HTTPException(404, detail={"code": "INVALID_CROP_ID"}) from exc


@router.get("/crops/{crop_id}/capabilities")
async def crop_capabilities(crop_id: str):
    return await get_crop(crop_id)


@router.get("/models/status")
async def model_status():
    registry = load_registry()
    resolver = ReadinessResolver(registry, PROJECT_ROOT)
    return [
        {
            **resolver.resolve(entry.crop_id).public_dict(),
            "pilot_inference_eligible": entry.pilot_inference_eligible,
            "disease_detection_enabled": entry.disease_detection_enabled,
            "model_status": entry.model_status.value,
            "declared_status": entry.model_status.value,
            "field_validation_status": entry.field_validation_status,
            "official_accuracy_claim": False,
        }
        for entry in registry.document.crops
    ]
