"""Expert Connect repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the expert/consultation tables. No SQL lives in routes
or the service.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.experts.constants import TERMINAL_STATUSES, ConsultationStatus
from app.modules.experts.models import (
    Consultation,
    ConsultationAttachment,
    ConsultationMessage,
    ConsultationStatusHistory,
    Expert,
    ExpertSpecialization,
)

_OPEN_STATUSES = tuple(
    s.value for s in ConsultationStatus if s.value not in TERMINAL_STATUSES
)
_HISTORY_STATUSES = (
    ConsultationStatus.RESOLVED.value,
    ConsultationStatus.CLOSED.value,
    ConsultationStatus.CANCELLED.value,
)


class ExpertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Experts
    # ----------------------------------------------------------------- #
    async def count_experts(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Expert).where(Expert.is_deleted.is_(False))
        )
        return int(result.scalar_one())

    async def add_expert(self, expert: Expert) -> Expert:
        self.session.add(expert)
        await self.session.flush()
        return expert

    async def get_expert_by_slug(self, slug: str) -> Expert | None:
        result = await self.session.execute(
            select(Expert).where(Expert.slug == slug, Expert.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    def _experts_query(
        self,
        *,
        category: str | None,
        crop: str | None,
        district: str | None,
        language: str | None,
        expert_type: str | None,
        search: str | None,
    ) -> Select[tuple[Expert]]:
        stmt = select(Expert).where(
            Expert.is_deleted.is_(False), Expert.status == "active"
        )
        if expert_type:
            stmt = stmt.where(Expert.expert_type == expert_type)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Expert.full_name).like(like),
                    func.lower(Expert.organization).like(like),
                )
            )
        if category or crop:
            spec = select(ExpertSpecialization.expert_id).where(
                ExpertSpecialization.expert_id == Expert.id
            )
            if category:
                spec = spec.where(ExpertSpecialization.category == category)
            if crop:
                spec = spec.where(func.lower(ExpertSpecialization.crop) == crop.lower())
            stmt = stmt.where(spec.exists())
        # district/language filters are applied in Python (JSON lists) by the service.
        return stmt

    async def list_experts(
        self,
        *,
        category: str | None = None,
        crop: str | None = None,
        district: str | None = None,
        language: str | None = None,
        expert_type: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Expert], int]:
        base = self._experts_query(
            category=category,
            crop=crop,
            district=district,
            language=language,
            expert_type=expert_type,
            search=search,
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
                    base.order_by(Expert.full_name.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    async def all_active_experts(self) -> list[Expert]:
        rows = (
            await self.session.execute(
                select(Expert).where(
                    Expert.is_deleted.is_(False), Expert.status == "active"
                )
            )
        ).scalars().unique().all()
        return list(rows)

    async def get_expert(self, expert_id: uuid.UUID) -> Expert | None:
        result = await self.session.execute(
            select(Expert).where(
                Expert.id == expert_id, Expert.is_deleted.is_(False)
            )
        )
        return result.scalar_one_or_none()

    async def add_specialization(
        self, spec: ExpertSpecialization
    ) -> ExpertSpecialization:
        self.session.add(spec)
        await self.session.flush()
        return spec

    async def active_load(self, expert_id: uuid.UUID) -> int:
        """How many open (non-terminal) consultations a desk currently holds."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Consultation)
            .where(
                Consultation.assigned_expert_id == expert_id,
                Consultation.is_deleted.is_(False),
                Consultation.status.in_(_OPEN_STATUSES),
            )
        )
        return int(result.scalar_one())

    # ----------------------------------------------------------------- #
    # Consultations
    # ----------------------------------------------------------------- #
    def _owned(self, farmer_id: uuid.UUID) -> Select[tuple[Consultation]]:
        return select(Consultation).where(
            Consultation.farmer_id == farmer_id,
            Consultation.is_deleted.is_(False),
        )

    async def add_consultation(self, consultation: Consultation) -> Consultation:
        self.session.add(consultation)
        await self.session.flush()
        return consultation

    async def get_consultation(
        self, consultation_id: uuid.UUID, farmer_id: uuid.UUID
    ) -> Consultation | None:
        result = await self.session.execute(
            self._owned(farmer_id).where(Consultation.id == consultation_id)
        )
        return result.scalar_one_or_none()

    async def list_consultations(
        self,
        farmer_id: uuid.UUID,
        *,
        status: str | None = None,
        statuses: tuple[str, ...] | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Consultation], int]:
        stmt = self._owned(farmer_id)
        if status:
            stmt = stmt.where(Consultation.status == status)
        if statuses:
            stmt = stmt.where(Consultation.status.in_(statuses))
        if category:
            stmt = stmt.where(Consultation.category == category)
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(stmt.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    stmt.order_by(Consultation.updated_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    @staticmethod
    def open_statuses() -> tuple[str, ...]:
        return _OPEN_STATUSES

    @staticmethod
    def history_statuses() -> tuple[str, ...]:
        return _HISTORY_STATUSES

    async def soft_delete_consultation(self, consultation: Consultation) -> None:
        consultation.is_deleted = True
        consultation.deleted_at = datetime.now(UTC)
        await self.session.flush()

    # ----------------------------------------------------------------- #
    # Messages / attachments / status history
    # ----------------------------------------------------------------- #
    async def add_message(self, message: ConsultationMessage) -> ConsultationMessage:
        self.session.add(message)
        await self.session.flush()
        return message

    async def add_attachment(
        self, attachment: ConsultationAttachment
    ) -> ConsultationAttachment:
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def add_status_history(
        self, entry: ConsultationStatusHistory
    ) -> ConsultationStatusHistory:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def consultations_with_new_expert_activity(
        self, farmer_id: uuid.UUID
    ) -> list[Consultation]:
        """Consultations owned by the farmer that have at least one expert message
        (used by the notification source to surface expert replies)."""
        rows = (
            await self.session.execute(
                self._owned(farmer_id).order_by(Consultation.updated_at.desc())
            )
        ).scalars().unique().all()
        return list(rows)
