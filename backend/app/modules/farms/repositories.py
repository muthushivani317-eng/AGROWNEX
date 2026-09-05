"""Farm-domain repositories (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the farm tables. Ownership is always scoped by
``user_id`` and soft-deleted farms are excluded. Relationships (location,
boundary, media) are eager-loaded via the models' ``lazy="selectin"`` strategy.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, func, select

from app.modules.farms.constants import FarmStatus
from app.modules.farms.models import Farm, FarmBoundary, FarmLocation, FarmMedia
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

    async def list_active_farms_with_boundary(self) -> list[Farm]:
        """Active, non-deleted farms that have a saved field boundary -- the
        audience for satellite-derived background jobs (added for the Daily
        Task advisory layer's overnight generation job; mirrors the sibling
        `distinct_crop_district_targets` / `list_owner_ids` query pattern
        above rather than querying Farm directly from the job itself)."""
        result = await self.session.execute(
            select(Farm)
            .join(FarmBoundary, FarmBoundary.farm_id == Farm.id)
            .where(Farm.is_deleted.is_(False), Farm.status == FarmStatus.ACTIVE.value)
            .distinct()
        )
        return list(result.scalars().all())

    async def distinct_crop_district_targets(self) -> list[tuple[str, str]]:
        """Distinct (crop, district) pairs across every active farm with both on
        file -- the audience the market-price background refresh job keeps warm
        in addition to explicit favourites, so a farmer's own crop in their own
        district already has *something* stored before they ever open the
        Market Prices screen, instead of depending on a live provider call the
        first time (docs: 2026-09 market reliability -- most first-time queries
        aren't for a favourited combo, they're for the farmer's own farm)."""
        result = await self.session.execute(
            select(Farm.crop, FarmLocation.district)
            .join(FarmLocation, FarmLocation.farm_id == Farm.id)
            .where(
                Farm.is_deleted.is_(False),
                Farm.status == FarmStatus.ACTIVE.value,
                Farm.crop.is_not(None),
                FarmLocation.district.is_not(None),
            )
            .distinct()
        )
        return [(crop, district) for crop, district in result.all()]

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
