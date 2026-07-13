"""Integration tests for the Satellite service: acquisition, honest unavailability,
index/alert/history persistence, trend detection and ownership (in-memory DB,
injected providers, fixed 'now')."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from app.modules.auth.models import User
from app.modules.farms.models import Farm, FarmBoundary, FarmLocation
from app.modules.satellite.engine import BandReflectance
from app.modules.satellite.exceptions import (
    FarmNotOwnedError,
    SatelliteUnavailableError,
)
from app.modules.satellite.provider import (
    FetchOutcome,
    MockSatelliteProvider,
    ProviderScene,
    SatelliteProvider,
)
from app.modules.satellite.service import SatelliteService

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[79.1, 10.7], [79.2, 10.7], [79.2, 10.8], [79.1, 10.8], [79.1, 10.7]]],
}


class FakeProvider:
    """A provider returning a fixed outcome (for controlled scene tests)."""

    name = "sentinel"

    def __init__(self, outcome: FetchOutcome) -> None:
        self._outcome = outcome

    async def fetch_scene(self, polygon, *, capture_before) -> FetchOutcome:
        return self._outcome


def _scene(*, red: float, nir: float, cloud: float = 5.0, std: float = 0.05) -> ProviderScene:
    ndvi = round((nir - red) / (nir + red), 4)
    return ProviderScene(
        capture_date=date(2026, 7, 11),
        provider="sentinel",
        cloud_cover=cloud,
        resolution_m=10.0,
        bands=BandReflectance(red=red, nir=nir, red_edge=0.30, swir=0.25, blue=0.06),
        index_stats={"ndvi": (ndvi, ndvi - std, ndvi + std, std)},
    )


async def _make_user(db_session, uid: str = "fb-sat") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user, *, polygon: dict | None = POLYGON) -> Farm:
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(farm_id=farm.id, latitude=10.7, longitude=79.1)
    if polygon is not None:
        farm.boundary = FarmBoundary(
            farm_id=farm.id, geojson=polygon, centroid_lat=10.75, centroid_lng=79.15
        )
    await db_session.flush()
    return farm


def _service(db_session, provider: SatelliteProvider) -> SatelliteService:
    return SatelliteService(db_session, provider=provider, now=NOW, enable_weather=False)


# --------------------------------------------------------------------------- #
# Availability + honesty
# --------------------------------------------------------------------------- #
async def test_refresh_without_polygon_is_unavailable(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user, polygon=None)
    service = _service(db_session, MockSatelliteProvider())
    session = await service.refresh(user, farm.id)
    assert session.status == "unavailable"
    assert session.unavailable_reason == "no_polygon"
    assert session.ndvi is None  # never fabricated


async def test_refresh_provider_unavailable(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, FakeProvider(FetchOutcome(None, "provider_error")))
    session = await service.refresh(user, farm.id)
    assert session.status == "unavailable"
    assert session.unavailable_reason == "provider_error"
    codes = [a.code for a in session.alerts]
    assert "satellite.alert.missing_imagery" in codes


async def test_refresh_rejects_cloudy_scene(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, FakeProvider(FetchOutcome(_scene(red=0.15, nir=0.45, cloud=80))))
    session = await service.refresh(user, farm.id)
    assert session.status == "unavailable"
    assert session.unavailable_reason == "cloud_cover"
    assert any(a.code == "satellite.alert.cloud_obstruction" for a in session.alerts)


async def test_refresh_available_scene_computes_indices(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, FakeProvider(FetchOutcome(_scene(red=0.15, nir=0.45))))
    session = await service.refresh(user, farm.id)
    assert session.status == "available"
    assert session.ndvi == 0.5
    assert session.vegetation_health == "moderate"
    assert session.confidence > 0

    indices = await service.indices(user, farm.id)
    assert {i.index_name for i in indices} >= {"ndvi", "ndmi", "ndre"}
    page = await service.history(user, farm.id, page=1, page_size=10)
    assert page.total == 1


async def test_requires_owned_farm(db_session) -> None:
    owner = await _make_user(db_session, uid="owner")
    other = await _make_user(db_session, uid="other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session, MockSatelliteProvider())
    with pytest.raises(FarmNotOwnedError):
        await service.refresh(other, farm.id)


# --------------------------------------------------------------------------- #
# Trend detection across sessions
# --------------------------------------------------------------------------- #
async def test_declining_ndvi_raises_alert(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    # First: healthy NDVI 0.5.
    await _service(db_session, FakeProvider(FetchOutcome(_scene(red=0.15, nir=0.45)))).refresh(
        user, farm.id
    )
    # Second: NDVI collapses to ~0.14 → decline + low vigor.
    session = await _service(
        db_session, FakeProvider(FetchOutcome(_scene(red=0.30, nir=0.40)))
    ).refresh(user, farm.id)
    assert session.trend == "declining"
    assert session.ndvi_delta is not None and session.ndvi_delta < 0
    codes = {a.code for a in session.alerts}
    assert "satellite.alert.low_vigor" in codes


# --------------------------------------------------------------------------- #
# Dashboard / latest / timeline
# --------------------------------------------------------------------------- #
async def test_dashboard_no_polygon_prompts(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user, polygon=None)
    service = _service(db_session, MockSatelliteProvider())
    data = await service.get_dashboard(user, farm.id)
    assert data["has_polygon"] is False
    assert data["message_code"] == "satellite.status.no_polygon"
    assert data["session"] is None


async def test_dashboard_after_available(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, FakeProvider(FetchOutcome(_scene(red=0.15, nir=0.45))))
    await service.refresh(user, farm.id)
    data = await service.get_dashboard(user, farm.id)
    assert data["has_data"] is True
    assert data["session"].ndvi == 0.5


async def test_latest_requires_available_session(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, FakeProvider(FetchOutcome(None, "no_imagery")))
    await service.refresh(user, farm.id)  # unavailable only
    with pytest.raises(SatelliteUnavailableError):
        await service.latest(user, farm.id)


async def test_timeline_aggregates(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _service(db_session, FakeProvider(FetchOutcome(_scene(red=0.15, nir=0.45)))).refresh(
        user, farm.id
    )
    await _service(db_session, FakeProvider(FetchOutcome(_scene(red=0.16, nir=0.44)))).refresh(
        user, farm.id
    )
    points = await _service(db_session, MockSatelliteProvider()).timeline(
        user, farm.id, range_="monthly"
    )
    assert len(points) >= 1
    assert points[0]["ndvi"] is not None


async def test_mock_provider_is_sample_and_no_imagery(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, MockSatelliteProvider())
    session = await service.refresh(user, farm.id)
    assert session.status == "available"
    assert session.is_sample is True          # clearly flagged sample data
    assert session.images == []               # no fabricated imagery


async def test_provider_never_fabricates_without_config(db_session) -> None:
    from app.modules.satellite.provider import SentinelProvider

    outcome = await SentinelProvider().fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.scene is None  # honest "not available" until wired
