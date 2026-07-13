"""Soil Intelligence repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the soil tables — profiles, reports, test results,
recommendations and history. No SQL lives in routes or the service.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.soil.models import (
    SoilHistory,
    SoilProfile,
    SoilRecommendation,
    SoilReport,
    SoilTestResult,
)


class SoilRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Profile
    # ----------------------------------------------------------------- #
    async def get_profile(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> SoilProfile | None:
        result = await self.session.execute(
            select(SoilProfile).where(
                SoilProfile.user_id == user_id,
                SoilProfile.farm_id == farm_id,
                SoilProfile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add_profile(self, profile: SoilProfile) -> SoilProfile:
        self.session.add(profile)
        await self.session.flush()
        return profile

    # ----------------------------------------------------------------- #
    # Reports + results
    # ----------------------------------------------------------------- #
    def _owned_reports(self, user_id: uuid.UUID) -> Select[tuple[SoilReport]]:
        return select(SoilReport).where(
            SoilReport.user_id == user_id,
            SoilReport.is_deleted.is_(False),
        )

    async def add_report(self, report: SoilReport) -> SoilReport:
        self.session.add(report)
        await self.session.flush()
        return report

    async def add_result(self, result: SoilTestResult) -> SoilTestResult:
        self.session.add(result)
        await self.session.flush()
        return result

    async def get_report(
        self, report_id: uuid.UUID, user_id: uuid.UUID
    ) -> SoilReport | None:
        res = await self.session.execute(
            self._owned_reports(user_id).where(SoilReport.id == report_id)
        )
        return res.scalar_one_or_none()

    async def latest_report(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> SoilReport | None:
        res = await self.session.execute(
            self._owned_reports(user_id)
            .where(SoilReport.farm_id == farm_id)
            .order_by(SoilReport.test_date.desc().nullslast(), SoilReport.created_at.desc())
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
    ) -> tuple[list[SoilReport], int]:
        base = self._owned_reports(user_id).where(SoilReport.farm_id == farm_id)
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
                    base.order_by(SoilReport.created_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    # ----------------------------------------------------------------- #
    # Recommendations
    # ----------------------------------------------------------------- #
    async def add_recommendation(
        self, rec: SoilRecommendation
    ) -> SoilRecommendation:
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def latest_recommendations(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> list[SoilRecommendation]:
        """Recommendations tied to the farm's most recent report (or farm-wide)."""
        latest = await self.latest_report(user_id, farm_id)
        stmt = select(SoilRecommendation).where(
            SoilRecommendation.user_id == user_id,
            SoilRecommendation.farm_id == farm_id,
        )
        if latest is not None:
            stmt = stmt.where(SoilRecommendation.report_id == latest.id)
        else:
            stmt = stmt.where(SoilRecommendation.report_id.is_(None))
        stmt = stmt.order_by(SoilRecommendation.created_at.asc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def delete_farm_recommendations(
        self, user_id: uuid.UUID, farm_id: uuid.UUID, *, report_id: uuid.UUID | None
    ) -> None:
        """Remove the previous generic (report-less) recommendations before a
        regeneration so a farm never accumulates stale advice."""
        stmt = select(SoilRecommendation).where(
            SoilRecommendation.user_id == user_id,
            SoilRecommendation.farm_id == farm_id,
            SoilRecommendation.report_id.is_(None)
            if report_id is None
            else SoilRecommendation.report_id == report_id,
        )
        for rec in (await self.session.execute(stmt)).scalars().all():
            await self.session.delete(rec)
        await self.session.flush()

    # ----------------------------------------------------------------- #
    # History
    # ----------------------------------------------------------------- #
    async def add_history(self, entry: SoilHistory) -> SoilHistory:
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
    ) -> tuple[list[SoilHistory], int]:
        base = select(SoilHistory).where(
            SoilHistory.user_id == user_id,
            SoilHistory.farm_id == farm_id,
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
                    base.order_by(SoilHistory.recorded_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
