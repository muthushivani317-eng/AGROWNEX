"""Integration tests for the weather service (fake Open-Meteo provider, no network)."""
from __future__ import annotations

import uuid

import pytest
from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.models import Farm, FarmLocation
from app.modules.weather.cache import WeatherCache
from app.modules.weather.exceptions import FarmLocationMissingError
from app.modules.weather.service import WeatherService

from tests.weather_fixture import build_raw


class FakeProvider:
    def __init__(self, raw: dict) -> None:
        self.raw = raw
        self.calls = 0

    async def fetch(self, latitude: float, longitude: float) -> dict:
        self.calls += 1
        return self.raw


async def _make_user(db_session, uid: str = "fb-weather-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number="+919876511111",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user: User, *, with_location: bool = True) -> Farm:
    farm = Farm(user_id=user.id, name="North Field")
    db_session.add(farm)
    await db_session.flush()
    if with_location:
        db_session.add(
            FarmLocation(
                farm_id=farm.id, latitude=9.9, longitude=78.1, source="gps"
            )
        )
        await db_session.flush()
    return farm


async def test_get_by_farm_returns_full_bundle(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = WeatherService(
        db_session, provider=FakeProvider(build_raw()), cache=WeatherCache()
    )

    bundle = await service.get_by_farm(user, farm.id)
    assert bundle.location.name == "North Field"
    assert bundle.current.temperature_c == 30.0
    assert len(bundle.hourly) == 24
    assert len(bundle.daily) == 7
    assert bundle.insights  # deterministic insights always present
    assert bundle.source == "open-meteo"


async def test_farm_without_location_raises(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user, with_location=False)
    service = WeatherService(
        db_session, provider=FakeProvider(build_raw()), cache=WeatherCache()
    )
    with pytest.raises(FarmLocationMissingError):
        await service.get_by_farm(user, farm.id)


async def test_unknown_farm_raises(db_session):
    user = await _make_user(db_session)
    service = WeatherService(
        db_session, provider=FakeProvider(build_raw()), cache=WeatherCache()
    )
    with pytest.raises(FarmNotFoundError):
        await service.get_by_farm(user, uuid.uuid4())


async def test_cache_avoids_a_second_upstream_call(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    provider = FakeProvider(build_raw())
    service = WeatherService(db_session, provider=provider, cache=WeatherCache())

    await service.get_by_farm(user, farm.id)
    await service.get_by_farm(user, farm.id)
    assert provider.calls == 1  # second read served from cache


async def test_get_by_coordinates_has_no_farm_name(db_session):
    service = WeatherService(
        db_session, provider=FakeProvider(build_raw()), cache=WeatherCache()
    )
    bundle = await service.get_by_coordinates(9.9, 78.1)
    assert bundle.location.name is None
    assert bundle.current.humidity_pct == 70
