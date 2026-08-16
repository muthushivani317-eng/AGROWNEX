"""Disease report history tests."""
from __future__ import annotations

import pytest
from app.modules.auth.models import User
from app.modules.disease.exceptions import DiseaseReportNotFoundError
from app.modules.disease.models import DiseaseReport
from app.modules.disease.service import DiseaseService
from app.modules.farms.models import Farm


async def _make_user(db_session, uid: str = "fb-disease-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number="+919876533333",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_report(
    db_session,
    user: User,
    *,
    disease: str = "Leaf blast",
    farm_id=None,
) -> DiseaseReport:
    report = DiseaseReport(
        user_id=user.id,
        farm_id=farm_id,
        image_url="https://r2.mock.local/disease/report.jpg",
        crop="paddy",
        disease=disease,
        confidence=77,
        language="en",
    )
    db_session.add(report)
    await db_session.flush()
    return report


async def test_history_and_delete(db_session):
    service = DiseaseService(db_session)
    user = await _make_user(db_session)
    first = await _make_report(db_session, user)
    await _make_report(db_session, user, disease="Brown spot")

    _, total = await service.list_reports(user, page=1, page_size=20)
    assert total == 2

    await service.delete_report(user, first.id)
    _, after = await service.list_reports(user, page=1, page_size=20)
    assert after == 1
    with pytest.raises(DiseaseReportNotFoundError):
        await service.get_report(user, first.id)


async def test_ownership_isolation(db_session):
    service = DiseaseService(db_session)
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    report = await _make_report(db_session, owner)

    with pytest.raises(DiseaseReportNotFoundError):
        await service.get_report(other, report.id)


async def test_history_is_scoped_by_farm_and_keeps_unassigned_separate(db_session):
    service = DiseaseService(db_session)
    user = await _make_user(db_session, uid="fb-farm-scope")
    farm_a = Farm(user_id=user.id, name="North field", status="active")
    farm_b = Farm(user_id=user.id, name="South field", status="active")
    db_session.add_all([farm_a, farm_b])
    await db_session.flush()
    report_a = await _make_report(db_session, user, disease="A", farm_id=farm_a.id)
    report_b = await _make_report(db_session, user, disease="B", farm_id=farm_b.id)
    legacy = await _make_report(db_session, user, disease="Legacy")

    items_a, total_a = await service.list_reports(
        user, page=1, page_size=20, farm_id=farm_a.id
    )
    items_b, total_b = await service.list_reports(
        user, page=1, page_size=20, farm_id=farm_b.id
    )
    unassigned, total_unassigned = await service.list_reports(
        user, page=1, page_size=20, unassigned_only=True
    )

    assert ([item.id for item in items_a], total_a) == ([report_a.id], 1)
    assert ([item.id for item in items_b], total_b) == ([report_b.id], 1)
    assert ([item.id for item in unassigned], total_unassigned) == ([legacy.id], 1)
