from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.core.exceptions import ForbiddenError, ValidationError
from app.modules.admin.constants import AdminPermission
from app.modules.admin.service import AdminContext
from app.modules.auth.models import User
from app.modules.inputs_marketplace.constants import STATUS_TRANSITIONS, InputOrderStatus
from app.modules.inputs_marketplace.exceptions import (
    CatalogItemUnavailableError,
    InputOrderNotFoundError,
    InvalidOrderTransitionError,
    StaleCatalogPriceError,
)
from app.modules.inputs_marketplace.models import (
    InputCatalogItem,
    InputOrder,
    InputOrderEvent,
    InputOrderItem,
)
from app.modules.inputs_marketplace.schemas import (
    AdminOrderUpdate,
    CashSummaryOut,
    CatalogItemOut,
    CatalogItemWrite,
    OrderEventOut,
    OrderItemOut,
    OrderOut,
    PlaceOrderIn,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _catalog_out(item: InputCatalogItem) -> CatalogItemOut:
    return CatalogItemOut(
        id=item.id,
        name=item.name,
        name_ta=item.name_ta,
        category=item.category,
        unit=item.unit,
        unit_price=item.unit_price,
        stock_quantity=item.stock_quantity,
        stock_version=item.stock_version,
        crop_tags=[x for x in (item.crop_tags or "").split(",") if x],
        description=item.description,
        is_active=item.is_active,
        updated_at=item.updated_at,
    )


def _order_out(order: InputOrder) -> OrderOut:
    return OrderOut(
        id=order.id,
        order_ref=order.order_ref,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        delivery_address=order.delivery_address,
        delivery_eta=order.delivery_eta,
        cash_collected_at=order.cash_collected_at,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                product_name=x.product_name_snapshot,
                category=x.category_snapshot,
                unit=x.unit_snapshot,
                unit_price=x.unit_price_snapshot,
                quantity=x.quantity,
                line_total=x.line_total,
            )
            for x in order.items
        ],
        events=[
            OrderEventOut(
                event_type=x.event_type,
                old_status=x.old_status,
                new_status=x.new_status,
                amount=x.amount,
                created_at=x.created_at,
            )
            for x in order.events
        ],
    )


class InputsMarketplaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def require_admin(ctx: AdminContext) -> None:
        if AdminPermission.MANAGE_PROCUREMENT.value not in ctx.permissions:
            raise ForbiddenError(
                "Inputs marketplace access is required.", error_code="admin_permission_denied"
            )

    async def catalog(
        self, *, category: str | None = None, crop: str | None = None, admin: bool = False
    ) -> list[CatalogItemOut]:
        stmt = select(InputCatalogItem).where(InputCatalogItem.is_deleted.is_(False))
        if not admin:
            stmt = stmt.where(
                InputCatalogItem.is_active.is_(True), InputCatalogItem.stock_quantity > 0
            )
        if category:
            stmt = stmt.where(InputCatalogItem.category == category)
        if crop:
            normalized_crop = crop.strip().lower()
            stmt = stmt.where(InputCatalogItem.crop_tags.ilike(f"%,{normalized_crop},%"))
        rows = (await self.session.execute(stmt.order_by(InputCatalogItem.name))).scalars().all()
        return [_catalog_out(row) for row in rows]

    async def place_order(self, user: User, payload: PlaceOrderIn) -> OrderOut:
        existing = (
            await self.session.execute(
                select(InputOrder).where(
                    InputOrder.user_id == user.id,
                    InputOrder.idempotency_key == payload.idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return _order_out(existing)
        ids = [line.catalog_item_id for line in payload.items]
        if len(ids) != len(set(ids)):
            raise ValidationError(
                "Duplicate cart items are not allowed.", error_code="duplicate_cart_item"
            )
        locked = (
            (
                await self.session.execute(
                    select(InputCatalogItem).where(InputCatalogItem.id.in_(ids)).with_for_update()
                )
            )
            .scalars()
            .all()
        )
        by_id = {item.id: item for item in locked}
        order = InputOrder(
            user_id=user.id,
            order_ref=f"AGI-{datetime.now(UTC):%Y%m%d}-{uuid.uuid4().hex[:10].upper()}",
            status=InputOrderStatus.PLACED.value,
            total_amount=Decimal("0.00"),
            delivery_address=payload.delivery_address.strip(),
            idempotency_key=payload.idempotency_key,
        )
        total = Decimal("0.00")
        for line in payload.items:
            item = by_id.get(line.catalog_item_id)
            if (
                item is None
                or item.is_deleted
                or not item.is_active
                or item.stock_quantity < line.quantity
            ):
                raise CatalogItemUnavailableError()
            if (
                item.unit_price != line.expected_unit_price
                or item.stock_version != line.expected_stock_version
            ):
                raise StaleCatalogPriceError()
            item.stock_quantity -= line.quantity
            item.stock_version += 1
            line_total = item.unit_price * line.quantity
            total += line_total
            order.items.append(
                InputOrderItem(
                    catalog_item_id=item.id,
                    product_name_snapshot=item.name,
                    category_snapshot=item.category,
                    unit_snapshot=item.unit,
                    unit_price_snapshot=item.unit_price,
                    quantity=line.quantity,
                    line_total=line_total,
                )
            )
        order.total_amount = total
        order.events.append(
            InputOrderEvent(
                event_type="order_placed",
                new_status=order.status,
                actor_user_id=user.id,
                amount=total,
            )
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return _order_out(order)

    async def orders_for_user(self, user: User) -> list[OrderOut]:
        rows = (
            (
                await self.session.execute(
                    select(InputOrder)
                    .where(InputOrder.user_id == user.id)
                    .order_by(InputOrder.created_at.desc())
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return [_order_out(row) for row in rows]

    async def order_for_user(self, user: User, order_id: uuid.UUID) -> OrderOut:
        order = (
            await self.session.execute(
                select(InputOrder).where(InputOrder.id == order_id, InputOrder.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not order:
            raise InputOrderNotFoundError()
        return _order_out(order)

    async def admin_upsert_item(
        self, ctx: AdminContext, payload: CatalogItemWrite, item_id: uuid.UUID | None = None
    ) -> CatalogItemOut:
        self.require_admin(ctx)
        item = await self.session.get(InputCatalogItem, item_id) if item_id else InputCatalogItem()
        if item is None or item.is_deleted:
            raise CatalogItemUnavailableError()
        old_price = item.unit_price if item_id else None
        for key, value in payload.model_dump(exclude={"crop_tags"}).items():
            setattr(item, key, value)
        tags = sorted({tag.strip().lower() for tag in payload.crop_tags if tag.strip()})
        item.crop_tags = f",{','.join(tags)}," if tags else None
        if item_id and old_price != item.unit_price:
            item.stock_version += 1
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return _catalog_out(item)

    async def admin_orders(self, ctx: AdminContext) -> list[OrderOut]:
        self.require_admin(ctx)
        rows = (
            (await self.session.execute(select(InputOrder).order_by(InputOrder.created_at.desc())))
            .scalars()
            .unique()
            .all()
        )
        return [_order_out(row) for row in rows]

    async def admin_update_order(
        self, ctx: AdminContext, order_id: uuid.UUID, payload: AdminOrderUpdate
    ) -> OrderOut:
        self.require_admin(ctx)
        order = await self.session.get(InputOrder, order_id, with_for_update=True)
        if not order:
            raise InputOrderNotFoundError()
        current, target = InputOrderStatus(order.status), payload.status
        if target not in STATUS_TRANSITIONS[current]:
            raise InvalidOrderTransitionError()
        old = order.status
        order.status = target.value
        if payload.delivery_eta is not None:
            order.delivery_eta = payload.delivery_eta
        amount = None
        event_type = "status_changed"
        if target is InputOrderStatus.DELIVERED:
            order.cash_collected_at = datetime.now(UTC)
            order.cash_collected_by_admin_id = ctx.admin.id
            amount = order.total_amount
            event_type = "delivered_cash_collected"
        order.events.append(
            InputOrderEvent(
                event_type=event_type,
                old_status=old,
                new_status=target.value,
                actor_admin_id=ctx.admin.id,
                amount=amount,
                note=payload.note,
            )
        )
        await self.session.commit()
        await self.session.refresh(order)
        return _order_out(order)

    async def cash_summary(self, ctx: AdminContext) -> CashSummaryOut:
        self.require_admin(ctx)
        row = (
            await self.session.execute(
                select(
                    func.count(InputOrder.id), func.coalesce(func.sum(InputOrder.total_amount), 0)
                ).where(InputOrder.cash_collected_at.is_not(None))
            )
        ).one()
        return CashSummaryOut(delivered_orders=row[0], cash_collected_total=row[1])
