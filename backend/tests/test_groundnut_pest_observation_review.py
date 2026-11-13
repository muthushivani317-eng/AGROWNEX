from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.modules.auth.constants import UserStatus
from app.modules.auth.models import User
from app.modules.disease import router as disease_router
from app.modules.disease.models import DiseaseReport
from app.modules.disease.service import DiseaseService
from app.modules.disease.exceptions import DiseaseReportNotFoundError
from app.modules.disease.schemas import DiseaseReportOut, DiseaseReportSummaryOut
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.review import (
    complete_groundnut_pest_observation,
    groundnut_pest_observation_for_review,
    list_pending_groundnut_pest_observations,
)
from app.modules.notifications.models import Notification, NotificationPreferences
from sqlalchemy import select


def _raw(extent: str = "several", spread: str = "rapid") -> dict:
    return {
        "record_type": "farmer_pest_damage_observation",
        "farmer_reported": {"damage_extent": extent, "spread_speed": spread},
        "diagnosis_assigned": False,
    }


async def _record(db_session, user_id, **overrides):  # noqa: ANN001, ANN201
    values = {
        "user_id": user_id,
        "crop": "groundnut",
        "disease": None,
        "confidence": None,
        "image_key": f"disease/groundnut-pest-observations/{user_id}/{uuid.uuid4()}.jpg",
        "needs_expert_review": True,
        "review_status": "pending",
        "review_consent": True,
        "kvk_session": True,
        "raw_response": _raw(),
        "language": "en",
    }
    values.update(overrides)
    row = DiseaseReport(**values)
    db_session.add(row)
    await db_session.flush()
    return row


async def test_queue_only_lists_consented_pending_groundnut_observations(db_session) -> None:  # noqa: ANN001
    user = User(firebase_uid="groundnut-pest-review-owner", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    expected = await _record(db_session, user.id)
    await _record(db_session, user.id, crop="redgram")
    await _record(db_session, user.id, review_consent=False)
    await _record(db_session, user.id, review_status="confirmed")
    await _record(db_session, user.id, raw_response={"record_type": "other"})

    rows = await list_pending_groundnut_pest_observations(db_session, limit=50, offset=0)
    assert [row.observation_id for row in rows] == [expected.id]
    exposed = rows[0].model_dump()
    assert exposed["damage_extent"] == "several"
    assert exposed["spread_speed"] == "rapid"
    assert "user_id" not in exposed
    assert "farm_id" not in exposed
    assert "image_key" not in exposed


async def test_repository_does_not_change_redgram_review_selection(db_session) -> None:  # noqa: ANN001
    user = User(firebase_uid="redgram-review-still-isolated", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    redgram = await _record(
        db_session,
        user.id,
        crop="redgram",
        disease="redgram__healthy",
        review_status="confirmed",
    )
    await _record(db_session, user.id)
    rows = await DiseaseReportRepository(db_session).list_consented_reviewed_redgram()
    assert [row.id for row in rows] == [redgram.id]


async def test_kvk_private_photo_response_is_non_cacheable(monkeypatch) -> None:  # noqa: ANN001
    record = SimpleNamespace(
        id=uuid.uuid4(),
        image_key="disease/groundnut-pest-observations/private/photo.jpg",
        raw_response=_raw("few", "stable"),
        created_at=datetime.now(UTC),
    )
    lookup = AsyncMock(return_value=record)
    storage = SimpleNamespace(get=AsyncMock(return_value=b"private-groundnut-photo"))
    monkeypatch.setattr(disease_router, "get_pending_groundnut_pest_observation", lookup)
    monkeypatch.setattr(disease_router, "get_private_storage", lambda: storage)

    response = await disease_router.get_groundnut_pest_observation_image(
        record.id, SimpleNamespace(role="kvk_reviewer"), object()
    )
    assert response.body == b"private-groundnut-photo"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    storage.get.assert_awaited_once_with(key=record.image_key)


def test_kvk_queue_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(disease_router.router, prefix="/api/v1")

    async def fake_session():  # noqa: ANN202
        yield object()

    app.dependency_overrides[get_session] = fake_session
    response = TestClient(app).get("/api/v1/disease/kvk/groundnut-pest-observations")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_review_view_rejects_malformed_evidence_envelope() -> None:
    record = SimpleNamespace(
        id=uuid.uuid4(),
        image_key="private.jpg",
        raw_response=_raw(extent="diagnosed_aphids"),
        created_at=datetime.now(UTC),
    )
    try:
        groundnut_pest_observation_for_review(record)
    except LookupError as exc:
        assert str(exc) == "GROUNDNUT_PEST_OBSERVATION_NOT_FOUND"
    else:
        raise AssertionError("Malformed farmer evidence must fail closed")


async def test_kvk_completion_is_non_diagnostic_and_notifies_farmer_once(db_session) -> None:  # noqa: ANN001
    user = User(firebase_uid="groundnut-pest-completion-owner", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    observation = await _record(db_session, user.id)

    completed = await complete_groundnut_pest_observation(
        db_session,
        report_id=observation.id,
        feedback="seek_in_person_field_assessment",
    )
    assert completed.review_status == "reviewed"
    assert completed.reviewer_role == "kvk_officer"
    assert completed.review_timestamp is not None
    assert completed.needs_expert_review is False
    assert completed.disease is None
    assert completed.corrected_label is None
    assert completed.raw_response["review"] == {
        "feedback": "seek_in_person_field_assessment",
        "diagnostic": False,
    }

    notifications = list(
        (
            await db_session.execute(
                select(Notification).where(Notification.user_id == user.id)
            )
        ).scalars()
    )
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.event_type == "groundnut_pest_review_completed"
    assert notification.farm_id is None
    assert notification.payload_json == {
        "observation_id": str(observation.id),
        "feedback": "seek_in_person_field_assessment",
    }
    assert "pest" not in notification.payload_json
    assert "farm" not in notification.payload_json

    try:
        await complete_groundnut_pest_observation(
            db_session,
            report_id=observation.id,
            feedback="monitor_field_conditions",
        )
    except RuntimeError as exc:
        assert str(exc) == "GROUNDNUT_PEST_OBSERVATION_ALREADY_COMPLETED"
    else:
        raise AssertionError("A completed observation must not be completed twice")
    notification_count = (
        await db_session.execute(
            select(Notification).where(Notification.user_id == user.id)
        )
    ).scalars().all()
    assert len(notification_count) == 1


async def test_review_completion_respects_farmer_disease_notification_opt_out(db_session) -> None:  # noqa: ANN001
    user = User(firebase_uid="groundnut-pest-opted-out-owner", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        NotificationPreferences(
            user_id=user.id,
            disease_enabled=False,
        )
    )
    observation = await _record(db_session, user.id)
    await complete_groundnut_pest_observation(
        db_session,
        report_id=observation.id,
        feedback="submit_clearer_photo",
    )
    notifications = (
        await db_session.execute(
            select(Notification).where(Notification.user_id == user.id)
        )
    ).scalars().all()
    assert notifications == []
    assert observation.review_status == "reviewed"


async def test_farmer_history_enforces_observation_ownership_and_consent(db_session) -> None:  # noqa: ANN001
    owner = User(firebase_uid="groundnut-history-owner", status=UserStatus.ACTIVE)
    other = User(firebase_uid="groundnut-history-other", status=UserStatus.ACTIVE)
    db_session.add_all([owner, other])
    await db_session.flush()
    consented = await _record(db_session, owner.id)
    unconsented = await _record(db_session, owner.id, review_consent=False)

    service = DiseaseService(db_session)
    rows, total = await service.list_reports(owner, page=1, page_size=20)
    assert [row.id for row in rows] == [consented.id]
    assert total == 1
    assert (await service.get_report(owner, consented.id)).id == consented.id
    for user, report_id in ((owner, unconsented.id), (other, consented.id)):
        try:
            await service.get_report(user, report_id)
        except DiseaseReportNotFoundError:
            pass
        else:
            raise AssertionError("Observation reads must require ownership and consent")


async def test_farmer_contract_exposes_only_safe_observation_status_and_feedback(db_session) -> None:  # noqa: ANN001
    user = User(firebase_uid="groundnut-safe-history-contract", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    observation = await _record(db_session, user.id)
    await complete_groundnut_pest_observation(
        db_session,
        report_id=observation.id,
        feedback="monitor_field_conditions",
    )

    detail = DiseaseReportOut.from_report(observation).model_dump()
    summary = DiseaseReportSummaryOut.from_report(observation).model_dump()
    for payload in (detail["pest_observation"], summary["pest_observation"]):
        assert payload["review_status"] == "reviewed"
        assert payload["feedback"] == "monitor_field_conditions"
        assert "pest_label" not in payload
        assert "farm_id" not in payload
    assert detail["disease"] is None
    assert detail["confidence"] is None
