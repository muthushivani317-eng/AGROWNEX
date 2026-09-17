"""Farmer-domain repositories (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the farmer preference / language tables. The profile
table is served by the existing ``FarmerProfileRepository`` (auth module), which
we reuse rather than duplicate.
"""
from __future__ import annotations

import uuid

from app.modules.auth.profile_models import FarmerLanguage, FarmerPreference
from app.shared.base_repository import BaseRepository
from sqlalchemy import delete, select


class FarmerPreferenceRepository(BaseRepository[FarmerPreference]):
    model = FarmerPreference

    async def get_by_farmer_id(self, farmer_id: uuid.UUID) -> FarmerPreference | None:
        result = await self.session.execute(
            select(FarmerPreference).where(FarmerPreference.farmer_id == farmer_id)
        )
        return result.scalar_one_or_none()


class FarmerLanguageRepository(BaseRepository[FarmerLanguage]):
    model = FarmerLanguage

    async def list_for_farmer(self, farmer_id: uuid.UUID) -> list[FarmerLanguage]:
        result = await self.session.execute(
            select(FarmerLanguage)
            .where(FarmerLanguage.farmer_id == farmer_id)
            .order_by(FarmerLanguage.is_default.desc(), FarmerLanguage.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete_all_for_farmer(self, farmer_id: uuid.UUID) -> None:
        """Clear the farmer's language set before writing a fresh one.

        The language list is a fully replaceable collection (no soft delete),
        so a hard delete of the rows is intentional here.
        """
        await self.session.execute(
            delete(FarmerLanguage).where(FarmerLanguage.farmer_id == farmer_id)
        )
