from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import QuotaExceededError
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.ai.repositories import TokenUsageRepository
from app.modules.ai.usage_ledger import record_usage_durable
from app.modules.auth.dependencies import CurrentUser

from .provider import (
    PlantIdentifierProvider,
    PlantIdentifierProviderError,
    get_plant_identifier_provider,
)
from .schemas import PlantIdentificationResponse
from .service import (
    InvalidPlantIdentifierResponseError,
    failure_response,
    parse_plant_identification,
    response_from_identification,
)

router = APIRouter(prefix="/plant-identifier", tags=["plant-identifier"])
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_configured_provider() -> PlantIdentifierProvider | None:
    try:
        return get_plant_identifier_provider()
    except PlantIdentifierProviderError:
        return None


ProviderDep = Annotated[PlantIdentifierProvider | None, Depends(get_configured_provider)]


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or uuid.uuid4())


async def _validated_image(upload: UploadFile) -> tuple[bytes, str, str | None]:
    if upload.content_type not in ALLOWED_TYPES:
        await upload.close()
        return b"", "", "IMAGE_FORMAT_UNSUPPORTED"
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if len(data) > MAX_IMAGE_BYTES:
        return b"", "", "IMAGE_SIZE_INVALID"
    if not data:
        return b"", "", "CORRUPT_OR_INVALID_IMAGE"
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image = Image.open(io.BytesIO(data))
        image.load()
        require_safe_image(image)
    except UnsafeImageError as exc:
        return b"", "", exc.reason_code
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return b"", "", "CORRUPT_OR_INVALID_IMAGE"
    return data, upload.content_type, None


@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "general_availability",
        "provider": "gemini",
        "configured": get_configured_provider() is not None,
        "informational_only": True,
        "used_for_disease_routing": False,
        "general_farmer_release_authorized": True,
    }


# AUTHORIZED FOR GENERAL FARMER RELEASE (docs: product decision, 2026-08-09).
# Unlike the crop-identity disease-routing models, Plant Identifier is strictly
# informational (never diagnoses disease, never authorizes disease-model routing,
# always includes a safety disclaimer, and its prompt explicitly refuses to guess).
# A per-farmer daily quota (ai_daily_plant_identifier_quota) protects against
# runaway Gemini cost. Authorized for all authenticated farmers.
@router.post("/identify", response_model=PlantIdentificationResponse)
async def identify_plant(
    request: Request,
    current_user: CurrentUser,
    provider: ProviderDep,
    session: Annotated[AsyncSession, Depends(get_session)],
    image: UploadFile = File(...),
    preferred_language: Literal["ta", "en"] = Form("ta"),
    user_note: str | None = Form(default=None, max_length=300),
) -> PlantIdentificationResponse:
    request_id = _request_id(request)
    data, mime_type, error = await _validated_image(image)
    if error:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="invalid_image",
            error_code="PLANT_IDENTIFIER_INVALID_IMAGE",
            retry_allowed=True,
        )
    if provider is None:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code="PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
            retry_allowed=True,
        )
    token_usage = TokenUsageRepository(session)
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = await token_usage.count_today(
        current_user.id, "plant_identifier", since=day_start
    )
    if used >= settings.ai_daily_plant_identifier_quota:
        raise QuotaExceededError()
    try:
        raw = await provider.identify(data, mime_type, preferred_language, user_note)
        parsed = parse_plant_identification(raw)
        model = getattr(provider, "model", "unknown")
        await record_usage_durable(
            farmer_id=current_user.id,
            module="plant_identifier",
            model=model,
            input_tokens=None,
            output_tokens=None,
            latency_ms=None,
            provider="gemini",
            is_sample="mock" in model.lower(),
        )
        return response_from_identification(
            parsed, request_id=request_id, language=preferred_language
        )
    except InvalidPlantIdentifierResponseError:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code="PLANT_IDENTIFIER_INVALID_PROVIDER_RESPONSE",
            retry_allowed=True,
        )
    except PlantIdentifierProviderError as exc:
        safe_code = str(exc)
        if safe_code not in {
            "PLANT_IDENTIFIER_PROVIDER_TIMEOUT",
            "PLANT_IDENTIFIER_PROVIDER_RATE_LIMIT",
            "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
            "PLANT_IDENTIFIER_INVALID_PROVIDER_RESPONSE",
        }:
            safe_code = "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE"
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code=safe_code,
            retry_allowed=True,
        )
    except Exception:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code="PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
            retry_allowed=True,
        )
