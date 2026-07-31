"""Disease API routes (docs/API_CONTRACT.md → DISEASE DETECTION).

    POST   /disease/analyze
    GET    /disease/history      GET /disease/{id}    DELETE /disease/{id}

Thin routes — the full pipeline lives in ``DiseaseService``.
"""

from __future__ import annotations

import json
import math
import time
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.crop_runtime.registry import load_registry
from app.crop_runtime.schemas import ModelAvailabilityStatus, ModelUnavailableResponse
from app.modules.disease.capabilities import (
    disease_model_available,
    normalize_crop_id,
    public_capabilities,
)
from app.modules.disease.dependencies import CurrentUser, DiseaseServiceDep
from app.modules.disease.ml_runtime import get_model_runtime
from app.modules.disease.ml_runtime.orchestrator import decide
from app.modules.disease.schemas import (
    AnalyzeRequest,
    AnalyzeV2Request,
    CropCapabilityOut,
    DiagnosisV2Envelope,
    DiseaseReportOut,
    DiseaseReportSummaryOut,
    ModelMetadataOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/disease", tags=["disease"])
logger = get_logger("disease.inference")


@router.post("/analyze", response_model=SuccessResponse[DiseaseReportOut], status_code=201)
async def analyze(payload: AnalyzeRequest, current_user: CurrentUser, service: DiseaseServiceDep):
    """Validate a photo, run Gemini vision analysis, store and return the report."""
    if payload.crop:
        try:
            entry = load_registry().get(payload.crop)
        except KeyError:
            entry = None
        if (
            entry is not None
            and entry.model_status == ModelAvailabilityStatus.FROZEN_RUNTIME_READY
            and not entry.disease_detection_enabled
        ):
            unavailable = ModelUnavailableResponse(
                crop_id=entry.crop_id,
                message_en=entry.limitation_message_en,
                message_ta=entry.limitation_message_ta,
                limitation=entry.model_status,
            )
            raise HTTPException(
                status_code=503, detail=unavailable.model_dump(mode="json")
            )
    report = await service.analyze(current_user, payload)
    return success(DiseaseReportOut.from_report(report), message="Analysis complete")


@router.post("/analyze-v2", response_model=SuccessResponse[DiagnosisV2Envelope])
async def analyze_v2(payload: AnalyzeV2Request, current_user: CurrentUser):
    """Deprecated global-calibration route; crop-specific routes are mandatory."""
    del current_user  # authentication is required; identity is intentionally not logged.
    canonical_crop = normalize_crop_id(payload.selected_crop)
    if not disease_model_available(canonical_crop) or canonical_crop in {
        "rice",
        "cotton",
        "groundnut",
        "banana",
    }:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNSUPPORTED_CROP",
                "message_tamil": "இந்தப் பயிருக்கான நோய் கண்டறிதல் மாதிரி இன்னும் பயன்பாட்டிற்கு தயாராகவில்லை.",
                "message_english": (
                    "Use the verified crop-specific diagnosis endpoint. "
                    "Global calibration is disabled."
                ),
            },
        )
    started = time.perf_counter()
    runtime = get_model_runtime()
    try:
        prediction = runtime.predict(payload.image_base64, payload.mime_type)
    except Exception as exc:
        logger.warning(
            "disease_inference %s",
            json.dumps(
                {
                    "request_id": payload.request_id,
                    "model_version": "mobilenetv3_small_v1",
                    "selected_crop": canonical_crop,
                    "accepted": False,
                    "error_category": type(exc).__name__,
                    "total_ms": round((time.perf_counter() - started) * 1000, 3),
                },
                separators=(",", ":"),
            ),
        )
        raise
    response = decide(
        request_id=payload.request_id,
        selected_crop=canonical_crop,
        language=payload.language,
        prediction=prediction,
        symptoms=payload.symptoms,
        growth_stage=payload.growth_stage,
        knowledge_evidence=payload.knowledge_evidence,
        image_reference=payload.image_reference,
        image_storage_consent=payload.image_storage_consent,
    )
    log_record = {
        "request_id": payload.request_id,
        "model_version": response["model_version"],
        "selected_crop": canonical_crop,
        "predicted_class": prediction.predicted_class,
        "calibrated_confidence": prediction.confidence,
        "top3": prediction.top3,
        "accepted": response["accepted"],
        "decision_type": response["decision_type"],
        "inference_ms": round(prediction.inference_ms, 3),
        "preprocessing_ms": round(prediction.preprocessing_ms, 3),
        "total_ms": round((time.perf_counter() - started) * 1000, 3),
        "error_category": None,
    }
    logger.info("disease_inference %s", json.dumps(log_record, separators=(",", ":")))
    return success(DiagnosisV2Envelope(response=response, audit=response["audit_record"]))


@router.get("/model-metadata", response_model=SuccessResponse[ModelMetadataOut])
async def model_metadata(current_user: CurrentUser):
    del current_user
    return success(ModelMetadataOut.model_validate(get_model_runtime().metadata()))


@router.get("/capabilities", response_model=SuccessResponse[list[CropCapabilityOut]])
async def crop_capabilities(current_user: CurrentUser):
    del current_user
    return success([CropCapabilityOut.model_validate(item) for item in public_capabilities()])


@router.get(
    "/history",
    response_model=SuccessResponse[PaginatedData[DiseaseReportSummaryOut]],
)
async def list_history(
    current_user: CurrentUser,
    service: DiseaseServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    farm_id: uuid.UUID | None = Query(None),
    crop: str | None = Query(None),
):
    """List past diagnoses (most recent first; filterable by farm and crop)."""
    items, total = await service.list_reports(
        current_user, page=page, page_size=page_size, farm_id=farm_id, crop=crop
    )
    data = PaginatedData(
        items=[DiseaseReportSummaryOut.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )
    return success(data)


@router.get("/{report_id}", response_model=SuccessResponse[DiseaseReportOut])
async def get_report(report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep):
    """Fetch a full disease report."""
    report = await service.get_report(current_user, report_id)
    return success(DiseaseReportOut.from_report(report))


@router.delete("/{report_id}", response_model=SuccessResponse[None])
async def delete_report(
    report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep
):
    """Delete a disease report (soft delete)."""
    await service.delete_report(current_user, report_id)
    return success(None, message="Report deleted")
