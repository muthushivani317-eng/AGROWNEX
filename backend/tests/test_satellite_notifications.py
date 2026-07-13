"""The Satellite ↔ Notification engine reuse: a vegetation alert and an unavailable
scene each surface as a notification."""
from __future__ import annotations

from datetime import UTC, date, datetime

from app.modules.auth.models import User
from app.modules.farms.models import Farm, FarmBoundary
from app.modules.notifications.service import NotificationService
from app.modules.satellite.engine import BandReflectance
from app.modules.satellite.provider import FetchOutcome, ProviderScene
from app.modules.satellite.service import SatelliteService

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[79.1, 10.7], [79.2, 10.7], [79.2, 10.8], [79.1, 10.7]]],
}


class FakeProvider:
    name = "sentinel"

    def __init__(self, outcome: FetchOutcome) -> None:
        self._outcome = outcome

    async def fetch_scene(self, polygon, *, capture_before) -> FetchOutcome:
        return self._outcome


async def _user_farm(db_session):
    user = User(firebase_uid="fb-satnotif", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    farm.boundary = FarmBoundary(farm_id=farm.id, geojson=POLYGON)
    await db_session.flush()
    return user, farm


async def test_low_vigor_creates_vegetation_notification(db_session) -> None:
    user, farm = await _user_farm(db_session)
    scene = ProviderScene(
        capture_date=date(2026, 7, 11), provider="sentinel", cloud_cover=5.0,
        resolution_m=10.0,
        bands=BandReflectance(red=0.30, nir=0.35, red_edge=0.30, swir=0.25, blue=0.06),
    )
    await SatelliteService(
        db_session, provider=FakeProvider(FetchOutcome(scene)), now=NOW
    ).refresh(user, farm.id)

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="satellite", sync=False)
    assert any(n.event_type == "vegetation_decline" for n in page.items)


async def test_unavailable_creates_imagery_notification(db_session) -> None:
    user, farm = await _user_farm(db_session)
    await SatelliteService(
        db_session, provider=FakeProvider(FetchOutcome(None, "no_imagery")), now=NOW
    ).refresh(user, farm.id)

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="satellite", sync=False)
    assert any(n.event_type == "imagery_unavailable" for n in page.items)
