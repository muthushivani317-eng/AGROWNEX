"""Graceful-degradation tests -- "missing data must never break the
workflow or become a false finding." Covers: PDF export disabled/failing
during Evidence Pack generation, no usable satellite scene for a signal
provider, and the zonal-analysis feature flag being off.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.modules.daily_task.evidence_pack import EvidencePackService
from app.modules.daily_task.schemas import EvidencePackTriggerRequest
from app.modules.daily_task.signal_providers import SowingGerminationProvider, UnevenGrowthZoneProvider
from app.modules.daily_task.zonal_analysis import ZonalAnalysisService
from app.modules.disease.storage import StorageUnavailableError
from app.modules.satellite.exceptions import SatelliteUnavailableError

pytestmark = pytest.mark.asyncio


class _FakeSatelliteServiceNoScenes:
    async def latest(self, user, farm_id):
        raise SatelliteUnavailableError()

    async def history(self, user, farm_id, *, page, page_size):
        return type("Page", (), {"items": []})()

    async def latest_waterlogging(self, user, farm_id):
        return None


class _FakeWeatherServiceNoData:
    async def get_by_farm(self, user, farm_id):
        return None


class _FakeUser:
    id = uuid.uuid4()


class _FakeFarm:
    def __init__(self):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.name = "Test Farmer"
        self.boundary = None
        self.crop = "paddy"
        self.sowing_date = None


class _FakeRepo:
    async def create_evidence_pack(self, **kwargs):
        return type("Pack", (), kwargs)()


async def test_evidence_pack_skips_pdf_when_flag_disabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "evidence_pack_pdf_enabled", False)
    service = EvidencePackService(
        repo=_FakeRepo(),
        satellite_service=_FakeSatelliteServiceNoScenes(),
        weather_service=_FakeWeatherServiceNoData(),
        storage=None,
    )
    farm = _FakeFarm()
    request = EvidencePackTriggerRequest(field_id=farm.id, event_type="heavy_rain", event_date_start=datetime.now(UTC))

    pack = await service.generate(_FakeUser(), farm, request)

    assert pack.imagery_degraded_reason == "pdf_export_disabled"
    assert pack.pdf_object_url is None
    assert pack.confidence_level == "limited"


async def test_evidence_pack_never_raises_on_storage_failure(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "evidence_pack_pdf_enabled", True)

    class _BoomStorage:
        async def put(self, **kwargs):
            raise StorageUnavailableError()

    service = EvidencePackService(
        repo=_FakeRepo(),
        satellite_service=_FakeSatelliteServiceNoScenes(),
        weather_service=_FakeWeatherServiceNoData(),
        storage=_BoomStorage(),
    )
    farm = _FakeFarm()
    request = EvidencePackTriggerRequest(field_id=farm.id, event_type="cyclone", event_date_start=datetime.now(UTC))

    pack = await service.generate(_FakeUser(), farm, request)  # must not raise

    assert pack.imagery_degraded_reason == "storage_unavailable"
    assert pack.pdf_object_url is None


async def test_uneven_growth_provider_returns_empty_when_zonal_flag_disabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uneven_growth_enabled", False)

    class _ZonalServiceThatWouldRaiseIfCalled:
        async def get_confirmed_zones(self, user, farm):
            raise AssertionError("get_confirmed_zones must not be called while the feature flag is off")

    provider = UnevenGrowthZoneProvider(_ZonalServiceThatWouldRaiseIfCalled())
    farm = _FakeFarm()
    signals = await provider.collect(_FakeUser(), farm)
    assert signals == []


async def test_zonal_analysis_returns_empty_with_no_usable_scene(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uneven_growth_enabled", True)

    class _FakeZoneRepo:
        async def expire_unconfirmed_zones_older_than(self, farm_id, *, days):
            return None

    service = ZonalAnalysisService(_FakeSatelliteServiceNoScenes(), _FakeZoneRepo())
    result = await service.refresh_and_confirm_zones(_FakeUser(), _FakeFarm())
    assert result == []  # absence of a usable scene must never be treated as "no weak zone found"


async def test_sowing_germination_provider_suppresses_on_no_usable_scene():
    """Cloud-cover through the whole emergence window must route to
    'insufficient data', never a false 'germination failed' claim.
    """
    from datetime import timedelta

    class _CalendarNoEvents:
        async def for_farm(self, user, farm_id, *, page, page_size):
            return []

    farm = _FakeFarm()
    farm.sowing_date = (datetime.now(UTC) - timedelta(days=60)).date()

    provider = SowingGerminationProvider(_CalendarNoEvents(), _FakeSatelliteServiceNoScenes())
    signals = await provider.collect(_FakeUser(), farm)
    assert signals == []
