"""Disease service — the detection pipeline (docs: STEP 1 → STEP 7).

    validate image (deterministic) → analyse (plant presence + crop + disease,
    with parse retry) → store image in R2 → persist report.

API → Service → Repository. Reuses the AI context builder, the farm/profile
repositories and the weather service; identity comes from auth.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.ai.context import build_farm_memory
from app.modules.ai.repositories import TokenUsageRepository
from app.modules.auth.models import User
from app.modules.auth.repositories import FarmerProfileRepository
from app.modules.disease.constants import (
    DEFAULT_LANGUAGE,
    DISEASE_IMAGE_PREFIX,
    CaptureMethod,
    QualityIssue,
)
from app.modules.disease.exceptions import (
    DiseaseReportNotFoundError,
    NoPlantDetectedError,
    PoorImageQualityError,
)
from app.modules.disease.models import DiseaseReport
from app.modules.disease.quality import assess_quality, extract_metrics
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.schemas import AnalyzeRequest
from app.modules.disease.storage import ObjectStorage, get_default_storage
from app.modules.disease.vision import (
    AnalysisProvider,
    AnalysisRequest,
    get_default_provider,
)
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.weather.schemas import WeatherBundle
from app.modules.weather.service import WeatherService

logger = get_logger("disease.service")

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _weather_snapshot(weather: WeatherBundle | None) -> dict | None:
    if weather is None:
        return None
    current = weather.current
    return {
        "condition": current.condition,
        "temperature_c": current.temperature_c,
        "humidity_pct": current.humidity_pct,
        "wind_speed_kmh": current.wind_speed_kmh,
        "fetched_at": weather.fetched_at,
    }


class DiseaseService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: AnalysisProvider | None = None,
        storage: ObjectStorage | None = None,
        weather_service: WeatherService | None = None,
    ) -> None:
        self.session = session
        self.reports = DiseaseReportRepository(session)
        self.token_usage = TokenUsageRepository(session)
        self.profiles = FarmerProfileRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
        self.storage = storage or get_default_storage()
        self.weather_service = weather_service

    async def analyze(self, user: User, req: AnalyzeRequest) -> DiseaseReport:
        # STEP 1 — decode + deterministic quality gate (never call AI on junk).
        try:
            data = base64.b64decode(req.image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PoorImageQualityError([QualityIssue.CORRUPTED.value]) from exc
        quality = assess_quality(extract_metrics(data, req.mime_type))
        if not quality.acceptable:
            raise PoorImageQualityError(quality.issues)

        # Context (farm memory + best-effort weather).
        profile = await self.profiles.get_by_user_id(user.id)
        language = (
            req.language
            or (profile.language if profile else None)
            or DEFAULT_LANGUAGE
        )
        farm = await self._load_farm(user, req.farm_id)
        weather = await self._safe_weather(user, farm)
        farm_context = build_farm_memory(profile, farm, weather)

        # STEP 2-5 — plant presence + crop id + disease, with parse retry.
        analysis = await self.provider.analyze(
            AnalysisRequest(
                image_base64=req.image_base64,
                mime_type=req.mime_type,
                crop=req.crop,
                language=language,
                farm_context=farm_context,
            )
        )
        # Record AI usage/cost — the model call happened even if the image is
        # later rejected, so it must still be accounted for (Phase 1 cost control).
        model_used = analysis.model_used or self.provider.model
        is_sample = "mock" in model_used.lower()
        await self.token_usage.record(
            farmer_id=user.id,
            module="disease",
            model=model_used,
            input_tokens=analysis.input_tokens,
            output_tokens=analysis.output_tokens,
            latency_ms=analysis.latency_ms,
            provider="mock" if is_sample else "gemini",
            is_sample=is_sample,
        )

        if not analysis.plant_present:
            raise NoPlantDetectedError(analysis.reject_reason)

        # STEP 6 — store the image in R2 (only for genuine plant photos).
        ext = _EXT.get(req.mime_type, "jpg")
        key = f"{DISEASE_IMAGE_PREFIX}/{user.id}/{uuid.uuid4().hex}.{ext}"
        image_url = await self.storage.put(
            key=key, data=data, content_type=req.mime_type
        )

        latitude, longitude = self._resolve_gps(req, farm)
        report = DiseaseReport(
            user_id=user.id,
            farm_id=farm.id if farm else None,
            image_url=image_url,
            capture_method=(req.capture_method or CaptureMethod.GALLERY.value),
            crop=analysis.crop,
            crop_confidence=analysis.crop_confidence,
            disease=analysis.disease,
            confidence=analysis.confidence,
            severity=analysis.severity,
            symptoms=analysis.symptoms,
            causes=analysis.causes,
            recommendations=analysis.recommendations,
            prevention=analysis.prevention,
            visible_parts=analysis.visible_parts,
            needs_expert_review=analysis.needs_expert_review,
            explanation_tamil=analysis.explanation_tamil,
            explanation_english=analysis.explanation_english,
            model_used=analysis.model_used or self.provider.model,
            raw_response=analysis.raw,
            weather_snapshot=_weather_snapshot(weather),
            latitude=latitude,
            longitude=longitude,
            language=language,
        )
        await self.reports.add(report)
        logger.info("Disease report %s saved for user=%s", report.id, user.id)
        return report

    # ----- History -----
    async def list_reports(
        self,
        user: User,
        *,
        page: int,
        page_size: int,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
    ) -> tuple[list[DiseaseReport], int]:
        offset = (page - 1) * page_size
        items = await self.reports.list_for_user(
            user.id, limit=page_size, offset=offset, farm_id=farm_id, crop=crop
        )
        total = await self.reports.count_for_user(user.id, farm_id=farm_id, crop=crop)
        return items, total

    async def get_report(self, user: User, report_id: uuid.UUID) -> DiseaseReport:
        report = await self.reports.get_for_user(report_id, user.id)
        if report is None:
            raise DiseaseReportNotFoundError()
        return report

    async def delete_report(self, user: User, report_id: uuid.UUID) -> None:
        report = await self.get_report(user, report_id)
        report.is_deleted = True
        report.deleted_at = datetime.now(UTC)
        await self.session.flush()

    # ----- Helpers -----
    async def _load_farm(self, user: User, farm_id: uuid.UUID | None) -> Farm | None:
        if farm_id is None:
            return None
        return await self.farms.get_for_user(farm_id, user.id)

    async def _safe_weather(
        self, user: User, farm: Farm | None
    ) -> WeatherBundle | None:
        if self.weather_service is None or farm is None:
            return None
        location = farm.location
        if location is None or location.latitude is None or location.longitude is None:
            return None
        try:
            return await self.weather_service.get_by_farm(user, farm.id)
        except Exception:
            logger.info("weather snapshot unavailable; continuing without it")
            return None

    @staticmethod
    def _resolve_gps(
        req: AnalyzeRequest, farm: Farm | None
    ) -> tuple[float | None, float | None]:
        if req.latitude is not None and req.longitude is not None:
            return req.latitude, req.longitude
        location = farm.location if farm else None
        if location is not None:
            return location.latitude, location.longitude
        return None, None
