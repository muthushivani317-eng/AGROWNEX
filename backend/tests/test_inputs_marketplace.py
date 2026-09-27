from decimal import Decimal

import pytest
from app.modules.auth.models import User
from app.modules.inputs_marketplace.exceptions import (
    CatalogItemUnavailableError,
    StaleCatalogPriceError,
)
from app.modules.inputs_marketplace.models import InputCatalogItem
from app.modules.inputs_marketplace.schemas import CartLineIn, PlaceOrderIn
from app.modules.inputs_marketplace.service import InputsMarketplaceService


async def _seed(db_session):
    user = User(firebase_uid="inputs-farmer", phone_number="+919999999999")
    item = InputCatalogItem(
        name="Paddy seed",
        category="seed",
        unit="5 kg bag",
        unit_price=Decimal("450.00"),
        stock_quantity=3,
        stock_version=1,
        is_active=True,
    )
    db_session.add_all([user, item])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(item)
    return user, item


def _payload(item, *, price=Decimal("450.00"), version=1, quantity=2):
    return PlaceOrderIn(
        items=[
            CartLineIn(
                catalog_item_id=item.id,
                quantity=quantity,
                expected_unit_price=price,
                expected_stock_version=version,
            )
        ],
        delivery_address="12 Main Road, Sample Village",
        idempotency_key="order-test-00000001",
    )


@pytest.mark.asyncio
async def test_checkout_snapshots_price_decrements_stock_and_is_idempotent(db_session):
    user, item = await _seed(db_session)
    service = InputsMarketplaceService(db_session)
    first = await service.place_order(user, _payload(item))
    second = await service.place_order(user, _payload(item))
    await db_session.refresh(item)
    assert first.id == second.id
    assert first.total_amount == Decimal("900.00")
    assert item.stock_quantity == 1
    assert item.stock_version == 2
    assert first.items[0].unit_price == Decimal("450.00")


@pytest.mark.asyncio
async def test_checkout_fails_closed_on_stale_price(db_session):
    user, item = await _seed(db_session)
    with pytest.raises(StaleCatalogPriceError):
        await InputsMarketplaceService(db_session).place_order(
            user, _payload(item, price=Decimal("400.00"))
        )


@pytest.mark.asyncio
async def test_checkout_fails_closed_on_insufficient_stock(db_session):
    user, item = await _seed(db_session)
    with pytest.raises(CatalogItemUnavailableError):
        await InputsMarketplaceService(db_session).place_order(user, _payload(item, quantity=4))

@pytest.mark.asyncio
async def test_crop_filter_keeps_untagged_general_items(db_session):
    general = InputCatalogItem(
        name="Vermicompost", category="fertilizer", unit="1 kg",
        unit_price=Decimal("250.00"), stock_quantity=10, stock_version=1, is_active=True,
    )
    paddy = InputCatalogItem(
        name="Paddy seed", category="seed", unit="5 kg bag", unit_price=Decimal("450.00"),
        stock_quantity=5, stock_version=1, is_active=True, crop_tags=",paddy,",
    )
    chilli = InputCatalogItem(
        name="Chilli seed", category="seed", unit="100 g", unit_price=Decimal("120.00"),
        stock_quantity=5, stock_version=1, is_active=True, crop_tags=",chilli,",
    )
    db_session.add_all([general, paddy, chilli])
    await db_session.commit()
    names = {i.name for i in await InputsMarketplaceService(db_session).catalog(crop="Paddy")}
    assert names == {"Vermicompost", "Paddy seed"}
