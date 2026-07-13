"""Expert Connect service (docs: Repository → Service → Expert Engine → Provider).

Orchestrates the consultation platform: seeds the verified expert desk network,
lists/reads experts, and runs the full consultation lifecycle — create → assign
(deterministic engine) → acknowledge (provider system message) → farmer replies →
status changes → resolved. The conversation is immutable (messages are only ever
appended) and every status change is logged. Business logic lives here; routes
stay thin. Farmer data is never modified by experts.
"""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.auth.repositories import FarmerProfileRepository
from app.modules.experts.constants import (
    DEFAULT_LANGUAGE,
    FARMER_REPLY_STATUS_MAP,
    TERMINAL_STATUSES,
    ConsultationChannel,
    ConsultationStatus,
    SenderType,
)
from app.modules.experts.engine import (
    AssignmentResult,
    ConsultationContext,
    ExpertCandidate,
    assign_expert,
    can_transition,
    farmer_can_set,
)
from app.modules.experts.exceptions import (
    ConsultationClosedError,
    ConsultationNotFoundError,
    ExpertNotFoundError,
    FarmNotOwnedError,
    InvalidStatusTransitionError,
)
from app.modules.experts.models import (
    Consultation,
    ConsultationAttachment,
    ConsultationMessage,
    ConsultationStatusHistory,
    Expert,
    ExpertSpecialization,
)
from app.modules.experts.provider import (
    AssignmentRef,
    ExpertProvider,
    SeedExpert,
    get_default_provider,
)
from app.modules.experts.repository import ExpertRepository
from app.modules.experts.schemas import (
    AttachmentIn,
    ConsultationCreate,
    ConsultationListFilters,
    ExpertListFilters,
    ReplyIn,
    StatusUpdateIn,
)
from app.modules.farms.repositories import FarmRepository
from app.schemas.response import PaginatedData

logger = get_logger("experts.service")


class ExpertService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: ExpertProvider | None = None,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.repo = ExpertRepository(session)
        self.farms = FarmRepository(session)
        self.profiles = FarmerProfileRepository(session)
        self.provider = provider or get_default_provider()
        self._now = now

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    # ----------------------------------------------------------------- #
    # Seeding (verified desks — idempotent by slug)
    # ----------------------------------------------------------------- #
    async def ensure_seeded(self) -> None:
        if await self.repo.count_experts() > 0:
            return
        for seed in await self.provider.fetch_experts():
            await self._seed_expert(seed)
        logger.info("seeded verified expert desks")

    async def _seed_expert(self, seed: SeedExpert) -> Expert:
        existing = await self.repo.get_expert_by_slug(seed.slug)
        if existing is not None:
            return existing
        expert = Expert(
            full_name=seed.full_name,
            expert_type=seed.expert_type,
            organization=seed.organization,
            title=seed.title,
            bio=seed.bio,
            districts=list(seed.districts),
            languages=list(seed.languages),
            verified=True,
            status="active",
            slug=seed.slug,
            source=seed.source,
            contact=seed.contact,
        )
        await self.repo.add_expert(expert)
        for category in seed.categories:
            await self.repo.add_specialization(
                ExpertSpecialization(expert_id=expert.id, category=category, crop=None)
            )
        for crop in seed.crops:
            await self.repo.add_specialization(
                ExpertSpecialization(
                    expert_id=expert.id, category=seed.categories[0], crop=crop
                )
            )
        await self.session.flush()
        await self.session.refresh(expert)
        return expert

    # ----------------------------------------------------------------- #
    # Experts (reads)
    # ----------------------------------------------------------------- #
    @staticmethod
    def _matches_coverage(
        expert: Expert, *, district: str | None, language: str | None
    ) -> bool:
        if district:
            districts = [d.lower() for d in (expert.districts or [])]
            # An empty district list = statewide/generalist desk → always matches.
            if districts and district.lower() not in districts:
                return False
        if language:
            languages = [lang.lower() for lang in (expert.languages or [])]
            if languages and language.lower() not in languages:
                return False
        return True

    async def list_experts(
        self, filters: ExpertListFilters
    ) -> PaginatedData[Expert]:
        await self.ensure_seeded()
        offset = (filters.page - 1) * filters.page_size
        # Over-fetch so Python-side JSON coverage filtering can still paginate.
        rows, _total = await self.repo.list_experts(
            category=filters.category.value if filters.category else None,
            crop=filters.crop,
            expert_type=filters.expert_type.value if filters.expert_type else None,
            search=filters.search,
            limit=1000,
            offset=0,
        )
        filtered = [
            e
            for e in rows
            if self._matches_coverage(
                e, district=filters.district, language=filters.language
            )
        ]
        total = len(filtered)
        page_rows = filtered[offset : offset + filters.page_size]
        total_pages = (
            (total + filters.page_size - 1) // filters.page_size if total else 0
        )
        return PaginatedData(
            items=page_rows,
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_expert(self, expert_id: uuid.UUID) -> Expert:
        await self.ensure_seeded()
        expert = await self.repo.get_expert(expert_id)
        if expert is None:
            raise ExpertNotFoundError()
        return expert

    # ----------------------------------------------------------------- #
    # Consultation context + assignment
    # ----------------------------------------------------------------- #
    async def _build_context(
        self, user: User, data: ConsultationCreate
    ) -> tuple[ConsultationContext, str]:
        district: str | None = None
        if data.farm_id is not None:
            farm = await self.farms.get_for_user(data.farm_id, user.id)
            if farm is None:
                raise FarmNotOwnedError()
            district = farm.location.district if farm.location else None
        profile = await self.profiles.get_by_user_id(user.id)
        if district is None and profile is not None:
            district = profile.district
        language = (
            data.language
            or (profile.language if profile else None)
            or DEFAULT_LANGUAGE
        )
        return (
            ConsultationContext(
                category=data.category.value,
                crop=data.crop,
                district=district,
                language=language,
            ),
            language,
        )

    async def _candidate(self, expert: Expert) -> ExpertCandidate:
        return ExpertCandidate(
            id=str(expert.id),
            categories=frozenset(s.category for s in (expert.specializations or [])),
            crops=frozenset(
                s.crop for s in (expert.specializations or []) if s.crop
            ),
            districts=frozenset(expert.districts or []),
            languages=frozenset(expert.languages or []),
            verified=expert.verified,
            is_available=expert.status == "active",
            is_generalist=not expert.districts,
            rating=expert.rating,
            active_load=await self.repo.active_load(expert.id),
        )

    async def _assign(
        self, context: ConsultationContext, preferred_expert_id: uuid.UUID | None
    ) -> tuple[Expert | None, AssignmentResult]:
        experts = await self.repo.all_active_experts()
        by_id = {str(e.id): e for e in experts}

        if preferred_expert_id is not None and str(preferred_expert_id) in by_id:
            chosen = by_id[str(preferred_expert_id)]
            return chosen, AssignmentResult(
                expert_id=str(chosen.id), score=0, reasons=("preferred",)
            )

        candidates = [await self._candidate(e) for e in experts]
        result = assign_expert(candidates, context)
        expert = by_id.get(result.expert_id) if result.expert_id else None
        return expert, result

    # ----------------------------------------------------------------- #
    # Create
    # ----------------------------------------------------------------- #
    async def create_consultation(
        self, user: User, data: ConsultationCreate
    ) -> Consultation:
        await self.ensure_seeded()
        context, language = await self._build_context(user, data)

        consultation = Consultation(
            farmer_id=user.id,
            farm_id=data.farm_id,
            category=data.category.value,
            crop=data.crop,
            subject=data.subject,
            description=data.description,
            priority=data.priority.value,
            status=ConsultationStatus.SUBMITTED.value,
            channel=ConsultationChannel.IN_APP.value,
            language=language,
        )
        await self.repo.add_consultation(consultation)
        await self._record_status(
            consultation, old=None, new=ConsultationStatus.SUBMITTED.value,
            by_type=SenderType.FARMER.value, by_id=user.id, note="Consultation created",
        )

        # The farmer's opening message is the description; attachments hang off it.
        opening = await self._add_message(
            consultation,
            sender_type=SenderType.FARMER.value,
            sender_user_id=user.id,
            body=data.description,
            language=language,
        )
        for attachment in data.attachments:
            await self._attach(consultation, attachment, message_id=opening.id, by=user.id)

        # Deterministic assignment to a verified desk.
        expert, _result = await self._assign(context, data.preferred_expert_id)
        if expert is not None:
            consultation.assigned_expert_id = expert.id
            consultation.assigned_at = self._now_dt()
            await self._change_status_internal(
                consultation,
                new=ConsultationStatus.ASSIGNED.value,
                by_type=SenderType.SYSTEM.value,
                by_id=None,
                note=f"Assigned to {expert.full_name}",
            )
            ack = await self.provider.acknowledge(
                AssignmentRef(
                    consultation_id=str(consultation.id),
                    category=consultation.category,
                    crop=consultation.crop,
                    subject=consultation.subject,
                    expert_name=expert.full_name,
                )
            )
            await self._add_message(
                consultation,
                sender_type=SenderType.SYSTEM.value,
                sender_expert_id=expert.id,
                body=ack.message,
                language=language,
                is_system=True,
            )
            consultation.channel = ack.channel

        await self.session.flush()
        await self.session.refresh(consultation)
        return consultation

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def _require(self, user: User, consultation_id: uuid.UUID) -> Consultation:
        consultation = await self.repo.get_consultation(consultation_id, user.id)
        if consultation is None:
            raise ConsultationNotFoundError()
        return consultation

    async def list_consultations(
        self, user: User, filters: ConsultationListFilters
    ) -> PaginatedData[Consultation]:
        offset = (filters.page - 1) * filters.page_size
        rows, total = await self.repo.list_consultations(
            user.id,
            status=filters.status.value if filters.status else None,
            category=filters.category.value if filters.category else None,
            limit=filters.page_size,
            offset=offset,
        )
        return self._page(rows, total, filters.page, filters.page_size)

    async def pending(
        self, user: User, *, page: int, page_size: int
    ) -> PaginatedData[Consultation]:
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_consultations(
            user.id, statuses=self.repo.open_statuses(), limit=page_size, offset=offset
        )
        return self._page(rows, total, page, page_size)

    async def history(
        self, user: User, *, page: int, page_size: int
    ) -> PaginatedData[Consultation]:
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_consultations(
            user.id, statuses=self.repo.history_statuses(), limit=page_size, offset=offset
        )
        return self._page(rows, total, page, page_size)

    @staticmethod
    def _page(
        rows: list[Consultation], total: int, page: int, page_size: int
    ) -> PaginatedData[Consultation]:
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows, page=page, page_size=page_size, total=total,
            total_pages=total_pages,
        )

    async def get_consultation(
        self, user: User, consultation_id: uuid.UUID
    ) -> Consultation:
        return await self._require(user, consultation_id)

    # ----------------------------------------------------------------- #
    # Reply / attachments / status
    # ----------------------------------------------------------------- #
    async def reply(
        self, user: User, consultation_id: uuid.UUID, data: ReplyIn
    ) -> Consultation:
        consultation = await self._require(user, consultation_id)
        if consultation.status in {
            ConsultationStatus.CANCELLED.value, ConsultationStatus.CLOSED.value
        }:
            raise ConsultationClosedError()

        message = await self._add_message(
            consultation,
            sender_type=SenderType.FARMER.value,
            sender_user_id=user.id,
            body=data.body,
            language=consultation.language,
        )
        for attachment in data.attachments:
            await self._attach(
                consultation, attachment, message_id=message.id, by=user.id
            )

        # A farmer reply moves the thread to the expert (or reopens a resolved one).
        if consultation.status == ConsultationStatus.RESOLVED.value:
            await self._change_status_internal(
                consultation, new=ConsultationStatus.IN_PROGRESS.value,
                by_type=SenderType.FARMER.value, by_id=user.id, note="Reopened by farmer",
            )
        else:
            mapped = FARMER_REPLY_STATUS_MAP.get(consultation.status)
            if mapped:
                await self._change_status_internal(
                    consultation, new=mapped, by_type=SenderType.FARMER.value,
                    by_id=user.id, note=None,
                )

        await self.session.flush()
        await self.session.refresh(consultation)
        return consultation

    async def add_attachment(
        self, user: User, consultation_id: uuid.UUID, attachment: AttachmentIn
    ) -> Consultation:
        consultation = await self._require(user, consultation_id)
        if consultation.status in {
            ConsultationStatus.CANCELLED.value, ConsultationStatus.CLOSED.value
        }:
            raise ConsultationClosedError()
        await self._attach(consultation, attachment, message_id=None, by=user.id)
        await self.session.flush()
        await self.session.refresh(consultation)
        return consultation

    async def update_status(
        self, user: User, consultation_id: uuid.UUID, data: StatusUpdateIn
    ) -> Consultation:
        consultation = await self._require(user, consultation_id)
        new = data.status.value
        if new == consultation.status:
            return consultation
        if not farmer_can_set(new):
            raise InvalidStatusTransitionError(
                "A farmer can only resolve or cancel a consultation."
            )
        if not can_transition(consultation.status, new):
            raise InvalidStatusTransitionError(
                f"Cannot move from '{consultation.status}' to '{new}'."
            )
        if new == ConsultationStatus.RESOLVED.value and data.note:
            consultation.resolution_note = data.note
        await self._change_status_internal(
            consultation, new=new, by_type=SenderType.FARMER.value,
            by_id=user.id, note=data.note,
        )
        await self.session.flush()
        await self.session.refresh(consultation)
        return consultation

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #
    async def _add_message(
        self,
        consultation: Consultation,
        *,
        sender_type: str,
        body: str,
        language: str,
        sender_user_id: uuid.UUID | None = None,
        sender_expert_id: uuid.UUID | None = None,
        is_system: bool = False,
    ) -> ConsultationMessage:
        message = await self.repo.add_message(
            ConsultationMessage(
                consultation_id=consultation.id,
                sender_type=sender_type,
                sender_user_id=sender_user_id,
                sender_expert_id=sender_expert_id,
                body=body,
                language=language,
                is_system=is_system,
            )
        )
        consultation.last_message_at = self._now_dt()
        return message

    async def _attach(
        self,
        consultation: Consultation,
        attachment: AttachmentIn,
        *,
        message_id: uuid.UUID | None,
        by: uuid.UUID,
    ) -> ConsultationAttachment:
        return await self.repo.add_attachment(
            ConsultationAttachment(
                consultation_id=consultation.id,
                message_id=message_id,
                uploaded_by=by,
                kind=attachment.kind.value,
                file_url=attachment.file_url,
                thumbnail_url=attachment.thumbnail_url,
                mime_type=attachment.mime_type,
                file_size=attachment.file_size,
                caption=attachment.caption,
            )
        )

    async def _record_status(
        self,
        consultation: Consultation,
        *,
        old: str | None,
        new: str,
        by_type: str,
        by_id: uuid.UUID | None,
        note: str | None,
    ) -> None:
        await self.repo.add_status_history(
            ConsultationStatusHistory(
                consultation_id=consultation.id,
                old_status=old,
                new_status=new,
                changed_by_type=by_type,
                changed_by_id=by_id,
                note=note,
            )
        )

    async def _change_status_internal(
        self,
        consultation: Consultation,
        *,
        new: str,
        by_type: str,
        by_id: uuid.UUID | None,
        note: str | None,
    ) -> None:
        old = consultation.status
        consultation.status = new
        if new == ConsultationStatus.RESOLVED.value:
            consultation.resolved_at = self._now_dt()
        await self._record_status(
            consultation, old=old, new=new, by_type=by_type, by_id=by_id, note=note
        )

    @staticmethod
    def slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @staticmethod
    def is_terminal(status: str) -> bool:
        return status in TERMINAL_STATUSES
