"""Admin repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

Owns the admin-domain tables (admin_users, roles/permissions, broadcasts,
announcements, audit_logs, dashboard widgets/preferences). The current procurement
status of an offer is derived from the immutable ``audit_logs`` (the last
``procurement_status_changed`` entry) — no farmer table is mutated.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.constants import (
    AuditAction,
    ProcurementStatus,
)
from app.modules.admin.models import (
    AdminUser,
    AuditLog,
    BroadcastMessage,
    SystemAnnouncement,
)


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Admin users
    # ----------------------------------------------------------------- #
    async def get_admin_by_user(self, user_id: uuid.UUID) -> AdminUser | None:
        res = await self.session.execute(
            select(AdminUser).where(
                AdminUser.user_id == user_id, AdminUser.is_deleted.is_(False)
            )
        )
        return res.scalar_one_or_none()

    async def add_admin(self, admin: AdminUser) -> AdminUser:
        self.session.add(admin)
        await self.session.flush()
        return admin

    # ----------------------------------------------------------------- #
    # Audit (immutable)
    # ----------------------------------------------------------------- #
    async def add_audit(self, entry: AuditLog) -> AuditLog:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_audit(
        self,
        *,
        action: str | None = None,
        target: str | None = None,
        admin_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        base: Select = select(AuditLog)
        if action:
            base = base.where(AuditLog.action == action)
        if target:
            base = base.where(AuditLog.target == target)
        if admin_id:
            base = base.where(AuditLog.admin_id == admin_id)
        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                base.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return list(rows), total

    # ----------------------------------------------------------------- #
    # Procurement status (derived from the audit trail — never fabricated)
    # ----------------------------------------------------------------- #
    async def procurement_status_map(
        self, offer_ids: list[uuid.UUID]
    ) -> dict[str, str]:
        """The latest admin procurement status per offer id (default ``new``)."""
        if not offer_ids:
            return {}
        ids = [str(i) for i in offer_ids]
        rows = (
            await self.session.execute(
                select(AuditLog)
                .where(
                    AuditLog.action == AuditAction.PROCUREMENT_STATUS_CHANGED.value,
                    AuditLog.target == "procurement",
                    AuditLog.target_id.in_(ids),
                )
                .order_by(AuditLog.created_at.asc())
            )
        ).scalars().all()
        out: dict[str, str] = {}
        for row in rows:  # ascending → the last write wins
            status = (row.meta or {}).get("status")
            if status:
                out[row.target_id or ""] = status
        return {oid: out.get(oid, ProcurementStatus.NEW.value) for oid in ids}

    async def procurement_status_of(self, offer_id: uuid.UUID) -> str:
        return (await self.procurement_status_map([offer_id])).get(
            str(offer_id), ProcurementStatus.NEW.value
        )

    async def procurement_status_counts(self) -> dict[str, int]:
        """Count offers currently in each admin procurement status (from the trail)."""
        rows = (
            await self.session.execute(
                select(AuditLog)
                .where(
                    AuditLog.action == AuditAction.PROCUREMENT_STATUS_CHANGED.value,
                    AuditLog.target == "procurement",
                )
                .order_by(AuditLog.created_at.asc())
            )
        ).scalars().all()
        latest: dict[str, str] = {}
        for row in rows:
            status = (row.meta or {}).get("status")
            if status and row.target_id:
                latest[row.target_id] = status
        counts: dict[str, int] = {}
        for status in latest.values():
            counts[status] = counts.get(status, 0) + 1
        return counts

    # ----------------------------------------------------------------- #
    # Broadcasts
    # ----------------------------------------------------------------- #
    async def add_broadcast(self, broadcast: BroadcastMessage) -> BroadcastMessage:
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def list_broadcasts(
        self, *, limit: int = 20, offset: int = 0
    ) -> tuple[list[BroadcastMessage], int]:
        base = select(BroadcastMessage).where(BroadcastMessage.is_deleted.is_(False))
        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                base.order_by(BroadcastMessage.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return list(rows), total

    # ----------------------------------------------------------------- #
    # Announcements
    # ----------------------------------------------------------------- #
    async def add_announcement(self, announcement: SystemAnnouncement) -> SystemAnnouncement:
        self.session.add(announcement)
        await self.session.flush()
        return announcement

    async def list_announcements(
        self, *, active_only: bool = False, limit: int = 20, offset: int = 0
    ) -> tuple[list[SystemAnnouncement], int]:
        base = select(SystemAnnouncement).where(SystemAnnouncement.is_deleted.is_(False))
        if active_only:
            base = base.where(SystemAnnouncement.is_active.is_(True))
        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                base.order_by(SystemAnnouncement.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return list(rows), total
