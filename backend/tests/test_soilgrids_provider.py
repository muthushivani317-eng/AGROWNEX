"""ISRIC SoilGrids remote-estimate provider (docs: real, free, no-key global
soil map -- a compiled model, never a fresh measurement; see provider.py's
module comment above SoilGridsProvider for the citation and unit-conversion
reasoning). These tests encode ISRIC's documented `properties/query` response
shape (name/unit_measure.d_factor/depths[].values) and verify the provider
never fabricates a value when that shape isn't met.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
from app.modules.soil.provider import SoilGridsProvider

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[79.1, 10.7], [79.2, 10.7], [79.2, 10.8], [79.1, 10.8], [79.1, 10.7]]],
}


def _soilgrids_response(
    *,
    ph_mean: float | None = 65,
    ph_low: float | None = 55,
    ph_high: float | None = 78,
    soc_mean: float | None = 245,
    soc_low: float | None = 120,
    soc_high: float | None = 400,
) -> httpx.Response:
    payload = {
        "properties": {
            "layers": [
                {
                    "name": "phh2o",
                    "unit_measure": {"d_factor": 10, "mapped_units": "pH*10", "target_units": "pH"},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "values": {"mean": ph_mean, "Q0.05": ph_low, "Q0.95": ph_high},
                        }
                    ],
                },
                {
                    "name": "soc",
                    "unit_measure": {"d_factor": 10, "mapped_units": "dg/kg", "target_units": "g/kg"},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "values": {"mean": soc_mean, "Q0.05": soc_low, "Q0.95": soc_high},
                        }
                    ],
                },
            ]
        }
    }
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.test"))


async def test_real_contract_produces_ph_and_organic_carbon_estimates() -> None:
    client = AsyncMock()
    client.get.return_value = _soilgrids_response()
    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(POLYGON)

    assert outcome.status == "available"
    by_indicator = {e.indicator: e for e in outcome.estimates}
    assert set(by_indicator) == {"ph", "organic_carbon"}

    ph = by_indicator["ph"]
    assert ph.value == 6.5  # raw 65 / d_factor 10
    assert ph.unit == "pH"
    assert ph.provider == "soilgrids"
    assert ph.resolution_m == 250.0
    assert ph.uncertainty_low == 5.5
    assert ph.uncertainty_high == 7.8

    oc = by_indicator["organic_carbon"]
    assert oc.value == 2.45  # (245 / 10) g/kg -> /10 -> percent
    assert oc.unit == "%"


def _texture_layer(name: str, mean: float) -> dict:
    return {
        "name": name,
        "unit_measure": {"d_factor": 10, "mapped_units": "dg/kg", "target_units": "g/kg"},
        "depths": [{"label": "0-5cm", "values": {"mean": mean, "Q0.05": mean - 10, "Q0.95": mean + 10}}],
    }


async def test_texture_composition_produces_three_percentage_estimates() -> None:
    """clay/sand/silt (2026-08-19, feeds the Soil Scan texture fallback) use
    the same g/kg -> % conversion already verified for organic carbon above."""
    client = AsyncMock()
    payload = {
        "properties": {
            "layers": [
                _texture_layer("clay", 320),  # 32.0%
                _texture_layer("sand", 410),  # 41.0%
                _texture_layer("silt", 270),  # 27.0%
            ]
        }
    }
    client.get.return_value = httpx.Response(
        200, json=payload, request=httpx.Request("GET", "https://example.test")
    )
    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(POLYGON)

    assert outcome.status == "available"
    by_indicator = {e.indicator: e for e in outcome.estimates}
    assert set(by_indicator) == {"clay_pct", "sand_pct", "silt_pct"}
    assert by_indicator["clay_pct"].value == 32.0
    assert by_indicator["sand_pct"].value == 41.0
    assert by_indicator["silt_pct"].value == 27.0
    assert by_indicator["clay_pct"].unit == "%"


async def test_masked_location_reports_no_data_never_fabricates() -> None:
    """SoilGrids returns a null mean for cells it can't estimate (e.g. open
    water) -- that must surface as an honest unavailable state, never a
    guessed value."""
    client = AsyncMock()
    client.get.return_value = _soilgrids_response(
        ph_mean=None, ph_low=None, ph_high=None, soc_mean=None, soc_low=None, soc_high=None
    )
    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(POLYGON)

    assert outcome.estimates == ()
    assert outcome.status == "remote_estimation_unavailable"
    assert outcome.reason == "no_data_for_location"


async def test_masked_centroid_falls_back_to_an_interior_field_point() -> None:
    client = AsyncMock()
    masked = _soilgrids_response(
        ph_mean=None, ph_low=None, ph_high=None, soc_mean=None, soc_low=None, soc_high=None
    )
    client.get.side_effect = [masked, _soilgrids_response()]

    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(POLYGON)

    assert outcome.status == "available"
    assert client.get.await_count == 2
    assert all(estimate.scene_id != "soilgrids:10.7500,79.1500" for estimate in outcome.estimates)


async def test_invalid_aoi_fails_closed_without_a_request() -> None:
    client = AsyncMock()
    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(
        {"type": "Point", "coordinates": [1, 2]}
    )

    assert outcome.status == "remote_estimation_unavailable"
    assert outcome.reason == "invalid_aoi"
    client.get.assert_not_called()


async def test_rate_limit_and_timeout_are_stable() -> None:
    limited_client = AsyncMock()
    limited_client.get.return_value = httpx.Response(
        429, request=httpx.Request("GET", "https://example.test")
    )
    outcome = await SoilGridsProvider(client=limited_client).fetch_remote_estimates(POLYGON)
    assert outcome.reason == "provider_rate_limited"

    timeout_client = AsyncMock()
    timeout_client.get.side_effect = httpx.TimeoutException("timeout")
    outcome = await SoilGridsProvider(client=timeout_client).fetch_remote_estimates(POLYGON)
    assert outcome.reason == "provider_timeout"


async def test_malformed_response_fails_closed_not_crash() -> None:
    client = AsyncMock()
    client.get.return_value = httpx.Response(
        200, json={"unexpected": True}, request=httpx.Request("GET", "https://example.test")
    )
    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(POLYGON)

    assert outcome.estimates == ()
    assert outcome.status == "remote_estimation_unavailable"


async def test_unknown_property_in_response_is_ignored_not_invented() -> None:
    """An ISRIC property this provider doesn't map (e.g. bulk density) must be
    skipped, not coerced into one of our known indicators. (clay/sand/silt
    used to be the example here -- they're mapped now, see
    test_texture_composition_produces_three_percentage_estimates below.)"""
    client = AsyncMock()
    payload = {
        "properties": {
            "layers": [
                {
                    "name": "bdod",
                    "unit_measure": {"d_factor": 10},
                    "depths": [{"label": "0-5cm", "values": {"mean": 300}}],
                }
            ]
        }
    }
    client.get.return_value = httpx.Response(
        200, json=payload, request=httpx.Request("GET", "https://example.test")
    )
    outcome = await SoilGridsProvider(client=client).fetch_remote_estimates(POLYGON)

    assert outcome.estimates == ()
    assert outcome.status == "remote_estimation_unavailable"
