from datetime import date

import pytest
from app.modules.auth.models import User
from app.modules.calendar.schemas import GenerateCalendarRequest
from app.modules.calendar.service import CalendarService
from app.modules.farms.models import Farm


@pytest.mark.asyncio
async def test_verified_organic_calendar_filter_and_action_are_idempotent(db_session):
    user = User(firebase_uid="organic-calendar-owner", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(
        user_id=user.id, name="Paddy organic calendar", crop="paddy",
        sowing_date=date.today(), status="active",
    )
    db_session.add(farm)
    await db_session.flush()
    service = CalendarService(db_session)
    generated = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))
    organic = await service.timeline(user, farm_id=farm.id, organic_only=True)
    assert organic
    assert all(row.organic_practice for row, _ in organic)
    target = organic[0][0]
    assert any(row.id == target.id for row, _ in generated)
    first = await service.register_organic_action(user, target.id)
    second = await service.register_organic_action(user, target.id)
    assert first.id == second.id
    assert first.source_module == "organic_calendar"
    assert target.registry_content_hash in first.source_version
