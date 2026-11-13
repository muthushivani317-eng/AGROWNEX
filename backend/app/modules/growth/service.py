"""Growth service — the monitoring pipeline (docs/BACKEND_ARCHITECTURE.md).

    validate image (reused disease quality gate) → growth analysis (Gemini/mock,
    comparing with the previous week) → optional reused disease check → store image
    in R2 → persist image + analysis + timeline → roll up the session.

API → Service → Repository. Reuses the AI context builder, the farm/profile
repositories, the weather service and the Disease pipeline's quality gate + R2
storage; identity comes from auth. Business logic never lives in routes.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import QuotaExceededError
from app.core.logging import get_logger
from app.modules.ai.context import build_farm_memory
from app.modules.ai.repositories import TokenUsageRepository
from app.modules.ai.usage_ledger import record_usage_durable
from app.modules.auth.models import User
from app.modules.auth.repositories import FarmerProfileRepository
from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY, CropStageRegistry
from app.modules.disease.constants import CaptureMethod, QualityIssue
from app.modules.disease.quality import (
    QualityMetrics,
    assess_quality,
    extract_metrics,
)
from app.modules.disease.storage import ObjectStorage, get_default_storage
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.growth.analyzer import (
    GrowthAnalysisProvider,
    GrowthAnalysisRequest,
    NullNutrientProvider,
    NutrientProvider,
    get_default_provider,
)
from app.modules.growth.constants import (
    DAYS_PER_WEEK,
    DEFAULT_LANGUAGE,
    GROWTH_IMAGE_PREFIX,
    GrowthStage,
    RiskLevel,
    SessionStatus,
)
from app.modules.growth.exceptions import (
    FarmNotFoundError,
    GroundnutStageConfirmationError,
    GrowthImageNotFoundError,
    GrowthSessionNotFoundError,
    NoPlantDetectedError,
    PoorImageQualityError,
)
from app.modules.growth.models import (
    CropGrowthAnalysis,
    CropGrowthImage,
    CropGrowthSession,
    CropGrowthTimeline,
)
from app.modules.growth.repository import GrowthRepository
from app.modules.growth.schemas import UploadGrowthRequest
from app.modules.weather.schemas import WeatherBundle
from app.modules.weather.service import WeatherService

logger = get_logger("growth.service")

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _weather_snapshot(weather: WeatherBundle | None) -> dict | None:
    """Compact, verified weather snapshot (reuses the WeatherService output)."""
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


def _quality_snapshot(metrics: QualityMetrics) -> dict:
    return {
        "width": metrics.width,
        "height": metrics.height,
        "file_size": metrics.file_size,
        "brightness": metrics.brightness,
        "sharpness": metrics.sharpness,
    }


def _risk_level(health_score: int | None, *, needs_review: bool, abnormalities: list[str]) -> str:
    if needs_review or (health_score is not None and health_score < 40):
        return RiskLevel.HIGH.value
    if (health_score is not None and health_score < 65) or abnormalities:
        return RiskLevel.MODERATE.value
    return RiskLevel.LOW.value


@dataclass
class UploadOutcome:
    session: CropGrowthSession
    image: CropGrowthImage
    analysis: CropGrowthAnalysis
    timeline_entry: CropGrowthTimeline
    stage_comparison: dict | None = None


_GROUNDNUT_CALENDAR_TO_GEMINI = {
    "sowing_and_establishment": {"germination", "seedling"},
    "vegetative_growth": {"vegetative"},
    "flowering_pegging": {"flowering", "fruiting"},
    "pod_development": {"fruiting"},
    "maturity_and_harvest": {"maturity", "harvest"},
}


class GrowthService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: GrowthAnalysisProvider | None = None,
        storage: ObjectStorage | None = None,
        weather_service: WeatherService | None = None,
        nutrient_provider: NutrientProvider | None = None,
        stage_registry: CropStageRegistry | None = None,
    ) -> None:
        self.session = session
        self.repo = GrowthRepository(session)
        self.token_usage = TokenUsageRepository(session)
        self.profiles = FarmerProfileRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
        self.storage = storage or get_default_storage()
        self.weather_service = weather_service
        # Optional nutrient seam that returns None until a model is configured.
        self.nutrient_provider = nutrient_provider or NullNutrientProvider()
        self.stage_registry = stage_registry or ACTIVE_CROP_STAGE_REGISTRY

    # ----------------------------------------------------------------- #
    # Upload
    # ----------------------------------------------------------------- #
    async def upload(self, user: User, req: UploadGrowthRequest) -> UploadOutcome:
        # STEP 1 — decode + deterministic quality gate (reused from Disease).
        try:
            data = base64.b64decode(req.image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PoorImageQualityError([QualityIssue.CORRUPTED.value]) from exc
        metrics = extract_metrics(data, req.mime_type)
        quality = assess_quality(metrics)
        if not quality.acceptable:
            raise PoorImageQualityError(quality.issues)

        # Context: farmer profile → language, farm (ownership), weather snapshot.
        profile = await self.profiles.get_by_user_id(user.id)
        language = req.language or (profile.language if profile else None) or DEFAULT_LANGUAGE
        farm = await self._load_farm(user, req.farm_id)
        weather = await self._safe_weather(user, farm)
        farm_context = build_farm_memory(profile, farm, weather)

        # Resolve the monitoring session (reuse the active one or create it).
        crop = req.crop or farm.crop
        session = await self._resolve_session(user, farm, req, crop)

        # Previous week context (for comparison) + baseline for the health delta.
        previous_entry = await self.repo.latest_timeline_entry(session.id)
        previous_context = self._previous_context(previous_entry)

        # STEP 2 — growth analysis (compares against the previous week).
        day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        used = await self.token_usage.count_today(user.id, "growth", since=day_start)
        if used >= settings.ai_daily_growth_quota:
            raise QuotaExceededError()
        analysis = await self.provider.analyze(
            GrowthAnalysisRequest(
                image_base64=req.image_base64,
                mime_type=req.mime_type,
                crop=crop,
                language=language,
                farm_context=farm_context,
                previous_context=previous_context,
            )
        )
        model_used = analysis.model_used or self.provider.model
        is_sample = "mock" in model_used.lower()
        await record_usage_durable(
            farmer_id=user.id,
            module="growth",
            model=model_used,
            input_tokens=None,
            output_tokens=None,
            latency_ms=None,
            provider="mock" if is_sample else "gemini",
            is_sample=is_sample,
        )
        if not analysis.plant_present:
            raise NoPlantDetectedError(analysis.reject_reason)

        # Disease diagnosis is intentionally separate from Growth; keep only the
        # optional nutrient-analysis seam here.
        disease_result = None
        nutrient_result = await self.nutrient_provider.analyze(
            GrowthAnalysisRequest(
                image_base64=req.image_base64,
                mime_type=req.mime_type,
                crop=crop,
                language=language,
                farm_context=farm_context,
                previous_context=previous_context,
            )
        )

        # STEP 3 — store the image in R2 (only for genuine plant photos).
        ext = _EXT.get(req.mime_type, "jpg")
        key = f"{GROWTH_IMAGE_PREFIX}/{user.id}/{session.id}/{uuid.uuid4().hex}.{ext}"
        image_url = await self.storage.put(key=key, data=data, content_type=req.mime_type)

        now = datetime.now(UTC)
        week_number = self._week_number(session, now)
        latitude, longitude = self._resolve_gps(req, farm)

        image = await self.repo.add_image(
            CropGrowthImage(
                session_id=session.id,
                user_id=user.id,
                farm_id=farm.id,
                image_url=image_url,
                capture_method=(req.capture_method or CaptureMethod.GALLERY.value),
                captured_at=now,
                week_number=week_number,
                latitude=latitude,
                longitude=longitude,
                weather_snapshot=_weather_snapshot(weather),
                image_quality=_quality_snapshot(metrics),
                notes=req.notes,
            )
        )

        analysis_row = await self.repo.add_analysis(
            CropGrowthAnalysis(
                image_id=image.id,
                session_id=session.id,
                growth_stage=analysis.growth_stage,
                plant_vigor=analysis.plant_vigor,
                health_score=analysis.health_score,
                confidence=analysis.confidence,
                leaf_color_observations=analysis.leaf_color_observations,
                visible_abnormalities=analysis.visible_abnormalities,
                changes_from_previous=analysis.changes_from_previous,
                recommendations=analysis.recommendations,
                disease_result=disease_result,
                nutrient_result=nutrient_result,
                needs_expert_review=analysis.needs_expert_review,
                growth_summary_tamil=analysis.growth_summary_tamil,
                growth_summary_english=analysis.growth_summary_english,
                model_used=analysis.model_used or self.provider.model,
                raw_response=analysis.raw,
                language=language,
            )
        )

        risk = _risk_level(
            analysis.health_score,
            needs_review=analysis.needs_expert_review,
            abnormalities=analysis.visible_abnormalities,
        )
        health_delta = self._health_delta(analysis.health_score, previous_entry)
        timeline_entry = await self.repo.add_timeline_entry(
            CropGrowthTimeline(
                session_id=session.id,
                user_id=user.id,
                image_id=image.id,
                week_number=week_number,
                growth_stage=analysis.growth_stage,
                health_score=analysis.health_score,
                health_delta=health_delta,
                risk_level=risk,
                summary=analysis.growth_summary_english or analysis.growth_summary_tamil,
                recorded_at=now,
            )
        )

        stage_comparison = self._groundnut_stage_comparison(
            crop=crop,
            sowing_date=farm.sowing_date,
            gemini_stage=analysis.growth_stage,
        )

        # Roll up the session with the latest observation.
        await self._roll_up(session, analysis, risk, crop, req.variety)

        # _roll_up flushes, which expires server-generated columns (e.g.
        # updated_at via DB onupdate). Refresh here so those attributes are
        # loaded inside async context, before GrowthSessionOut.from_row reads
        # them synchronously during response serialization (avoids
        # sqlalchemy.exc.MissingGreenlet).
        await self.session.refresh(session)

        logger.info(
            "Growth upload saved image=%s session=%s user=%s",
            image.id,
            session.id,
            user.id,
        )
        return UploadOutcome(
            session=session,
            image=image,
            analysis=analysis_row,
            timeline_entry=timeline_entry,
            stage_comparison=stage_comparison,
        )

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def history(
        self,
        user: User,
        *,
        page: int,
        page_size: int,
        session_id: uuid.UUID | None = None,
        farm_id: uuid.UUID | None = None,
    ) -> tuple[list[tuple[CropGrowthImage, CropGrowthAnalysis | None]], int]:
        offset = (page - 1) * page_size
        return await self.repo.list_images(
            user.id,
            session_id=session_id,
            farm_id=farm_id,
            limit=page_size,
            offset=offset,
        )

    async def sessions(
        self,
        user: User,
        *,
        page: int,
        page_size: int,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
    ) -> tuple[list[CropGrowthSession], int]:
        offset = (page - 1) * page_size
        return await self.repo.list_sessions(
            user.id, farm_id=farm_id, crop=crop, limit=page_size, offset=offset
        )

    async def timeline(
        self,
        user: User,
        session_id: uuid.UUID | None,
        *,
        farm_id: uuid.UUID | None = None,
    ) -> tuple[CropGrowthSession, list[tuple[CropGrowthTimeline, CropGrowthImage | None]]]:
        session = await self._resolve_read_session(user, session_id, farm_id=farm_id)
        entries = await self.repo.timeline_for_session(session.id)
        return session, entries

    async def latest(self, user: User) -> tuple[CropGrowthImage, CropGrowthAnalysis | None] | None:
        session = await self.repo.latest_session(user.id)
        if session is None:
            return None
        image = await self.repo.latest_image_for_session(session.id)
        if image is None:
            return None
        images, _ = await self.repo.list_images(user.id, session_id=session.id, limit=1, offset=0)
        return images[0] if images else (image, None)

    async def session_detail(
        self, user: User, session_id: uuid.UUID
    ) -> tuple[
        CropGrowthSession,
        list[tuple[CropGrowthImage, CropGrowthAnalysis | None]],
        list[tuple[CropGrowthTimeline, CropGrowthImage | None]],
    ]:
        session = await self.repo.get_session(session_id, user.id)
        if session is None:
            raise GrowthSessionNotFoundError()
        images = await self.repo.images_for_session(session.id)
        timeline = await self.repo.timeline_for_session(session.id)
        return session, images, timeline

    async def delete_image(self, user: User, image_id: uuid.UUID) -> None:
        image = await self.repo.get_image(image_id, user.id)
        if image is None:
            raise GrowthImageNotFoundError()
        image.is_deleted = True
        image.deleted_at = datetime.now(UTC)
        await self.repo.delete_timeline_for_image(image.id)
        # Keep the session's image_count in step with reality.
        session = await self.repo.get_session(image.session_id, user.id)
        if session is not None:
            session.image_count = await self.repo.count_images_for_session(session.id)
        await self.session.flush()

    async def confirm_groundnut_stage(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
        image_id: uuid.UUID,
        action: str,
        stage: str,
    ) -> CropGrowthSession:
        """Apply an explicit farmer decision to a Groundnut Gemini suggestion."""
        session = await self.repo.get_session(session_id, user.id)
        if session is None:
            raise GrowthSessionNotFoundError()
        if (session.crop or "").strip().lower() not in {"groundnut", "peanut"}:
            raise GroundnutStageConfirmationError("This endpoint is only for Groundnut.")

        row = await self.repo.get_image_analysis(image_id, user.id)
        if row is None:
            raise GrowthImageNotFoundError()
        image, analysis = row
        if image.session_id != session.id:
            raise GroundnutStageConfirmationError(
                "The growth photo does not belong to this session."
            )
        if action == "confirm" and stage != analysis.growth_stage:
            raise GroundnutStageConfirmationError(
                "Confirmation must match the Gemini suggestion; use correction otherwise."
            )

        session.current_growth_stage = stage
        analysis.raw_response = {
            **(analysis.raw_response or {}),
            "farmer_stage_decision": {
                "action": action,
                "stage": stage,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        }
        await self.session.flush()
        await self.session.refresh(session)
        return session

    # ----------------------------------------------------------------- #
    # Helpers
    # ----------------------------------------------------------------- #
    async def _resolve_session(
        self,
        user: User,
        farm: Farm,
        req: UploadGrowthRequest,
        crop: str | None,
    ) -> CropGrowthSession:
        if req.session_id is not None:
            session = await self.repo.get_session(req.session_id, user.id)
            if session is None:
                raise GrowthSessionNotFoundError()
            return session
        existing = await self.repo.find_active_session(user.id, farm.id, crop)
        if existing is not None:
            return existing
        return await self.repo.add_session(
            CropGrowthSession(
                user_id=user.id,
                farm_id=farm.id,
                crop=crop,
                variety=req.variety or farm.crop_variety,
                title=None,
                sowing_date=farm.sowing_date,
                status=SessionStatus.ACTIVE.value,
                current_growth_stage=GrowthStage.UNKNOWN.value,
                image_count=0,
            )
        )

    async def _resolve_read_session(
        self,
        user: User,
        session_id: uuid.UUID | None,
        *,
        farm_id: uuid.UUID | None = None,
    ) -> CropGrowthSession:
        if session_id is not None:
            session = await self.repo.get_session(session_id, user.id)
        else:
            session = await self.repo.latest_session(user.id, farm_id=farm_id)
        if session is None:
            raise GrowthSessionNotFoundError()
        return session

    async def _roll_up(
        self,
        session: CropGrowthSession,
        analysis,
        risk: str,
        crop: str | None,
        variety: str | None,
    ) -> None:
        # Groundnut Gemini output is advisory until the farmer explicitly
        # confirms or corrects it through confirm_groundnut_stage().
        if (session.crop or crop or "").strip().lower() not in {"groundnut", "peanut"}:
            session.current_growth_stage = analysis.growth_stage
        session.latest_health_score = analysis.health_score
        session.latest_risk_level = risk
        session.image_count = await self.repo.count_images_for_session(session.id)
        if not session.crop and crop:
            session.crop = crop
        if not session.variety and variety:
            session.variety = variety
        await self.session.flush()

    def _groundnut_stage_comparison(
        self,
        *,
        crop: str | None,
        sowing_date,
        gemini_stage: str,
    ) -> dict | None:
        """Compare advisory image output with the dated Groundnut calendar."""
        if (crop or "").strip().lower() not in {"groundnut", "peanut"} or sowing_date is None:
            return None
        schedule = self.stage_registry.resolve("groundnut")
        if schedule is None:
            return None
        age_days = (datetime.now(UTC).date() - sowing_date).days
        calendar_stage = next(
            (
                stage.code
                for stage in schedule.stages
                if stage.start_offset <= age_days <= stage.end_offset
            ),
            None,
        )
        expected = _GROUNDNUT_CALENDAR_TO_GEMINI.get(calendar_stage or "")
        if calendar_stage is None or expected is None:
            return None
        mismatch = gemini_stage not in expected
        return {
            "gemini_stage": gemini_stage,
            "calendar_stage": calendar_stage,
            "expected_gemini_stages": sorted(expected),
            "mismatch": mismatch,
            "warning_code": "GROUNDNUT_STAGE_CALENDAR_MISMATCH" if mismatch else None,
        }

    async def _load_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotFoundError()
        return farm

    async def _safe_weather(self, user: User, farm: Farm | None) -> WeatherBundle | None:
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
    def _previous_context(entry: CropGrowthTimeline | None) -> str | None:
        if entry is None:
            return None
        parts = [f"Week {entry.week_number}: stage={entry.growth_stage}"]
        if entry.health_score is not None:
            parts.append(f"health={entry.health_score}")
        if entry.summary:
            parts.append(entry.summary)
        return ", ".join(parts)

    @staticmethod
    def _health_delta(health_score: int | None, previous: CropGrowthTimeline | None) -> int | None:
        if health_score is None or previous is None or previous.health_score is None:
            return None
        return health_score - previous.health_score

    @staticmethod
    def _week_number(session: CropGrowthSession, now: datetime) -> int:
        start = session.created_at or now
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        days = (now - start).days
        return max(1, days // DAYS_PER_WEEK + 1)

    @staticmethod
    def _resolve_gps(
        req: UploadGrowthRequest, farm: Farm | None
    ) -> tuple[float | None, float | None]:
        if req.latitude is not None and req.longitude is not None:
            return req.latitude, req.longitude
        location = farm.location if farm else None
        if location is not None:
            return location.latitude, location.longitude
        return None, None
