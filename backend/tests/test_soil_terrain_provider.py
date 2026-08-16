from app.modules.soil.terrain import UnavailableTerrainProvider


async def test_unconfigured_terrain_provider_fails_closed_without_values():
    result = await UnavailableTerrainProvider().fetch(
        {
            "type": "Polygon",
            "coordinates": [[[78.0, 11.0], [78.1, 11.0], [78.1, 11.1], [78.0, 11.0]]],
        }
    )
    assert result.state == "unavailable"
    assert result.observations == ()
    assert result.reason == "terrain_provider_not_configured"
