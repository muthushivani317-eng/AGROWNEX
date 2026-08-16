from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.dependencies import ControlledTester

from .runtime import (
    CropRecommendationRuntime,
    CropRecommendationRuntimeError,
    get_runtime,
)
from .schemas import CropRecommendationRequest, CropRecommendationResponse

router = APIRouter(
    prefix="/crop-recommendation-controlled",
    tags=["crop-recommendation-controlled"],
)
RuntimeDep = Annotated[CropRecommendationRuntime, Depends(get_runtime)]
DISCLAIMER = (
    "TEST MODE: This is a provisional model suggestion, not agronomic advice. "
    "It has not completed independent AgrowAI field evaluation. Verify crop choice "
    "with a KVK or qualified agronomist before planting or spending money."
)


@router.get("/health")
async def health(_: ControlledTester, runtime: RuntimeDep) -> dict[str, object]:
    return {
        "status": "ready",
        "model_version": runtime.metadata["artifact_status"],
        "validation_status": runtime.metadata["validation_status"],
        "test_mode": True,
        "general_farmer_release_authorized": False,
    }


@router.post("/predict", response_model=CropRecommendationResponse)
async def predict(
    payload: CropRecommendationRequest,
    _: ControlledTester,
    runtime: RuntimeDep,
) -> CropRecommendationResponse:
    try:
        result, alternatives = runtime.predict(payload)
    except CropRecommendationRuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "CROP_RECOMMENDATION_RUNTIME_UNAVAILABLE"},
        ) from exc
    return CropRecommendationResponse(
        recommended_crop=result.crop,
        model_probability=result.model_probability,
        alternatives=alternatives,
        disclaimer=DISCLAIMER,
    )
