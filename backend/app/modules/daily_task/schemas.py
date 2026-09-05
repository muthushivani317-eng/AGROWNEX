"""Pydantic v2 schemas for the Daily Task advisory layer.

Farmer-facing schemas (TaskCardPublic, TaskHistoryItem, ...) have no field
capable of carrying a raw index value or technical term -- by construction,
not by convention. Internal/advanced schemas (EvidenceSignal,
TaskAdvancedView) carry the full technical payload for the opt-in advanced
view only.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.daily_task.constants import (
    Confidence,
    EvidencePackConfidence,
    EvidencePackStatus,
    ResponseType,
    Severity,
    SignalStatus,
    SignalType,
    SourceModule,
    TaskStatus,
    TaskType,
    Urgency,
)


class EvidenceSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    farmer_id: uuid.UUID
    field_id: uuid.UUID
    signal_type: SignalType
    source_module: SourceModule
    observed_at: datetime
    valid_until: datetime
    confidence: Confidence
    severity: Severity
    urgency: Urgency
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_technical: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: dict[str, str] = Field(default_factory=dict)
    policy_flags: list[str] = Field(default_factory=list)
    recommended_task_type: TaskType
    dedupe_key: str
    status: SignalStatus = SignalStatus.CANDIDATE


class TaskCardPublic(BaseModel):
    id: uuid.UUID
    task_type: TaskType
    rank_position: Literal[1, 2]
    title_ta: str
    task_text_ta: str
    reason_text_ta: str
    why_am_i_seeing_this_ta: str
    field_label: str | None
    urgency: Urgency
    status: TaskStatus
    valid_until: datetime
    created_at: datetime
    can_upload_photo: bool = True
    can_record_voice_note: bool = True
    response_options: list[ResponseType] = Field(
        default_factory=lambda: [
            ResponseType.DONE,
            ResponseType.PROBLEM_FOUND,
            ResponseType.NO_ISSUE,
            ResponseType.NEED_HELP,
        ]
    )


class TodayTasksResponse(BaseModel):
    tasks: list[TaskCardPublic] = Field(max_length=2)
    generated_at: datetime


class TaskHistoryItem(BaseModel):
    id: uuid.UUID
    task_type: TaskType
    title_ta: str
    task_text_ta: str
    field_label: str | None
    status: TaskStatus
    created_at: datetime
    final_response: ResponseType | None


class TaskHistoryResponse(BaseModel):
    items: list[TaskHistoryItem]
    next_cursor: str | None = None


class TaskRespondRequest(BaseModel):
    response_type: ResponseType
    note_text: str | None = Field(default=None, max_length=500)


class TaskRespondResponse(BaseModel):
    task_id: uuid.UUID
    status: TaskStatus
    follow_up_prompt: Literal["photo_voice_optional", "photo_voice_encouraged", "none"]
    escalated: bool


class TaskSnoozeRequest(BaseModel):
    snooze_until: Literal["later_today", "tomorrow_morning"]


class TaskPhotoUploadResponse(BaseModel):
    task_id: uuid.UUID
    photo_object_id: str
    total_photos_on_task: int


class TaskVoiceNoteUploadResponse(BaseModel):
    task_id: uuid.UUID
    voice_note_object_id: str
    duration_seconds: float


class TaskAdvancedView(BaseModel):
    task: TaskCardPublic
    signal: EvidenceSignal
    data_freshness_hours: float
    merged_signal_ids: list[uuid.UUID]
    rank_score: float | None
    audit_trail: list[dict[str, Any]]


class EvidencePackTriggerRequest(BaseModel):
    field_id: uuid.UUID
    event_type: Literal["heavy_rain", "cyclone", "drought", "farmer_reported"]
    event_date_start: datetime
    event_date_end: datetime | None = None
    farmer_note: str | None = Field(default=None, max_length=500)


class EvidencePackContent(BaseModel):
    farmer_name: str
    farm_id: uuid.UUID
    field_polygon_geojson: dict[str, Any] | None
    event_type: str
    event_date_start: datetime
    event_date_end: datetime | None
    pre_event_scan_date: datetime | None
    post_event_scan_date: datetime | None
    pre_event_trend_summary_ta: str
    post_event_trend_summary_ta: str
    standing_water_note_ta: str | None = Field(
        default=None,
        description="Cautious wording only -- e.g. 'a possible standing-water "
        "change was detected'. Never a flood confirmation.",
    )
    weather_context_ta: str
    farmer_photo_object_ids: list[str] = Field(default_factory=list)
    farmer_voice_note_object_ids: list[str] = Field(default_factory=list)
    confidence_level: EvidencePackConfidence
    disclaimer_ta: str = (
        "இந்த அறிக்கை வயல் சான்று ஆதரவுக்காக மட்டுமே. இது இறுதி வெள்ள மதிப்பீடு, "
        "காப்பீட்டு முடிவு அல்லது இழப்பீடு உத்தரவாதம் அல்ல."
    )
    disclaimer_en: str = (
        "This report is supporting field evidence. It is not a final flood "
        "assessment, insurance decision, or compensation guarantee."
    )


class EvidencePackPublic(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    event_type: str
    status: EvidencePackStatus
    confidence_level: EvidencePackConfidence
    has_pre_event_imagery: bool
    has_post_event_imagery: bool
    imagery_degraded_reason: str | None
    content: EvidencePackContent
    pdf_download_url: str | None
    version: int
    created_at: datetime


class EvidencePackShareRequest(BaseModel):
    share_with: Literal["fpo", "self_download", "external"]
    fpo_contact_id: uuid.UUID | None = None
