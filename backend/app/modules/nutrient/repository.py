"""Nutrient repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the nutrient tables — reports, analysis, symptoms,
recommendations and history. No SQL lives in routes or the service.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nutrient.models import (
    NutrientAnalysis,
    NutrientHistory,
    NutrientRecommendation,
    NutrientReport,
    NutrientSymptom,
)


class NutrientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Reports
    # ----------------------------------------------------------------- #
    def _owned(self, user_id: uuid.UUID) -> Select[tuple[NutrientReport]]:
        return select(NutrientReport).where(
            NutrientReport.user_id == user_id,
            NutrientReport.is_deleted.is_(False),
        )

    async def add_report(self, report: NutrientReport) -> NutrientReport:
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_report(self, report_id: uuid.UUID, user_id: uuid.UUID) -> NutrientReport | None:
        res = await self.session.execute(self._owned(user_id).where(NutrientReport.id == report_id))
        return res.scalar_one_or_none()

    async def latest_report(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> NutrientReport | None:
        res = await self.session.execute(
            self._owned(user_id)
            .where(NutrientReport.farm_id == farm_id)
            .order_by(NutrientReport.created_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def list_reports(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NutrientReport], int]:
        base = self._owned(user_id).where(NutrientReport.farm_id == farm_id)
        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(NutrientReport.created_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    async def recent_reports(self, user_id: uuid.UUID, *, limit: int = 50) -> list[NutrientReport]:
        """Recent analysed reports across farms (for the notification source)."""
        rows = (
            (
                await self.session.execute(
                    self._owned(user_id).order_by(NutrientReport.created_at.desc()).limit(limit)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows)

    # ----------------------------------------------------------------- #
    # Analysis + symptoms
    # ----------------------------------------------------------------- #
    async def add_analysis(self, analysis: NutrientAnalysis) -> NutrientAnalysis:
        self.session.add(analysis)
        await self.session.flush()
        return analysis

    async def add_symptom(self, symptom: NutrientSymptom) -> NutrientSymptom:
        self.session.add(symptom)
        await self.session.flush()
        return symptom

    # ----------------------------------------------------------------- #
    # Recommendations
    # ----------------------------------------------------------------- #
    async def add_recommendation(self, rec: NutrientRecommendation) -> NutrientRecommendation:
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def recommendations_for_report(
        self, report_id: uuid.UUID
    ) -> list[NutrientRecommendation]:
        rows = (
            (
                await self.session.execute(
                    select(NutrientRecommendation)
                    .where(NutrientRecommendation.report_id == report_id)
                    .order_by(NutrientRecommendation.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def latest_recommendations(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> list[NutrientRecommendation]:
        latest = await self.latest_report(user_id, farm_id)
        if latest is None:
            return []
        return await self.recommendations_for_report(latest.id)

    # ----------------------------------------------------------------- #
    # History
    # ----------------------------------------------------------------- #
    async def add_history(self, entry: NutrientHistory) -> NutrientHistory:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_history(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NutrientHistory], int]:
        base = select(NutrientHistory).where(
            NutrientHistory.user_id == user_id,
            NutrientHistory.farm_id == farm_id,
        )
        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(NutrientHistory.recorded_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
