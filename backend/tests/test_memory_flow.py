"""Integration tests for the Farm Memory service + repository.

Covers a rebuild with no data (honest empty, never fabricated), a rebuild that reads
real Disease + Soil records through each module's own repository, persistence of
memories / events / tags / summaries / links, the dashboard / latest / history /
summary / detail reads, idempotent + immutable rebuild, filtering, and ownership
isolation. Weather is disabled (network) — best-effort by design.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm, FarmLocation
from app.modules.memory.exceptions import FarmNotOwnedError, MemoryNotFoundError
from app.modules.memory.service import MemoryService
from app.modules.soil.models import SoilReport

NOW = datetime(2026, 12, 1, 6, 0, tzinfo=UTC)


async def _make_user(db_session, uid: str = "fb-mem-1") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user: User, *, crop: str | None = "paddy") -> Farm:
    farm = Farm(user_id=user.id, name="Field A", crop=crop)
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(
        farm_id=farm.id, latitude=10.7, longitude=79.1, district="Thanjavur"
    )
    await db_session.flush()
    return farm


def _service(db_session, *, now: datetime = NOW) -> MemoryService:
    return MemoryService(db_session, weather_service=None, now=now, enable_weather=False)


async def _add_disease(
    db_session, user, farm, *, severity="high", confidence=90, when: datetime
) -> DiseaseReport:
    report = DiseaseReport(
        user_id=user.id,
        farm_id=farm.id,
        image_url="https://r2/x.jpg",
        disease="Leaf blast",
        confidence=confidence,
        severity=severity,
        crop="paddy",
        language="ta",
        needs_expert_review=True,
        created_at=when,
    )
    db_session.add(report)
    await db_session.flush()
    return report


async def _add_soil(db_session, user, farm, *, when: datetime) -> SoilReport:
    report = SoilReport(
        user_id=user.id, farm_id=farm.id, source="lab", confidence=95, created_at=when
    )
    db_session.add(report)
    await db_session.flush()
    return report


# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_rebuild_empty_is_honest(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    result = await service.rebuild(user, farm.id)
    assert result.created == 0
    assert result.total == 0

    dash = await service.get_dashboard(user, farm.id)
    assert dash["has_data"] is False
    assert dash["message_code"] == "memory.status.no_memory"

    with pytest.raises(MemoryNotFoundError):
        await service.latest(user, farm.id)


@pytest.mark.asyncio
async def test_rebuild_learns_from_modules(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm, when=datetime(2026, 7, 1, 6, tzinfo=UTC))
    await _add_disease(
        db_session, user, farm, severity="moderate", confidence=80,
        when=datetime(2026, 7, 20, 6, tzinfo=UTC),
    )
    await _add_soil(db_session, user, farm, when=datetime(2026, 8, 1, 6, tzinfo=UTC))
    service = _service(db_session)

    result = await service.rebuild(user, farm.id)
    assert result.created == 3
    assert result.total == 3
    assert result.summaries >= 2  # a season + a year summary at minimum

    # Dashboard
    dash = await service.get_dashboard(user, farm.id)
    assert dash["has_data"] is True
    assert dash["total"] == 3
    assert dash["latest_summary"] is not None

    # Latest = most recent occurrence (the soil report on Aug 1)
    latest = await service.latest(user, farm.id)
    assert latest.source_module == "soil"
    assert latest.location == "Thanjavur"

    # History timeline, newest first
    page = await service.history(user, farm.id, page=1, page_size=10)
    assert page.total == 3
    assert page.items[0].occurred_at >= page.items[-1].occurred_at

    # Filter by module
    only_disease = await service.history(
        user, farm.id, page=1, page_size=10, source_module="disease"
    )
    assert only_disease.total == 2

    # Summaries: one kharif season summary covers all three (Jul+Aug 2026)
    summaries = await service.summaries(user, farm.id)
    season = next(s for s in summaries if s.period_type == "season")
    assert season.period_key == "2026-kharif"
    assert season.event_count == 3
    assert season.importance == "critical"  # the high-severity disease dominates


@pytest.mark.asyncio
async def test_rebuild_links_related_memories(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm, when=datetime(2026, 7, 1, 6, tzinfo=UTC))
    await _add_disease(
        db_session, user, farm, severity="low", confidence=60,
        when=datetime(2026, 7, 15, 6, tzinfo=UTC),
    )
    await _add_soil(db_session, user, farm, when=datetime(2026, 7, 10, 6, tzinfo=UTC))
    service = _service(db_session)

    result = await service.rebuild(user, farm.id)
    assert result.links >= 1

    # The soil memory relates to a disease memory (same crop + season, cross-module).
    page = await service.history(user, farm.id, page=1, page_size=10, source_module="soil")
    soil_id = page.items[0].id
    _memory, links = await service.get_memory(user, soil_id)
    assert any(link.link_type == "relates" for link in links)


@pytest.mark.asyncio
async def test_rebuild_is_idempotent_and_immutable(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm, when=datetime(2026, 7, 1, 6, tzinfo=UTC))
    service = _service(db_session)

    first = await service.rebuild(user, farm.id)
    assert first.created == 1
    original = await service.latest(user, farm.id)
    original_id, original_occurred = original.id, original.occurred_at

    # Second rebuild with no new data creates nothing and rewrites no history.
    second = await service.rebuild(user, farm.id)
    assert second.created == 0
    assert second.total == 1
    again = await service.latest(user, farm.id)
    assert again.id == original_id
    assert again.occurred_at == original_occurred


@pytest.mark.asyncio
async def test_ownership_isolation(db_session):
    owner = await _make_user(db_session, "fb-owner")
    farm = await _make_farm(db_session, owner)
    await _add_disease(db_session, owner, farm, when=datetime(2026, 7, 1, 6, tzinfo=UTC))
    service = _service(db_session)
    await service.rebuild(owner, farm.id)
    memory = await service.latest(owner, farm.id)

    intruder = await _make_user(db_session, "fb-intruder")
    with pytest.raises(FarmNotOwnedError):
        await service.rebuild(intruder, farm.id)
    with pytest.raises(FarmNotOwnedError):
        await service.get_dashboard(intruder, farm.id)
    with pytest.raises(MemoryNotFoundError):
        await service.get_memory(intruder, memory.id)


@pytest.mark.asyncio
async def test_unknown_farm_rejected(db_session):
    user = await _make_user(db_session)
    service = _service(db_session)
    with pytest.raises(FarmNotOwnedError):
        await service.rebuild(user, uuid.uuid4())
