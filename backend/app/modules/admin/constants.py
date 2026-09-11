"""Admin platform constants (docs/SECURITY.md → RBAC; audit; least privilege).

Transparent, reproducible role→permission mapping and the enumerations that drive the
dashboard. Adding a new admin role or permission is a data change here — no redesign
(docs: future Super Admin / District Managers / Procurement Managers / Agriculture
Officers / Customer Support / Enterprise / Export dashboards).
"""

from __future__ import annotations

from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class AdminRole(StrEnum):
    """Admin roles (docs: future roles plug in with no redesign)."""

    OWNER = "owner"
    SUPER_ADMIN = "super_admin"
    DISTRICT_MANAGER = "district_manager"
    PROCUREMENT_MANAGER = "procurement_manager"
    AGRICULTURE_OFFICER = "agriculture_officer"
    CUSTOMER_SUPPORT = "customer_support"


class AdminPermission(StrEnum):
    """Granular permissions — every endpoint checks one (least privilege)."""

    VIEW_DASHBOARD = "view_dashboard"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_CROP_INTELLIGENCE = "view_crop_intelligence"
    MANAGE_FARMERS = "manage_farmers"
    MANAGE_PROCUREMENT = "manage_procurement"
    VIEW_AI = "view_ai"
    MANAGE_CONTENT = "manage_content"
    SEND_BROADCAST = "send_broadcast"
    VIEW_AUDIT = "view_audit"
    MANAGE_ADMINS = "manage_admins"
    REVEAL_BUYER_CONTACT = "reveal_buyer_contact"
    VIEW_REVENUE = "view_revenue"
    VIEW_AI_COSTS = "view_ai_costs"
    MANAGE_SUPPORT = "manage_support"


_ALL = tuple(AdminPermission)
_SUPER_ADMIN = tuple(
    permission for permission in AdminPermission if permission != AdminPermission.MANAGE_ADMINS
)

# Transparent role → permission grants (docs: RBAC, least privilege).
ROLE_PERMISSIONS: dict[str, tuple[AdminPermission, ...]] = {
    AdminRole.OWNER.value: _ALL,
    AdminRole.SUPER_ADMIN.value: _SUPER_ADMIN,
    AdminRole.DISTRICT_MANAGER.value: (
        AdminPermission.VIEW_DASHBOARD,
        AdminPermission.VIEW_CROP_INTELLIGENCE,
        AdminPermission.MANAGE_FARMERS,
    ),
    AdminRole.PROCUREMENT_MANAGER.value: (
        AdminPermission.VIEW_DASHBOARD,
        AdminPermission.VIEW_ANALYTICS,
        AdminPermission.VIEW_CROP_INTELLIGENCE,
        AdminPermission.MANAGE_PROCUREMENT,
        AdminPermission.REVEAL_BUYER_CONTACT,
    ),
    AdminRole.AGRICULTURE_OFFICER.value: (
        AdminPermission.VIEW_DASHBOARD,
        AdminPermission.VIEW_ANALYTICS,
        AdminPermission.VIEW_CROP_INTELLIGENCE,
        AdminPermission.MANAGE_FARMERS,
        AdminPermission.VIEW_AI,
        AdminPermission.MANAGE_CONTENT,
    ),
    AdminRole.CUSTOMER_SUPPORT.value: (
        AdminPermission.VIEW_DASHBOARD,
        AdminPermission.MANAGE_FARMERS,
        AdminPermission.MANAGE_SUPPORT,
    ),
}


def permissions_for(role: str) -> tuple[str, ...]:
    """The permission codes granted to a role (empty for an unknown role)."""
    return tuple(p.value for p in ROLE_PERMISSIONS.get(role, ()))


class AdminUserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class AuditAction(StrEnum):
    """Audited admin actions (docs/SECURITY.md → audit is immutable)."""

    VIEW_DASHBOARD = "view_dashboard"
    VIEW_FARMERS = "view_farmers"
    VIEW_FARMER_DETAIL = "view_farmer_detail"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_PROCUREMENT = "view_procurement"
    PROCUREMENT_STATUS_CHANGED = "procurement_status_changed"
    BUYER_CONTACT_REVEALED = "buyer_contact_revealed"
    PICKUP_LEDGER_RECORDED = "pickup_ledger_recorded"
    TRANSACTION_RECORDED = "transaction_recorded"
    PAYMENT_LEDGER_RECORDED = "payment_ledger_recorded"
    COMMISSION_LEDGER_RECORDED = "commission_ledger_recorded"
    VIEW_AI = "view_ai"
    VIEW_CLOUD_BILLING = "view_cloud_billing"
    VIEW_NOTIFICATIONS = "view_notifications"
    BROADCAST_SENT = "broadcast_sent"
    ANNOUNCEMENT_CREATED = "announcement_created"
    VIEW_AUDIT = "view_audit"
    ADMIN_INVITED = "admin_invited"
    ADMIN_INVITATION_ACCEPTED = "admin_invitation_accepted"
    ADMIN_STATUS_CHANGED = "admin_status_changed"


class ProcurementStatus(StrEnum):
    """Internal procurement pipeline (NOT a marketplace; overlays farmer offers)."""

    NEW = "new"
    UNDER_REVIEW = "under_review"
    FARMER_CONTACTED = "farmer_contacted"
    FINDING_BUYERS = "finding_buyers"
    BUYER_INTERESTED = "buyer_interested"
    OFFER_RECEIVED = "offer_received"
    FARMER_APPROVAL_PENDING = "farmer_approval_pending"
    FARMER_ACCEPTED = "farmer_accepted"
    FARMER_REJECTED = "farmer_rejected"
    CANCELLED = "cancelled"

    # Source-compatible names for callers on the previous admin contract.
    CONTACTED = "farmer_contacted"
    NEGOTIATING = "finding_buyers"


PROCUREMENT_OPEN = (
    ProcurementStatus.NEW.value,
    ProcurementStatus.UNDER_REVIEW.value,
    ProcurementStatus.FARMER_CONTACTED.value,
    ProcurementStatus.FINDING_BUYERS.value,
    ProcurementStatus.BUYER_INTERESTED.value,
    ProcurementStatus.OFFER_RECEIVED.value,
    ProcurementStatus.FARMER_APPROVAL_PENDING.value,
    ProcurementStatus.FARMER_ACCEPTED.value,
)


class BroadcastTargetType(StrEnum):
    ALL = "all"
    VILLAGE = "village"
    DISTRICT = "district"
    CROP = "crop"
    LANGUAGE = "language"


class BroadcastScheduleType(StrEnum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"


class BroadcastStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class AnnouncementAudience(StrEnum):
    ALL = "all"
    FARMERS = "farmers"
    ADMINS = "admins"


# The overview cards on the admin dashboard (docs: DASHBOARD).
OVERVIEW_METRICS = (
    "total_farmers",
    "total_farms",
    "active_users",
    "today_ai_chats",
    "disease_reports",
    "soil_reports",
    "satellite_reports",
    "intelligence_reports",
    "scheme_saves",
    "produce_listings",
    "expert_consultations",
    "notifications_sent",
)

# Active-user window (docs: Active Users).
ACTIVE_USER_DAYS = 7

# Default dashboard widgets seeded for every admin (docs: dashboard_widgets).
DEFAULT_WIDGETS = (
    ("overview", "admin.widget.overview", "cards", 0),
    ("analytics", "admin.widget.analytics", "charts", 1),
    ("procurement", "admin.widget.procurement", "table", 2),
    ("ai_monitoring", "admin.widget.ai", "metrics", 3),
    ("audit", "admin.widget.audit", "table", 4),
)
