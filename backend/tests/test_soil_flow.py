"""Integration tests for the Soil service: report submission, profile merge,
generic recommendations, history, the honest 'no data' dashboard and ownership
(in-memory DB, mock provider, fixed 'now')."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.modules.auth.models import User
from app.modules.farms.models import Farm, FarmBoundary, FarmLocation
from app.modules.satellite.models import SatelliteSession
from app.modules.soil.constants import SoilSource
from app.modules.soil.exceptions import (
    FarmNotOwnedError,
    InvalidSoilReportError,
    SoilDataUnavailableError,
)
from app.modules.soil.provider import MockSoilProvider, UnavailableSoilProvider
from app.modules.soil.schemas import SoilReportCreate, SoilValuesIn
from app.modules.soil.service import SoilService

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


async def _make_user(db_session, uid: str = "fb-soil") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user, *, soil_type="Sandy loam") -> Farm:
    farm = Farm(user_id=user.id, name="Field A", soil_type=soil_type)
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(
        farm_id=farm.id, district="Thanjavur", latitude=10.7, longitude=79.1
    )
    await db_session.flush()
    return farm


def _service(db_session) -> SoilService:
    return SoilService(db_session, provider=MockSoilProvider(), now=NOW)


def _report(farm_id, **values) -> SoilReportCreate:
    return SoilReportCreate(
        farm_id=farm_id,
        source=SoilSource.SOIL_HEALTH_CARD,
        test_date=date(2026, 7, 1),
        values=SoilValuesIn(**values),
    )


# --------------------------------------------------------------------------- #
# Submit report
# --------------------------------------------------------------------------- #
async def test_submit_report_builds_profile_and_recommendations(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    profile, report = await service.submit_report(
        user, _report(farm.id, ph=5.2, organic_carbon=0.3, nitrogen=200, potassium=100)
    )
    assert report.status == "processed"
    assert report.confidence == 90  # soil_health_card
    assert profile.ph == 5.2
    assert profile.soil_type == "Sandy loam"  # inherited from the farm
    assert profile.latitude == 10.7

    recs = await service.recommendations(user, farm.id)
    codes = {r.code for r in recs}
    assert "soil.rec.ph.strongly_acidic" in codes
    assert "soil.rec.nitrogen.low" in codes

    dashboard = await service.get_dashboard(user, farm.id)
    assert {item["evidence_type"] for item in dashboard["indicator_evidence"]} == {"user_entered"}
    assert all(
        item["verification_state"] == "unverified" for item in dashboard["indicator_evidence"]
    )


async def test_submit_requires_a_value_or_image(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    with pytest.raises(InvalidSoilReportError):
        await service.submit_report(user, _report(farm.id))


async def test_submit_with_image_only_is_allowed(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    data = SoilReportCreate(farm_id=farm.id, report_url="https://r2/soil-card.jpg")
    _profile, report = await service.submit_report(user, data)
    assert report.report_url == "https://r2/soil-card.jpg"


async def test_submit_requires_owned_farm(db_session) -> None:
    owner = await _make_user(db_session, uid="owner")
    other = await _make_user(db_session, uid="other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    with pytest.raises(FarmNotOwnedError):
        await service.submit_report(other, _report(farm.id, ph=6.5))


async def test_remote_estimation_returns_explicit_unavailable_without_fabrication(
    db_session,
) -> None:
    user = await _make_user(db_session, uid="remote-owner")
    farm = await _make_farm(db_session, user)
    farm.boundary = FarmBoundary(
        farm_id=farm.id,
        geojson={
            "type": "Polygon",
            "coordinates": [[[79.0, 10.7], [79.1, 10.7], [79.1, 10.8], [79.0, 10.7]]],
        },
    )
    await db_session.flush()
    service = SoilService(db_session, provider=UnavailableSoilProvider(), now=NOW)

    outcome = await service.remote_estimation(user, farm.id)

    assert outcome.status == "remote_estimation_unavailable"
    assert outcome.reason == "provider_not_configured"
    assert outcome.estimates == ()


async def test_second_report_merges_and_keeps_prior_values(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.submit_report(user, _report(farm.id, ph=6.0, nitrogen=200))
    profile, _ = await service.submit_report(user, _report(farm.id, potassium=100))
    assert profile.potassium == 100  # new value
    assert profile.nitrogen == 200  # retained from the earlier report
    assert profile.ph == 6.0


# --------------------------------------------------------------------------- #
# Dashboard (honest 'no data')
# --------------------------------------------------------------------------- #
async def test_dashboard_without_data_is_honest(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    data = await service.get_dashboard(user, farm.id)
    assert data["has_data"] is False
    assert data["message_code"] == "soil.status.no_data"
    assert data["profile"] is None
    # A sandy-soil baseline recommendation is offered (from the farmer's soil type).
    assert any(r.code == "soil.rec.water_holding.sandy" for r in data["recommendations"])


async def test_dashboard_with_data(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.submit_report(user, _report(farm.id, ph=7.0, nitrogen=600))
    data = await service.get_dashboard(user, farm.id)
    assert data["has_data"] is True
    assert data["assessment"].nitrogen == "high"
    assert data["latest_report"] is not None


# --------------------------------------------------------------------------- #
# Latest / history
# --------------------------------------------------------------------------- #
async def test_latest_requires_a_report(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    with pytest.raises(SoilDataUnavailableError):
        await service.latest(user, farm.id)
    await service.submit_report(user, _report(farm.id, ph=6.5))
    report = await service.latest(user, farm.id)
    assert report.test_date == date(2026, 7, 1)


async def test_history_accumulates_snapshots(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.submit_report(user, _report(farm.id, ph=6.0))
    await service.submit_report(user, _report(farm.id, ph=6.4))
    page = await service.history(user, farm.id, page=1, page_size=10)
    assert page.total == 2


async def test_provider_never_fabricates(db_session) -> None:
    # The mock provider returns no external soil data — values stay farmer-sourced.
    provider = MockSoilProvider()
    assert await provider.fetch_location_soil(10.7, 79.1) is None
    assert await provider.parse_report("https://r2/x.jpg", "image/jpeg") is None


async def test_soil_scan_is_append_only_and_latest_is_farm_scoped(db_session) -> None:
    user = await _make_user(db_session, uid="scan-owner")
    farm = await _make_farm(db_session, user)
    farm.boundary = FarmBoundary(
        farm_id=farm.id,
        geojson={
            "type": "Polygon",
            "coordinates": [[[79.0, 10.7], [79.2, 10.7], [79.2, 10.9], [79.0, 10.9], [79.0, 10.7]]],
        },
    )
    await db_session.flush()

    class NoWeather:
        async def get_by_farm(self, _user, _farm_id):
            raise RuntimeError("weather unavailable")

    # Two distinct service instances with distinct injected clocks -- a fixed
    # 'now' shared across both calls would give both scans the identical
    # generated_at (and, on SQLite, the identical whole-second created_at
    # too), leaving latest_scan()'s ORDER BY with no column to break the tie
    # and making "latest" nondeterministic. Real requests always carry
    # microsecond-distinct timestamps; this test asserts the real guarantee
    # -- the more-recently-generated scan is 'latest' -- rather than
    # accidentally depending on undefined same-timestamp tie-breaking
    # (2026-08 pre-release audit).
    first_service = SoilService(
        db_session,
        provider=UnavailableSoilProvider(),
        weather_service=NoWeather(),
        now=NOW,
    )
    second_service = SoilService(
        db_session,
        provider=UnavailableSoilProvider(),
        weather_service=NoWeather(),
        now=NOW + timedelta(minutes=5),
    )

    first = await first_service.run_soil_scan(user, farm.id)
    second = await second_service.run_soil_scan(user, farm.id)
    history = await second_service.scan_history(user, farm.id, page=1, page_size=10)
    latest = await second_service.latest_soil_scan(user, farm.id)

    assert first.id != second.id
    assert history.total == 2
    assert latest.id == second.id
    assert latest.aoi_geojson == farm.boundary.geojson
    assert latest.provider_states["terrain"] == "unavailable"


async def test_scan_and_sampling_plan_are_owner_isolated(db_session) -> None:
    owner = await _make_user(db_session, uid="scan-owner-2")
    other = await _make_user(db_session, uid="scan-other-2")
    farm = await _make_farm(db_session, owner)
    with pytest.raises(FarmNotOwnedError):
        await SoilService(db_session, provider=UnavailableSoilProvider()).scan_history(
            other, farm.id, page=1, page_size=10
        )


async def test_non_sample_spatial_satellite_product_persists_inside_aoi_plan(db_session) -> None:
    user = await _make_user(db_session, uid="spatial-owner")
    farm = await _make_farm(db_session, user)
    farm.boundary = FarmBoundary(
        farm_id=farm.id,
        geojson={
            "type": "Polygon",
            "coordinates": [[[79.0, 10.7], [79.2, 10.7], [79.2, 10.9], [79.0, 10.9], [79.0, 10.7]]],
        },
    )
    db_session.add(
        SatelliteSession(
            user_id=user.id,
            farm_id=farm.id,
            provider="copernicus-sentinel-2-l2a",
            status="available",
            unavailable_reason="none",
            is_sample=False,
            capture_date=date(2026, 8, 10),
            moisture_status="relatively_dry",
            confidence=70,
            session_metadata={
                "scene_id": "S2-real-scene",
                "spatial_variability_zones": [
                    {
                        "zone_id": "field-zone-a",
                        "variability_class": "higher_variability",
                        "quality": "usable",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [79.05, 10.75],
                                    [79.1, 10.75],
                                    [79.1, 10.8],
                                    [79.05, 10.8],
                                    [79.05, 10.75],
                                ]
                            ],
                        },
                    }
                ],
            },
        )
    )
    await db_session.flush()

    class NoWeather:
        async def get_by_farm(self, _user, _farm_id):
            raise RuntimeError("weather unavailable")

    row = await SoilService(
        db_session, provider=UnavailableSoilProvider(), weather_service=NoWeather()
    ).run_soil_scan(user, farm.id)
    assert row.sampling_plan is not None
    assert row.sampling_plan["points"] == [
        {
            "zone_id": "field-zone-a",
            "longitude": 79.075,
            "latitude": 10.775,
            "source": "copernicus-sentinel-2-l2a",
            "reference": "S2-real-scene",
            "reason": "spatial_variability:higher_variability",
            "quality": "usable",
            "sample_data": False,
        }
    ]
    assert row.provenance["production_mock_used"] is False
