"""Disease-domain repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select

from app.modules.disease.models import DiseaseReport
from app.shared.base_repository import BaseRepository


class DiseaseReportRepository(BaseRepository[DiseaseReport]):
    model = DiseaseReport

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        farm_id: uuid.UUID | None,
        unassigned_only: bool,
        crop: str | None,
    ) -> Select[tuple[DiseaseReport]]:
        stmt = select(DiseaseReport).where(
            DiseaseReport.user_id == user_id,
            DiseaseReport.is_deleted.is_(False),
        )
        if unassigned_only:
            stmt = stmt.where(DiseaseReport.farm_id.is_(None))
        elif farm_id is not None:
            stmt = stmt.where(DiseaseReport.farm_id == farm_id)
        if crop:
            stmt = stmt.where(DiseaseReport.crop == crop)
        return stmt

    async def get_for_user(
        self, report_id: uuid.UUID, user_id: uuid.UUID
    ) -> DiseaseReport | None:
        result = await self.session.execute(
            select(DiseaseReport).where(
                DiseaseReport.id == report_id,
                DiseaseReport.user_id == user_id,
                DiseaseReport.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_kvk_review_record(self, report_id: uuid.UUID) -> DiseaseReport | None:
        result = await self.session.execute(
            select(DiseaseReport).where(
                DiseaseReport.id == report_id,
                DiseaseReport.crop == "redgram",
                DiseaseReport.kvk_session.is_(True),
                DiseaseReport.review_consent.is_(True),
                DiseaseReport.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_consented_reviewed_redgram(self) -> list[DiseaseReport]:
        result = await self.session.execute(
            select(DiseaseReport).where(
                DiseaseReport.crop == "redgram",
                DiseaseReport.kvk_session.is_(True),
                DiseaseReport.review_consent.is_(True),
                DiseaseReport.review_status.in_(("confirmed", "corrected")),
                DiseaseReport.is_deleted.is_(False),
            ).order_by(DiseaseReport.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        farm_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
        crop: str | None = None,
    ) -> list[DiseaseReport]:
        stmt = (
            self._filtered(
                user_id,
                farm_id=farm_id,
                unassigned_only=unassigned_only,
                crop=crop,
            )
            .order_by(DiseaseReport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(
        self,
        user_id: uuid.UUID,
        *,
        farm_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
        crop: str | None = None,
    ) -> int:
        inner = self._filtered(
            user_id,
            farm_id=farm_id,
            unassigned_only=unassigned_only,
            crop=crop,
        ).order_by(None)
        result = await self.session.execute(
            select(func.count()).select_from(inner.subquery())
        )
        return int(result.scalar_one())

    async def district_outbreak_groups(
        self, *, since: datetime, min_distinct_farms: int
    ) -> list[tuple[str, str, str, int]]:
        """Return privacy-safe district/crop/disease aggregates across all users.

        Individual user and farm identities never leave this repository method.
        Repeated reports from one farm count only once toward the threshold.
        """
        from app.modules.farms.models import Farm, FarmLocation

        normalized_district = func.lower(func.trim(FarmLocation.district))
        distinct_farm_count = func.count(func.distinct(DiseaseReport.farm_id))
        stmt = (
            select(
                normalized_district.label("district"),
                DiseaseReport.crop,
                DiseaseReport.disease,
                distinct_farm_count.label("farm_count"),
            )
            .join(Farm, DiseaseReport.farm_id == Farm.id)
            .join(FarmLocation, Farm.id == FarmLocation.farm_id)
            .where(
                DiseaseReport.is_deleted.is_(False),
                DiseaseReport.farm_id.is_not(None),
                DiseaseReport.crop.is_not(None),
                DiseaseReport.disease.is_not(None),
                DiseaseReport.created_at >= since,
                FarmLocation.district.is_not(None),
            )
            .group_by(
                normalized_district,
                DiseaseReport.crop,
                DiseaseReport.disease,
            )
            .having(distinct_farm_count >= min_distinct_farms)
        )
        result = await self.session.execute(stmt)
        return [
            (str(row[0]), str(row[1]), str(row[2]), int(row[3]))
            for row in result.all()
        ]
