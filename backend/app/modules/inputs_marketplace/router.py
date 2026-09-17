from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.admin.dependencies import AdminContextDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.inputs_marketplace.dependencies import InputsServiceDep
from app.modules.inputs_marketplace.schemas import (
    AdminOrderUpdate,
    CashSummaryOut,
    CatalogItemOut,
    CatalogItemWrite,
    OrderOut,
    PlaceOrderIn,
)
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/inputs", tags=["inputs-marketplace"])
admin_router = APIRouter(prefix="/admin/inputs", tags=["admin-inputs-marketplace"])


@router.get("/catalog", response_model=SuccessResponse[list[CatalogItemOut]])
async def catalog(
    service: InputsServiceDep,
    user: CurrentUser,
    category: str | None = Query(None),
    crop: str | None = Query(None),
):
    del user
    return success(await service.catalog(category=category, crop=crop))


@router.post(
    "/orders", response_model=SuccessResponse[OrderOut], status_code=status.HTTP_201_CREATED
)
async def place_order(payload: PlaceOrderIn, user: CurrentUser, service: InputsServiceDep):
    return success(
        await service.place_order(user, payload), message="Order placed for cash on delivery"
    )


@router.get("/orders", response_model=SuccessResponse[list[OrderOut]])
async def order_history(user: CurrentUser, service: InputsServiceDep):
    return success(await service.orders_for_user(user))


@router.get("/orders/{order_id}", response_model=SuccessResponse[OrderOut])
async def order_detail(order_id: uuid.UUID, user: CurrentUser, service: InputsServiceDep):
    return success(await service.order_for_user(user, order_id))


@admin_router.get("/catalog", response_model=SuccessResponse[list[CatalogItemOut]])
async def admin_catalog(ctx: AdminContextDep, service: InputsServiceDep):
    service.require_admin(ctx)
    return success(await service.catalog(admin=True))


@admin_router.post(
    "/catalog", response_model=SuccessResponse[CatalogItemOut], status_code=status.HTTP_201_CREATED
)
async def create_catalog_item(
    payload: CatalogItemWrite, ctx: AdminContextDep, service: InputsServiceDep
):
    return success(await service.admin_upsert_item(ctx, payload))


@admin_router.put("/catalog/{item_id}", response_model=SuccessResponse[CatalogItemOut])
async def update_catalog_item(
    item_id: uuid.UUID, payload: CatalogItemWrite, ctx: AdminContextDep, service: InputsServiceDep
):
    return success(await service.admin_upsert_item(ctx, payload, item_id))


@admin_router.get("/orders", response_model=SuccessResponse[list[OrderOut]])
async def admin_orders(ctx: AdminContextDep, service: InputsServiceDep):
    return success(await service.admin_orders(ctx))


@admin_router.put("/orders/{order_id}/status", response_model=SuccessResponse[OrderOut])
async def update_order(
    order_id: uuid.UUID, payload: AdminOrderUpdate, ctx: AdminContextDep, service: InputsServiceDep
):
    return success(await service.admin_update_order(ctx, order_id, payload))


@admin_router.get("/cash-summary", response_model=SuccessResponse[CashSummaryOut])
async def cash_summary(ctx: AdminContextDep, service: InputsServiceDep):
    return success(await service.cash_summary(ctx))
