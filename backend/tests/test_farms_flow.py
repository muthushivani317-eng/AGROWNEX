"""Integration tests for the Farm service (docs/API_CONTRACT.md → FARM MODULE).

Exercises the real repositories against the in-memory DB: CRUD, ownership
scoping, duplicate detection, boundary/area computation, manual override,
soft delete, filtering/pagination and images.
"""
from __future__ import annotations

import pytest
from app.modules.auth.models import User
from app.modules.farms.exceptions import (
    DuplicateFarmError,
    FarmNotFoundError,
    InvalidBoundaryError,
)
from app.modules.farms.schemas import (
    BoundaryIn,
    FarmMediaCreate,
    FarmWrite,
    LocationIn,
)
from app.modules.farms.service import FarmService


async def _make_user(db_session, uid: str = "fb-farm-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number=f"+9198765{uid[-4:].rjust(4, '0')}",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _square(side: float = 0.01, lat0: float = 9.9, lng0: float = 78.1) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lng0, lat0],
                [lng0 + side, lat0],
                [lng0 + side, lat0 + side],
                [lng0, lat0 + side],
                [lng0, lat0],
            ]
        ],
    }


async def test_create_minimal_farm(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)

    farm = await service.create_farm(user, FarmWrite(name="North Field"))
    assert farm.name == "North Field"
    assert farm.status == "active"
    assert farm.area_hectares is None
    assert farm.location is None
    assert farm.boundary is None


async def test_duplicate_name_rejected(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    await service.create_farm(user, FarmWrite(name="Paddy Plot"))
    with pytest.raises(DuplicateFarmError):
        await service.create_farm(user, FarmWrite(name="  paddy plot  "))


async def test_create_with_location_and_boundary_computes_area(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)

    farm = await service.create_farm(
        user,
        FarmWrite(
            name="Riverside",
            crop="paddy",
            crop_variety="ADT 43",
            soil_type="alluvial",
            irrigation_type="canal",
            water_source="river",
            location=LocationIn(
                latitude=9.9, longitude=78.1, district="madurai", block="Melur"
            ),
            boundary=BoundaryIn(geojson=_square()),
        ),
    )
    assert farm.location is not None
    assert farm.location.district == "madurai"
    assert farm.boundary is not None
    assert farm.boundary.vertex_count == 4
    assert farm.boundary.area_hectares is not None and farm.boundary.area_hectares > 0
    # Auto area equals the computed boundary area.
    assert farm.area_hectares == pytest.approx(farm.boundary.area_hectares)
    assert farm.soil_type == "alluvial"


async def test_manual_area_override_wins(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    farm = await service.create_farm(
        user,
        FarmWrite(
            name="Manual Area",
            area_source="manual",
            area_hectares=2.5,
            boundary=BoundaryIn(geojson=_square()),
        ),
    )
    assert farm.area_source == "manual"
    assert farm.area_hectares == 2.5
    # The boundary still records its own computed area.
    assert farm.boundary.area_hectares != 2.5


async def test_invalid_boundary_rejected_by_schema(db_session):
    # The schema validates the polygon before the service runs.
    with pytest.raises(ValueError):
        BoundaryIn(geojson={"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]})


async def test_service_rejects_invalid_boundary_defensively(db_session):
    service = FarmService(db_session)
    with pytest.raises(InvalidBoundaryError):
        # Bypass the schema by calling the metric helper with a bad ring.
        service._boundary_metrics({"type": "Polygon", "coordinates": [[[0, 0]]]})


async def test_get_and_list_and_filter(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    await service.create_farm(
        user,
        FarmWrite(
            name="Alpha",
            crop="paddy",
            status="active",
            location=LocationIn(district="madurai"),
        ),
    )
    await service.create_farm(
        user,
        FarmWrite(
            name="Beta",
            crop="cotton",
            status="harvested",
            location=LocationIn(district="salem"),
        ),
    )

    items, total = await service.list_farms(user, page=1, page_size=20)
    assert total == 2
    assert {f.name for f in items} == {"Alpha", "Beta"}

    by_crop, total_crop = await service.list_farms(
        user, page=1, page_size=20, crop="cotton"
    )
    assert total_crop == 1 and by_crop[0].name == "Beta"

    by_district, _ = await service.list_farms(
        user, page=1, page_size=20, district="madurai"
    )
    assert [f.name for f in by_district] == ["Alpha"]

    by_search, _ = await service.list_farms(user, page=1, page_size=20, search="alph")
    assert [f.name for f in by_search] == ["Alpha"]


async def test_pagination(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    for i in range(5):
        await service.create_farm(user, FarmWrite(name=f"Farm {i}"))
    page1, total = await service.list_farms(user, page=1, page_size=2)
    assert total == 5
    assert len(page1) == 2


async def test_update_farm_and_rename_conflict(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    a = await service.create_farm(user, FarmWrite(name="Old Name", crop="paddy"))
    await service.create_farm(user, FarmWrite(name="Taken"))

    updated = await service.update_farm(
        user, a.id, FarmWrite(name="New Name", crop="maize", status="harvested")
    )
    assert updated.id == a.id
    assert updated.name == "New Name"
    assert updated.crop == "maize"
    assert updated.status == "harvested"

    with pytest.raises(DuplicateFarmError):
        await service.update_farm(user, a.id, FarmWrite(name="Taken"))


async def test_soft_delete_hides_farm(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    farm = await service.create_farm(user, FarmWrite(name="Temp"))

    await service.delete_farm(user, farm.id)
    _, total = await service.list_farms(user, page=1, page_size=20)
    assert total == 0
    with pytest.raises(FarmNotFoundError):
        await service.get_farm(user, farm.id)


async def test_boundary_get_and_update(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    farm = await service.create_farm(user, FarmWrite(name="Boundaryless"))

    assert await service.get_boundary(user, farm.id) is None

    boundary = await service.update_boundary(
        user, farm.id, BoundaryIn(geojson=_square(side=0.02))
    )
    assert boundary.area_hectares is not None and boundary.area_hectares > 0

    refreshed = await service.get_farm(user, farm.id)
    # Auto area picked up the newly drawn boundary.
    assert refreshed.area_hectares == pytest.approx(boundary.area_hectares)


async def test_images_add_and_list(db_session):
    service = FarmService(db_session)
    user = await _make_user(db_session)
    farm = await service.create_farm(user, FarmWrite(name="With Photos"))

    await service.add_image(
        user, farm.id, FarmMediaCreate(file_url="https://cdn/a.jpg", caption="North")
    )
    await service.add_image(
        user, farm.id, FarmMediaCreate(file_url="https://cdn/b.jpg")
    )
    images = await service.list_images(user, farm.id)
    assert len(images) == 2
    assert images[0].uploaded_by == user.id


async def test_ownership_isolation(db_session):
    service = FarmService(db_session)
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await service.create_farm(owner, FarmWrite(name="Private"))

    with pytest.raises(FarmNotFoundError):
        await service.get_farm(other, farm.id)
    _, total = await service.list_farms(other, page=1, page_size=20)
    assert total == 0
