"""Integration tests for the growth repository (in-memory DB)."""
from __future__ import annotations

from datetime import UTC, datetime

from app.modules.auth.models import User
from app.modules.growth.models import (
    CropGrowthAnalysis,
    CropGrowthImage,
    CropGrowthSession,
    CropGrowthTimeline,
)
from app.modules.growth.repository import GrowthRepository


async def _user(db_session, uid: str = "fb-growth-repo") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _session(db_session, user: User, *, crop: str = "paddy") -> CropGrowthSession:
    from app.modules.farms.models import Farm

    farm = Farm(user_id=user.id, name="North Field", crop=crop)
    db_session.add(farm)
    await db_session.flush()
    session = CropGrowthSession(
        user_id=user.id, farm_id=farm.id, crop=crop, status="active", image_count=0
    )
    db_session.add(session)
    await db_session.flush()
    return session


async def _add_image(db_session, repo, user, session, *, week: int = 1) -> CropGrowthImage:
    image = await repo.add_image(
        CropGrowthImage(
            session_id=session.id,
            user_id=user.id,
            farm_id=session.farm_id,
            image_url=f"https://r2.mock.local/growth/{week}.jpg",
            capture_method="camera",
            captured_at=datetime.now(UTC),
            week_number=week,
        )
    )
    return image


async def test_session_add_get_and_find_active(db_session) -> None:
    repo = GrowthRepository(db_session)
    user = await _user(db_session)
    session = await _session(db_session, user)

    assert (await repo.get_session(session.id, user.id)).id == session.id
    found = await repo.find_active_session(user.id, session.farm_id, "paddy")
    assert found is not None and found.id == session.id
    # Wrong crop → no active session.
    assert await repo.find_active_session(user.id, session.farm_id, "wheat") is None


async def test_session_ownership_isolation(db_session) -> None:
    repo = GrowthRepository(db_session)
    owner = await _user(db_session, uid="own")
    other = await _user(db_session, uid="oth")
    session = await _session(db_session, owner)
    assert await repo.get_session(session.id, other.id) is None


async def test_active_sessions_for_user_filters_status_and_owner(db_session) -> None:
    repo = GrowthRepository(db_session)
    owner = await _user(db_session, uid="active-owner")
    other = await _user(db_session, uid="active-other")
    active_one = await _session(db_session, owner, crop="paddy")
    active_two = await _session(db_session, owner, crop="cotton")
    completed = await _session(db_session, owner, crop="groundnut")
    completed.status = "completed"
    await _session(db_session, other, crop="banana")
    await db_session.flush()

    sessions = await repo.active_sessions_for_user(owner.id)

    assert {session.id for session in sessions} == {active_one.id, active_two.id}


async def test_image_add_latest_and_count(db_session) -> None:
    repo = GrowthRepository(db_session)
    user = await _user(db_session)
    session = await _session(db_session, user)

    await _add_image(db_session, repo, user, session, week=1)
    img2 = await _add_image(db_session, repo, user, session, week=2)

    latest = await repo.latest_image_for_session(session.id)
    assert latest.id == img2.id
    assert await repo.count_images_for_session(session.id) == 2


async def test_latest_image_uses_deterministic_tie_breakers(db_session) -> None:
    repo = GrowthRepository(db_session)
    user = await _user(db_session)
    session = await _session(db_session, user)
    captured_at = datetime(2026, 1, 1, tzinfo=UTC)

    first = await repo.add_image(
        CropGrowthImage(
            session_id=session.id,
            user_id=user.id,
            farm_id=session.farm_id,
            image_url="https://r2.mock.local/growth/tie-week-1.jpg",
            capture_method="camera",
            captured_at=captured_at,
            week_number=1,
        )
    )
    second = await repo.add_image(
        CropGrowthImage(
            session_id=session.id,
            user_id=user.id,
            farm_id=session.farm_id,
            image_url="https://r2.mock.local/growth/tie-week-2.jpg",
            capture_method="camera",
            captured_at=captured_at,
            week_number=2,
        )
    )

    latest = await repo.latest_image_for_session(session.id)
    assert latest is not None
    assert latest.id == second.id
    assert latest.id != first.id


async def test_list_images_with_analysis_and_pagination(db_session) -> None:
    repo = GrowthRepository(db_session)
    user = await _user(db_session)
    session = await _session(db_session, user)
    img1 = await _add_image(db_session, repo, user, session, week=1)
    await _add_image(db_session, repo, user, session, week=2)
    await repo.add_analysis(
        CropGrowthAnalysis(
            image_id=img1.id,
            session_id=session.id,
            growth_stage="vegetative",
            plant_vigor="good",
            health_score=80,
        )
    )

    rows, total = await repo.list_images(user.id, session_id=session.id)
    assert total == 2
    # Newest first; the analysis is joined where present.
    by_image = {image.id: analysis for image, analysis in rows}
    assert by_image[img1.id] is not None
    assert by_image[img1.id].health_score == 80

    page1, _ = await repo.list_images(user.id, limit=1, offset=0)
    assert len(page1) == 1


async def test_timeline_add_latest_and_ordering(db_session) -> None:
    repo = GrowthRepository(db_session)
    user = await _user(db_session)
    session = await _session(db_session, user)
    img1 = await _add_image(db_session, repo, user, session, week=1)
    img2 = await _add_image(db_session, repo, user, session, week=2)

    await repo.add_timeline_entry(
        CropGrowthTimeline(
            session_id=session.id, user_id=user.id, image_id=img1.id,
            week_number=1, growth_stage="seedling", health_score=60, risk_level="low",
        )
    )
    e2 = await repo.add_timeline_entry(
        CropGrowthTimeline(
            session_id=session.id, user_id=user.id, image_id=img2.id,
            week_number=2, growth_stage="vegetative", health_score=75, risk_level="low",
        )
    )
    latest = await repo.latest_timeline_entry(session.id)
    assert latest.id == e2.id

    timeline = await repo.timeline_for_session(session.id)
    assert [entry.week_number for entry, _ in timeline] == [1, 2]
    assert timeline[0][1].id == img1.id  # image joined


async def test_delete_timeline_for_image(db_session) -> None:
    repo = GrowthRepository(db_session)
    user = await _user(db_session)
    session = await _session(db_session, user)
    img = await _add_image(db_session, repo, user, session, week=1)
    await repo.add_timeline_entry(
        CropGrowthTimeline(
            session_id=session.id, user_id=user.id, image_id=img.id,
            week_number=1, growth_stage="seedling", health_score=60, risk_level="low",
        )
    )
    await repo.delete_timeline_for_image(img.id)
    assert await repo.timeline_for_session(session.id) == []
