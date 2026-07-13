"""The Soil Intelligence ↔ Notification engine reuse: a processed soil report
surfaces as a notification, and a deficiency raises a warning alert."""
from __future__ import annotations

from datetime import UTC, date, datetime

from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.notifications.service import NotificationService
from app.modules.soil.constants import SoilSource
from app.modules.soil.provider import MockSoilProvider
from app.modules.soil.schemas import SoilReportCreate, SoilValuesIn
from app.modules.soil.service import SoilService

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


async def _user_farm(db_session):
    user = User(firebase_uid="fb-soilnotif", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Field A", soil_type="Clay")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


async def test_processed_report_creates_notification(db_session) -> None:
    user, farm = await _user_farm(db_session)
    soil = SoilService(db_session, provider=MockSoilProvider(), now=NOW)
    await soil.submit_report(
        user,
        SoilReportCreate(
            farm_id=farm.id,
            source=SoilSource.SOIL_HEALTH_CARD,
            test_date=date(2026, 7, 1),
            values=SoilValuesIn(ph=7.0, nitrogen=600),  # no deficiency
        ),
    )

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="soil", sync=False)
    assert page.total == 1
    assert page.items[0].event_type == "report_processed"


async def test_deficiency_raises_alert(db_session) -> None:
    user, farm = await _user_farm(db_session)
    soil = SoilService(db_session, provider=MockSoilProvider(), now=NOW)
    await soil.submit_report(
        user,
        SoilReportCreate(
            farm_id=farm.id,
            source=SoilSource.SOIL_HEALTH_CARD,
            values=SoilValuesIn(ph=5.0, nitrogen=100),  # strongly acidic + low N
        ),
    )

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="soil", sync=False)
    types = {n.event_type for n in page.items}
    assert types == {"report_processed", "deficiency_alert"}
