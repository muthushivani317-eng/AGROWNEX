"""Crop Intelligence service (docs: Repository → Service → Engine → Decision →
Recommendation → API).

``refresh`` reads every module (guarded), runs the pure Crop Intelligence Engine,
Decision Engine and Recommendation Engine, and persists one report (+ health scores,
risk, recommendations and a history snapshot). Reads serve the dashboard / latest /
history / report. Source-module data is only read — never overwritten. Business logic
lives here; routes stay thin.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.intelligence.decision import assess_risk, detect_issues
from app.modules.intelligence.engine import HealthScores, compute_health
from app.modules.intelligence.exceptions import (
    FarmNotOwnedError,
    IntelligenceReportNotFoundError,
    IntelligenceUnavailableError,
)
from app.modules.intelligence.models import (
    CropDecisionHistory,
    CropHealthScore,
    CropIntelligenceReport,
    CropRecommendation,
    CropRiskScore,
)
from app.modules.intelligence.recommendation import generate_recommendations
from app.modules.intelligence.repository import IntelligenceRepository
from app.modules.intelligence.sources import IntelligenceSources
from app.schemas.response import PaginatedData

logger = get_logger("intelligence.service")


class IntelligenceService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        weather_service=None,  # noqa: ANN001 — optional WeatherService (best-effort)
        now: datetime | None = None,
        enable_weather: bool = True,
    ) -> None:
        self.session = session
        self.repo = IntelligenceRepository(session)
        self.farms = FarmRepository(session)
        self.weather_service = weather_service
        self.enable_weather = enable_weather
        self._now = now

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    async def _require_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotOwnedError()
        return farm

    # ----------------------------------------------------------------- #
    # Refresh (generate one report)
    # ----------------------------------------------------------------- #
    async def refresh(
        self, user: User, farm_id: uuid.UUID
    ) -> CropIntelligenceReport:
        farm = await self._require_farm(user, farm_id)
        now = self._now_dt()

        sources = IntelligenceSources(
            self.session,
            now=now,
            weather_service=self.weather_service,
            enable_weather=self.enable_weather,
        )
        inputs = await sources.gather(user, farm)

        scores = compute_health(inputs)
        issues = detect_issues(inputs, scores)
        risk = assess_risk(inputs, scores, issues)
        drafts = generate_recommendations(inputs, scores, issues, risk)

        report = await self._persist(user, farm, now, scores, risk, issues, drafts)
        logger.info(
            "Intelligence report %s for user=%s farm=%s (health=%s risk=%s conf=%s)",
            report.id, user.id, farm.id, scores.overall, risk, scores.confidence,
        )
        return report

    async def _persist(
        self,
        user: User,
        farm: Farm,
        now: datetime,
        scores: HealthScores,
        risk: str,
        issues,
        drafts,
    ) -> CropIntelligenceReport:
        report = CropIntelligenceReport(
            user_id=user.id,
            farm_id=farm.id,
            crop=getattr(farm, "crop", None),
            generated_at=now,
            overall_health_score=scores.overall,
            confidence=scores.confidence,
            overall_risk=risk,
            sources_used=list(scores.sources_used),
        )
        await self.repo.add_report(report)

        await self.repo.add_health(
            CropHealthScore(
                report_id=report.id,
                overall_health_score=scores.overall,
                confidence=scores.confidence,
                disease_score=scores.disease,
                nutrient_score=scores.nutrient,
                soil_score=scores.soil,
                satellite_score=scores.satellite,
                weather_score=scores.weather,
                growth_score=scores.growth,
            )
        )
        await self.repo.add_risk(
            CropRiskScore(
                report_id=report.id,
                overall_risk=risk,
                risk_score=(100 - scores.overall) if scores.overall is not None else None,
                priority_issues=[
                    {"code": i.code, "severity": i.severity, "modules": list(i.modules)}
                    for i in issues
                ],
            )
        )
        for rank, draft in enumerate(drafts):
            await self.repo.add_recommendation(
                CropRecommendation(
                    report_id=report.id,
                    user_id=user.id,
                    farm_id=farm.id,
                    code=draft.code,
                    priority=draft.priority,
                    category=draft.category,
                    modules=list(draft.modules),
                    rank=rank,
                )
            )
        await self.repo.add_history(
            CropDecisionHistory(
                user_id=user.id,
                farm_id=farm.id,
                report_id=report.id,
                overall_health_score=scores.overall,
                overall_risk=risk,
                confidence=scores.confidence,
                recorded_at=now,
            )
        )

        await self.session.flush()
        await self.session.refresh(report)
        return report

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def get_dashboard(self, user: User, farm_id: uuid.UUID) -> dict:
        await self._require_farm(user, farm_id)
        report = await self.repo.latest_report(user.id, farm_id)
        return {
            "farm_id": farm_id,
            "has_data": report is not None,
            "message_code": None if report else "intelligence.status.no_report",
            "report": report,
        }

    async def latest(self, user: User, farm_id: uuid.UUID) -> CropIntelligenceReport:
        await self._require_farm(user, farm_id)
        report = await self.repo.latest_report(user.id, farm_id)
        if report is None:
            raise IntelligenceUnavailableError()
        return report

    async def history(
        self, user: User, farm_id: uuid.UUID, *, page: int, page_size: int
    ) -> PaginatedData[CropDecisionHistory]:
        await self._require_farm(user, farm_id)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_history(
            user.id, farm_id, limit=page_size, offset=offset
        )
        source_counts = await self.repo.report_source_counts(
            user.id, [row.report_id for row in rows if row.report_id is not None]
        )
        for row in rows:
            row._sufficient_evidence = source_counts.get(row.report_id, 0) >= 2
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows, page=page, page_size=page_size, total=total, total_pages=total_pages
        )

    async def get_report(
        self, user: User, report_id: uuid.UUID
    ) -> CropIntelligenceReport:
        report = await self.repo.get_report(report_id, user.id)
        if report is None:
            raise IntelligenceReportNotFoundError()
        return report
