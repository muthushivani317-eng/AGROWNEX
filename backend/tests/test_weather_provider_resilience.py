"""Open-Meteo retry and notification-source isolation tests (no network)."""
from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from app.modules.auth.models import User
from app.modules.notifications.sources import NotificationSources
from app.modules.weather.exceptions import WeatherUnavailableError
from app.modules.weather.provider import OpenMeteoClient


async def _no_sleep(_delay: float) -> None:
    return None


async def test_open_meteo_503_retries_are_bounded(monkeypatch):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("app.modules.weather.provider.get_http_client", lambda: client)
    monkeypatch.setattr("app.modules.weather.provider.asyncio.sleep", _no_sleep)
    with pytest.raises(WeatherUnavailableError):
        await OpenMeteoClient(max_retries=3).fetch(9.9, 78.1)
    await client.aclose()
    assert calls == 3


async def _empty_source(self, user):
    return []


async def _unavailable_weather(self, user):
    raise WeatherUnavailableError()


async def test_weather_503_exhaustion_is_skipped_by_notification_source(
    db_session, monkeypatch
):
    user = User(firebase_uid="fb-weather-503", status="active")
    db_session.add(user)
    await db_session.flush()
    for name in (
        "calendar", "disease", "growth", "market", "schemes", "produce", "ai",
        "experts", "soil", "satellite", "nutrient", "intelligence",
    ):
        monkeypatch.setattr(NotificationSources, f"_collect_{name}", _empty_source)
    monkeypatch.setattr(NotificationSources, "_collect_weather", _unavailable_weather)
    events = await NotificationSources(
        db_session, now=datetime.now(UTC), enable_weather=True
    ).collect(user)
    assert events == []
