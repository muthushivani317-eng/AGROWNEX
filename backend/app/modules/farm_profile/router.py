"""Onboarding v2 farmer endpoints.

    GET  /farm-catalog                          standard items, units, needs, farmer types
    GET  /farmers/me/farm-items                 my crops / livestock / products
    PUT  /farmers/me/farm-items                 replace the whole list (Crops step)
    GET  /organic-partner/directory             FPOs / KVKs a farmer can join
    POST /organic-partner/organizations/{id}/join   farmer asks to join (with consent)

Profile extras (land holding, farmer type, landmark, needs) are optional
fields on the existing PUT /auth/profile and PUT /farmers/me.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.farm_profile import service
from app.modules.farm_profile.catalog import catalog_payload
from app.modules.farm_profile.schemas import FarmItemOut, FarmItemsIn, JoinRequestIn
from app.schemas.response import SuccessResponse, success

router = APIRouter(tags=["farm-profile"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/farm-catalog")
async def farm_catalog(_: CurrentUser):
    return success(catalog_payload())


@router.get("/farmers/me/farm-items", response_model=SuccessResponse[list[FarmItemOut]])
async def my_farm_items(session: Session, user: CurrentUser):
    return success([service.item_out(r) for r in await service.list_items(session, user.id)])


@router.put("/farmers/me/farm-items", response_model=SuccessResponse[list[FarmItemOut]])
async def replace_farm_items(body: FarmItemsIn, session: Session, user: CurrentUser):
    rows = await service.replace_items(session, user.id, body.items)
    return success([service.item_out(r) for r in rows], message="Saved")


@router.get("/organic-partner/directory")
async def partner_directory(
    session: Session,
    _: CurrentUser,
    kind: Literal["fpo", "kvk", "agri_community"] | None = None,
    district: Annotated[str | None, Query(max_length=80)] = None,
):
    return success(await service.directory(session, kind=kind, district=district))


@router.post("/organic-partner/organizations/{organization_id}/join")
async def join_organization(organization_id: uuid.UUID, body: JoinRequestIn, session: Session, user: CurrentUser):
    return success(await service.request_join(session, user, organization_id))
