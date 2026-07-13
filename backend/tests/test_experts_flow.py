"""Integration tests for the Expert Connect service: seeding, deterministic
assignment, the consultation lifecycle (create → reply → status), immutability,
attachments and ownership (in-memory DB, mock provider, fixed 'now')."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.modules.auth.models import User
from app.modules.experts.constants import (
    ConsultationCategory,
    ConsultationPriority,
    ConsultationStatus,
    SenderType,
)
from app.modules.experts.exceptions import (
    ConsultationClosedError,
    ConsultationNotFoundError,
    ExpertNotFoundError,
    FarmNotOwnedError,
    InvalidStatusTransitionError,
)
from app.modules.experts.provider import MockExpertProvider
from app.modules.experts.schemas import (
    AttachmentIn,
    ConsultationCreate,
    ConsultationListFilters,
    ExpertListFilters,
    ReplyIn,
    StatusUpdateIn,
)
from app.modules.experts.service import ExpertService
from app.modules.farms.models import Farm, FarmLocation

NOW = datetime(2026, 7, 11, 6, 0, tzinfo=UTC)


async def _make_user(db_session, uid: str = "fb-expert") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user, *, district="Thanjavur") -> Farm:
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(
        farm_id=farm.id, district=district, block="Block-1", village="Village-1"
    )
    await db_session.flush()
    return farm


def _service(db_session) -> ExpertService:
    return ExpertService(db_session, provider=MockExpertProvider(), now=NOW)


def _create(**overrides) -> ConsultationCreate:
    data = {
        "category": ConsultationCategory.CROP_DISEASE,
        "subject": "Yellow spots on paddy leaves",
        "description": "My paddy leaves have yellow spots spreading fast. What should I do?",
    }
    data.update(overrides)
    return ConsultationCreate(**data)


# --------------------------------------------------------------------------- #
# Seeding + experts
# --------------------------------------------------------------------------- #
async def test_experts_are_seeded_and_listed(db_session) -> None:
    service = _service(db_session)
    page = await service.list_experts(ExpertListFilters())
    assert page.total >= 5
    assert all(e.verified for e in page.items)


async def test_expert_filter_by_category(db_session) -> None:
    service = _service(db_session)
    page = await service.list_experts(
        ExpertListFilters(category=ConsultationCategory.CROP_DISEASE)
    )
    assert page.total >= 1
    for expert in page.items:
        assert any(s.category == "crop_disease" for s in expert.specializations)


async def test_get_expert_and_missing(db_session) -> None:
    service = _service(db_session)
    page = await service.list_experts(ExpertListFilters())
    expert = await service.get_expert(page.items[0].id)
    assert expert.id == page.items[0].id
    with pytest.raises(ExpertNotFoundError):
        await service.get_expert(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Create + assignment
# --------------------------------------------------------------------------- #
async def test_create_assigns_verified_expert_and_opens_thread(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    c = await service.create_consultation(user, _create(farm_id=farm.id))
    assert c.status == ConsultationStatus.ASSIGNED.value
    assert c.assigned_expert_id is not None
    assert c.assigned_at is not None
    # A crop_disease consultation goes to a desk that covers crop_disease.
    assert any(s.category == "crop_disease" for s in c.expert.specializations)

    # Opening farmer message + a system acknowledgement (no fabricated advice).
    assert c.messages[0].sender_type == SenderType.FARMER.value
    assert c.messages[0].body.startswith("My paddy leaves")
    assert any(m.is_system for m in c.messages)
    # Status history logs submitted → assigned.
    assert [h.new_status for h in c.status_history] == [
        ConsultationStatus.SUBMITTED.value,
        ConsultationStatus.ASSIGNED.value,
    ]


async def test_create_with_attachments(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(
        user,
        _create(attachments=[AttachmentIn(file_url="https://r2/leaf.jpg")]),
    )
    assert len(c.attachments) == 1
    # The attachment hangs off the farmer's opening message.
    assert c.attachments[0].message_id == c.messages[0].id


async def test_create_requires_owned_farm(db_session) -> None:
    owner = await _make_user(db_session, uid="owner")
    other = await _make_user(db_session, uid="other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    with pytest.raises(FarmNotOwnedError):
        await service.create_consultation(other, _create(farm_id=farm.id))


async def test_preferred_expert_is_honoured(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    experts = await service.list_experts(ExpertListFilters())
    preferred = experts.items[-1]
    c = await service.create_consultation(
        user, _create(preferred_expert_id=preferred.id)
    )
    assert c.assigned_expert_id == preferred.id


# --------------------------------------------------------------------------- #
# Reply + immutability
# --------------------------------------------------------------------------- #
async def test_reply_appends_message_and_moves_to_expert(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(user, _create())
    before = len(c.messages)

    c = await service.reply(user, c.id, ReplyIn(body="It started three days ago."))
    assert len(c.messages) == before + 1
    assert c.messages[-1].sender_type == SenderType.FARMER.value
    assert c.status == ConsultationStatus.AWAITING_EXPERT.value


async def test_reply_blocked_after_cancel(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(user, _create())
    await service.update_status(
        user, c.id, StatusUpdateIn(status=ConsultationStatus.CANCELLED)
    )
    with pytest.raises(ConsultationClosedError):
        await service.reply(user, c.id, ReplyIn(body="hello?"))


async def test_reply_reopens_a_resolved_consultation(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(user, _create())
    await service.update_status(
        user, c.id, StatusUpdateIn(status=ConsultationStatus.RESOLVED)
    )
    c = await service.reply(user, c.id, ReplyIn(body="It came back."))
    assert c.status == ConsultationStatus.IN_PROGRESS.value


# --------------------------------------------------------------------------- #
# Attachments
# --------------------------------------------------------------------------- #
async def test_add_attachment(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(user, _create())
    c = await service.add_attachment(
        user, c.id, AttachmentIn(file_url="https://r2/extra.jpg", caption="close-up")
    )
    assert any(a.caption == "close-up" for a in c.attachments)


# --------------------------------------------------------------------------- #
# Status lifecycle
# --------------------------------------------------------------------------- #
async def test_resolve_sets_note_and_timestamp(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(user, _create())
    c = await service.update_status(
        user, c.id, StatusUpdateIn(status=ConsultationStatus.RESOLVED, note="Sorted"),
    )
    assert c.status == ConsultationStatus.RESOLVED.value
    assert c.resolved_at is not None
    assert c.resolution_note == "Sorted"


async def test_farmer_cannot_set_expert_status(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(user, _create())
    with pytest.raises(InvalidStatusTransitionError):
        await service.update_status(
            user, c.id, StatusUpdateIn(status=ConsultationStatus.IN_PROGRESS)
        )


# --------------------------------------------------------------------------- #
# Lists + ownership
# --------------------------------------------------------------------------- #
async def test_pending_and_history_split(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    open_c = await service.create_consultation(user, _create(subject="Open one still"))
    done = await service.create_consultation(user, _create(subject="Done one now"))
    await service.update_status(
        user, done.id, StatusUpdateIn(status=ConsultationStatus.RESOLVED)
    )

    pending = await service.pending(user, page=1, page_size=10)
    history = await service.history(user, page=1, page_size=10)
    pending_ids = {c.id for c in pending.items}
    history_ids = {c.id for c in history.items}
    assert open_c.id in pending_ids
    assert done.id in history_ids
    assert done.id not in pending_ids


async def test_list_filters_by_status(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    await service.create_consultation(user, _create())
    page = await service.list_consultations(
        user, ConsultationListFilters(status=ConsultationStatus.ASSIGNED)
    )
    assert page.total == 1


async def test_get_consultation_ownership_enforced(db_session) -> None:
    owner = await _make_user(db_session, uid="owner")
    other = await _make_user(db_session, uid="other")
    service = _service(db_session)
    c = await service.create_consultation(owner, _create())
    with pytest.raises(ConsultationNotFoundError):
        await service.get_consultation(other, c.id)
    with pytest.raises(ConsultationNotFoundError):
        await service.get_consultation(owner, uuid.uuid4())


async def test_priority_is_persisted(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    c = await service.create_consultation(
        user, _create(priority=ConsultationPriority.URGENT)
    )
    assert c.priority == ConsultationPriority.URGENT.value
