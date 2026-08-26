"""Crop Intelligence repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the intelligence tables. Source-module data is read by
the service through each module's own repository — never from here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.intelligence.models import (
    CropDecisionHistory,
    CropHealthScore,
    CropIntelligenceReport,
    CropRecommendation,
    CropRiskScore,
)


class IntelligenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _owned(self, user_id: uuid.UUID) -> Select[tuple[CropIntelligenceReport]]:
        return select(CropIntelligenceReport).where(
            CropIntelligenceReport.user_id == user_id,
            CropIntelligenceReport.is_deleted.is_(False),
        )

    async def add_report(
        self, report: CropIntelligenceReport
    ) -> CropIntelligenceReport:
        self.session.add(report)
        await self.session.flush()
        return report

    async def add_health(self, health: CropHealthScore) -> CropHealthScore:
        self.session.add(health)
        await self.session.flush()
        return health

    async def add_risk(self, risk: CropRiskScore) -> CropRiskScore:
        self.session.add(risk)
        await self.session.flush()
        return risk

    async def add_recommendation(
        self, rec: CropRecommendation
    ) -> CropRecommendation:
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def add_history(self, entry: CropDecisionHistory) -> CropDecisionHistory:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_report(
        self, report_id: uuid.UUID, user_id: uuid.UUID
    ) -> CropIntelligenceReport | None:
        res = await self.session.execute(
            self._owned(user_id).where(CropIntelligenceReport.id == report_id)
        )
        return res.scalar_one_or_none()

    async def latest_report(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> CropIntelligenceReport | None:
        res = await self.session.execute(
            self._owned(user_id)
            .where(CropIntelligenceReport.farm_id == farm_id)
            .order_by(CropIntelligenceReport.generated_at.desc())
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
    ) -> tuple[list[CropIntelligenceReport], int]:
        base = self._owned(user_id).where(CropIntelligenceReport.farm_id == farm_id)
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(CropIntelligenceReport.generated_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    async def recent_reports(
        self, user_id: uuid.UUID, *, limit: int = 50
    ) -> list[CropIntelligenceReport]:
        rows = (
            await self.session.execute(
                self._owned(user_id)
                .order_by(CropIntelligenceReport.generated_at.desc())
                .limit(limit)
            )
        ).scalars().unique().all()
        return list(rows)

    async def list_history(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CropDecisionHistory], int]:
        base = select(CropDecisionHistory).where(
            CropDecisionHistory.user_id == user_id,
            CropDecisionHistory.farm_id == farm_id,
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(CropDecisionHistory.recorded_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def report_source_counts(
        self, user_id: uuid.UUID, report_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not report_ids:
            return {}
        rows = await self.session.execute(
            select(CropIntelligenceReport.id, CropIntelligenceReport.sources_used).where(
                CropIntelligenceReport.user_id == user_id,
                CropIntelligenceReport.id.in_(report_ids),
            )
        )
        return {report_id: len(set(sources or [])) for report_id, sources in rows.all()}
