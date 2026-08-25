"""Admin platform ORM models (docs/DATABASE_SCHEMA.md → Administration domain).

Normalized tables for the AgrowAI team platform:

* ``admin_roles`` / ``admin_permissions`` — the RBAC master data (seeded from
  ``constants``; a new role/permission is a data change, never a redesign).
* ``admin_users``          — an authenticated user promoted to an admin (FK ``users.id``),
  with a role and status. Farmer data is never modified from here.
* ``broadcast_messages``   — every broadcast (history retained; delivery counts + status).
* ``system_announcements`` — team/farmer announcements (content management).
* ``audit_logs``           — an immutable row per admin action (role, action, target,
  target_id, ip_address). Also the source of truth for procurement status changes.
* ``dashboard_widgets``    — the master list of available dashboard widgets.
* ``dashboard_preferences``— a per-admin widget layout (enabled + position).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.admin.constants import (
    DEFAULT_LANGUAGE,
    AdminUserStatus,
    BroadcastStatus,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class AdminRoleModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "admin_roles"

    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AdminPermissionModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "admin_permissions"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class AdminUser(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "admin_users"
    __table_args__ = (UniqueConstraint("user_id", name="uq_admin_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(16), default=AdminUserStatus.ACTIVE.value, nullable=False, index=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BroadcastMessage(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "broadcast_messages"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("admin_users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default=DEFAULT_LANGUAGE, nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_value: Mapped[str | None] = mapped_column(String(120))
    schedule_type: Mapped[str] = mapped_column(String(12), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(12), default=BroadcastStatus.DRAFT.value, nullable=False, index=True
    )
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemAnnouncement(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "system_announcements"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("admin_users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default=DEFAULT_LANGUAGE, nullable=False)
    category: Mapped[str | None] = mapped_column(String(40))
    audience: Mapped[str] = mapped_column(String(12), default="all", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDMixin, TimestampMixin, Base):
    """Immutable audit trail (docs/SECURITY.md → audit logs are never deleted)."""

    __tablename__ = "audit_logs"

    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id"), index=True
    )
    role: Mapped[str | None] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    target: Mapped[str | None] = mapped_column(String(48), index=True)
    target_id: Mapped[str | None] = mapped_column(String(64), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    meta: Mapped[dict | None] = mapped_column(JSON)


class ProcurementCase(UUIDMixin, TimestampMixin, Base):
    """Internal sales-team workspace; never serialized by farmer-facing APIs."""

    __tablename__ = "procurement_cases"
    __table_args__ = (
        UniqueConstraint("offer_id", name="uq_procurement_case_offer"),
        CheckConstraint(
            "buyer_offer_quantity IS NULL OR buyer_offer_quantity > 0",
            name="ck_procurement_offer_qty_positive",
        ),
        CheckConstraint(
            "buyer_offer_price IS NULL OR buyer_offer_price > 0",
            name="ck_procurement_offer_price_positive",
        ),
        CheckConstraint(
            "transport_cost IS NULL OR transport_cost >= 0",
            name="ck_procurement_transport_nonnegative",
        ),
        CheckConstraint(
            "commission_rate IS NULL OR (commission_rate >= 0 AND commission_rate <= 100)",
            name="ck_procurement_commission_rate",
        ),
        CheckConstraint(
            "status IN ('new','under_review','farmer_contacted','finding_buyers',"
            "'buyer_interested','offer_received','farmer_approval_pending','cancelled')",
            name="ck_procurement_phase1_status",
        ),
    )

    offer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("produce_offers.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="new", index=True, nullable=False)
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id"), index=True
    )
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    buyer_name: Mapped[str | None] = mapped_column(String(160))
    buyer_contact: Mapped[str | None] = mapped_column(String(160))
    buyer_offer_quantity: Mapped[float | None] = mapped_column(Float)
    buyer_offer_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    transport_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    price_unit: Mapped[str | None] = mapped_column(String(16))
    negotiation_notes: Mapped[str | None] = mapped_column(Text)

    @property
    def earned_commission(self) -> None:
        """Commercial inputs are projections until a separate sale ledger exists."""
        return None


class DashboardWidget(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_widgets"

    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title_key: Mapped[str] = mapped_column(String(80), nullable=False)
    widget_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DashboardPreference(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_preferences"
    __table_args__ = (UniqueConstraint("admin_id", "widget_key", name="uq_dashboard_pref"),)

    admin_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("admin_users.id"), index=True, nullable=False
    )
    widget_key: Mapped[str] = mapped_column(String(40), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON)
