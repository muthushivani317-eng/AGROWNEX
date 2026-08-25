from datetime import UTC, datetime

import pytest
from app.api.v1.router import api_router
from app.modules.action_verification.router import actions, detail
from app.modules.action_verification.schemas import ActionCreateIn
from app.modules.action_verification.service import ActionVerificationService
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from fastapi import FastAPI


def test_action_verification_routes_are_registered() -> None:
    app = FastAPI()
    app.include_router(api_router)
    paths = app.openapi()["paths"]

    assert "get" in paths["/action-verification/actions"]
    assert "post" in paths["/action-verification/actions"]
    assert "get" in paths["/action-verification/actions/{action_id}"]
    assert "post" in paths["/action-verification/actions/{action_id}/responses"]
    assert "get" in paths["/action-verification/actions/{action_id}/history"]


async def _action_owner(db_session):
    user = User(firebase_uid="action-api-owner", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Action API farm", crop="paddy", status="active")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


async def _create_action(db_session):
    user, farm = await _action_owner(db_session)
    service = ActionVerificationService(db_session)
    row = await service.create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="weather_to_action",
            source_record_id="weather:daily:rain",
            source_version="1",
            action_code="check_drainage",
            suggestion_time=datetime.now(UTC),
        ),
    )
    return user, service, row


@pytest.mark.asyncio
async def test_actions_list_maps_database_source_module_to_api_source_feature(db_session) -> None:
    user, service, _ = await _create_action(db_session)

    response = await actions(user, service)

    assert response.data is not None
    assert len(response.data) == 1
    assert response.data[0].source_feature == "weather_to_action"
    assert "source_module" not in response.data[0].model_dump()


@pytest.mark.asyncio
async def test_action_detail_maps_database_source_module_to_api_source_feature(db_session) -> None:
    user, service, row = await _create_action(db_session)

    response = await detail(row.id, user, service)

    assert response.data is not None
    assert response.data.source_feature == "weather_to_action"
    assert "source_module" not in response.data.model_dump()
