"""Satellite Intelligence repository (docs/BACKEND_ARCHITECTURE.md → Repository).

The only layer that queries the satellite tables — sessions, images, indices,
alerts and history. No SQL lives in routes or the service.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.satellite.constants import SessionStatus
from app.modules.satellite.models import (
    SatelliteAlert,
    SatelliteHistory,
    SatelliteImage,
    SatelliteIndex,
    SatelliteSession,
)


class SatelliteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Sessions
    # ----------------------------------------------------------------- #
    def _owned(self, user_id: uuid.UUID) -> Select[tuple[SatelliteSession]]:
        return select(SatelliteSession).where(
            SatelliteSession.user_id == user_id,
            SatelliteSession.is_deleted.is_(False),
        )

    async def add_session(self, session: SatelliteSession) -> SatelliteSession:
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> SatelliteSession | None:
        result = await self.session.execute(
            self._owned(user_id).where(SatelliteSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def latest_session(
        self, user_id: uuid.UUID, farm_id: uuid.UUID, *, available_only: bool = False
    ) -> SatelliteSession | None:
        stmt = self._owned(user_id).where(SatelliteSession.farm_id == farm_id)
        if available_only:
            stmt = stmt.where(SatelliteSession.status == SessionStatus.AVAILABLE.value)
        stmt = stmt.order_by(SatelliteSession.created_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def previous_available_ndvi(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> float | None:
        """The most recent available NDVI (for trend comparison on the next scene)."""
        stmt = (
            self._owned(user_id)
            .where(
                SatelliteSession.farm_id == farm_id,
                SatelliteSession.status == SessionStatus.AVAILABLE.value,
                SatelliteSession.ndvi.is_not(None),
            )
            .order_by(SatelliteSession.created_at.desc())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return row.ndvi if row else None

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SatelliteSession], int]:
        base = self._owned(user_id).where(SatelliteSession.farm_id == farm_id)
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
                    base.order_by(SatelliteSession.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    # ----------------------------------------------------------------- #
    # Images / indices / alerts
    # ----------------------------------------------------------------- #
    async def add_image(self, image: SatelliteImage) -> SatelliteImage:
        self.session.add(image)
        await self.session.flush()
        return image

    async def add_index(self, index: SatelliteIndex) -> SatelliteIndex:
        self.session.add(index)
        await self.session.flush()
        return index

    async def list_indices(self, session_id: uuid.UUID) -> list[SatelliteIndex]:
        rows = (
            await self.session.execute(
                select(SatelliteIndex).where(SatelliteIndex.session_id == session_id)
            )
        ).scalars().all()
        return list(rows)

    async def add_alert(self, alert: SatelliteAlert) -> SatelliteAlert:
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def list_alerts(self, session_id: uuid.UUID) -> list[SatelliteAlert]:
        rows = (
            await self.session.execute(
                select(SatelliteAlert)
                .where(SatelliteAlert.session_id == session_id)
                .order_by(SatelliteAlert.created_at.asc())
            )
        ).scalars().all()
        return list(rows)

    async def sessions_with_alerts(
        self, user_id: uuid.UUID
    ) -> list[SatelliteSession]:
        """Recent sessions (with their alerts eager-loaded) for the notification
        source to surface satellite alerts."""
        rows = (
            await self.session.execute(
                self._owned(user_id)
                .order_by(SatelliteSession.created_at.desc())
                .limit(50)
            )
        ).scalars().unique().all()
        return list(rows)

    # ----------------------------------------------------------------- #
    # History
    # ----------------------------------------------------------------- #
    async def add_history(self, entry: SatelliteHistory) -> SatelliteHistory:
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
    ) -> tuple[list[SatelliteHistory], int]:
        base = select(SatelliteHistory).where(
            SatelliteHistory.user_id == user_id,
            SatelliteHistory.farm_id == farm_id,
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
                    base.order_by(SatelliteHistory.recorded_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def history_for_timeline(
        self, user_id: uuid.UUID, farm_id: uuid.UUID, *, limit: int = 365
    ) -> list[SatelliteHistory]:
        rows = (
            await self.session.execute(
                select(SatelliteHistory)
                .where(
                    SatelliteHistory.user_id == user_id,
                    SatelliteHistory.farm_id == farm_id,
                )
                .order_by(SatelliteHistory.recorded_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)
