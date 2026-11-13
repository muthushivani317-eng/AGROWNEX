"""Authenticated controlled-test API for experimental Groundnut inference."""

from __future__ import annotations

import asyncio
import io
import time
import uuid
import warnings
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.modules.auth.constants import RoleName
from app.modules.auth.dependencies import TesterContext, require_any_role
from app.modules.disease.ml_runtime.orchestrator import preliminary_groundnut_text_guidance

from .schemas import (
    GroundnutPredictionResponse,
    GroundnutPestObservationResponse,
    GroundnutTextGuidanceResponse,
    GroundnutTextSymptomRequest,
    GroundnutTranscriptMapRequest,
    GroundnutTranscriptMapResponse,
    GroundnutTranscriptResponse,
    ImageQualityOut,
    RankedPredictionOut,
)
from .pest_observations import (
    PestObservationFarmNotFoundError,
    persist_groundnut_pest_observation,
)
from .service import (
    GroundnutModelUnavailableError,
    GroundnutPredictionService,
    get_groundnut_prediction_service,
)
from .stt import (
    GroundnutSpeechError,
    GroundnutSpeechService,
    get_groundnut_speech_service,
)
from .symptom_mapper import map_groundnut_transcript

router = APIRouter(prefix="/doctor/groundnut", tags=["groundnut-experimental"])
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_PIL_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
EXPERIMENTAL_NOTICE = (
    "Experimental model. External test accuracy was 70.22%; this result is not agronomically validated and must not be treated as a confirmed diagnosis."
)


async def require_groundnut_controlled_tester(
    tester: TesterContext = Depends(
        require_any_role(
            RoleName.INTERNAL_TESTER.value,
            RoleName.PILOT_TESTER.value,
            RoleName.KVK_REVIEWER.value,
        )
    ),
) -> TesterContext:
    return tester


GroundnutServiceDep = Annotated[
    GroundnutPredictionService,
    Depends(get_groundnut_prediction_service),
]
GroundnutSpeechServiceDep = Annotated[
    GroundnutSpeechService,
    Depends(get_groundnut_speech_service),
]

ALLOWED_AUDIO_TYPES = frozenset(
    {"audio/amr", "audio/wav", "audio/x-wav", "audio/flac", "audio/mpeg", "audio/ogg", "audio/webm"}
)
SUPPORTED_STT_LANGUAGES = frozenset({"en-IN", "ta-IN", "ml-IN"})


async def _read_upload(image: UploadFile) -> bytes:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        await image.close()
        raise HTTPException(
            415,
            detail={
                "code": "GROUNDNUT_IMAGE_FORMAT_UNSUPPORTED",
                "message": "Upload a JPEG, PNG, or WebP image.",
            },
        )
    payload = await image.read(settings.groundnut_max_upload_bytes + 1)
    await image.close()
    if not payload:
        raise HTTPException(
            422,
            detail={"code": "GROUNDNUT_IMAGE_EMPTY", "message": "The uploaded image is empty."},
        )
    if len(payload) > settings.groundnut_max_upload_bytes:
        raise HTTPException(
            413,
            detail={
                "code": "GROUNDNUT_IMAGE_TOO_LARGE",
                "message": "The uploaded image exceeds the allowed size.",
            },
        )
    return payload


def _decode_upload(payload: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(payload))
            detected_format = image.format
            image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(
            422,
            detail={
                "code": "GROUNDNUT_IMAGE_CORRUPTED",
                "message": "The uploaded file is not a readable image.",
            },
        ) from exc
    if detected_format not in ALLOWED_PIL_FORMATS:
        raise HTTPException(
            415,
            detail={
                "code": "GROUNDNUT_IMAGE_FORMAT_UNSUPPORTED",
                "message": "The decoded image format is not supported.",
            },
        )
    if image.width * image.height > settings.groundnut_max_image_pixels:
        raise HTTPException(
            413,
            detail={
                "code": "GROUNDNUT_IMAGE_PIXEL_LIMIT_EXCEEDED",
                "message": "The image dimensions exceed the allowed pixel limit.",
            },
        )
    if min(image.size) < settings.groundnut_min_image_dimension:
        raise HTTPException(
            422,
            detail={
                "code": "GROUNDNUT_IMAGE_TOO_SMALL",
                "message": "The image is too small for Groundnut disease inference.",
            },
        )
    return image.convert("RGB")


def _prediction(value: dict | None) -> RankedPredictionOut | None:
    return RankedPredictionOut.model_validate(value) if value else None


@router.post("/pest-observations", response_model=GroundnutPestObservationResponse, status_code=201)
async def submit_groundnut_pest_observation(
    tester: Annotated[TesterContext, Depends(require_groundnut_controlled_tester)],
    session: Annotated[AsyncSession, Depends(get_session)],
    damage_extent: Annotated[Literal["few", "several", "widespread"], Form(...)],
    spread_speed: Annotated[Literal["unknown", "stable", "rapid"], Form(...)],
    consent: Annotated[bool, Form(...)],
    image: UploadFile = File(...),
    capture_method: Annotated[Literal["camera", "gallery"], Form()] = "gallery",
    farm_id: Annotated[uuid.UUID | None, Form()] = None,
) -> GroundnutPestObservationResponse:
    if not consent:
        await image.close()
        raise HTTPException(
            422,
            detail={"code": "GROUNDNUT_PEST_REVIEW_CONSENT_REQUIRED"},
        )
    payload = await _read_upload(image)
    _decode_upload(payload)
    try:
        report = await persist_groundnut_pest_observation(
            session,
            user_id=tester.user.id,
            farm_id=farm_id,
            image=payload,
            content_type=image.content_type or "",
            capture_method=capture_method,
            damage_extent=damage_extent,
            spread_speed=spread_speed,
        )
    except PestObservationFarmNotFoundError as exc:
        raise HTTPException(
            404,
            detail={"code": "GROUNDNUT_FARM_NOT_FOUND"},
        ) from exc
    return GroundnutPestObservationResponse(
        observation_id=report.id,
        damage_extent=damage_extent,
        spread_speed=spread_speed,
    )


@router.post("/symptoms", response_model=GroundnutTextGuidanceResponse)
async def groundnut_text_symptoms(
    payload: GroundnutTextSymptomRequest,
    tester: Annotated[TesterContext, Depends(require_groundnut_controlled_tester)],
) -> GroundnutTextGuidanceResponse:
    del tester
    result = preliminary_groundnut_text_guidance(list(payload.symptoms))
    return GroundnutTextGuidanceResponse.model_validate(result)


@router.post("/transcribe", response_model=GroundnutTranscriptResponse)
async def transcribe_groundnut_symptoms(
    tester: Annotated[TesterContext, Depends(require_groundnut_controlled_tester)],
    service: GroundnutSpeechServiceDep,
    audio: UploadFile = File(...),
    language: str = Form(...),
) -> GroundnutTranscriptResponse:
    del tester
    if language not in SUPPORTED_STT_LANGUAGES:
        await audio.close()
        raise HTTPException(422, detail={"code": "GROUNDNUT_STT_LANGUAGE_UNSUPPORTED"})
    if audio.content_type not in ALLOWED_AUDIO_TYPES:
        await audio.close()
        raise HTTPException(415, detail={"code": "GROUNDNUT_STT_AUDIO_FORMAT_UNSUPPORTED"})
    payload = await audio.read(settings.groundnut_stt_max_audio_bytes + 1)
    await audio.close()
    if not payload:
        raise HTTPException(422, detail={"code": "GROUNDNUT_STT_AUDIO_EMPTY"})
    if len(payload) > settings.groundnut_stt_max_audio_bytes:
        raise HTTPException(413, detail={"code": "GROUNDNUT_STT_AUDIO_TOO_LARGE"})
    try:
        transcript = await service.transcribe(
            payload,
            content_type=audio.content_type,
            language=language,
        )
    except GroundnutSpeechError as exc:
        status = 422 if exc.code == "GROUNDNUT_STT_NO_SPEECH" else 503
        raise HTTPException(status, detail={"code": exc.code}) from exc
    return GroundnutTranscriptResponse(transcript=transcript)


@router.post("/symptoms/map-transcript", response_model=GroundnutTranscriptMapResponse)
async def map_groundnut_symptom_transcript(
    payload: GroundnutTranscriptMapRequest,
    tester: Annotated[TesterContext, Depends(require_groundnut_controlled_tester)],
) -> GroundnutTranscriptMapResponse:
    del tester
    result = map_groundnut_transcript(payload.transcript, payload.language)
    return GroundnutTranscriptMapResponse(
        matched_symptoms=result.matched_symptoms,
        unmatched_text=result.unmatched_text,
        ambiguous_text=result.ambiguous_text,
    )


@router.post("/predict", response_model=GroundnutPredictionResponse)
async def predict_groundnut_disease(
    tester: Annotated[TesterContext, Depends(require_groundnut_controlled_tester)],
    service: GroundnutServiceDep,
    image: UploadFile = File(...),
) -> GroundnutPredictionResponse:
    del tester  # Authentication/authorization only; do not log identity or image.
    if not settings.groundnut_experimental_enabled:
        raise HTTPException(
            503,
            detail={
                "code": "GROUNDNUT_EXPERIMENT_DISABLED",
                "message": "Experimental Groundnut inference is not enabled.",
            },
        )
    payload = await _read_upload(image)
    decoded = _decode_upload(payload)
    started = time.perf_counter()
    try:
        result = await asyncio.to_thread(service.predict, decoded)
    except GroundnutModelUnavailableError as exc:
        raise HTTPException(
            503,
            detail={
                "code": str(exc),
                "message": "The experimental Groundnut model is temporarily unavailable.",
            },
        ) from exc

    candidate = _prediction(result.get("candidate_prediction"))
    predicted = _prediction(result.get("prediction"))
    top_three = [RankedPredictionOut.model_validate(item) for item in result.get("top_predictions", [])]
    quality = result["quality"]
    confidence = candidate.confidence if candidate else None
    return GroundnutPredictionResponse(
        request_id=uuid.uuid4(),
        experimental_notice=EXPERIMENTAL_NOTICE,
        status=result["status"],
        predicted_disease=predicted,
        confidence_category=result.get("confidence_category"),
        confidence_score=confidence,
        top_three_predictions=top_three,
        candidate_prediction=candidate,
        image_quality=ImageQualityOut(
            status="accepted" if quality["accepted"] else "rejected",
            reasons=quality["reasons"],
            width=quality["width"],
            height=quality["height"],
            brightness=quality["brightness"],
            contrast=quality["contrast"],
            blur_score=quality["blur_score"],
        ),
        rejection_reasons=result["rejection_reasons"],
        expert_review_required=result["expert_review_required"],
        runtime_device=result["device"],
        processing_time_ms=round((time.perf_counter() - started) * 1000),
    )
