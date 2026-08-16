"""Background job unit tests (Phase 3 — ARQ). Mocked providers, no network."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.market.jobs import refresh_market_prices
from app.modules.market.models import MarketFavourite
from app.modules.market.provider import PriceQuery, ProviderPrice
from app.modules.notifications.engine import CandidateEvent
from app.modules.notifications.jobs import (
    evaluate_weather_alerts,
    retry_failed_notifications,
)
from app.modules.notifications.models import Notification, NotificationDeliveryLog
from app.modules.notifications.provider import DeliveryRequest, DeliveryResult
from app.modules.produce.constants import ProduceStatus
from app.modules.produce.jobs import EXPIRY_GRACE_DAYS, expire_stale_offers
from app.modules.produce.models import ProduceOffer
from app.modules.produce.repository import ProduceRepository


async def _user(db_session, uid: str = "fb-job") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


# --------------------------------------------------------------------------- #
# (a) refresh_market_prices
# --------------------------------------------------------------------------- #
class FakeMarketProvider:
    def __init__(self) -> None:
        self.queries: list[PriceQuery] = []

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        self.queries.append(query)
        return [
            ProviderPrice(
                commodity=query.commodity or "Paddy",
                variety="Common",
                market=query.market or "Thanjavur",
                district=query.district or "Thanjavur",
                state=query.state or "Tamil Nadu",
                minimum_price=1900,
                maximum_price=2100,
                modal_price=2000,
                unit="quintal",
                price_date=date.today(),
                source="mock",
            )
        ]


async def test_refresh_market_prices_refreshes_tracked_favourites(db_session):
    user = await _user(db_session, "fb-market-job")
    db_session.add(
        MarketFavourite(
            user_id=user.id,
            commodity="Paddy",
            market_name="Thanjavur",
            district="Thanjavur",
            state="Tamil Nadu",
        )
    )
    await db_session.flush()

    provider = FakeMarketProvider()
    result = await refresh_market_prices(db_session, provider=provider)

    assert result["targets"] == 1
    assert result["prices"] >= 1
    assert provider.queries[0].commodity == "Paddy"


async def test_refresh_market_prices_no_favourites_is_noop(db_session):
    result = await refresh_market_prices(db_session, provider=FakeMarketProvider())
    assert result == {"targets": 0, "refreshed_targets": 0, "prices": 0}


# --------------------------------------------------------------------------- #
# (b) evaluate_weather_alerts
# --------------------------------------------------------------------------- #
class FakeWeatherSources:
    """Emits a single weather alert candidate for the user's farm."""

    def __init__(self, farm_id: str) -> None:
        self.farm_id = farm_id

    async def collect(self, user) -> list[CandidateEvent]:
        return [
            CandidateEvent(
                module="weather",
                event_type="heavy_rain",
                dedup_key=f"wx-{user.id}",
                payload={"mm": 80},
                farm_id=self.farm_id,
            )
        ]


async def test_evaluate_weather_alerts_creates_notifications(db_session):
    user = await _user(db_session, "fb-wx-job")
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()

    result = await evaluate_weather_alerts(
        db_session, sources=FakeWeatherSources(str(farm.id))
    )

    assert result["farmers"] == 1
    assert result["notifications_created"] == 1


async def test_evaluate_weather_alerts_no_farms_is_noop(db_session):
    result = await evaluate_weather_alerts(db_session, sources=FakeWeatherSources("x"))
    assert result == {"farmers": 0, "notifications_created": 0}


# --------------------------------------------------------------------------- #
# (c) retry_failed_notifications
# --------------------------------------------------------------------------- #
class RecoveringProvider:
    """A push provider that now succeeds (simulating recovery)."""

    name = "fake"

    async def deliver(self, request: DeliveryRequest, *, channels) -> list[DeliveryResult]:
        return [DeliveryResult(channel=ch, status="delivered") for ch in channels]


async def _failed_notification(db_session, user, *, attempts: int = 1) -> Notification:
    notification = Notification(
        user_id=user.id,
        module="weather",
        event_type="heavy_rain",
        title_key="t",
        message_key="m",
        severity="warning",
        priority="high",
        dedup_key=f"n-{user.id}-{attempts}",
    )
    db_session.add(notification)
    await db_session.flush()
    for _ in range(attempts):
        db_session.add(
            NotificationDeliveryLog(
                notification_id=notification.id, channel="push", status="failed"
            )
        )
    await db_session.flush()
    return notification


async def test_retry_redelivers_failed_notification(db_session):
    user = await _user(db_session, "fb-retry-job")
    notification = await _failed_notification(db_session, user, attempts=1)

    result = await retry_failed_notifications(
        db_session, provider=RecoveringProvider(), max_retries=3
    )

    assert result["retried"] == 1
    assert result["delivered"] == 1
    await db_session.refresh(notification)
    assert notification.delivered_at is not None


async def test_retry_respects_max_attempts_cap(db_session):
    user = await _user(db_session, "fb-retry-cap")
    # Already tried 3 times → excluded from the retry queue.
    await _failed_notification(db_session, user, attempts=3)

    result = await retry_failed_notifications(
        db_session, provider=RecoveringProvider(), max_retries=3, now=datetime.now(UTC)
    )
    assert result["retried"] == 0


# --------------------------------------------------------------------------- #
# (d) expire_stale_offers
# --------------------------------------------------------------------------- #
async def _make_farm(db_session, user) -> Farm:
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    return farm


async def _offer(db_session, user, farm, *, harvest_date, status) -> ProduceOffer:
    offer = ProduceOffer(
        user_id=user.id,
        farm_id=farm.id,
        crop_name="Paddy",
        quantity=100,
        unit="kg",
        expected_harvest_date=harvest_date,
        status=status,
    )
    db_session.add(offer)
    await db_session.flush()
    return offer


async def test_expire_stale_offers_moves_long_overdue_open_offers(db_session):
    user = await _user(db_session, "fb-produce-expiry")
    farm = await _make_farm(db_session, user)
    today = date.today()
    stale = await _offer(
        db_session,
        user,
        farm,
        harvest_date=today - timedelta(days=EXPIRY_GRACE_DAYS + 1),
        status=ProduceStatus.SUBMITTED.value,
    )

    result = await expire_stale_offers(db_session)

    assert result["expired"] == 1
    await db_session.refresh(stale)
    assert stale.status == ProduceStatus.EXPIRED.value
    history = await ProduceRepository(db_session).list_status_history(stale.id)
    assert history[-1].new_status == ProduceStatus.EXPIRED.value
    assert history[-1].old_status == ProduceStatus.SUBMITTED.value


async def test_expire_stale_offers_leaves_recent_and_concluded_offers_alone(db_session):
    user = await _user(db_session, "fb-produce-expiry-2")
    farm = await _make_farm(db_session, user)
    today = date.today()
    recent = await _offer(
        db_session,
        user,
        farm,
        harvest_date=today - timedelta(days=1),
        status=ProduceStatus.SUBMITTED.value,
    )
    concluded = await _offer(
        db_session,
        user,
        farm,
        harvest_date=today - timedelta(days=EXPIRY_GRACE_DAYS + 30),
        status=ProduceStatus.HARVESTED.value,
    )

    result = await expire_stale_offers(db_session)

    assert result["expired"] == 0
    await db_session.refresh(recent)
    await db_session.refresh(concluded)
    assert recent.status == ProduceStatus.SUBMITTED.value
    assert concluded.status == ProduceStatus.HARVESTED.value
