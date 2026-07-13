"""Integration tests for the Crop Intelligence service + repository.

Covers refresh with no module data (honest low confidence, never fabricated), refresh
that reads a real Disease report through that module's own repository, persistence of
report/health/risk/recommendations/history, the dashboard/latest/history/report reads,
pagination and ownership isolation. Weather is disabled (network) — best-effort by
design.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm, FarmLocation
from app.modules.intelligence.exceptions import (
    FarmNotOwnedError,
    IntelligenceReportNotFoundError,
    IntelligenceUnavailableError,
)
from app.modules.intelligence.repository import IntelligenceRepository
from app.modules.intelligence.service import IntelligenceService

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


async def _make_user(db_session, uid: str = "fb-intel-1") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user: User, *, crop: str | None = "paddy") -> Farm:
    farm = Farm(user_id=user.id, name="Field A", crop=crop)
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(farm_id=farm.id, latitude=10.7, longitude=79.1)
    await db_session.flush()
    return farm


def _service(db_session, *, now: datetime = NOW) -> IntelligenceService:
    # Weather off — best-effort by design; the refresh must still work.
    return IntelligenceService(db_session, weather_service=None, now=now, enable_weather=False)


async def _add_disease(db_session, user, farm, *, severity="high", confidence=90) -> None:
    db_session.add(
        DiseaseReport(
            user_id=user.id,
            farm_id=farm.id,
            image_url="https://r2/x.jpg",
            disease="Leaf blast",
            confidence=confidence,
            severity=severity,
            language="ta",
            needs_expert_review=False,
        )
    )
    await db_session.flush()


# --------------------------------------------------------------------------- #
# Refresh
# --------------------------------------------------------------------------- #
async def test_refresh_with_no_module_data_is_honest(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    report = await service.refresh(user, farm.id)
    # No modules → nothing invented: no overall score, zero confidence, low risk.
    assert report.overall_health_score is None
    assert report.confidence == 0
    assert report.overall_risk == "low"
    assert report.sources_used == []
    assert report.crop == "paddy"
    # Health/risk rows and a history snapshot are still persisted.
    assert report.health is not None
    assert report.risk is not None


async def test_refresh_reads_disease_module(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm, severity="high", confidence=90)

    report = await service.refresh(user, farm.id)
    assert "disease" in report.sources_used
    assert report.health.disease_score is not None
    assert report.overall_health_score is not None
    # A confident, severe disease escalates the overall risk.
    assert report.overall_risk == "critical"
    # And produces prioritized, generic recommendations (no brands).
    assert report.recommendations
    assert all(r.code.startswith("intelligence.rec.") for r in report.recommendations)
    assert any(r.code == "intelligence.rec.treat_disease" for r in report.recommendations)


async def test_refresh_persists_priority_issues(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm)

    report = await service.refresh(user, farm.id)
    issues = report.risk.priority_issues or []
    assert any(i["code"] == "intelligence.issue.disease_active" for i in issues)


async def test_refresh_appends_history_snapshots(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    await service.refresh(user, farm.id)
    await service.refresh(user, farm.id)

    page = await service.history(user, farm.id, page=1, page_size=20)
    assert page.total == 2


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #
async def test_dashboard_before_and_after_refresh(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    empty = await service.get_dashboard(user, farm.id)
    assert empty["has_data"] is False
    assert empty["message_code"] == "intelligence.status.no_report"
    assert empty["report"] is None

    await service.refresh(user, farm.id)
    populated = await service.get_dashboard(user, farm.id)
    assert populated["has_data"] is True
    assert populated["report"] is not None


async def test_latest_unavailable_before_any_refresh(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    with pytest.raises(IntelligenceUnavailableError):
        await service.latest(user, farm.id)


async def test_latest_returns_most_recent(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    first = await _service(db_session, now=NOW).refresh(user, farm.id)
    second = await _service(db_session, now=NOW + timedelta(hours=1)).refresh(user, farm.id)

    latest = await _service(db_session).latest(user, farm.id)
    assert latest.id == second.id
    assert latest.id != first.id


async def test_history_pagination(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    for i in range(3):
        await _service(db_session, now=NOW + timedelta(hours=i)).refresh(user, farm.id)

    page1 = await _service(db_session).history(user, farm.id, page=1, page_size=2)
    assert page1.total == 3
    assert page1.total_pages == 2
    assert len(page1.items) == 2
    page2 = await _service(db_session).history(user, farm.id, page=2, page_size=2)
    assert len(page2.items) == 1


async def test_get_report_by_id(db_session) -> None:
    service = _service(db_session)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    report = await service.refresh(user, farm.id)

    fetched = await service.get_report(user, report.id)
    assert fetched.id == report.id


# --------------------------------------------------------------------------- #
# Ownership / not-found
# --------------------------------------------------------------------------- #
async def test_refresh_rejects_foreign_farm(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    with pytest.raises(FarmNotOwnedError):
        await service.refresh(other, farm.id)


async def test_get_report_is_owner_scoped(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner-2")
    other = await _make_user(db_session, uid="fb-other-2")
    farm = await _make_farm(db_session, owner)
    report = await _service(db_session).refresh(owner, farm.id)

    service = _service(db_session)
    with pytest.raises(IntelligenceReportNotFoundError):
        await service.get_report(other, report.id)
    with pytest.raises(IntelligenceReportNotFoundError):
        await service.get_report(owner, uuid.uuid4())


# --------------------------------------------------------------------------- #
# Repository directly
# --------------------------------------------------------------------------- #
async def test_repository_recent_reports_scoped_to_user(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-repo-1")
    other = await _make_user(db_session, uid="fb-repo-2")
    farm = await _make_farm(db_session, owner)
    other_farm = await _make_farm(db_session, other)
    await _service(db_session).refresh(owner, farm.id)
    await _service(db_session).refresh(other, other_farm.id)

    repo = IntelligenceRepository(db_session)
    owner_reports = await repo.recent_reports(owner.id, limit=50)
    assert len(owner_reports) == 1
    assert owner_reports[0].user_id == owner.id


async def test_repository_latest_report_is_newest(db_session) -> None:
    user = await _make_user(db_session, uid="fb-repo-3")
    farm = await _make_farm(db_session, user)
    await _service(db_session, now=NOW).refresh(user, farm.id)
    newest = await _service(db_session, now=NOW + timedelta(days=1)).refresh(user, farm.id)

    repo = IntelligenceRepository(db_session)
    latest = await repo.latest_report(user.id, farm.id)
    assert latest.id == newest.id
