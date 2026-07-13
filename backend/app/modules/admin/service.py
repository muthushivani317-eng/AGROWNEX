"""Admin service (docs: Repository → Service → Admin Engine → Provider → API).

Enforces admin RBAC, **audits every action** (docs/SECURITY.md — audit is immutable),
aggregates read-only metrics through the Admin Engine, and delivers broadcasts by
reusing the Notification engine. Farmer data is never modified here; the only writes are
admin-domain rows (audit, broadcast, announcement, admin status changes). Business logic
lives here; routes stay thin.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.admin.constants import (
    AdminPermission,
    AdminUserStatus,
    AuditAction,
    BroadcastScheduleType,
    BroadcastStatus,
    BroadcastTargetType,
    ProcurementStatus,
    permissions_for,
)
from app.modules.admin.engine import build_overview, procurement_analytics
from app.modules.admin.exceptions import (
    AdminSuspendedError,
    FarmerNotFoundError,
    InvalidBroadcastError,
    InvalidProcurementStatusError,
    NotAnAdminError,
    OfferNotFoundError,
    PermissionDeniedError,
)
from app.modules.admin.metrics import AdminMetrics
from app.modules.admin.models import (
    AdminUser,
    AuditLog,
    BroadcastMessage,
    SystemAnnouncement,
)
from app.modules.admin.provider import BroadcastProvider, get_default_broadcast_provider
from app.modules.admin.queries import AdminQueries
from app.modules.admin.repository import AdminRepository
from app.modules.auth.models import User
from app.schemas.response import PaginatedData

logger = get_logger("admin.service")


@dataclass
class AdminContext:
    admin: AdminUser
    permissions: frozenset[str]
    ip_address: str | None = None


class AdminService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        now: datetime | None = None,
        broadcast_provider: BroadcastProvider | None = None,
    ) -> None:
        self.session = session
        self.repo = AdminRepository(session)
        self.queries = AdminQueries(session)
        self.metrics = AdminMetrics(session, now=now)
        self.broadcast_provider = broadcast_provider or get_default_broadcast_provider()
        self._now = now

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    # ----------------------------------------------------------------- #
    # Auth + permissions + audit
    # ----------------------------------------------------------------- #
    async def resolve_admin(self, user: User, *, ip_address: str | None = None) -> AdminContext:
        admin = await self.repo.get_admin_by_user(user.id)
        if admin is None:
            raise NotAnAdminError()
        if admin.status != AdminUserStatus.ACTIVE.value:
            raise AdminSuspendedError()
        perms = frozenset(permissions_for(admin.role))
        return AdminContext(admin=admin, permissions=perms, ip_address=ip_address)

    def _require(self, ctx: AdminContext, permission: AdminPermission) -> None:
        if permission.value not in ctx.permissions:
            raise PermissionDeniedError()

    async def _audit(
        self,
        ctx: AdminContext,
        action: AuditAction,
        *,
        target: str | None = None,
        target_id: str | None = None,
        meta: dict | None = None,
    ) -> None:
        await self.repo.add_audit(
            AuditLog(
                admin_id=ctx.admin.id,
                role=ctx.admin.role,
                action=action.value,
                target=target,
                target_id=target_id,
                ip_address=ctx.ip_address,
                meta=meta,
            )
        )

    # ----------------------------------------------------------------- #
    # Dashboard
    # ----------------------------------------------------------------- #
    async def dashboard(self, ctx: AdminContext) -> dict:
        self._require(ctx, AdminPermission.VIEW_DASHBOARD)
        counts = await self.metrics.overview()
        cards = build_overview(counts)
        procurement_counts = await self.repo.procurement_status_counts()
        await self._audit(ctx, AuditAction.VIEW_DASHBOARD)
        return {
            "cards": cards,
            "counts": counts,
            "procurement_status_counts": procurement_counts,
            "generated_at": self._now_dt(),
        }

    # ----------------------------------------------------------------- #
    # Farmer management
    # ----------------------------------------------------------------- #
    async def farmers(
        self,
        ctx: AdminContext,
        *,
        search: str | None,
        district: str | None,
        crop: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedData:
        self._require(ctx, AdminPermission.MANAGE_FARMERS)
        offset = (page - 1) * page_size
        rows, total = await self.queries.farmers(
            search=search, district=district, crop=crop, limit=page_size, offset=offset
        )
        await self._audit(ctx, AuditAction.VIEW_FARMERS, meta={"search": search})
        return _paginate(rows, page, page_size, total)

    async def farmer_detail(self, ctx: AdminContext, user_id: uuid.UUID) -> dict:
        self._require(ctx, AdminPermission.MANAGE_FARMERS)
        detail = await self.queries.farmer_detail(user_id)
        if detail is None:
            raise FarmerNotFoundError()
        await self._audit(
            ctx, AuditAction.VIEW_FARMER_DETAIL, target="farmer", target_id=str(user_id)
        )
        return detail

    # ----------------------------------------------------------------- #
    # Analytics
    # ----------------------------------------------------------------- #
    async def analytics(self, ctx: AdminContext) -> dict:
        self._require(ctx, AdminPermission.VIEW_ANALYTICS)
        data = await self.metrics.analytics()
        await self._audit(ctx, AuditAction.VIEW_ANALYTICS)
        return data

    # ----------------------------------------------------------------- #
    # Procurement
    # ----------------------------------------------------------------- #
    async def procurement(
        self,
        ctx: AdminContext,
        *,
        crop: str | None,
        village: str | None,
        district: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        offset = (page - 1) * page_size
        rows, total = await self.queries.procurement_offers(
            crop=crop, village=village, district=district, limit=page_size, offset=offset
        )
        status_map = await self.repo.procurement_status_map([r.offer_id for r in rows])
        facts = await self.queries.procurement_facts()
        analytics = procurement_analytics(facts)
        await self._audit(ctx, AuditAction.VIEW_PROCUREMENT)
        items = [
            {"row": r, "admin_status": status_map.get(str(r.offer_id), ProcurementStatus.NEW.value)}
            for r in rows
        ]
        return {
            "page": _paginate(items, page, page_size, total),
            "analytics": analytics,
        }

    async def update_procurement_status(
        self,
        ctx: AdminContext,
        offer_id: uuid.UUID,
        status: str,
        *,
        note: str | None = None,
    ) -> str:
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        if status not in {s.value for s in ProcurementStatus}:
            raise InvalidProcurementStatusError()
        if not await self.queries.offer_exists(offer_id):
            raise OfferNotFoundError()
        previous = await self.repo.procurement_status_of(offer_id)
        await self._audit(
            ctx,
            AuditAction.PROCUREMENT_STATUS_CHANGED,
            target="procurement",
            target_id=str(offer_id),
            meta={"status": status, "previous": previous, "note": note},
        )
        await self.session.flush()
        logger.info(
            "procurement %s: %s → %s by admin=%s", offer_id, previous, status, ctx.admin.id
        )
        return status

    # ----------------------------------------------------------------- #
    # AI monitoring
    # ----------------------------------------------------------------- #
    async def ai_monitoring(self, ctx: AdminContext) -> dict:
        self._require(ctx, AdminPermission.VIEW_AI)
        data = await self.metrics.ai_monitoring()
        await self._audit(ctx, AuditAction.VIEW_AI)
        return data

    # ----------------------------------------------------------------- #
    # Notification management
    # ----------------------------------------------------------------- #
    async def notifications_overview(
        self, ctx: AdminContext, *, page: int, page_size: int
    ) -> dict:
        self._require(ctx, AdminPermission.SEND_BROADCAST)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_broadcasts(limit=page_size, offset=offset)
        sent = sum(b.delivered_count for b in rows)
        await self._audit(ctx, AuditAction.VIEW_NOTIFICATIONS)
        return {
            "broadcasts": _paginate(rows, page, page_size, total),
            "delivered_total": sent,
        }

    async def broadcast(
        self,
        ctx: AdminContext,
        *,
        title: str,
        body: str,
        language: str,
        target_type: str,
        target_value: str | None,
        schedule_type: str,
        scheduled_for: datetime | None,
    ) -> BroadcastMessage:
        self._require(ctx, AdminPermission.SEND_BROADCAST)
        if not title.strip() or not body.strip():
            raise InvalidBroadcastError("Title and body are required.")
        if target_type not in {t.value for t in BroadcastTargetType}:
            raise InvalidBroadcastError("Invalid target type.")
        if target_type != BroadcastTargetType.ALL.value and not target_value:
            raise InvalidBroadcastError("A target value is required for this target type.")

        immediate = schedule_type == BroadcastScheduleType.IMMEDIATE.value
        recipients = await self.queries.recipient_ids(target_type, target_value)

        broadcast = BroadcastMessage(
            admin_id=ctx.admin.id,
            title=title.strip(),
            body=body.strip(),
            language=language,
            target_type=target_type,
            target_value=target_value,
            schedule_type=schedule_type,
            scheduled_for=scheduled_for,
            status=BroadcastStatus.SENT.value if immediate else BroadcastStatus.QUEUED.value,
            recipient_count=len(recipients),
        )
        await self.repo.add_broadcast(broadcast)

        if immediate:
            delivered = await self.broadcast_provider.deliver(
                self.session, broadcast, recipients
            )
            broadcast.delivered_count = delivered
            broadcast.sent_at = self._now_dt()

        await self._audit(
            ctx,
            AuditAction.BROADCAST_SENT,
            target="broadcast",
            target_id=str(broadcast.id),
            meta={
                "target_type": target_type,
                "target_value": target_value,
                "recipients": len(recipients),
                "immediate": immediate,
            },
        )
        await self.session.flush()
        await self.session.refresh(broadcast)
        return broadcast

    # ----------------------------------------------------------------- #
    # Content management (announcements)
    # ----------------------------------------------------------------- #
    async def create_announcement(
        self,
        ctx: AdminContext,
        *,
        title: str,
        body: str,
        language: str,
        category: str | None,
        audience: str,
    ) -> SystemAnnouncement:
        self._require(ctx, AdminPermission.MANAGE_CONTENT)
        if not title.strip() or not body.strip():
            raise InvalidBroadcastError("Title and body are required.")
        announcement = SystemAnnouncement(
            admin_id=ctx.admin.id,
            title=title.strip(),
            body=body.strip(),
            language=language,
            category=category,
            audience=audience,
        )
        await self.repo.add_announcement(announcement)
        await self._audit(
            ctx,
            AuditAction.ANNOUNCEMENT_CREATED,
            target="announcement",
            target_id=str(announcement.id),
        )
        await self.session.flush()
        return announcement

    async def announcements(
        self, ctx: AdminContext, *, page: int, page_size: int
    ) -> PaginatedData:
        self._require(ctx, AdminPermission.VIEW_DASHBOARD)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_announcements(limit=page_size, offset=offset)
        return _paginate(rows, page, page_size, total)

    # ----------------------------------------------------------------- #
    # Audit
    # ----------------------------------------------------------------- #
    async def audit(
        self,
        ctx: AdminContext,
        *,
        action: str | None,
        target: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedData:
        self._require(ctx, AdminPermission.VIEW_AUDIT)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_audit(
            action=action, target=target, limit=page_size, offset=offset
        )
        await self._audit(ctx, AuditAction.VIEW_AUDIT)
        return _paginate(rows, page, page_size, total)


def _paginate(items: list, page: int, page_size: int, total: int) -> PaginatedData:
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedData(
        items=items, page=page, page_size=page_size, total=total, total_pages=total_pages
    )
