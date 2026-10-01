"""Expert Connect request/response schemas (docs: reuse response envelope)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.experts.constants import (
    AttachmentKind,
    ConsultationCategory,
    ConsultationPriority,
    ConsultationStatus,
    ExpertType,
)
from app.modules.experts.models import (
    Consultation,
    ConsultationAttachment,
    ConsultationMessage,
    Expert,
)
from app.shared.url_safety import HttpsUrl


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class AttachmentIn(BaseModel):
    file_url: HttpsUrl = Field(min_length=1, max_length=512)
    thumbnail_url: HttpsUrl | None = Field(default=None, max_length=512)
    mime_type: str | None = Field(default=None, max_length=80)
    file_size: int | None = Field(default=None, ge=0)
    caption: str | None = Field(default=None, max_length=255)
    kind: AttachmentKind = AttachmentKind.IMAGE


class ConsultationCreate(BaseModel):
    farm_id: uuid.UUID | None = None
    category: ConsultationCategory = ConsultationCategory.GENERAL
    crop: str | None = Field(default=None, max_length=80)
    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    priority: ConsultationPriority = ConsultationPriority.MEDIUM
    language: str | None = Field(default=None, min_length=2, max_length=8)
    preferred_expert_id: uuid.UUID | None = None
    attachments: list[AttachmentIn] = Field(default_factory=list)


class ReplyIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    attachments: list[AttachmentIn] = Field(default_factory=list)


class StatusUpdateIn(BaseModel):
    status: ConsultationStatus
    note: str | None = Field(default=None, max_length=255)


class ConsultationListFilters(BaseModel):
    status: ConsultationStatus | None = None
    category: ConsultationCategory | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ExpertListFilters(BaseModel):
    category: ConsultationCategory | None = None
    crop: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=8)
    expert_type: ExpertType | None = None
    search: str | None = Field(default=None, max_length=120)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class ExpertSpecializationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    crop: str | None


class ExpertAvailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_of_week: int | None
    start_time: str | None
    end_time: str | None
    timezone: str
    is_available: bool


class ExpertSummaryOut(BaseModel):
    id: uuid.UUID
    full_name: str
    expert_type: str
    organization: str | None
    title: str | None
    photo_url: str | None
    districts: list[str]
    languages: list[str]
    years_experience: int | None
    rating: float | None
    rating_count: int
    verified: bool
    categories: list[str]

    @classmethod
    def from_expert(cls, expert: Expert) -> ExpertSummaryOut:
        return cls(
            id=expert.id,
            full_name=expert.full_name,
            expert_type=expert.expert_type,
            organization=expert.organization,
            title=expert.title,
            photo_url=expert.photo_url,
            districts=list(expert.districts or []),
            languages=list(expert.languages or []),
            years_experience=expert.years_experience,
            rating=expert.rating,
            rating_count=expert.rating_count,
            verified=expert.verified,
            categories=sorted({s.category for s in (expert.specializations or [])}),
        )


class ExpertDetailOut(ExpertSummaryOut):
    bio: str | None
    source: str | None
    contact: str | None
    specializations: list[ExpertSpecializationOut]
    availability: list[ExpertAvailabilityOut]

    @classmethod
    def from_expert_detail(cls, expert: Expert) -> ExpertDetailOut:
        base = ExpertSummaryOut.from_expert(expert)
        return cls(
            **base.model_dump(),
            bio=expert.bio,
            source=expert.source,
            contact=expert.contact,
            specializations=[
                ExpertSpecializationOut.model_validate(s)
                for s in (expert.specializations or [])
            ],
            availability=[
                ExpertAvailabilityOut.model_validate(a)
                for a in (expert.availability or [])
            ],
        )


class ConsultationAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID | None
    kind: str
    file_url: str
    thumbnail_url: str | None
    mime_type: str | None
    caption: str | None
    created_at: datetime


class ConsultationMessageOut(BaseModel):
    id: uuid.UUID
    sender_type: str
    sender_expert_id: uuid.UUID | None
    body: str
    language: str
    is_system: bool
    created_at: datetime
    attachments: list[ConsultationAttachmentOut] = Field(default_factory=list)

    @classmethod
    def from_message(
        cls,
        message: ConsultationMessage,
        attachments: list[ConsultationAttachment] | None = None,
    ) -> ConsultationMessageOut:
        return cls(
            id=message.id,
            sender_type=message.sender_type,
            sender_expert_id=message.sender_expert_id,
            body=message.body,
            language=message.language,
            is_system=message.is_system,
            created_at=message.created_at,
            attachments=[
                ConsultationAttachmentOut.model_validate(a) for a in (attachments or [])
            ],
        )


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    old_status: str | None
    new_status: str
    changed_by_type: str
    note: str | None
    created_at: datetime


class ConsultationSummaryOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID | None
    category: str
    crop: str | None
    subject: str
    priority: str
    status: str
    channel: str
    assigned_expert_id: uuid.UUID | None
    expert: ExpertSummaryOut | None
    attachment_count: int
    message_count: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_consultation(cls, c: Consultation) -> ConsultationSummaryOut:
        return cls(
            id=c.id,
            farm_id=c.farm_id,
            category=c.category,
            crop=c.crop,
            subject=c.subject,
            priority=c.priority,
            status=c.status,
            channel=c.channel,
            assigned_expert_id=c.assigned_expert_id,
            expert=ExpertSummaryOut.from_expert(c.expert) if c.expert else None,
            attachment_count=len(c.attachments or []),
            message_count=len(c.messages or []),
            last_message_at=c.last_message_at,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class ConsultationDetailOut(ConsultationSummaryOut):
    description: str
    language: str
    resolution_note: str | None
    assigned_at: datetime | None
    resolved_at: datetime | None
    messages: list[ConsultationMessageOut]
    attachments: list[ConsultationAttachmentOut]
    status_history: list[StatusHistoryOut]

    @classmethod
    def from_consultation_detail(cls, c: Consultation) -> ConsultationDetailOut:
        base = ConsultationSummaryOut.from_consultation(c)
        by_message: dict[uuid.UUID, list[ConsultationAttachment]] = {}
        loose: list[ConsultationAttachment] = []
        for att in c.attachments or []:
            if att.message_id is not None:
                by_message.setdefault(att.message_id, []).append(att)
            else:
                loose.append(att)
        return cls(
            **base.model_dump(),
            description=c.description,
            language=c.language,
            resolution_note=c.resolution_note,
            assigned_at=c.assigned_at,
            resolved_at=c.resolved_at,
            messages=[
                ConsultationMessageOut.from_message(m, by_message.get(m.id, []))
                for m in (c.messages or [])
            ],
            attachments=[
                ConsultationAttachmentOut.model_validate(a) for a in (c.attachments or [])
            ],
            status_history=[
                StatusHistoryOut.model_validate(h) for h in (c.status_history or [])
            ],
        )
