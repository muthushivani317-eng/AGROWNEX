"""Integration tests for the produce service, provider, validation and snapshot
(in-memory DB, mock provider, fixed 'today')."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from app.modules.auth.models import User
from app.modules.farms.models import Farm, FarmLocation
from app.modules.market.provider import ProviderPrice
from app.modules.market.repository import MarketRepository
from app.modules.produce.constants import ProduceStatus, ProduceUnit
from app.modules.produce.exceptions import (
    FarmNotOwnedError,
    InvalidProduceError,
    InvalidStatusTransitionError,
    ProduceOfferNotFoundError,
)
from app.modules.produce.provider import MockProduceProvider
from app.modules.produce.schemas import (
    ProduceImageIn,
    ProduceListFilters,
    ProduceOfferCreate,
    ProduceOfferUpdate,
)
from app.modules.produce.service import ProduceService

TODAY = date(2026, 7, 11)


async def _make_user(db_session, uid: str = "fb-produce") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user, *, district="Thanjavur", **kwargs) -> Farm:
    farm = Farm(user_id=user.id, name=kwargs.pop("name", "Field A"), **kwargs)
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(
        farm_id=farm.id, district=district, block="Block-1", village="Village-1"
    )
    await db_session.flush()
    return farm


async def _seed_price(
    db_session, *, commodity="Paddy", district="Thanjavur", modal=2050.0
) -> None:
    repo = MarketRepository(db_session)
    await repo.save_prices(
        [
            ProviderPrice(
                commodity=commodity,
                variety="Common",
                market=f"{district} Mandi",
                district=district,
                state="Tamil Nadu",
                minimum_price=modal - 100,
                maximum_price=modal + 100,
                modal_price=modal,
                unit="quintal",
                price_date=TODAY,
                source="agmarknet",
            )
        ]
    )
    await db_session.flush()


def _service(db_session) -> ProduceService:
    return ProduceService(db_session, provider=MockProduceProvider(), today=TODAY)


def _create_payload(farm_id, **overrides) -> ProduceOfferCreate:
    data = {
        "farm_id": farm_id,
        "crop_name": "Paddy",
        "quantity": 20.0,
        "unit": ProduceUnit.QUINTAL,
        "expected_harvest_date": TODAY + timedelta(days=10),
    }
    data.update(overrides)
    return ProduceOfferCreate(**data)


# --------------------------------------------------------------------------- #
# Create + validation
# --------------------------------------------------------------------------- #
async def test_create_offer_persists_and_derives_location_from_farm(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    offer = await service.create_offer(user, _create_payload(farm.id))
    assert offer.id is not None
    assert offer.user_id == user.id
    assert offer.district == "Thanjavur"  # inherited from the farm location
    assert offer.block == "Block-1"
    assert offer.status == ProduceStatus.SUBMITTED.value


async def test_create_rejects_past_harvest_date(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    with pytest.raises(InvalidProduceError):
        await service.create_offer(
            user, _create_payload(farm.id, expected_harvest_date=TODAY - timedelta(days=1))
        )


async def test_create_rejects_non_positive_quantity_at_schema() -> None:
    # Quantity <= 0 is rejected by the schema before it reaches the service.
    with pytest.raises(ValueError):
        _create_payload(uuid.uuid4(), quantity=0)


async def test_create_requires_owned_farm(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    with pytest.raises(FarmNotOwnedError):
        await service.create_offer(other, _create_payload(farm.id))


async def test_create_routes_to_provider_and_records_status(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    offer = await service.create_offer(user, _create_payload(farm.id))
    # Submitted offers are acknowledged by the (mock) procurement channel.
    assert offer.procurement_channel == "mock"
    assert offer.procurement_reference is not None
    assert offer.procurement_reference.startswith("MOCK-")

    _, insight = await service.get_offer(user, offer.id)
    history = offer.status_history
    assert len(history) == 1
    assert history[0].new_status == ProduceStatus.SUBMITTED.value


async def test_draft_offer_is_not_submitted_to_provider(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(
        user, _create_payload(farm.id, status=ProduceStatus.DRAFT)
    )
    assert offer.procurement_reference is None
    assert offer.status == ProduceStatus.DRAFT.value


# --------------------------------------------------------------------------- #
# Verified market-price snapshot (never fabricated)
# --------------------------------------------------------------------------- #
async def test_snapshot_uses_verified_market_price_when_available(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _seed_price(db_session, commodity="Paddy", district="Thanjavur", modal=2050.0)
    service = _service(db_session)

    offer = await service.create_offer(user, _create_payload(farm.id))
    assert offer.current_market_price_snapshot == 2050.0
    assert offer.market_price_source == "agmarknet"
    assert offer.market_price_unit == "quintal"

    _, insight = await service.get_offer(user, offer.id)
    # 20 quintal × ₹2,050 → ₹41,000.
    assert insight.estimated_market_value == 41000.0
    assert insight.price_reference is not None
    assert insight.price_reference.source == "agmarknet"


async def test_snapshot_is_null_when_no_verified_price(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)  # no market price seeded
    offer = await service.create_offer(user, _create_payload(farm.id, crop_name="Ragi"))
    assert offer.current_market_price_snapshot is None
    _, insight = await service.get_offer(user, offer.id)
    assert insight.estimated_market_value is None  # never fabricated


# --------------------------------------------------------------------------- #
# List / get / upcoming / history
# --------------------------------------------------------------------------- #
async def test_list_offers_paginates_and_carries_insight(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    for i in range(3):
        await service.create_offer(
            user, _create_payload(farm.id, crop_name=f"Crop{i}")
        )
    page, insights = await service.list_offers(
        user, ProduceListFilters(page=1, page_size=2)
    )
    assert page.total == 3
    assert len(page.items) == 2
    assert page.total_pages == 2
    assert all(o.id in insights for o in page.items)


async def test_list_filters_by_crop_and_farm(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.create_offer(user, _create_payload(farm.id, crop_name="Paddy"))
    await service.create_offer(user, _create_payload(farm.id, crop_name="Maize"))
    page, _ = await service.list_offers(
        user, ProduceListFilters(crop="paddy", farm_id=farm.id)
    )
    assert page.total == 1
    assert page.items[0].crop_name == "Paddy"


async def test_get_offer_ownership_enforced(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    offer = await service.create_offer(owner, _create_payload(farm.id))
    with pytest.raises(ProduceOfferNotFoundError):
        await service.get_offer(other, offer.id)
    with pytest.raises(ProduceOfferNotFoundError):
        await service.get_offer(owner, uuid.uuid4())


async def test_upcoming_orders_by_harvest_and_excludes_past(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.create_offer(
        user,
        _create_payload(
            farm.id, crop_name="Turmeric", expected_harvest_date=TODAY + timedelta(days=30)
        ),
    )
    await service.create_offer(
        user,
        _create_payload(
            farm.id, crop_name="Tomato", expected_harvest_date=TODAY + timedelta(days=3)
        ),
    )
    page, _ = await service.upcoming(user, page=1, page_size=10)
    assert [o.crop_name for o in page.items] == ["Tomato", "Turmeric"]


async def test_history_shows_only_concluded_offers(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.create_offer(user, _create_payload(farm.id, crop_name="Paddy"))
    concluded = await service.create_offer(user, _create_payload(farm.id, crop_name="Banana"))
    await service.update_offer(
        user, concluded.id, ProduceOfferUpdate(status=ProduceStatus.HARVESTED)
    )

    page, _ = await service.history(user, page=1, page_size=10)
    crops = {o.crop_name for o in page.items}
    assert "Banana" in crops
    assert "Paddy" not in crops


# --------------------------------------------------------------------------- #
# Update / delete
# --------------------------------------------------------------------------- #
async def test_update_offer_partial_and_revalidates_harvest(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id))

    updated, _ = await service.update_offer(
        user, offer.id, ProduceOfferUpdate(quantity=50.0, notes="Bigger harvest")
    )
    assert updated.quantity == 50.0
    assert updated.notes == "Bigger harvest"

    with pytest.raises(InvalidProduceError):
        await service.update_offer(
            user, offer.id,
            ProduceOfferUpdate(expected_harvest_date=TODAY - timedelta(days=2)),
        )


async def test_update_refreezes_snapshot_when_crop_changes(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _seed_price(db_session, commodity="Maize", district="Thanjavur", modal=1800.0)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id, crop_name="Paddy"))
    assert offer.current_market_price_snapshot is None  # no Paddy price seeded

    updated, _ = await service.update_offer(
        user, offer.id, ProduceOfferUpdate(crop_name="Maize")
    )
    assert updated.current_market_price_snapshot == 1800.0


async def test_update_rejects_non_farmer_settable_status(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id))
    with pytest.raises(InvalidStatusTransitionError):
        await service.update_offer(
            user, offer.id, ProduceOfferUpdate(status=ProduceStatus.FULFILLED)
        )


async def test_withdraw_records_status_history(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id))
    updated, _ = await service.update_offer(
        user, offer.id, ProduceOfferUpdate(status=ProduceStatus.WITHDRAWN)
    )
    statuses = [h.new_status for h in updated.status_history]
    assert statuses == [ProduceStatus.SUBMITTED.value, ProduceStatus.WITHDRAWN.value]


async def test_delete_is_soft_and_hides_offer(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id))
    await service.delete_offer(user, offer.id)
    with pytest.raises(ProduceOfferNotFoundError):
        await service.get_offer(user, offer.id)
    page, _ = await service.list_offers(user, ProduceListFilters())
    assert page.total == 0


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #
async def test_create_with_images_and_add_more(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(
        user,
        _create_payload(
            farm.id,
            images=[ProduceImageIn(image_url="https://cdn/r2/a.jpg")],
        ),
    )
    offer, image = await service.add_image(
        user, offer.id, ProduceImageIn(image_url="https://cdn/r2/b.jpg")
    )
    images = await service.repo.list_images(offer.id)
    assert len(images) == 2
    assert [i.display_order for i in images] == [0, 1]


async def test_add_image_rejects_seventh_image(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id))
    for index in range(6):
        await service.add_image(
            user,
            offer.id,
            ProduceImageIn(image_url=f"https://cdn/r2/{index}.jpg"),
        )
    with pytest.raises(InvalidProduceError, match="at most 6 images"):
        await service.add_image(
            user,
            offer.id,
            ProduceImageIn(image_url="https://cdn/r2/seventh.jpg"),
        )


# --------------------------------------------------------------------------- #
# Provider abstraction + buyer interest (future-ready)
# --------------------------------------------------------------------------- #
async def test_provider_is_injectable(db_session) -> None:
    class RecordingProvider(MockProduceProvider):
        channel = "mock"

        def __init__(self) -> None:
            super().__init__(reference_factory=lambda: "fixed")
            self.calls = 0

        async def submit(self, offer):  # type: ignore[override]
            self.calls += 1
            return await super().submit(offer)

    provider = RecordingProvider()
    service = ProduceService(db_session, provider=provider, today=TODAY)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    offer = await service.create_offer(user, _create_payload(farm.id))
    assert provider.calls == 1
    assert offer.procurement_reference == "MOCK-FIXED"


async def test_buyer_interest_is_empty_in_v1(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    offer = await service.create_offer(user, _create_payload(farm.id))
    assert await service.buyer_interest(user, offer.id) == []
