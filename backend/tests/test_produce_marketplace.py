from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from app.modules.admin.schemas import ProcurementRowOut
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.produce.constants import ProduceAvailabilityType, ProduceCategory, ProduceUnit
from app.modules.produce.exceptions import InvalidProduceError
from app.modules.produce.provider import MockProduceProvider
from app.modules.produce.schemas import (
    ProduceImageIn,
    ProduceListFilters,
    ProduceOfferCreate,
    ProduceOfferUpdate,
)
from app.modules.produce.service import ProduceService
from pydantic import ValidationError


def test_admin_procurement_contract_exposes_marketplace_fields():
    row = ProcurementRowOut(
        offer_id=uuid.uuid4(),
        listing_ref="AGP-TEST",
        farmer_ref="AGF-TEST",
        crop="Paddy",
        product_category="grains",
        availability_type="available_now",
        quantity=10,
        unit="kg",
        variety=None,
        expected_grade=None,
        harvest_date=None,
        village="Vadaku",
        district="Cuddalore",
        farmer_name="Farmer",
        offer_status="draft",
        admin_status="new",
    )
    payload = row.model_dump()
    assert payload["product_category"] == "grains"
    assert payload["availability_type"] == "available_now"


def test_produce_thumbnail_requires_same_https_storage_policy():
    with pytest.raises(ValidationError, match="thumbnail_url must be an HTTPS"):
        ProduceImageIn(
            image_url="https://cdn.example.test/full.jpg",
            thumbnail_url="http://cdn.example.test/thumb.jpg",
        )

TODAY = date(2026, 8, 28)


async def _farmer_and_farm(db_session, uid: str = "marketplace-owner"):
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Marketplace field")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


def _service(db_session):
    return ProduceService(db_session, provider=MockProduceProvider(), today=TODAY)


async def test_available_now_custom_agricultural_produce_persists_without_harvest_date(db_session):
    user, farm = await _farmer_and_farm(db_session)
    offer = await _service(db_session).create_offer(
        user,
        ProduceOfferCreate(
            farm_id=farm.id,
            product_name="Fresh moringa leaves",
            category=ProduceCategory.OTHER_PRODUCE,
            availability_type=ProduceAvailabilityType.AVAILABLE_NOW,
            quantity=25,
            unit=ProduceUnit.KG,
            packaging="Ventilated crate",
            price_unit="kg",
            negotiable=True,
            pickup_location="Farm gate",
            pickup_available=True,
        ),
    )
    assert offer.crop_name == "Fresh moringa leaves"
    assert offer.product_category == "other_produce"
    assert offer.availability_type == "available_now"
    assert offer.expected_harvest_date is None
    assert offer.packaging == "Ventilated crate"
    assert offer.price_unit == "kg"
    assert offer.negotiable is True
    assert offer.pickup_location == "Farm gate"


def test_upcoming_harvest_requires_non_past_date_and_legacy_payload_remains_valid():
    legacy = ProduceOfferCreate(
        farm_id="3d32729b-68fb-4d65-b585-e0a37859d4bf",
        crop_name="Paddy",
        quantity=2,
        unit=ProduceUnit.QUINTAL,
        expected_harvest_date=TODAY + timedelta(days=5),
    )
    assert legacy.product_name == "Paddy"
    assert legacy.category == ProduceCategory.GRAINS
    assert legacy.availability_type == ProduceAvailabilityType.UPCOMING_HARVEST

    unknown_legacy = ProduceOfferCreate(
        farm_id=legacy.farm_id,
        crop_name="Unreviewed field item",
        quantity=2,
        unit=ProduceUnit.KG,
        expected_harvest_date=TODAY + timedelta(days=5),
    )
    assert unknown_legacy.status.value == "draft"
    assert unknown_legacy.category == ProduceCategory.OTHER_PRODUCE

    with pytest.raises(ValidationError, match="expected_harvest_date"):
        ProduceOfferCreate(
            farm_id=legacy.farm_id,
            product_name="Banana",
            quantity=5,
            unit=ProduceUnit.KG,
            availability_type=ProduceAvailabilityType.UPCOMING_HARVEST,
        )


@pytest.mark.parametrize(
    "name",
    ["Organic pesticide", "Urea fertilizer", "Veterinary medicine", "Live goats"],
)
def test_regulated_or_non_produce_items_are_rejected(name):
    with pytest.raises(ValidationError, match="agricultural produce"):
        ProduceOfferCreate(
            farm_id="3d32729b-68fb-4d65-b585-e0a37859d4bf",
            product_name=name,
            category=ProduceCategory.OTHER_PRODUCE,
            availability_type=ProduceAvailabilityType.AVAILABLE_NOW,
            quantity=1,
            unit=ProduceUnit.KG,
        )


async def test_category_and_availability_filters_remain_owner_scoped(db_session):
    owner, farm = await _farmer_and_farm(db_session)
    other, other_farm = await _farmer_and_farm(db_session, "marketplace-other")
    service = _service(db_session)
    for user, owned_farm, name, category in (
        (owner, farm, "Tomato", ProduceCategory.VEGETABLES),
        (owner, farm, "Turmeric", ProduceCategory.SPICES),
        (other, other_farm, "Tomato", ProduceCategory.VEGETABLES),
    ):
        await service.create_offer(
            user,
            ProduceOfferCreate(
                farm_id=owned_farm.id,
                product_name=name,
                category=category,
                availability_type=ProduceAvailabilityType.AVAILABLE_NOW,
                quantity=10,
                unit=ProduceUnit.KG,
            ),
        )
    page, _ = await service.list_offers(
        owner,
        ProduceListFilters(
            category=ProduceCategory.VEGETABLES,
            availability_type=ProduceAvailabilityType.AVAILABLE_NOW,
        ),
    )
    assert [item.crop_name for item in page.items] == ["Tomato"]


def test_update_schema_rejects_identity_and_internal_buyer_overposting():
    with pytest.raises(ValidationError):
        ProduceOfferUpdate.model_validate(
            {
                "packaging": "Sack",
                "user_id": "3d32729b-68fb-4d65-b585-e0a37859d4bf",
                "buyer_match": {"buyer": "hidden"},
                "procurement_reference": "forged",
            }
        )


async def test_available_now_update_clears_legacy_harvest_date(db_session):
    user, farm = await _farmer_and_farm(db_session)
    service = _service(db_session)
    offer = await service.create_offer(
        user,
        ProduceOfferCreate(
            farm_id=farm.id,
            crop_name="Paddy",
            quantity=2,
            unit=ProduceUnit.QUINTAL,
            expected_harvest_date=TODAY + timedelta(days=5),
        ),
    )
    updated, _ = await service.update_offer(
        user,
        offer.id,
        ProduceOfferUpdate(availability_type=ProduceAvailabilityType.AVAILABLE_NOW),
    )
    assert updated.expected_harvest_date is None
    assert updated.availability_type == "available_now"

    with pytest.raises(InvalidProduceError, match="expected harvest date"):
        await service.update_offer(
            user,
            offer.id,
            ProduceOfferUpdate(availability_type=ProduceAvailabilityType.UPCOMING_HARVEST),
        )


async def test_update_rejects_regulated_product_name(db_session):
    user, farm = await _farmer_and_farm(db_session)
    service = _service(db_session)
    offer = await service.create_offer(
        user,
        ProduceOfferCreate(
            farm_id=farm.id,
            product_name="Tomato",
            availability_type=ProduceAvailabilityType.AVAILABLE_NOW,
            quantity=2,
            unit=ProduceUnit.KG,
        ),
    )
    with pytest.raises(InvalidProduceError, match="agricultural produce"):
        await service.update_offer(user, offer.id, ProduceOfferUpdate(product_name="Pesticide"))
