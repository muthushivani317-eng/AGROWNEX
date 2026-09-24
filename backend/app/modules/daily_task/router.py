"""FastAPI routes -- Layer 4 (farmer-facing) + Evidence Pack. Mounted in
`app/api/v1/router.py` as `daily_task_router` (prefix "/tasks") and
`evidence_pack_router` (prefix "/evidence-packs"), following the existing
per-module router pattern (see `app/modules/market/router.py`). Every
response uses the app-wide envelope (`app.schemas.response`).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, UploadFile, status

from app.modules.daily_task.constants import MAX_TASKS_PER_FARMER_PER_DAY, ResponseType
from app.modules.daily_task.dependencies import (
    CurrentUser,
    DailyTaskRepositoryDep,
    DailyTaskServiceDep,
    EvidencePackServiceDep,
    ObjectStorageDep,
)
from app.modules.daily_task.exceptions import EvidencePackNotFoundError, TaskNotFoundError
from app.modules.daily_task.schemas import (
    EvidencePackContent,
    EvidencePackPublic,
    EvidencePackShareRequest,
    EvidencePackTriggerRequest,
    EvidenceSignal,
    TaskAdvancedView,
    TaskCardPublic,
    TaskHistoryItem,
    TaskHistoryResponse,
    TaskPhotoUploadResponse,
    TaskRespondRequest,
    TaskRespondResponse,
    TaskSnoozeRequest,
    TaskVoiceNoteUploadResponse,
    TodayTasksResponse,
)
from app.modules.disease.storage import StorageError, StorageUnavailableError
from app.modules.farms.dependencies import FarmServiceDep
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/tasks", tags=["daily-task"])
evidence_pack_router = APIRouter(prefix="/evidence-packs", tags=["evidence-pack"])

MAX_VOICE_NOTE_SECONDS = 12  # 10s target + small tolerance for client-side rounding


# --------------------------------------------------------------------------- #
# Farmer-facing task endpoints
# --------------------------------------------------------------------------- #
@router.get("/today", response_model=SuccessResponse[TodayTasksResponse])
async def get_today_tasks(current_user: CurrentUser, repo: DailyTaskRepositoryDep):
    """`TodayTasksResponse.tasks` is capped at `MAX_TASKS_PER_FARMER_PER_DAY`
    (the PRD's "at most two tasks a day" rule -- see
    `daily_task/constants.py`). Generation already enforces this per run
    (`ranking_engine.py`), but ACTIVE rows can still exceed the cap when
    older tasks outlive their `valid_until` window without a farmer
    response (see AGROWAI-BACKEND-2 / Sentry) -- so the read path re-applies
    the same cap defensively instead of 500ing on `TodayTasksResponse`'s
    validation. `tasks` is already ordered by `rank_position`, so slicing
    keeps the highest-priority tasks, matching what generation would have
    shown."""
    tasks = await repo.get_active_tasks_for_user(current_user.id)
    shown = tasks[:MAX_TASKS_PER_FARMER_PER_DAY]
    data = TodayTasksResponse(
        tasks=[_to_public(t) for t in shown],
        generated_at=shown[0].created_at if shown else _now(),
    )
    return success(data)


@router.get("/history", response_model=SuccessResponse[TaskHistoryResponse])
async def get_task_history(
    current_user: CurrentUser,
    repo: DailyTaskRepositoryDep,
    cursor: str | None = Query(default=None),
):
    before = _decode_cursor(cursor)
    items = await repo.get_history_for_user(current_user.id, before=before)
    data = TaskHistoryResponse(
        items=[TaskHistoryItem(**_history_item_fields(t, await repo.get_final_response(t.id))) for t in items],
        next_cursor=_encode_cursor(items[-1].created_at) if len(items) == 20 else None,
    )
    return success(data)


@router.get("/{task_id}", response_model=SuccessResponse[TaskCardPublic])
async def get_task(task_id: uuid.UUID, current_user: CurrentUser, repo: DailyTaskRepositoryDep):
    task = await _owned_task(repo, task_id, current_user.id)
    return success(_to_public(task))


@router.get("/{task_id}/advanced", response_model=SuccessResponse[TaskAdvancedView])
async def get_task_advanced_view(task_id: uuid.UUID, current_user: CurrentUser, repo: DailyTaskRepositoryDep):
    """Advanced/technical view -- opt-in only. Never fetched by the default
    mobile task card; a separate, explicit "Show technical view" tap is
    required client-side.
    """
    task = await _owned_task(repo, task_id, current_user.id)
    signal = await repo.get_signal(task.signal_id)
    audit = await repo.get_audit_entries_for_signal(task.signal_id)
    data = TaskAdvancedView(
        task=_to_public(task),
        signal=_signal_to_schema(signal),
        data_freshness_hours=(_now() - signal.observed_at).total_seconds() / 3600,
        merged_signal_ids=[uuid.UUID(s) for s in task.merged_signal_ids],
        rank_score=signal.rank_score,
        audit_trail=audit,
    )
    return success(data)


@router.post("/{task_id}/respond", response_model=SuccessResponse[TaskRespondResponse])
async def respond_to_task(
    task_id: uuid.UUID,
    body: TaskRespondRequest,
    current_user: CurrentUser,
    service: DailyTaskServiceDep,
    repo: DailyTaskRepositoryDep,
):
    await _owned_task(repo, task_id, current_user.id)
    data = await service.respond_to_task(task_id, body)
    return success(data)


@router.post("/{task_id}/snooze", response_model=SuccessResponse[None], status_code=status.HTTP_200_OK)
async def snooze_task(
    task_id: uuid.UUID,
    body: TaskSnoozeRequest,
    current_user: CurrentUser,
    service: DailyTaskServiceDep,
    repo: DailyTaskRepositoryDep,
):
    await _owned_task(repo, task_id, current_user.id)
    await service.snooze_task(task_id, body.snooze_until)
    return success(None, message="Snoozed")


@router.post("/{task_id}/photo", response_model=SuccessResponse[TaskPhotoUploadResponse])
async def upload_task_photo(
    task_id: uuid.UUID,
    file: UploadFile,
    current_user: CurrentUser,
    repo: DailyTaskRepositoryDep,
    storage: ObjectStorageDep,
):
    await _owned_task(repo, task_id, current_user.id)
    try:
        object_url = await storage.put(
            key=f"daily_task/{task_id}/{uuid.uuid4().hex}.jpg",
            data=await file.read(),
            content_type=file.content_type or "image/jpeg",
        )
    except (StorageError, StorageUnavailableError) as exc:
        raise StorageUnavailableError(
            "Photo storage temporarily unavailable. Your response was still saved."
        ) from exc
    responses = await repo.get_responses(task_id)
    latest = responses[-1] if responses else await repo.add_response(
        task_id=task_id, response_type=ResponseType.PROBLEM_FOUND.value
    )
    await repo.append_photo_to_response(latest.id, object_url)
    data = TaskPhotoUploadResponse(
        task_id=task_id, photo_object_id=object_url, total_photos_on_task=len(latest.photo_object_ids) + 1
    )
    return success(data)


@router.post("/{task_id}/voice-note", response_model=SuccessResponse[TaskVoiceNoteUploadResponse])
async def upload_task_voice_note(
    task_id: uuid.UUID,
    file: UploadFile,
    duration_seconds: float,
    current_user: CurrentUser,
    repo: DailyTaskRepositoryDep,
    storage: ObjectStorageDep,
):
    from app.core.exceptions import ValidationError

    await _owned_task(repo, task_id, current_user.id)
    if duration_seconds > MAX_VOICE_NOTE_SECONDS:
        raise ValidationError(f"Voice note exceeds {MAX_VOICE_NOTE_SECONDS}s cap")
    try:
        object_url = await storage.put(
            key=f"daily_task/{task_id}/voice/{uuid.uuid4().hex}.m4a",
            data=await file.read(),
            content_type=file.content_type or "audio/m4a",
        )
    except (StorageError, StorageUnavailableError) as exc:
        raise StorageUnavailableError(
            "Voice note storage temporarily unavailable. Your response was still saved."
        ) from exc
    responses = await repo.get_responses(task_id)
    latest = responses[-1] if responses else await repo.add_response(
        task_id=task_id, response_type=ResponseType.PROBLEM_FOUND.value
    )
    await repo.set_voice_note_on_response(latest.id, object_url)
    data = TaskVoiceNoteUploadResponse(
        task_id=task_id, voice_note_object_id=object_url, duration_seconds=duration_seconds
    )
    return success(data)


# --------------------------------------------------------------------------- #
# Evidence pack endpoints
# --------------------------------------------------------------------------- #
@evidence_pack_router.post(
    "", response_model=SuccessResponse[EvidencePackPublic], status_code=status.HTTP_201_CREATED
)
async def trigger_evidence_pack(
    body: EvidencePackTriggerRequest,
    current_user: CurrentUser,
    evidence_pack_service: EvidencePackServiceDep,
    farm_service: FarmServiceDep,
):
    farm = await farm_service.get_farm(current_user, body.field_id)
    pack = await evidence_pack_service.generate(current_user, farm, body)
    return success(_pack_to_public(pack), message="Evidence pack created")


@evidence_pack_router.get("/{pack_id}", response_model=SuccessResponse[EvidencePackPublic])
async def get_evidence_pack(pack_id: uuid.UUID, current_user: CurrentUser, repo: DailyTaskRepositoryDep):
    pack = await repo.get_evidence_pack(pack_id)
    if pack is None or pack.user_id != current_user.id:
        raise EvidencePackNotFoundError()
    return success(_pack_to_public(pack))


@evidence_pack_router.post("/{pack_id}/share", response_model=SuccessResponse[None])
async def share_evidence_pack(
    pack_id: uuid.UUID,
    body: EvidencePackShareRequest,
    current_user: CurrentUser,
    repo: DailyTaskRepositoryDep,
):
    pack = await repo.get_evidence_pack(pack_id)
    if pack is None or pack.user_id != current_user.id:
        raise EvidencePackNotFoundError()
    target = f"fpo:{body.fpo_contact_id}" if body.share_with == "fpo" and body.fpo_contact_id else body.share_with
    await repo.mark_evidence_pack_shared(pack_id, target)
    return success(None, message="Shared")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _now():
    import datetime as dt

    return dt.datetime.now(dt.UTC)


async def _owned_task(repo: DailyTaskRepositoryDep, task_id: uuid.UUID, user_id: uuid.UUID):
    task = await repo.get_task(task_id)
    if task is None or task.user_id != user_id:
        raise TaskNotFoundError()
    return task


def _to_public(task) -> TaskCardPublic:
    return TaskCardPublic(
        id=task.id,
        task_type=task.task_type,
        rank_position=task.rank_position,
        title_ta=task.title_ta,
        task_text_ta=task.task_text_ta,
        reason_text_ta=task.reason_text_ta,
        why_am_i_seeing_this_ta=task.why_am_i_seeing_this_ta,
        field_label=task.field_label,
        urgency=task.urgency,
        status=task.status,
        valid_until=task.valid_until,
        created_at=task.created_at,
    )


def _history_item_fields(task, final_response) -> dict:
    return {
        "id": task.id,
        "task_type": task.task_type,
        "title_ta": task.title_ta,
        "task_text_ta": task.task_text_ta,
        "field_label": task.field_label,
        "status": task.status,
        "created_at": task.created_at,
        "final_response": final_response,
    }


def _pack_to_public(pack) -> EvidencePackPublic:
    return EvidencePackPublic(
        id=pack.id,
        farm_id=pack.farm_id,
        event_type=pack.event_type,
        status=pack.status,
        confidence_level=pack.confidence_level,
        has_pre_event_imagery=pack.has_pre_event_imagery,
        has_post_event_imagery=pack.has_post_event_imagery,
        imagery_degraded_reason=pack.imagery_degraded_reason,
        content=EvidencePackContent.model_validate(pack.content),
        pdf_download_url=pack.pdf_object_url,
        version=pack.version,
        created_at=pack.created_at,
    )


def _signal_to_schema(signal) -> EvidenceSignal:
    return EvidenceSignal(
        id=signal.id,
        farmer_id=signal.user_id,
        field_id=signal.farm_id,
        signal_type=signal.signal_type,
        source_module=signal.source_module,
        observed_at=signal.observed_at,
        valid_until=signal.valid_until,
        confidence=signal.confidence,
        severity=signal.severity,
        urgency=signal.urgency,
        evidence_summary=signal.evidence_summary,
        evidence_technical=signal.evidence_technical,
        evidence_refs=signal.evidence_refs,
        policy_flags=signal.policy_flags,
        recommended_task_type=signal.recommended_task_type,
        dedupe_key=signal.dedupe_key,
        status=signal.status,
    )


def _encode_cursor(dt_value) -> str:
    return dt_value.isoformat()


def _decode_cursor(cursor: str | None):
    import datetime as dt

    return dt.datetime.fromisoformat(cursor) if cursor else None
