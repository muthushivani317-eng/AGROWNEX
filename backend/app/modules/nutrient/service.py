"""Nutrient service (docs: Repository → Service → Engine → Provider).

The analysis pipeline:

    decode + deterministic quality gate (reused from Disease) → visual observation
    (provider) → gather Soil / Satellite / Weather references (each module's own
    repository/service; none is modified) → Nutrient Engine corroborates → generic
    recommendations → store image in R2 (reused) → persist report + analysis +
    symptoms + recommendations + history.

Business logic lives here; routes stay thin. A deficiency is never fabricated: when
the evidence is thin the engine returns "not confirmed" and a soil/tissue test is
advised.
"""

from __future__ import annotations

import base64
import binascii
import uuid
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
from app.modules.disease.constants import QualityIssue
from app.modules.disease.quality import assess_quality, extract_metrics
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.storage import ObjectStorage, get_default_storage
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.nutrient.constants import (
    DEFAULT_LANGUAGE,
    NUTRIENT_IMAGE_PREFIX,
    ReportStatus,
)
from app.modules.nutrient.crops import (
    normalize_nutrient_crop,
    normalize_observed_nutrient_crop,
)
from app.modules.nutrient.engine import (
    NutrientAssessment,
    RecommendationDraft,
    SatelliteReference,
    SoilReference,
    WeatherReference,
    build_recommendations,
    corroborate,
)
from app.modules.nutrient.exceptions import (
    FarmNotOwnedError,
    NoPlantDetectedError,
    NutrientCropMismatchError,
    NutrientDataUnavailableError,
    NutrientReportNotFoundError,
    NutrientUnsupportedCropError,
    PoorImageQualityError,
)
from app.modules.nutrient.models import (
    NutrientAnalysis,
    NutrientHistory,
    NutrientRecommendation,
    NutrientReport,
    NutrientSymptom,
)
from app.modules.nutrient.provider import (
    AnalysisInput,
    NutrientProvider,
    get_default_provider,
)
from app.modules.nutrient.repository import NutrientRepository
from app.modules.nutrient.schemas import AnalyzeNutrientRequest
from app.modules.satellite.repository import SatelliteRepository
from app.modules.soil.service import SoilService
from app.modules.weather.schemas import WeatherBundle
from app.modules.weather.service import WeatherService
from app.schemas.response import PaginatedData

logger = get_logger("nutrient.service")

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

# A recent disease at/above this confidence is treated as an evidence-based conflict
# (the engine then lowers certainty and asks for an expert — never a silent override).
_DISEASE_CONFLICT_CONFIDENCE = 80
_LOW_VIGOR_HEALTH = frozenset({"bare", "very_low", "low"})
_MAX_DECODED_IMAGE_BYTES = 10 * 1024 * 1024


def _weather_snapshot(weather: WeatherBundle | None) -> dict | None:
    if weather is None:
        return None
    current = weather.current
    return {
        "condition": current.condition,
        "temperature_c": current.temperature_c,
        "humidity_pct": current.humidity_pct,
        "fetched_at": weather.fetched_at,
    }


class NutrientService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: NutrientProvider | None = None,
        storage: ObjectStorage | None = None,
        weather_service: WeatherService | None = None,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.repo = NutrientRepository(session)
        self.token_usage = TokenUsageRepository(session)
        self.profiles = FarmerProfileRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
        self.storage = storage or get_default_storage()
        self.weather_service = weather_service
        self._now = now

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    async def _require_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotOwnedError()
        return farm

    # ----------------------------------------------------------------- #
    # Analyze
    # ----------------------------------------------------------------- #
    async def analyze(self, user: User, req: AnalyzeNutrientRequest) -> NutrientReport:
        farm = await self._require_farm(user, req.farm_id)
        try:
            requested_crop = normalize_nutrient_crop(req.crop) if req.crop else None
            farm_crop = normalize_nutrient_crop(farm.crop) if farm.crop else None
        except ValueError as exc:
            raise NutrientUnsupportedCropError() from exc
        if requested_crop and farm_crop and requested_crop != farm_crop:
            raise NutrientCropMismatchError()
        # Pass a bounded canonical value, never raw user-controlled spelling,
        # into the model prompt.
        selected_crop = requested_crop or farm_crop

        # STEP 1 — decode + deterministic quality gate (never call the model on junk).
        try:
            data = base64.b64decode(req.image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PoorImageQualityError([QualityIssue.CORRUPTED.value]) from exc
        if len(data) > _MAX_DECODED_IMAGE_BYTES:
            raise PoorImageQualityError(["image_too_large"])
        quality = assess_quality(extract_metrics(data, req.mime_type))
        if not quality.acceptable:
            raise PoorImageQualityError(quality.issues)

        # Context (farm memory + best-effort weather).
        profile = await self.profiles.get_by_user_id(user.id)
        language = req.language or (profile.language if profile else None) or DEFAULT_LANGUAGE
        weather = await self._safe_weather(user, farm)
        farm_context = build_farm_memory(profile, farm, weather)

        # STEP 2 — visual observation from the provider.
        day_start = self._now_dt().replace(hour=0, minute=0, second=0, microsecond=0)
        used = await self.token_usage.count_today(user.id, "nutrient", since=day_start)
        if used >= settings.ai_daily_nutrient_quota:
            raise QuotaExceededError()
        observation = await self.provider.analyze(
            AnalysisInput(
                image_base64=req.image_base64,
                mime_type=req.mime_type,
                crop=selected_crop,
                language=language,
                farm_context=farm_context,
            )
        )
        model_used = observation.model_used or getattr(self.provider, "model", "unknown")
        provider_name = getattr(self.provider, "name", "gemini")
        await record_usage_durable(
            farmer_id=user.id,
            module="nutrient",
            model=model_used,
            input_tokens=None,
            output_tokens=None,
            latency_ms=None,
            provider=provider_name,
            is_sample=provider_name == "mock" or "mock" in model_used.lower(),
        )
        if not observation.plant_present:
            raise NoPlantDetectedError(observation.reject_reason)
        if selected_crop and observation.crop not in {"unknown", None}:
            try:
                observed_crop = normalize_observed_nutrient_crop(observation.crop)
                expected_crop = normalize_nutrient_crop(selected_crop)
            except ValueError as exc:
                raise NutrientUnsupportedCropError() from exc
            if observed_crop != expected_crop:
                raise NutrientCropMismatchError()

        # STEP 3 — gather corroborating signals from the other modules.
        soil_ref = await self._soil_reference(user, farm.id)
        satellite_ref = await self._satellite_reference(user, farm.id)
        weather_ref = self._weather_reference(weather)
        disease_conflict = await self._disease_conflict(user, farm.id)

        # STEP 4 — the engine decides the verdict + generic advice (pure).
        assessment = corroborate(
            observation,
            soil=soil_ref,
            satellite=satellite_ref,
            weather=weather_ref,
            disease_conflict=disease_conflict,
        )
        drafts = build_recommendations(assessment)

        # STEP 5 — store the image in R2 (reused disease pipeline).
        ext = _EXT.get(req.mime_type, "jpg")
        key = f"{NUTRIENT_IMAGE_PREFIX}/{user.id}/{uuid.uuid4().hex}.{ext}"
        image_url = await self.storage.put(key=key, data=data, content_type=req.mime_type)

        # STEP 6 — persist report + analysis + symptoms + recommendations + history.
        report = await self._persist(
            user=user,
            farm=farm,
            req=req,
            language=language,
            image_url=image_url,
            observation=observation,
            assessment=assessment,
            drafts=drafts,
            soil_ref=soil_ref,
            satellite_ref=satellite_ref,
            weather_ref=weather_ref,
            weather=weather,
        )
        logger.info(
            "Nutrient report %s saved for user=%s (status=%s)",
            report.id,
            user.id,
            assessment.status,
        )
        return report

    async def _persist(
        self,
        *,
        user: User,
        farm: Farm,
        req: AnalyzeNutrientRequest,
        language: str,
        image_url: str,
        observation,
        assessment: NutrientAssessment,
        drafts: list[RecommendationDraft],
        soil_ref: SoilReference,
        satellite_ref: SatelliteReference,
        weather_ref: WeatherReference,
        weather: WeatherBundle | None,
    ) -> NutrientReport:
        latitude, longitude = self._resolve_gps(req, farm)
        report = NutrientReport(
            user_id=user.id,
            farm_id=farm.id,
            crop=observation.crop if observation.crop != "unknown" else req.crop,
            image_url=image_url,
            capture_method=req.capture_method or "gallery",
            capture_date=self._now_dt().date(),
            provider=getattr(self.provider, "name", "gemini"),
            model_used=observation.model_used or getattr(self.provider, "model", None),
            status=ReportStatus.ANALYZED.value,
            language=language,
            latitude=latitude,
            longitude=longitude,
            weather_snapshot=_weather_snapshot(weather),
            raw_response=observation.raw,
        )
        await self.repo.add_report(report)

        await self.repo.add_analysis(
            NutrientAnalysis(
                report_id=report.id,
                primary_deficiency=assessment.primary_deficiency,
                secondary_deficiency=assessment.secondary_deficiency,
                status=assessment.status,
                confidence=assessment.confidence,
                severity=assessment.severity,
                affected_area=assessment.affected_area,
                soil_reference=self._soil_ref_json(soil_ref),
                satellite_reference=self._satellite_ref_json(satellite_ref),
                weather_reference=self._weather_ref_json(weather_ref),
                disease_conflict=assessment.disease_conflict,
                needs_test=assessment.needs_test,
                needs_expert=assessment.needs_expert,
                explanation_tamil=observation.explanation_tamil or None,
                explanation_english=observation.explanation_english or None,
            )
        )

        for code in observation.visible_symptoms:
            await self.repo.add_symptom(NutrientSymptom(report_id=report.id, code=code))

        for draft in drafts:
            await self.repo.add_recommendation(
                NutrientRecommendation(
                    user_id=user.id,
                    farm_id=farm.id,
                    report_id=report.id,
                    category=draft.category,
                    code=draft.code,
                    nutrient=draft.nutrient,
                    severity=draft.severity,
                    priority=draft.priority,
                )
            )

        await self.repo.add_history(
            NutrientHistory(
                user_id=user.id,
                farm_id=farm.id,
                report_id=report.id,
                crop=report.crop,
                primary_deficiency=assessment.primary_deficiency,
                status=assessment.status,
                confidence=assessment.confidence,
                severity=assessment.severity,
                recorded_at=self._now_dt(),
            )
        )

        await self.session.flush()
        await self.session.refresh(report)
        return report

    # ----------------------------------------------------------------- #
    # Cross-module references (each guarded — one module failing is never fatal)
    # ----------------------------------------------------------------- #
    async def _soil_reference(self, user: User, farm_id: uuid.UUID) -> SoilReference:
        try:
            assessment = await SoilService(self.session).assessment_for(user, farm_id)
        except Exception:  # noqa: BLE001 — soil is an optional corroborating signal
            logger.info("soil reference unavailable; continuing without it")
            return SoilReference()
        has_data = assessment.has_any_value or bool(assessment.deficient_micronutrients)
        return SoilReference(
            has_data=has_data,
            macro_ratings={
                "nitrogen": assessment.nitrogen,
                "phosphorus": assessment.phosphorus,
                "potassium": assessment.potassium,
            },
            deficient_micronutrients=tuple(assessment.deficient_micronutrients),
        )

    async def _satellite_reference(self, user: User, farm_id: uuid.UUID) -> SatelliteReference:
        try:
            session = await SatelliteRepository(self.session).latest_session(
                user.id, farm_id, available_only=True
            )
        except Exception:  # noqa: BLE001 — satellite is an optional signal
            logger.info("satellite reference unavailable; continuing without it")
            return SatelliteReference()
        if session is None:
            return SatelliteReference()
        health = session.vegetation_health
        low_vigor = health in _LOW_VIGOR_HEALTH or (session.ndvi is not None and session.ndvi < 0.3)
        return SatelliteReference(has_data=True, vegetation_health=health, low_vigor=low_vigor)

    @staticmethod
    def _weather_reference(weather: WeatherBundle | None) -> WeatherReference:
        if weather is None:
            return WeatherReference()
        codes = tuple(i.code for i in weather.insights)
        heavy_rain = any(c.startswith("heavy_rain") for c in codes)
        return WeatherReference(has_data=True, heavy_rain=heavy_rain, codes=codes)

    async def _disease_conflict(self, user: User, farm_id: uuid.UUID) -> bool:
        try:
            reports = await DiseaseReportRepository(self.session).list_for_user(
                user.id, limit=5, offset=0, farm_id=farm_id
            )
        except Exception:  # noqa: BLE001 — disease overlap is an optional check
            return False
        return any((r.confidence or 0) >= _DISEASE_CONFLICT_CONFIDENCE for r in reports)

    async def _safe_weather(self, user: User, farm: Farm | None) -> WeatherBundle | None:
        if self.weather_service is None or farm is None:
            return None
        location = farm.location
        if location is None or location.latitude is None or location.longitude is None:
            return None
        try:
            return await self.weather_service.get_by_farm(user, farm.id)
        except Exception:  # noqa: BLE001 — weather is best-effort context
            logger.info("weather snapshot unavailable; continuing without it")
            return None

    @staticmethod
    def _resolve_gps(
        req: AnalyzeNutrientRequest, farm: Farm | None
    ) -> tuple[float | None, float | None]:
        if req.latitude is not None and req.longitude is not None:
            return req.latitude, req.longitude
        location = farm.location if farm else None
        if location is not None:
            return location.latitude, location.longitude
        return None, None

    @staticmethod
    def _soil_ref_json(ref: SoilReference) -> dict | None:
        if not ref.has_data:
            return None
        return {
            "has_data": True,
            "macro_ratings": ref.macro_ratings,
            "deficient_micronutrients": list(ref.deficient_micronutrients),
        }

    @staticmethod
    def _satellite_ref_json(ref: SatelliteReference) -> dict | None:
        if not ref.has_data:
            return None
        return {
            "has_data": True,
            "vegetation_health": ref.vegetation_health,
            "low_vigor": ref.low_vigor,
        }

    @staticmethod
    def _weather_ref_json(ref: WeatherReference) -> dict | None:
        if not ref.has_data:
            return None
        return {"has_data": True, "heavy_rain": ref.heavy_rain, "codes": list(ref.codes)}

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def list_reports(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[NutrientReport]:
        await self._require_farm(user, farm_id)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_reports(user.id, farm_id, limit=page_size, offset=offset)
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def latest(self, user: User, farm_id: uuid.UUID) -> NutrientReport:
        await self._require_farm(user, farm_id)
        report = await self.repo.latest_report(user.id, farm_id)
        if report is None:
            raise NutrientDataUnavailableError()
        return report

    async def recommendations(self, user: User, farm_id: uuid.UUID) -> list[NutrientRecommendation]:
        await self._require_farm(user, farm_id)
        return await self.repo.latest_recommendations(user.id, farm_id)

    async def get_report(self, user: User, report_id: uuid.UUID) -> NutrientReport:
        report = await self.repo.get_report(report_id, user.id)
        if report is None:
            raise NutrientReportNotFoundError()
        return report
