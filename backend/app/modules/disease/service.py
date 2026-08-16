"""Disease report history service."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.disease.exceptions import DiseaseReportNotFoundError
from app.modules.disease.models import DiseaseReport
from app.modules.disease.repositories import DiseaseReportRepository


class DiseaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reports = DiseaseReportRepository(session)

    # ----- History -----
    async def list_reports(
        self,
        user: User,
        *,
        page: int,
        page_size: int,
        farm_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
        crop: str | None = None,
    ) -> tuple[list[DiseaseReport], int]:
        offset = (page - 1) * page_size
        items = await self.reports.list_for_user(
            user.id,
            limit=page_size,
            offset=offset,
            farm_id=farm_id,
            unassigned_only=unassigned_only,
            crop=crop,
        )
        total = await self.reports.count_for_user(
            user.id,
            farm_id=farm_id,
            unassigned_only=unassigned_only,
            crop=crop,
        )
        return items, total

    async def get_report(self, user: User, report_id: uuid.UUID) -> DiseaseReport:
        report = await self.reports.get_for_user(report_id, user.id)
        if report is None:
            raise DiseaseReportNotFoundError()
        return report

    async def delete_report(self, user: User, report_id: uuid.UUID) -> None:
        report = await self.get_report(user, report_id)
        report.is_deleted = True
        report.deleted_at = datetime.now(UTC)
        await self.session.flush()
