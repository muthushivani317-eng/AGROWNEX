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
from app.modules.soil.constants import (
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
from app.modules.soil.exceptions import (
    FarmNotOwnedError,
    InvalidSoilReportError,
    SoilDataUnavailableError,
)
from app.modules.soil.models import (
    SoilHistory,
    SoilProfile,
    SoilRecommendation,
    SoilReport,
    SoilTestResult,
)
from app.modules.soil.provider import SoilProvider, get_default_provider
from app.modules.soil.repository import SoilRepository
from app.modules.soil.schemas import SoilReportCreate
from app.schemas.response import PaginatedData

logger = get_logger("soil.service")

_VALUE_FIELDS = (
    "ph", "organic_carbon", "nitrogen", "phosphorus", "potassium",
    "ec_salinity", "water_holding_capacity",
)


class SoilService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: SoilProvider | None = None,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.repo = SoilRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
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
        report.status = ReportStatus.PROCESSED.value

        profile = await self._merge_profile(user, farm, report, values)
        merged = self._values_from_profile(profile)
        await self._store_recommendations(user, farm.id, report.id, merged)
        await self._append_history(user, farm.id, report, values)

        await self.session.flush()
        await self.session.refresh(report)
        return profile, report

    async def _merge_profile(
        self, user: User, farm: Farm, report: SoilReport, values
    ) -> SoilProfile:
        profile = await self.repo.get_profile(user.id, farm.id)
        if profile is None:
            profile = SoilProfile(user_id=user.id, farm_id=farm.id)
            await self.repo.add_profile(profile)

        # Merge — a new measured value overrides; otherwise keep the prior value.
        for field in _VALUE_FIELDS:
            new = getattr(values, field, None)
            if new is not None:
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

        if profile is not None:
            values = self._values_from_profile(profile)
            assessment = assess(values)
            recs = await self.repo.latest_recommendations(user.id, farm_id)
            rec_drafts = [self._rec_to_draft(r) for r in recs] or build_recommendations(
                values
            )
            latest_report = await self.repo.latest_report(user.id, farm_id)
            has_data = assessment.has_any_value or bool(
                assessment.deficient_micronutrients
            )
            message_code = None if has_data else "soil.status.profile_incomplete"
            return {
                "farm_id": farm_id,
                "has_data": has_data,
                "message_code": message_code,
                "profile": profile,
                "assessment": assessment,
                "recommendations": rec_drafts,
                "latest_report": latest_report,
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
        }

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

    async def history(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[SoilHistory]:
        await self._require_farm(user, farm_id)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_history(
            user.id, farm_id, limit=page_size, offset=offset
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows, page=page, page_size=page_size, total=total,
            total_pages=total_pages,
        )

    async def recommendations(
        self, user: User, farm_id: uuid.UUID
    ) -> list[RecommendationDraft]:
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
