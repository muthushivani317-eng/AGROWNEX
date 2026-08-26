from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from app.modules.admin.metrics import AdminMetrics
from app.modules.auth.models import User
from app.modules.farms.models import Farm, FarmLocation
from app.modules.growth.models import CropStageState
from app.modules.produce.models import ProduceOffer

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


async def _farm(db_session, uid: str, *, crop: str, village: str, area: float | None):
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name=uid, crop=crop, area_hectares=area)
    db_session.add(farm)
    await db_session.flush()
    db_session.add(
        FarmLocation(
            farm_id=farm.id,
            district="Tirunelveli",
            village=village,
            source="manual",
        )
    )
    await db_session.flush()
    return user, farm


@pytest.mark.asyncio
async def test_crop_intelligence_answers_location_crop_and_harvest_window(db_session):
    first_user, first = await _farm(
        db_session, "banana-one", crop="Banana", village="Ambasamudram", area=2.5
    )
    second_user, second = await _farm(
        db_session, "banana-two", crop="banana", village="Ambasamudram", area=None
    )
    await _farm(db_session, "paddy-one", crop="Paddy", village="Palayamkottai", area=4)

    db_session.add(
        CropStageState(
            user_id=first_user.id,
            farm_id=first.id,
            crop_cycle_id="banana-2026",
            state="confirmed",
            suggested_stage="flowering",
            confirmed_stage="fruiting",
            calculation_version="test",
            evidence_snapshot={},
        )
    )
    db_session.add_all(
        [
            ProduceOffer(
                user_id=first_user.id,
                farm_id=first.id,
                crop_name="Banana",
                quantity=1000,
                available_quantity=800,
                unit="kg",
                expected_harvest_date=date(2026, 8, 1),
                status="submitted",
            ),
            ProduceOffer(
                user_id=second_user.id,
                farm_id=second.id,
                crop_name="Banana",
                quantity=2,
                unit="tonne",
                expected_harvest_date=date(2026, 10, 1),
                status="planned",
            ),
        ]
    )
    await db_session.flush()

    data = await AdminMetrics(db_session, now=NOW).crop_intelligence(
        crop="banana", district="tirunelveli", harvest_days=30
    )

    assert data["summary"] == {
        "farmer_count": 2,
        "farm_count": 2,
        "known_area_hectares": 2.5,
        "farms_with_area": 1,
        "farms_without_area": 1,
        "recorded_stage_farms": 1,
        "sale_listing_count": 2,
        "harvest_window_farmer_count": 1,
        "harvest_window_listing_count": 1,
    }
    assert data["crop_stages"] == [{"label": "fruiting", "farm_count": 1}]
    assert data["offered_quantities"] == [
        {"unit": "kg", "quantity": 800.0},
        {"unit": "tonne", "quantity": 2.0},
    ]
    assert data["by_location"][0]["label"] == "Tirunelveli / Ambasamudram"
