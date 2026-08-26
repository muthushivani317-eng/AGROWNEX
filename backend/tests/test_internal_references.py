"""Stable human-readable references for farmer and produce operations."""

from datetime import date

from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.produce.models import ProduceOffer


async def test_farmer_and_listing_references_are_generated_and_unique(db_session) -> None:
    first = User(firebase_uid="ref-farmer-1", status="active")
    second = User(firebase_uid="ref-farmer-2", status="active")
    db_session.add_all([first, second])
    await db_session.flush()

    assert first.farmer_ref.startswith("AGF-")
    assert second.farmer_ref.startswith("AGF-")
    assert first.farmer_ref != second.farmer_ref

    farm = Farm(user_id=first.id, name="Reference field")
    db_session.add(farm)
    await db_session.flush()

    offers = [
        ProduceOffer(
            user_id=first.id,
            farm_id=farm.id,
            crop_name="Paddy",
            quantity=10,
            unit="quintal",
            expected_harvest_date=date(2026, 9, 1),
            status="submitted",
        ),
        ProduceOffer(
            user_id=first.id,
            farm_id=farm.id,
            crop_name="Paddy",
            quantity=12,
            unit="quintal",
            expected_harvest_date=date(2026, 9, 2),
            status="submitted",
        ),
    ]
    db_session.add_all(offers)
    await db_session.flush()

    assert all(offer.listing_ref.startswith("AGP-2026-") for offer in offers)
    assert offers[0].listing_ref != offers[1].listing_ref
