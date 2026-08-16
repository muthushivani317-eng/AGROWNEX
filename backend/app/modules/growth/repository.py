"""Growth repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the crop_growth_* tables. Always scoped by
``user_id`` and excludes soft-deleted rows. No SQL lives in routes or the service.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.growth.constants import SessionStatus
from app.modules.growth.models import (
    CropGrowthAnalysis,
    CropGrowthImage,
    CropGrowthSession,
    CropGrowthTimeline,
)


class GrowthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Sessions
    # ----------------------------------------------------------------- #
    async def add_session(self, session: CropGrowthSession) -> CropGrowthSession:
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> CropGrowthSession | None:
        result = await self.session.execute(
            select(CropGrowthSession).where(
                CropGrowthSession.id == session_id,
                CropGrowthSession.user_id == user_id,
                CropGrowthSession.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def find_active_session(
        self, user_id: uuid.UUID, farm_id: uuid.UUID, crop: str | None
    ) -> CropGrowthSession | None:
        stmt = select(CropGrowthSession).where(
            CropGrowthSession.user_id == user_id,
            CropGrowthSession.farm_id == farm_id,
            CropGrowthSession.status == SessionStatus.ACTIVE.value,
            CropGrowthSession.is_deleted.is_(False),
        )
        if crop:
            stmt = stmt.where(CropGrowthSession.crop == crop)
        stmt = stmt.order_by(CropGrowthSession.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _session_filter(
        self, user_id: uuid.UUID, *, farm_id: uuid.UUID | None, crop: str | None
    ) -> Select[tuple[CropGrowthSession]]:
        stmt = select(CropGrowthSession).where(
            CropGrowthSession.user_id == user_id,
            CropGrowthSession.is_deleted.is_(False),
        )
        if farm_id is not None:
            stmt = stmt.where(CropGrowthSession.farm_id == farm_id)
        if crop:
            stmt = stmt.where(CropGrowthSession.crop == crop)
        return stmt

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        *,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CropGrowthSession], int]:
        base = self._session_filter(user_id, farm_id=farm_id, crop=crop)
        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(CropGrowthSession.updated_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def latest_session(
        self, user_id: uuid.UUID, *, farm_id: uuid.UUID | None = None
    ) -> CropGrowthSession | None:
        conditions = [
            CropGrowthSession.user_id == user_id,
            CropGrowthSession.is_deleted.is_(False),
        ]
        if farm_id is not None:
            conditions.append(CropGrowthSession.farm_id == farm_id)
        result = await self.session.execute(
            select(CropGrowthSession)
            .where(*conditions)
            .order_by(CropGrowthSession.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def active_sessions_for_user(self, user_id: uuid.UUID) -> list[CropGrowthSession]:
        result = await self.session.execute(
            select(CropGrowthSession)
            .where(
                CropGrowthSession.user_id == user_id,
                CropGrowthSession.is_deleted.is_(False),
                CropGrowthSession.status == SessionStatus.ACTIVE.value,
            )
            .order_by(CropGrowthSession.updated_at.desc())
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------- #
    # Images
    # ----------------------------------------------------------------- #
    async def add_image(self, image: CropGrowthImage) -> CropGrowthImage:
        self.session.add(image)
        await self.session.flush()
        return image

    async def get_image(self, image_id: uuid.UUID, user_id: uuid.UUID) -> CropGrowthImage | None:
        result = await self.session.execute(
            select(CropGrowthImage).where(
                CropGrowthImage.id == image_id,
                CropGrowthImage.user_id == user_id,
                CropGrowthImage.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def latest_image_for_session(self, session_id: uuid.UUID) -> CropGrowthImage | None:
        result = await self.session.execute(
            select(CropGrowthImage)
            .where(
                CropGrowthImage.session_id == session_id,
                CropGrowthImage.is_deleted.is_(False),
            )
            .order_by(
                CropGrowthImage.captured_at.desc(),
                CropGrowthImage.week_number.desc(),
                CropGrowthImage.created_at.desc(),
                CropGrowthImage.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_images_for_session(self, session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(CropGrowthImage)
            .where(
                CropGrowthImage.session_id == session_id,
                CropGrowthImage.is_deleted.is_(False),
            )
        )
        return int(result.scalar_one())

    def _image_join(self, user_id: uuid.UUID) -> Select[tuple[CropGrowthImage, CropGrowthAnalysis]]:
        return (
            select(CropGrowthImage, CropGrowthAnalysis)
            .outerjoin(
                CropGrowthAnalysis,
                CropGrowthAnalysis.image_id == CropGrowthImage.id,
            )
            .where(
                CropGrowthImage.user_id == user_id,
                CropGrowthImage.is_deleted.is_(False),
            )
        )

    async def list_images(
        self,
        user_id: uuid.UUID,
        *,
        session_id: uuid.UUID | None = None,
        farm_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[CropGrowthImage, CropGrowthAnalysis | None]], int]:
        base = self._image_join(user_id)
        if session_id is not None:
            base = base.where(CropGrowthImage.session_id == session_id)
        if farm_id is not None:
            base = base.where(CropGrowthImage.farm_id == farm_id)

        count_stmt = (
            select(func.count())
            .select_from(CropGrowthImage)
            .where(
                CropGrowthImage.user_id == user_id,
                CropGrowthImage.is_deleted.is_(False),
            )
        )
        if session_id is not None:
            count_stmt = count_stmt.where(CropGrowthImage.session_id == session_id)
        if farm_id is not None:
            count_stmt = count_stmt.where(CropGrowthImage.farm_id == farm_id)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        rows = (
            await self.session.execute(
                base.order_by(CropGrowthImage.captured_at.desc()).limit(limit).offset(offset)
            )
        ).all()
        return [(row[0], row[1]) for row in rows], total

    async def images_for_session(
        self, session_id: uuid.UUID
    ) -> list[tuple[CropGrowthImage, CropGrowthAnalysis | None]]:
        rows = (
            await self.session.execute(
                select(CropGrowthImage, CropGrowthAnalysis)
                .outerjoin(
                    CropGrowthAnalysis,
                    CropGrowthAnalysis.image_id == CropGrowthImage.id,
                )
                .where(
                    CropGrowthImage.session_id == session_id,
                    CropGrowthImage.is_deleted.is_(False),
                )
                .order_by(CropGrowthImage.captured_at.asc())
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    # ----------------------------------------------------------------- #
    # Analysis
    # ----------------------------------------------------------------- #
    async def add_analysis(self, analysis: CropGrowthAnalysis) -> CropGrowthAnalysis:
        self.session.add(analysis)
        await self.session.flush()
        return analysis

    # ----------------------------------------------------------------- #
    # Timeline
    # ----------------------------------------------------------------- #
    async def add_timeline_entry(self, entry: CropGrowthTimeline) -> CropGrowthTimeline:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def latest_timeline_entry(self, session_id: uuid.UUID) -> CropGrowthTimeline | None:
        result = await self.session.execute(
            select(CropGrowthTimeline)
            .where(CropGrowthTimeline.session_id == session_id)
            .order_by(
                CropGrowthTimeline.recorded_at.desc(),
                CropGrowthTimeline.week_number.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def timeline_for_session(
        self, session_id: uuid.UUID
    ) -> list[tuple[CropGrowthTimeline, CropGrowthImage | None]]:
        rows = (
            await self.session.execute(
                select(CropGrowthTimeline, CropGrowthImage)
                .outerjoin(CropGrowthImage, CropGrowthImage.id == CropGrowthTimeline.image_id)
                .where(CropGrowthTimeline.session_id == session_id)
                .order_by(
                    CropGrowthTimeline.week_number.asc(), CropGrowthTimeline.recorded_at.asc()
                )
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def delete_timeline_for_image(self, image_id: uuid.UUID) -> None:
        entries = (
            (
                await self.session.execute(
                    select(CropGrowthTimeline).where(CropGrowthTimeline.image_id == image_id)
                )
            )
            .scalars()
            .all()
        )
        for entry in entries:
            await self.session.delete(entry)
        await self.session.flush()
