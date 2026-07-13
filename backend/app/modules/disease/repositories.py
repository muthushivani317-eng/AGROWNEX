"""Disease-domain repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern)."""
from __future__ import annotations

import uuid

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
        crop: str | None,
    ) -> Select[tuple[DiseaseReport]]:
        stmt = select(DiseaseReport).where(
            DiseaseReport.user_id == user_id,
            DiseaseReport.is_deleted.is_(False),
        )
        if farm_id is not None:
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

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
    ) -> list[DiseaseReport]:
        stmt = (
            self._filtered(user_id, farm_id=farm_id, crop=crop)
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
        crop: str | None = None,
    ) -> int:
        inner = self._filtered(user_id, farm_id=farm_id, crop=crop).order_by(None)
        result = await self.session.execute(
            select(func.count()).select_from(inner.subquery())
        )
        return int(result.scalar_one())
