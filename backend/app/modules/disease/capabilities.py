"""Fail-closed capability registry for the legacy joint disease endpoint.

Banana V3 has a separate verified endpoint. The legacy joint classifier is not
enabled until its checkpoint lineage, calibration, thresholds and bundle are
recovered and verified.
"""

from __future__ import annotations

from enum import StrEnum


class DatasetVerificationStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    EXPERT_REVIEW_PENDING = "EXPERT_REVIEW_PENDING"
    EXPERT_VERIFIED = "EXPERT_VERIFIED"
    REJECTED = "REJECTED"


class ModelDeploymentStatus(StrEnum):
    NOT_TRAINED = "NOT_TRAINED"
    TRAINING = "TRAINING"
    PROVISIONAL_EVALUATION = "PROVISIONAL_EVALUATION"
    DEPLOYED_RESEARCH_ONLY = "DEPLOYED_RESEARCH_ONLY"
    PRODUCTION_APPROVED = "PRODUCTION_APPROVED"


def _capability(
    crop: str,
    dataset: DatasetVerificationStatus,
    model: ModelDeploymentStatus,
    disease_available: bool,
) -> dict:
    return {
        "crop": crop,
        "visible_in_app": True,
        "dataset_verification_status": dataset.value,
        "disease_model_status": model.value,
        "disease_model_available": disease_available,
        "nutrient_model_available": True,
        "satellite_support_available": True,
        "production_approved": False,
    }


CROP_CAPABILITIES = {
    crop: _capability(
        crop,
        DatasetVerificationStatus.EXPERT_VERIFIED,
        ModelDeploymentStatus.DEPLOYED_RESEARCH_ONLY,
        True,
    )
    for crop in ("rice", "cotton", "groundnut")
}
CROP_CAPABILITIES.update(
    {
        crop: _capability(
            crop,
            DatasetVerificationStatus.EXPERT_VERIFIED,
            ModelDeploymentStatus.NOT_TRAINED,
            False,
        )
        for crop in ("banana", "chilli", "blackgram", "redgram")
    }
)
# Banana V3 remains independently verified and operational.
CROP_CAPABILITIES["banana"] = _capability(
    "banana",
    DatasetVerificationStatus.EXPERT_VERIFIED,
    ModelDeploymentStatus.DEPLOYED_RESEARCH_ONLY,
    True,
)
CROP_CAPABILITIES.update(
    {
        crop: _capability(
            crop,
            DatasetVerificationStatus.EXPERT_REVIEW_PENDING,
            ModelDeploymentStatus.NOT_TRAINED,
            False,
        )
        for crop in ("maize", "coconut", "greengram", "pearl_millet")
    }
)

_CROP_ALIASES = {
    "rice": "rice",
    "paddy": "rice",
    "paddy_rice": "rice",
    "paddy (rice)": "rice",
    "நெல்": "rice",
    "cotton": "cotton",
    "groundnut": "groundnut",
    "banana": "banana",
    "chilli": "chilli",
    "blackgram": "blackgram",
    "redgram": "redgram",
}


def normalize_crop_id(crop: str | None) -> str:
    """Return a stable model-facing crop ID without using display labels."""
    normalized = (crop or "").strip().casefold()
    return _CROP_ALIASES.get(normalized, normalized)


def disease_model_available(crop: str) -> bool:
    return bool(
        CROP_CAPABILITIES.get(normalize_crop_id(crop), {}).get(
            "disease_model_available"
        )
    )


def public_capabilities() -> list[dict]:
    return list(CROP_CAPABILITIES.values())
