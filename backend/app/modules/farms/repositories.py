"""Farm-domain repositories (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the farm tables. Ownership is always scoped by
``user_id`` and soft-deleted farms are excluded. Relationships (location,
boundary, media) are eager-loaded via the models' ``lazy="selectin"`` strategy.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, func, select

from app.modules.farms.models import Farm, FarmLocation, FarmMedia
from app.shared.base_repository import BaseRepository

_SORT_COLUMNS: dict[str, Any] = {
    "name": Farm.name,
    "created_at": Farm.created_at,
    "updated_at": Farm.updated_at,
    "area": Farm.area_hectares,
}


class FarmRepository(BaseRepository[Farm]):
    model = Farm

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None,
        district: str | None,
        crop: str | None,
        search: str | None,
    ) -> Select[tuple[Farm]]:
        stmt = select(Farm).where(
            Farm.user_id == user_id, Farm.is_deleted.is_(False)
        )
        if district:
            stmt = stmt.join(FarmLocation, FarmLocation.farm_id == Farm.id).where(
                func.lower(FarmLocation.district) == district.strip().lower()
            )
        if status:
            stmt = stmt.where(Farm.status == status)
        if crop:
            stmt = stmt.where(Farm.crop == crop)
        if search:
            stmt = stmt.where(Farm.name.ilike(f"%{search.strip()}%"))
        return stmt

    async def list_owner_ids(self) -> list[uuid.UUID]:
        """Distinct user ids that own at least one active farm — the audience the
        weather-alert background job evaluates."""
        result = await self.session.execute(
            select(Farm.user_id).where(Farm.is_deleted.is_(False)).distinct()
        )
        return [row[0] for row in result.all()]

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        district: str | None = None,
        crop: str | None = None,
        search: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
    ) -> list[Farm]:
        column = _SORT_COLUMNS.get(sort, Farm.updated_at)
        ordering = column.asc() if order == "asc" else column.desc()
        stmt = (
            self._filtered(
                user_id, status=status, district=district, crop=crop, search=search
            )
            .order_by(ordering)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        district: str | None = None,
        crop: str | None = None,
        search: str | None = None,
    ) -> int:
        inner = self._filtered(
            user_id, status=status, district=district, crop=crop, search=search
        ).order_by(None)
        stmt = select(func.count()).select_from(inner.subquery())
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_for_user(
        self, farm_id: uuid.UUID, user_id: uuid.UUID
    ) -> Farm | None:
        result = await self.session.execute(
            select(Farm).where(
                Farm.id == farm_id,
                Farm.user_id == user_id,
                Farm.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def name_exists(
        self, user_id: uuid.UUID, name: str, *, exclude_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Farm.id).where(
            Farm.user_id == user_id,
            Farm.is_deleted.is_(False),
            func.lower(Farm.name) == name.strip().lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(Farm.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.first() is not None


class FarmMediaRepository(BaseRepository[FarmMedia]):
    model = FarmMedia

    async def list_for_farm(self, farm_id: uuid.UUID) -> list[FarmMedia]:
        result = await self.session.execute(
            select(FarmMedia)
            .where(FarmMedia.farm_id == farm_id)
            .order_by(FarmMedia.created_at.asc())
        )
        return list(result.scalars().all())
