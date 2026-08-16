from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DiseaseRiskAlert


class DiseaseRiskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_key(self, user_id: uuid.UUID, key: str) -> DiseaseRiskAlert | None:
        return (
            await self.session.execute(
                select(DiseaseRiskAlert).where(
                    DiseaseRiskAlert.user_id == user_id, DiseaseRiskAlert.idempotency_key == key
                )
            )
        ).scalar_one_or_none()

    async def add(self, row: DiseaseRiskAlert) -> DiseaseRiskAlert:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get(self, user_id: uuid.UUID, risk_id: uuid.UUID) -> DiseaseRiskAlert | None:
        return (
            await self.session.execute(
                select(DiseaseRiskAlert).where(
                    DiseaseRiskAlert.id == risk_id, DiseaseRiskAlert.user_id == user_id
                )
            )
        ).scalar_one_or_none()

    async def latest(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> DiseaseRiskAlert | None:
        return (
            await self.session.execute(
                select(DiseaseRiskAlert)
                .where(DiseaseRiskAlert.user_id == user_id, DiseaseRiskAlert.farm_id == farm_id)
                .order_by(DiseaseRiskAlert.generated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def history(self, user_id: uuid.UUID, farm_id: uuid.UUID | None, limit: int, offset: int):
        where = [DiseaseRiskAlert.user_id == user_id]
        if farm_id:
            where.append(DiseaseRiskAlert.farm_id == farm_id)
        items = list(
            (
                await self.session.execute(
                    select(DiseaseRiskAlert)
                    .where(*where)
                    .order_by(DiseaseRiskAlert.generated_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).scalars()
        )
        total = (
            await self.session.execute(select(func.count(DiseaseRiskAlert.id)).where(*where))
        ).scalar_one()
        return items, total
