"""Satellite Intelligence service (docs: Repository → Service → Engine → Provider).

Orchestrates monitoring: fetch a scene for a farm's polygon, compute the vegetation
indices with the deterministic engine, classify health/stress/moisture, compare to
the previous session, raise alerts, and record a trend snapshot. When imagery is
genuinely unavailable (no polygon, cloud, delay, provider issue) it stores an honest
*unavailable* session — never fabricated values. Reuses the farm repository (+ its
polygon) and, optionally, weather context to avoid false moisture alerts.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.satellite.alerts import AlertContext, build_alerts
from app.modules.satellite.aoi import AoiValidationError, normalize_aoi
from app.modules.satellite.constants import (
    CLOUD_USABLE_MAX,
    TIMELINE_MONTHLY,
    IndexName,
    SessionStatus,
    UnavailableReason,
)
from app.modules.satellite.engine import (
    IndexValues,
    assess,
    compute_confidence,
    compute_indices,
)
from app.modules.satellite.exceptions import (
    FarmNotOwnedError,
    SatelliteUnavailableError,
)
from app.modules.satellite.models import (
    SatelliteAlert,
    SatelliteHistory,
    SatelliteImage,
    SatelliteIndex,
    SatelliteSession,
    WaterloggingAssessmentRecord,
)
from app.modules.satellite.provider import (
    ProviderScene,
    SatelliteProvider,
    get_default_provider,
)
from app.modules.satellite.repository import SatelliteRepository
from app.modules.satellite.waterlogging import assess_waterlogging
from app.schemas.response import PaginatedData

logger = get_logger("satellite.service")

_MOISTURE_SUPPRESS_RAINFALL_MM = 5.0


class SatelliteService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: SatelliteProvider | None = None,
        now: datetime | None = None,
        enable_weather: bool = False,
    ) -> None:
        self.session = session
        self.repo = SatelliteRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
        self._now = now
        self._enable_weather = enable_weather

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    def _today(self) -> date:
        return self._now_dt().date()

    async def _require_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotOwnedError()
        return farm

    @staticmethod
    def _polygon(farm: Farm) -> dict | None:
        boundary = getattr(farm, "boundary", None)
        if boundary is None or not boundary.geojson:
            return None
        return boundary.geojson

    # ----------------------------------------------------------------- #
    # Refresh (the acquisition pass)
    # ----------------------------------------------------------------- #
    async def refresh(self, user: User, farm_id: uuid.UUID) -> SatelliteSession:
        farm = await self._require_farm(user, farm_id)
        polygon = self._polygon(farm)
        if polygon is None:
            return await self._store_unavailable(
                user, farm_id, UnavailableReason.NO_POLYGON.value, cloud_cover=None
            )

        try:
            polygon = normalize_aoi(polygon)
        except AoiValidationError:
            return await self._store_unavailable(
                user, farm_id, UnavailableReason.PROCESSING_ERROR.value, cloud_cover=None
            )
        try:
            outcome = await self.provider.fetch_scene(polygon, capture_before=self._today())
        except Exception:
            logger.exception("satellite provider failed")
            return await self._store_unavailable(
                user, farm_id, UnavailableReason.PROVIDER_ERROR.value, cloud_cover=None
            )
        if outcome.scene is None:
            return await self._store_unavailable(user, farm_id, outcome.reason, cloud_cover=None)

        scene = outcome.scene
        scene_id = scene.metadata.get("scene_id") if scene.metadata else None
        if isinstance(scene_id, str) and scene_id:
            latest = await self.repo.latest_session(user.id, farm_id, available_only=True)
            if (
                latest is not None
                and latest.session_metadata
                and latest.session_metadata.get("scene_id") == scene_id
            ):
                return latest
        if scene.cloud_cover is not None and scene.cloud_cover > CLOUD_USABLE_MAX:
            return await self._store_unavailable(
                user,
                farm_id,
                UnavailableReason.CLOUD_COVER.value,
                cloud_cover=scene.cloud_cover,
            )

        try:
            if scene.indices is not None:
                indices = scene.indices
            elif scene.bands is not None:
                indices = compute_indices(scene.bands)
            else:
                indices = IndexValues()
        except Exception:
            logger.exception("satellite processing failed")
            return await self._store_unavailable(
                user,
                farm_id,
                UnavailableReason.PROCESSING_ERROR.value,
                cloud_cover=scene.cloud_cover,
            )
        if not any(v is not None for v in (indices.ndvi, indices.ndre, indices.evi, indices.ndmi)):
            return await self._store_unavailable(
                user,
                farm_id,
                UnavailableReason.NO_IMAGERY.value,
                cloud_cover=scene.cloud_cover,
            )

        return await self._store_available(user, farm_id, scene, indices)

    async def refresh_waterlogging(
        self, user: User, farm_id: uuid.UUID
    ) -> WaterloggingAssessmentRecord:
        farm = await self._require_farm(user, farm_id)
        polygon = self._polygon(farm)
        evidence = None
        reason: str | None = None
        normalized: dict | None = None
        if polygon is None:
            reason = UnavailableReason.NO_POLYGON.value
        else:
            try:
                normalized = normalize_aoi(polygon)
            except AoiValidationError:
                reason = UnavailableReason.PROCESSING_ERROR.value
        if reason is None:
            fetch = getattr(self.provider, "fetch_water_evidence", None)
            if fetch is None:
                reason = UnavailableReason.PROVIDER_ERROR.value
            else:
                try:
                    outcome = await fetch(normalized, capture_before=self._today())
                    evidence = outcome.evidence
                    reason = None if evidence is not None else outcome.reason
                except Exception:
                    logger.exception("waterlogging provider failed")
                    reason = UnavailableReason.PROVIDER_ERROR.value
        weather_context = (
            await self._waterlogging_weather_context(user, farm_id)
            if normalized is not None
            else {"status": "unavailable", "reason": "invalid_or_missing_aoi"}
        )
        assessment = assess_waterlogging(
            evidence,
            missing=[reason] if reason else None,
            weather_context=weather_context,
        )
        evidence_type = (
            "combined"
            if evidence is not None and weather_context.get("status") != "unavailable"
            else "satellite"
            if evidence is not None
            else "weather_only"
            if assessment.decision.value == "rainfall_risk_only"
            else "insufficient"
        )
        provenance = {
            "provider": self.provider.name,
            "scene_id": evidence.scene_id if evidence else None,
            "baseline_scene_id": evidence.baseline_scene_id if evidence else None,
            "aoi_hash": (
                hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
                if normalized
                else None
            ),
            "processing_version": "waterlogging-assessment-v1",
            "policy_verification": (
                "verified" if evidence and evidence.policy_verified else "unverified"
            ),
            "verification_requirement": "verify_against_official_source",
            "evidence_type": evidence_type,
            "weather_context": weather_context,
            "evidence_present": assessment.evidence_present,
            "evidence_missing": assessment.evidence_missing,
            "surface_water_change": assessment.surface_water_change,
            "is_sample": evidence.source == "mock" if evidence else False,
        }
        row = WaterloggingAssessmentRecord(
            user_id=user.id,
            farm_id=farm_id,
            decision=assessment.decision.value,
            observed_at=assessment.observed_at,
            processed_at=self._now_dt(),
            source=assessment.source,
            coverage_pct=assessment.coverage_pct,
            freshness=assessment.freshness,
            explanation=assessment.explanation,
            provenance=provenance,
        )
        await self.repo.add_waterlogging_assessment(row)
        await self.session.refresh(row)
        return row

    async def latest_waterlogging(
        self, user: User, farm_id: uuid.UUID
    ) -> WaterloggingAssessmentRecord | None:
        await self._require_farm(user, farm_id)
        return await self.repo.latest_waterlogging_assessment(user.id, farm_id)

    async def waterlogging_history(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[WaterloggingAssessmentRecord]:
        await self._require_farm(user, farm_id)
        rows, total = await self.repo.list_waterlogging_assessments(
            user.id,
            farm_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return PaginatedData(
            items=rows,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        )

    async def _waterlogging_weather_context(
        self, user: User, farm_id: uuid.UUID
    ) -> dict[str, object]:
        if not self._enable_weather:
            return {"status": "unavailable", "reason": "weather_disabled"}
        try:
            from app.modules.weather.service import WeatherService

            bundle = await WeatherService(self.session).get_by_farm(user, farm_id)
            heavy_rain = any(i.category == "heavy_rain" for i in bundle.insights)
            return {
                "status": bundle.data_state,
                "source": bundle.source,
                "weather_timestamp": bundle.fetched_at,
                "heavy_rain_signal": heavy_rain,
                "policy_verification": "unverified",
            }
        except Exception:  # noqa: BLE001 - missing weather must fail safely
            logger.info("weather context unavailable for waterlogging (farm %s)", farm_id)
            return {"status": "unavailable", "reason": "weather_unavailable"}

    async def _store_unavailable(
        self, user: User, farm_id: uuid.UUID, reason: str, *, cloud_cover: float | None
    ) -> SatelliteSession:
        session = SatelliteSession(
            user_id=user.id,
            farm_id=farm_id,
            provider=self.provider.name,
            status=SessionStatus.UNAVAILABLE.value,
            unavailable_reason=reason,
            cloud_cover=cloud_cover,
            confidence=0,
        )
        await self.repo.add_session(session)
        for draft in build_alerts(
            AlertContext(
                status=SessionStatus.UNAVAILABLE.value,
                unavailable_reason=reason,
                cloud_cover=cloud_cover,
            )
        ):
            await self._persist_alert(user, session, draft)
        await self.session.flush()
        await self.session.refresh(session)
        return session

    async def _store_available(
        self, user: User, farm_id: uuid.UUID, scene: ProviderScene, indices: IndexValues
    ) -> SatelliteSession:
        previous_ndvi = await self.repo.previous_available_ndvi(user.id, farm_id)
        a = assess(indices, previous_ndvi)
        confidence = compute_confidence(scene.cloud_cover, is_sample=scene.is_sample)

        session = SatelliteSession(
            user_id=user.id,
            farm_id=farm_id,
            provider=scene.provider,
            status=SessionStatus.AVAILABLE.value,
            unavailable_reason=UnavailableReason.NONE.value,
            is_sample=scene.is_sample,
            capture_date=scene.capture_date,
            cloud_cover=scene.cloud_cover,
            resolution_m=scene.resolution_m,
            ndvi=a.ndvi,
            ndre=a.ndre,
            evi=a.evi,
            ndmi=a.ndmi,
            vegetation_health=a.vegetation_health,
            stress_level=a.stress_level,
            moisture_status=a.moisture_status,
            trend=a.trend,
            ndvi_delta=a.ndvi_delta,
            confidence=confidence,
            session_metadata=scene.metadata or None,
        )
        await self.repo.add_session(session)

        ndvi_std = await self._persist_indices(farm_id, session, scene, indices)
        await self._persist_images(farm_id, session, scene)

        recent_rain = await self._recent_rainfall(user, farm_id)
        for draft in build_alerts(
            AlertContext(
                status=SessionStatus.AVAILABLE.value,
                cloud_cover=scene.cloud_cover,
                ndvi=a.ndvi,
                ndmi=a.ndmi,
                ndvi_delta=a.ndvi_delta,
                trend=a.trend,
                ndvi_std=ndvi_std,
            )
        ):
            # Weather context: suppress a moisture-stress alert if it rained recently.
            if (
                draft.code == "satellite.alert.moisture_stress"
                and recent_rain is not None
                and recent_rain >= _MOISTURE_SUPPRESS_RAINFALL_MM
            ):
                continue
            await self._persist_alert(user, session, draft)

        await self.repo.add_history(
            SatelliteHistory(
                user_id=user.id,
                farm_id=farm_id,
                session_id=session.id,
                capture_date=scene.capture_date,
                ndvi=a.ndvi,
                ndre=a.ndre,
                evi=a.evi,
                ndmi=a.ndmi,
                vegetation_health=a.vegetation_health,
                stress_level=a.stress_level,
                moisture_status=a.moisture_status,
                source=scene.provider,
                confidence=confidence,
                recorded_at=self._now_dt(),
            )
        )
        await self.session.flush()
        await self.session.refresh(session)
        return session

    async def _persist_indices(
        self,
        farm_id: uuid.UUID,
        session: SatelliteSession,
        scene: ProviderScene,
        indices: IndexValues,
    ) -> float | None:
        ndvi_std: float | None = None
        for name, value in (
            (IndexName.NDVI.value, indices.ndvi),
            (IndexName.NDRE.value, indices.ndre),
            (IndexName.EVI.value, indices.evi),
            (IndexName.NDMI.value, indices.ndmi),
        ):
            if value is None:
                continue
            stats = scene.index_stats.get(name)
            mean, mn, mx, std = stats if stats else (value, value, value, 0.0)
            if name == IndexName.NDVI.value:
                ndvi_std = std
            await self.repo.add_index(
                SatelliteIndex(
                    session_id=session.id,
                    farm_id=farm_id,
                    index_name=name,
                    mean=mean,
                    minimum=mn,
                    maximum=mx,
                    std=std,
                )
            )
        return ndvi_std

    async def _persist_images(
        self, farm_id: uuid.UUID, session: SatelliteSession, scene: ProviderScene
    ) -> None:
        for band, url in (scene.images or {}).items():
            await self.repo.add_image(
                SatelliteImage(
                    session_id=session.id,
                    farm_id=farm_id,
                    band=band,
                    image_url=url,
                    thumbnail_url=scene.thumbnail_url,
                    resolution_m=scene.resolution_m,
                )
            )

    async def _persist_alert(self, user: User, session: SatelliteSession, draft) -> None:
        await self.repo.add_alert(
            SatelliteAlert(
                user_id=user.id,
                session_id=session.id,
                farm_id=session.farm_id,
                code=draft.code,
                category=draft.category,
                severity=draft.severity,
                priority=draft.priority,
                value=draft.value,
                params=draft.params or None,
            )
        )

    async def _recent_rainfall(self, user: User, farm_id: uuid.UUID) -> float | None:
        """Best-effort recent rainfall from the Weather module (guarded). ``None``
        when weather is disabled or unavailable — never blocks satellite analysis."""
        if not self._enable_weather:
            return None
        try:
            from app.modules.weather.service import WeatherService

            bundle = await WeatherService(self.session).get_by_farm(user, farm_id)
            recent = [d.precipitation_sum_mm or 0 for d in bundle.daily[:2]]
            return sum(recent)
        except Exception:  # noqa: BLE001 — weather context is optional, never fatal
            logger.info("weather context unavailable for satellite (farm %s)", farm_id)
            return None

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def get_dashboard(self, user: User, farm_id: uuid.UUID) -> dict:
        farm = await self._require_farm(user, farm_id)
        has_polygon = self._polygon(farm) is not None
        latest = await self.repo.latest_session(user.id, farm_id)

        if latest is None:
            message = (
                "satellite.status.no_polygon"
                if not has_polygon
                else "satellite.status.never_refreshed"
            )
            return {
                "farm_id": farm_id,
                "has_polygon": has_polygon,
                "has_data": False,
                "status": SessionStatus.PENDING.value,
                "unavailable_reason": (
                    UnavailableReason.NO_POLYGON.value
                    if not has_polygon
                    else UnavailableReason.NONE.value
                ),
                "message_code": message,
                "session": None,
                "alerts": [],
            }

        available = latest.status == SessionStatus.AVAILABLE.value
        if not has_polygon:
            message = "satellite.status.no_polygon"
        elif available:
            message = None
        else:
            message = f"satellite.status.{latest.unavailable_reason}"
        return {
            "farm_id": farm_id,
            "has_polygon": has_polygon,
            "has_data": available,
            "status": latest.status,
            "unavailable_reason": latest.unavailable_reason,
            "message_code": message,
            "session": latest,
            "alerts": latest.alerts or [],
        }

    async def latest(self, user: User, farm_id: uuid.UUID) -> SatelliteSession:
        await self._require_farm(user, farm_id)
        session = await self.repo.latest_session(user.id, farm_id, available_only=True)
        if session is None:
            raise SatelliteUnavailableError()
        return session

    async def history(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[SatelliteHistory]:
        await self._require_farm(user, farm_id)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_history(user.id, farm_id, limit=page_size, offset=offset)
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def timeline(self, user: User, farm_id: uuid.UUID, *, range_: str) -> list[dict]:
        await self._require_farm(user, farm_id)
        rows = await self.repo.history_for_timeline(user.id, farm_id)
        buckets: dict[str, list[SatelliteHistory]] = defaultdict(list)
        for row in rows:
            when = row.capture_date or row.recorded_at.date()
            if range_ == TIMELINE_MONTHLY:
                key = f"{when.year}-{when.month:02d}"
            else:
                iso = when.isocalendar()
                key = f"{iso.year}-W{iso.week:02d}"
            buckets[key].append(row)

        points: list[dict] = []
        for key in sorted(buckets):
            group = buckets[key]
            points.append(
                {
                    "period": key,
                    "ndvi": _mean([r.ndvi for r in group]),
                    "ndre": _mean([r.ndre for r in group]),
                    "ndmi": _mean([r.ndmi for r in group]),
                    "count": len(group),
                }
            )
        return points

    async def indices(self, user: User, farm_id: uuid.UUID) -> list[SatelliteIndex]:
        await self._require_farm(user, farm_id)
        session = await self.repo.latest_session(user.id, farm_id, available_only=True)
        if session is None:
            raise SatelliteUnavailableError()
        return await self.repo.list_indices(session.id)

    async def alerts(self, user: User, farm_id: uuid.UUID) -> list[SatelliteAlert]:
        await self._require_farm(user, farm_id)
        session = await self.repo.latest_session(user.id, farm_id)
        if session is None:
            return []
        return await self.repo.list_alerts(session.id)


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 4) if present else None
