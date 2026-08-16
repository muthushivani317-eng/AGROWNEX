"""Soil Intelligence service (docs: Repository → Service → Soil Engine → Provider).

Orchestrates the soil platform: accept a farmer-uploaded report, merge it into the
farm's soil profile (never fabricating a missing value), run the deterministic Soil
Engine to produce *generic* agronomic recommendations, record a trend snapshot, and
serve the dashboard / latest / history / recommendations reads. When no soil data
exists the reads say so honestly. Business logic lives here; routes stay thin.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.satellite.constants import SessionStatus
from app.modules.satellite.repository import SatelliteRepository
from app.modules.soil.constants import (
    PARAMETER_UNITS,
    SOURCE_CONFIDENCE,
    ReportStatus,
)
from app.modules.soil.engine import (
    RecommendationDraft,
    SoilAssessment,
    SoilValues,
    assess,
    build_recommendations,
)
from app.modules.soil.evidence import EvidenceType, IndicatorEvidence, derive_indicator
from app.modules.soil.exceptions import (
    FarmNotOwnedError,
    InvalidSoilReportError,
    SoilDataUnavailableError,
)
from app.modules.soil.models import (
    SoilHistory,
    SoilIndicatorEvidence,
    SoilProfile,
    SoilRecommendation,
    SoilReport,
    SoilScanRecord,
    SoilTestResult,
)
from app.modules.soil.provider import RemoteSoilOutcome, SoilProvider, get_default_provider
from app.modules.soil.repository import SoilRepository
from app.modules.soil.scan import (
    EvidenceObservation,
    ScanInputs,
    SpatialVariabilityZone,
    build_scan,
)
from app.modules.soil.schemas import SoilReportCreate
from app.modules.soil.terrain import TerrainProvider, UnavailableTerrainProvider
from app.modules.weather.service import WeatherService
from app.schemas.response import PaginatedData

logger = get_logger("soil.service")

_VALUE_FIELDS = (
    "ph",
    "organic_carbon",
    "nitrogen",
    "phosphorus",
    "potassium",
    "ec_salinity",
    "water_holding_capacity",
)


class SoilService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: SoilProvider | None = None,
        weather_service: WeatherService | None = None,
        terrain_provider: TerrainProvider | None = None,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.repo = SoilRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
        self.weather_service = weather_service or WeatherService(session)
        self.terrain_provider = terrain_provider or UnavailableTerrainProvider()
        self.satellite = SatelliteRepository(session)
        self._now = now

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    async def _require_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotOwnedError()
        return farm

    # ----------------------------------------------------------------- #
    # Value helpers
    # ----------------------------------------------------------------- #
    @staticmethod
    def _values_from_profile(profile: SoilProfile | None) -> SoilValues:
        if profile is None:
            return SoilValues()
        return SoilValues(
            ph=profile.ph,
            organic_carbon=profile.organic_carbon,
            nitrogen=profile.nitrogen,
            phosphorus=profile.phosphorus,
            potassium=profile.potassium,
            ec_salinity=profile.ec_salinity,
            water_holding_capacity=profile.water_holding_capacity,
            drainage=profile.drainage,
            micronutrients=profile.micronutrients,
            soil_type=profile.soil_type,
        )

    @staticmethod
    def _baseline_values(farm: Farm) -> SoilValues:
        """A farm-registration baseline — only the farmer's registered soil type,
        no fabricated measurements."""
        return SoilValues(soil_type=farm.soil_type)

    # ----------------------------------------------------------------- #
    # Submit report
    # ----------------------------------------------------------------- #
    async def submit_report(
        self, user: User, data: SoilReportCreate
    ) -> tuple[SoilProfile, SoilReport]:
        farm = await self._require_farm(user, data.farm_id)
        values = data.values
        has_value = any(getattr(values, f) is not None for f in _VALUE_FIELDS) or bool(
            values.micronutrients
        )
        if not has_value and not data.report_url:
            raise InvalidSoilReportError(
                "Provide at least one soil value or upload a report image."
            )

        confidence = SOURCE_CONFIDENCE.get(data.source.value, 50)
        report = SoilReport(
            user_id=user.id,
            farm_id=farm.id,
            source=data.source.value,
            report_url=data.report_url,
            thumbnail_url=data.thumbnail_url,
            mime_type=data.mime_type,
            lab_name=data.lab_name,
            test_date=data.test_date,
            notes=data.notes,
            status=ReportStatus.SUBMITTED.value,
            confidence=confidence,
        )
        await self.repo.add_report(report)

        result = SoilTestResult(
            report_id=report.id,
            ph=values.ph,
            organic_carbon=values.organic_carbon,
            nitrogen=values.nitrogen,
            phosphorus=values.phosphorus,
            potassium=values.potassium,
            sulphur=values.sulphur,
            ec_salinity=values.ec_salinity,
            water_holding_capacity=values.water_holding_capacity,
            drainage=values.drainage.value if values.drainage else None,
            micronutrients=values.micronutrients,
        )
        await self.repo.add_result(result)
        await self._store_indicator_evidence(user, farm.id, report, values)
        report.status = ReportStatus.PROCESSED.value

        profile = await self._merge_profile(user, farm, report, values)
        merged = self._values_from_profile(profile)
        await self._store_recommendations(user, farm.id, report.id, merged)
        await self._append_history(user, farm.id, report, values)

        await self.session.flush()
        await self.session.refresh(report)
        return profile, report

    async def _store_indicator_evidence(self, user, farm_id, report, values) -> None:
        # Values in this endpoint are typed by the farmer. Merely selecting "lab" or
        # attaching a report does not prove extraction or laboratory verification.
        evidence_type = EvidenceType.USER_ENTERED.value
        collected_at = report.test_date or self._now_dt().date()
        for indicator in _VALUE_FIELDS:
            value = getattr(values, indicator, None)
            if value is None:
                continue
            await self.repo.add_evidence(
                SoilIndicatorEvidence(
                    user_id=user.id,
                    farm_id=farm_id,
                    report_id=report.id,
                    indicator=indicator,
                    numeric_value=value,
                    unit=PARAMETER_UNITS.get(indicator, ""),
                    evidence_type=evidence_type,
                    collection_method="submitted_report",
                    collected_at=collected_at,
                    source_reference=str(report.id),
                    spatial_coverage="soil_sample" if report.source == "lab" else "farm_report",
                    confidence=report.confidence,
                    verification_state="unverified",
                    report_reference=report.report_url or str(report.id),
                    provenance={
                        "source": report.source,
                        "merge_rule": "measured_precedes_estimated",
                    },
                )
            )

    async def _merge_profile(
        self, user: User, farm: Farm, report: SoilReport, values
    ) -> SoilProfile:
        profile = await self.repo.get_profile(user.id, farm.id)
        if profile is None:
            profile = SoilProfile(user_id=user.id, farm_id=farm.id)
            await self.repo.add_profile(profile)

        # Merge — a new measured value overrides; otherwise keep the prior value.
        estimated_source = report.source in {"satellite", "estimate"}
        for field in _VALUE_FIELDS:
            new = getattr(values, field, None)
            if new is not None and (not estimated_source or getattr(profile, field) is None):
                setattr(profile, field, new)
        if values.drainage is not None:
            profile.drainage = values.drainage.value
        if values.micronutrients:
            merged = dict(profile.micronutrients or {})
            merged.update(values.micronutrients)
            profile.micronutrients = merged

        profile.soil_type = profile.soil_type or farm.soil_type
        if farm.location is not None:
            profile.latitude = profile.latitude or farm.location.latitude
            profile.longitude = profile.longitude or farm.location.longitude
        profile.source = report.source
        profile.confidence = report.confidence
        profile.last_test_date = report.test_date or profile.last_test_date
        return profile

    async def _store_recommendations(
        self,
        user: User,
        farm_id: uuid.UUID,
        report_id: uuid.UUID,
        values: SoilValues,
    ) -> None:
        # Drop the previous farm-level (report-less) baseline advice, then persist
        # fresh recommendations tied to this report.
        await self.repo.delete_farm_recommendations(user.id, farm_id, report_id=None)
        for draft in build_recommendations(values):
            await self.repo.add_recommendation(
                SoilRecommendation(
                    user_id=user.id,
                    farm_id=farm_id,
                    report_id=report_id,
                    category=draft.category,
                    code=draft.code,
                    parameter=draft.parameter,
                    rating=draft.rating,
                    severity=draft.severity,
                    priority=draft.priority,
                    value=draft.value,
                    unit=draft.unit,
                )
            )

    async def _append_history(
        self, user: User, farm_id: uuid.UUID, report: SoilReport, values
    ) -> None:
        await self.repo.add_history(
            SoilHistory(
                user_id=user.id,
                farm_id=farm_id,
                report_id=report.id,
                test_date=report.test_date,
                ph=values.ph,
                organic_carbon=values.organic_carbon,
                nitrogen=values.nitrogen,
                phosphorus=values.phosphorus,
                potassium=values.potassium,
                source=report.source,
                confidence=report.confidence,
                recorded_at=self._now_dt(),
            )
        )

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def get_dashboard(self, user: User, farm_id: uuid.UUID):
        farm = await self._require_farm(user, farm_id)
        profile = await self.repo.get_profile(user.id, farm_id)

        evidence_rows = await self.repo.list_evidence(user.id, farm_id)
        evidence_out, overall_status = self._derive_evidence_view(evidence_rows)
        if profile is not None:
            values = self._values_from_profile(profile)
            assessment = assess(values)
            recs = await self.repo.latest_recommendations(user.id, farm_id)
            rec_drafts = [self._rec_to_draft(r) for r in recs] or build_recommendations(values)
            latest_report = await self.repo.latest_report(user.id, farm_id)
            has_data = assessment.has_any_value or bool(assessment.deficient_micronutrients)
            message_code = None if has_data else "soil.status.profile_incomplete"
            return {
                "farm_id": farm_id,
                "has_data": has_data,
                "message_code": message_code,
                "profile": profile,
                "assessment": assessment,
                "recommendations": rec_drafts,
                "latest_report": latest_report,
                "indicator_evidence": evidence_out,
                "overall_status": overall_status,
            }

        # No profile yet — a farm-registration baseline only (honest "no data").
        values = self._baseline_values(farm)
        return {
            "farm_id": farm_id,
            "has_data": False,
            "message_code": "soil.status.no_data",
            "profile": None,
            "assessment": assess(values),
            "recommendations": build_recommendations(values),
            "latest_report": None,
            "indicator_evidence": evidence_out,
            "overall_status": overall_status,
        }

    def _derive_evidence_view(self, rows: list[SoilIndicatorEvidence]) -> tuple[list[dict], str]:
        grouped: dict[str, list[SoilIndicatorEvidence]] = {}
        for row in rows:
            grouped.setdefault(row.indicator, []).append(row)
        output: list[dict] = []
        statuses: list[str] = []
        for indicator in _VALUE_FIELDS:
            items = grouped.get(indicator, [])
            domain = [
                IndicatorEvidence(
                    indicator=row.indicator,
                    value=(
                        row.numeric_value if row.numeric_value is not None else row.text_value or ""
                    ),
                    unit=row.unit,
                    evidence_type=EvidenceType(row.evidence_type),
                    collection_method=row.collection_method,
                    collected_at=row.collected_at,
                    source_reference=row.source_reference,
                    spatial_coverage=row.spatial_coverage,
                    confidence=row.confidence,
                    uncertainty_low=row.uncertainty_low,
                    uncertainty_high=row.uncertainty_high,
                    verification_state=row.verification_state,
                    report_reference=row.report_reference,
                )
                for row in items
            ]
            derived = derive_indicator(indicator, domain, today=self._now_dt().date())
            statuses.append(derived.status.value)
            for item in domain:
                output.append(
                    {
                        **item.__dict__,
                        "evidence_type": item.evidence_type.value,
                        "freshness": (
                            "stale"
                            if (self._now_dt().date() - item.collected_at).days > 730
                            else "current"
                        ),
                        "status": derived.status.value,
                    }
                )
        overall = (
            "insufficient_data"
            if not output
            else "review_required"
            if any(status in {"stale", "conflicting"} for status in statuses)
            else "assessed"
        )
        return output, overall

    @staticmethod
    def _rec_to_draft(rec: SoilRecommendation) -> RecommendationDraft:
        return RecommendationDraft(
            category=rec.category,
            code=rec.code,
            severity=rec.severity,
            priority=rec.priority,
            parameter=rec.parameter,
            rating=rec.rating,
            value=rec.value,
            unit=rec.unit,
        )

    async def latest(self, user: User, farm_id: uuid.UUID) -> SoilReport:
        await self._require_farm(user, farm_id)
        report = await self.repo.latest_report(user.id, farm_id)
        if report is None:
            raise SoilDataUnavailableError()
        return report

    async def remote_estimation(self, user: User, farm_id: uuid.UUID) -> RemoteSoilOutcome:
        """Request remote indicators for the owned farm's verified boundary.

        No approximate point AOI is manufactured. An unavailable provider or boundary
        is an ordinary explicit state and never creates a soil record.
        """
        farm = await self._require_farm(user, farm_id)
        boundary = getattr(farm, "boundary", None)
        if boundary is None or not boundary.geojson:
            return RemoteSoilOutcome(
                status="remote_estimation_unavailable", reason="no_verified_aoi"
            )
        return await self.provider.fetch_remote_estimates(boundary.geojson)

    async def soil_scan(self, user: User, farm_id: uuid.UUID):
        """Compatibility entry point: run and persist a bounded scan."""
        return await self.run_soil_scan(user, farm_id)

    async def run_soil_scan(self, user: User, farm_id: uuid.UUID) -> SoilScanRecord:
        farm = await self._require_farm(user, farm_id)
        boundary = getattr(farm, "boundary", None)
        aoi_verified = bool(boundary is not None and boundary.geojson)
        aoi = boundary.geojson if aoi_verified else None

        weather: tuple[EvidenceObservation, ...] = ()
        weather_state = "unavailable"
        try:
            bundle = await self.weather_service.get_by_farm(user, farm_id)
            observed_at = datetime.fromisoformat(bundle.fetched_at.replace("Z", "+00:00"))
            weather = (
                EvidenceObservation(
                    source=bundle.source,
                    observed_at=observed_at,
                    freshness=bundle.data_state,
                    quality="usable",
                    values={
                        "precipitation_mm": bundle.current.precipitation_mm,
                        "temperature_c": bundle.current.temperature_c,
                    },
                ),
            )
            weather_state = bundle.data_state
        except Exception as exc:  # provider/location failure is a partial state
            logger.info("soil_scan_weather_unavailable", reason=type(exc).__name__)

        satellite: tuple[EvidenceObservation, ...] = ()
        spatial_zones: tuple[SpatialVariabilityZone, ...] = ()
        satellite_state = "unavailable"
        session = await self.satellite.latest_session(user.id, farm_id)
        if (
            session is not None
            and session.status == SessionStatus.AVAILABLE.value
            and not session.is_sample
        ):
            captured = (
                datetime.combine(
                    session.capture_date,
                    datetime.min.time(),
                    tzinfo=UTC,
                )
                if session.capture_date
                else session.created_at
            )
            metadata = session.session_metadata or {}
            reference = str(metadata.get("scene_id") or session.id)
            satellite = (
                EvidenceObservation(
                    source=session.provider,
                    observed_at=captured,
                    freshness="current",
                    quality="usable",
                    values={
                        "moisture_status": session.moisture_status,
                        "vegetation_health": session.vegetation_health,
                        "stress_level": session.stress_level,
                    },
                    reference=reference,
                ),
            )
            satellite_state = "available"
            spatial_zones = self._spatial_zones(metadata, session.provider, reference, captured)
        elif session is not None:
            satellite_state = session.unavailable_reason or "unavailable"

        history_evidence: list[EvidenceObservation] = []
        soil_history, _ = await self.repo.list_history(user.id, farm_id, limit=100, offset=0)
        for entry in soil_history:
            if entry.organic_carbon is None:
                continue
            history_evidence.append(
                EvidenceObservation(
                    source=entry.source,
                    observed_at=(
                        entry.recorded_at
                        if entry.recorded_at.tzinfo
                        else entry.recorded_at.replace(tzinfo=UTC)
                    ),
                    freshness="historical",
                    quality="usable",
                    values={"organic_carbon": entry.organic_carbon},
                    reference=str(entry.report_id or entry.id),
                )
            )
        satellite_sessions, _ = await self.satellite.list_sessions(
            user.id, farm_id, limit=100, offset=0
        )
        for historical_session in satellite_sessions:
            if historical_session.is_sample or historical_session.status != "available":
                continue
            metadata = historical_session.session_metadata or {}
            zones = metadata.get("spatial_variability_zones")
            if not isinstance(zones, list):
                continue
            poor_ids = sorted(
                item["zone_id"]
                for item in zones
                if isinstance(item, dict)
                and item.get("observation_class") == "poor_performing"
                and item.get("quality") == "usable"
                and isinstance(item.get("zone_id"), str)
            )
            if not poor_ids:
                continue
            observed_at = (
                datetime.combine(
                    historical_session.capture_date,
                    datetime.min.time(),
                    tzinfo=UTC,
                )
                if historical_session.capture_date
                else (
                    historical_session.created_at
                    if historical_session.created_at.tzinfo
                    else historical_session.created_at.replace(tzinfo=UTC)
                )
            )
            history_evidence.append(
                EvidenceObservation(
                    source=historical_session.provider,
                    observed_at=observed_at,
                    freshness="historical",
                    quality="usable",
                    values={"poor_zone_ids": poor_ids},
                    reference=str(metadata.get("scene_id") or historical_session.id),
                )
            )

        waterlogging = await self.satellite.latest_waterlogging_assessment(user.id, farm_id)
        terrain_state = "unavailable"
        if aoi is not None:
            try:
                terrain_state = (await self.terrain_provider.fetch(aoi)).state
            except Exception as exc:
                logger.info("soil_scan_terrain_unavailable", reason=type(exc).__name__)
        scan = build_scan(
            ScanInputs(
                aoi_verified=aoi_verified,
                aoi_geojson=aoi,
                waterlogging_status=waterlogging.decision.lower() if waterlogging else None,
                spatial_zones=spatial_zones,
                weather=weather,
                satellite=satellite,
                history=tuple(history_evidence),
                weather_state=weather_state,
                satellite_state=satellite_state,
                terrain_state=terrain_state,
                # Propagate this service's (possibly test-injected) clock so
                # SoilScan.generated_at actually reflects it -- see the `now`
                # field docstring on ScanInputs for why this matters for
                # latest-scan ordering determinism.
                now=self._now_dt(),
            )
        )
        indicators = [self._indicator_payload(item) for item in scan.indicators]
        points = [
            point
            for item in indicators
            if item["code"] == "smart_sampling_navigator"
            for point in item["sampling_points"]
        ]
        plan = None
        if points:
            plan = {
                "id": str(uuid.uuid4()),
                "status": "available",
                "created_at": scan.generated_at.isoformat(),
                "points": points,
                "scope": "physical_sample_location_guidance_only",
            }
        row = SoilScanRecord(
            user_id=user.id,
            farm_id=farm_id,
            aoi_geojson=aoi,
            aoi_reference=str(boundary.id) if boundary is not None else None,
            generated_at=scan.generated_at,
            provider_states=scan.provider_states,
            indicators=indicators,
            sampling_plan=plan,
            provenance={
                "weather": [self._observation_payload(item) for item in weather],
                "satellite": [self._observation_payload(item) for item in satellite],
                "terrain": [],
                "production_mock_used": False,
            },
        )
        await self.repo.add_scan(row)
        return row

    @staticmethod
    def _spatial_zones(
        metadata: dict, provider: str, reference: str, observed_at: datetime
    ) -> tuple[SpatialVariabilityZone, ...]:
        raw = metadata.get("spatial_variability_zones")
        if not isinstance(raw, list):
            return ()
        zones: list[SpatialVariabilityZone] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            if not all(
                isinstance(item.get(key), str) and item[key]
                for key in ("zone_id", "variability_class")
            ):
                continue
            geometry = item.get("geometry")
            if not isinstance(geometry, dict):
                continue
            zones.append(
                SpatialVariabilityZone(
                    zone_id=item["zone_id"],
                    geometry=geometry,
                    variability_class=item["variability_class"],
                    source=provider,
                    reference=reference,
                    observed_at=observed_at,
                    quality=str(item.get("quality") or "unusable"),
                    is_sample=bool(item.get("is_sample", False)),
                )
            )
        return tuple(zones)

    @staticmethod
    def _observation_payload(item: EvidenceObservation) -> dict:
        return {
            "source": item.source,
            "observed_at": item.observed_at.isoformat(),
            "freshness": item.freshness,
            "quality": item.quality,
            "reference": item.reference,
            "values": item.values,
        }

    @staticmethod
    def _indicator_payload(item) -> dict:
        return {
            "code": item.code.value,
            "status": item.status,
            "evidence_class": item.evidence_class.value,
            "value": item.value,
            "explanation_code": item.explanation_code,
            "details": item.details,
            "sources": list(item.sources),
            "observation_timestamps": [value.isoformat() for value in item.observation_timestamps],
            "missing_evidence": list(item.missing_evidence),
            "sampling_points": [
                {
                    "zone_id": point.zone_id,
                    "longitude": point.longitude,
                    "latitude": point.latitude,
                    "source": point.source,
                    "reference": point.reference,
                    "reason": point.reason,
                    "quality": point.quality,
                    "sample_data": point.sample_data,
                }
                for point in item.sampling_points
            ],
        }

    async def latest_soil_scan(self, user: User, farm_id: uuid.UUID) -> SoilScanRecord:
        await self._require_farm(user, farm_id)
        row = await self.repo.latest_scan(user.id, farm_id)
        if row is None:
            raise SoilDataUnavailableError("No Soil Scan is available for this farm.")
        return row

    async def get_soil_scan(
        self, user: User, farm_id: uuid.UUID, scan_id: uuid.UUID
    ) -> SoilScanRecord:
        await self._require_farm(user, farm_id)
        row = await self.repo.get_scan(scan_id, user.id)
        if row is None or row.farm_id != farm_id:
            raise SoilDataUnavailableError("Soil Scan not found.")
        return row

    async def scan_history(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[SoilScanRecord]:
        await self._require_farm(user, farm_id)
        rows, total = await self.repo.list_scans(
            user.id, farm_id, limit=page_size, offset=(page - 1) * page_size
        )
        return PaginatedData(
            items=rows,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        )

    async def history(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[SoilHistory]:
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

    async def recommendations(self, user: User, farm_id: uuid.UUID) -> list[RecommendationDraft]:
        farm = await self._require_farm(user, farm_id)
        profile = await self.repo.get_profile(user.id, farm_id)
        if profile is not None:
            persisted = await self.repo.latest_recommendations(user.id, farm_id)
            if persisted:
                return [self._rec_to_draft(r) for r in persisted]
            return build_recommendations(self._values_from_profile(profile))
        return build_recommendations(self._baseline_values(farm))

    async def assessment_for(self, user: User, farm_id: uuid.UUID) -> SoilAssessment:
        profile = await self.repo.get_profile(user.id, farm_id)
        if profile is not None:
            return assess(self._values_from_profile(profile))
        farm = await self._require_farm(user, farm_id)
        return assess(self._baseline_values(farm))
