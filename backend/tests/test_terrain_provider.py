from unittest.mock import AsyncMock

import httpx
from app.modules.soil.terrain import OpenMeteoElevationProvider

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[79.1, 10.7], [79.2, 10.7], [79.2, 10.8], [79.1, 10.8], [79.1, 10.7]]],
}


async def test_real_elevation_samples_produce_screening_slope_evidence() -> None:
    client = AsyncMock()
    client.get.return_value = httpx.Response(
        200,
        json={"elevation": [100.0, 100.0, 130.0, 130.0, 100.0]},
        request=httpx.Request("GET", "https://example.test"),
    )

    outcome = await OpenMeteoElevationProvider(client).fetch(POLYGON)

    assert outcome.state == "available"
    assert len(outcome.observations) == 1
    observation = outcome.observations[0]
    assert observation.source == "open_meteo_elevation"
    assert observation.slope_class in {"flat", "gentle", "moderate", "steep"}
    assert observation.mean_slope_degrees is not None
    assert observation.elevation_range_m == 30.0


async def test_missing_elevation_values_fail_closed() -> None:
    client = AsyncMock()
    client.get.return_value = httpx.Response(
        200,
        json={"elevation": [None]},
        request=httpx.Request("GET", "https://example.test"),
    )

    outcome = await OpenMeteoElevationProvider(client).fetch(POLYGON)

    assert outcome.state == "unavailable"
    assert outcome.reason == "terrain_no_data"
