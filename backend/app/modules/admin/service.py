"""Admin service (docs: Repository → Service → Admin Engine → Provider → API).

Enforces admin RBAC, **audits every action** (docs/SECURITY.md — audit is immutable),
aggregates read-only metrics through the Admin Engine, and delivers broadcasts by
reusing the Notification engine. Farmer data is never modified here; the only writes are
admin-domain rows (audit, broadcast, announcement, admin status changes). Business logic
lives here; routes stay thin.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.admin.constants import (
    ROLE_PERMISSIONS,
    AdminPermission,
    AdminRole,
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
    AdminInvitation,
    AdminUser,
    AuditLog,
    BroadcastMessage,
    CommissionLedgerEntry,
    PaymentLedgerEntry,
    PickupLedgerEntry,
    ProcurementCase,
    ProcurementTransaction,
    SystemAnnouncement,
)
from app.modules.admin.provider import BroadcastProvider, get_default_broadcast_provider
from app.modules.admin.queries import AdminQueries
from app.modules.admin.repository import AdminRepository, normalize_procurement_status
from app.modules.admin.schemas import (
    CommissionLedgerIn,
    PaymentLedgerIn,
    PickupLedgerIn,
    ProcurementCaseUpdateIn,
    TransactionIn,
)
from app.modules.ai.repositories import CostRow, TokenUsageRepository
from app.modules.auth.models import User
from app.modules.produce.models import ProduceOffer
from app.schemas.response import PaginatedData

logger = get_logger("admin.service")


def _roll_up_weekly(daily: list[CostRow]) -> list[CostRow]:
    """Roll per-day cost rows up into ISO-week buckets (keyed ``YYYY-Www``)."""
    weeks: dict[str, CostRow] = {}
    for row in daily:
        try:
            iso = date.fromisoformat(row.key[:10]).isocalendar()
        except ValueError:
            continue
        wk = f"{iso.year}-W{iso.week:02d}"
        prev = weeks.get(wk)
        if prev is None:
            weeks[wk] = CostRow(
                key=wk,
                requests=row.requests,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                cost_inr=row.cost_inr,
            )
        else:
            weeks[wk] = CostRow(
                key=wk,
                requests=prev.requests + row.requests,
                input_tokens=prev.input_tokens + row.input_tokens,
                output_tokens=prev.output_tokens + row.output_tokens,
                cost_inr=round(prev.cost_inr + row.cost_inr, 6),
            )
    return sorted(weeks.values(), key=lambda r: r.key)


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

    def _procurement_override(self, ctx: AdminContext) -> bool:
        return ctx.admin.role in {AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}

    async def _require_procurement_scope(
        self, ctx: AdminContext, offer_id: uuid.UUID, *, allow_claim: bool = False
    ) -> ProcurementCase | None:
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        case = await self.repo.procurement_case_of(offer_id)
        if self._procurement_override(ctx):
            return case
        if case is None or case.assigned_admin_id is None:
            if allow_claim:
                return case
            raise PermissionDeniedError("This procurement case is not assigned to you.")
        if case.assigned_admin_id != ctx.admin.id:
            raise PermissionDeniedError("This procurement case is assigned to another admin.")
        return case

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

    async def invite_admin(
        self, ctx: AdminContext, *, email: str, role: str,
        district_scope: str | None = None, expires_in_hours: int = 48
    ) -> tuple[AdminInvitation, str]:
        """Create an expiring one-time invitation; only the owner can grant access."""
        self._require(ctx, AdminPermission.MANAGE_ADMINS)
        if ctx.admin.role != AdminRole.OWNER.value:
            raise PermissionDeniedError()
        if role not in ROLE_PERMISSIONS or role == AdminRole.OWNER.value:
            raise PermissionDeniedError()
        if role == AdminRole.DISTRICT_MANAGER.value and not district_scope:
            raise PermissionDeniedError()
        raw_token = secrets.token_urlsafe(32)
        invitation = AdminInvitation(
            email=email.strip().lower(),
            role=role,
            district_scope=district_scope.strip() if district_scope else None,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            invited_by_admin_id=ctx.admin.id,
            expires_at=self._now_dt() + timedelta(hours=expires_in_hours),
        )
        self.session.add(invitation)
        await self.session.flush()
        await self._audit(
            ctx,
            AuditAction.ADMIN_INVITED,
            target="admin_invitation",
            target_id=str(invitation.id),
            meta={"role": role},
        )
        await self.session.commit()
        return invitation, raw_token

    async def accept_admin_invitation(self, user: User, token: str) -> AdminUser:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        invitation = (
            await self.session.execute(
                select(AdminInvitation).where(AdminInvitation.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        now = self._now_dt()
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.expires_at <= now
            or not user.email
            or not user.is_email_verified
            or user.email.strip().lower() != invitation.email
            or await self.repo.get_admin_by_user(user.id)
        ):
            raise PermissionDeniedError()
        admin = await self.repo.add_admin(
            AdminUser(
                user_id=user.id,
                role=invitation.role,
                email=user.email,
                full_name=None,
                status=AdminUserStatus.ACTIVE.value,
                district_scope=invitation.district_scope,
            )
        )
        invitation.accepted_at = now
        invitation.accepted_user_id = user.id
        await self.repo.add_audit(
            AuditLog(
                admin_id=admin.id,
                role=admin.role,
                action=AuditAction.ADMIN_INVITATION_ACCEPTED.value,
                target="admin_invitation",
                target_id=str(invitation.id),
                meta={"role": admin.role},
            )
        )
        await self.session.commit()
        return admin

    async def set_admin_status(
        self, ctx: AdminContext, admin_id: uuid.UUID, status: str
    ) -> AdminUser:
        self._require(ctx, AdminPermission.MANAGE_ADMINS)
        if ctx.admin.role != AdminRole.OWNER.value or admin_id == ctx.admin.id:
            raise PermissionDeniedError()
        admin = await self.session.get(AdminUser, admin_id)
        if admin is None or admin.role == AdminRole.OWNER.value:
            raise PermissionDeniedError()
        if status not in {AdminUserStatus.ACTIVE.value, AdminUserStatus.SUSPENDED.value}:
            raise PermissionDeniedError()
        admin.status = status
        await self._audit(
            ctx,
            AuditAction.ADMIN_STATUS_CHANGED,
            target="admin",
            target_id=str(admin.id),
            meta={"status": status},
        )
        await self.session.commit()
        return admin

    async def list_admins(self, ctx: AdminContext) -> list[AdminUser]:
        self._require(ctx, AdminPermission.MANAGE_ADMINS)
        if ctx.admin.role != AdminRole.OWNER.value:
            raise PermissionDeniedError()
        rows = (
            await self.session.execute(
                select(AdminUser)
                .where(AdminUser.is_deleted.is_(False))
                .order_by(AdminUser.created_at.desc())
            )
        ).scalars().all()
        return list(rows)

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

    async def business_dashboard(self, ctx: AdminContext) -> dict:
        """Real daily funnel and assisted-sales ledger metrics; never inferred."""
        self._require(ctx, AdminPermission.VIEW_REVENUE)
        day_start = self._now_dt().replace(hour=0, minute=0, second=0, microsecond=0)
        users = select(func.count(User.id)).where(User.is_deleted.is_(False))

        async def count(stmt):
            return int((await self.session.scalar(stmt)) or 0)

        total_farmers = await count(users)
        new_today = await count(users.where(User.created_at >= day_start))
        active_today = await count(users.where(User.last_login >= day_start))
        active_7d = await count(users.where(User.last_login >= self._now_dt() - timedelta(days=7)))
        active_30d = await count(
            users.where(User.last_login >= self._now_dt() - timedelta(days=30))
        )
        listings_today = await count(
            select(func.count(ProduceOffer.id)).where(
                ProduceOffer.created_at >= day_start, ProduceOffer.is_deleted.is_(False)
            )
        )
        status_rows = (
            await self.session.execute(
                select(ProcurementCase.status, func.count(ProcurementCase.id)).group_by(
                    ProcurementCase.status
                )
            )
        ).all()
        transaction_count = await count(select(func.count(ProcurementTransaction.id)))
        gmv = Decimal(
            str(
                (
                    await self.session.scalar(
                        select(func.coalesce(func.sum(ProcurementTransaction.gross_amount), 0))
                    )
                )
                or 0
            )
        )
        earned_commission = Decimal(
            str(
                (
                    await self.session.scalar(
                        select(func.coalesce(func.sum(CommissionLedgerEntry.amount), 0)).where(
                            CommissionLedgerEntry.entry_type == "earned"
                        )
                    )
                )
                or 0
            )
        )
        buyer_receipts = Decimal(
            str(
                (
                    await self.session.scalar(
                        select(func.coalesce(func.sum(PaymentLedgerEntry.amount), 0)).where(
                            PaymentLedgerEntry.entry_type == "buyer_receipt"
                        )
                    )
                )
                or 0
            )
        )
        return {
            "generated_at": self._now_dt(),
            "total_farmers": total_farmers,
            "new_farmers_today": new_today,
            "active_farmers_today": active_today,
            "active_farmers_7d": active_7d,
            "active_farmers_30d": active_30d,
            "produce_listings_today": listings_today,
            "procurement_status_counts": {status: int(value) for status, value in status_rows},
            "transactions": transaction_count,
            "gmv": str(gmv),
            "buyer_receipts": str(buyer_receipts),
            "payment_outstanding": str(max(Decimal("0"), gmv - buyer_receipts)),
            "earned_commission": str(earned_commission),
            "currency": "INR",
        }

    # ----------------------------------------------------------------- #
    # Farmer management
    # ----------------------------------------------------------------- #
    async def farmers(
        self,
        ctx: AdminContext,
        *,
        search: str | None = None,
        district: str | None,
        crop: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedData:
        self._require(ctx, AdminPermission.MANAGE_FARMERS)
        if ctx.admin.role == AdminRole.DISTRICT_MANAGER.value:
            district = ctx.admin.district_scope
        offset = (page - 1) * page_size
        rows, total = await self.queries.farmers(
            search=search, district=district, crop=crop, limit=page_size, offset=offset
        )
        await self._audit(ctx, AuditAction.VIEW_FARMERS, meta={"search_used": bool(search)})
        return _paginate(rows, page, page_size, total)

    async def farmer_detail(self, ctx: AdminContext, user_id: uuid.UUID) -> dict:
        self._require(ctx, AdminPermission.MANAGE_FARMERS)
        detail = await self.queries.farmer_detail(user_id)
        if detail is None:
            raise FarmerNotFoundError()
        if (
            ctx.admin.role == AdminRole.DISTRICT_MANAGER.value
            and detail.get("district") != ctx.admin.district_scope
        ):
            raise FarmerNotFoundError()
        from app.modules.consents.service import ConsentService

        detail["consents"] = await ConsentService(self.session).current(user_id)
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

    async def crop_intelligence(
        self,
        ctx: AdminContext,
        *,
        crop: str | None,
        district: str | None,
        village: str | None,
        harvest_days: int,
    ) -> dict:
        self._require(ctx, AdminPermission.VIEW_CROP_INTELLIGENCE)
        if ctx.admin.role == AdminRole.DISTRICT_MANAGER.value:
            district = ctx.admin.district_scope
        data = await self.metrics.crop_intelligence(
            crop=crop,
            district=district,
            village=village,
            harvest_days=harvest_days,
        )
        await self._audit(
            ctx,
            AuditAction.VIEW_ANALYTICS,
            target="crop_intelligence",
            meta=data["filters"],
        )
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
        search: str | None = None,
        category: str | None = None,
        availability_type: str | None = None,
        page: int,
        page_size: int,
    ) -> dict:
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        offset = (page - 1) * page_size
        rows, total = await self.queries.procurement_offers(
            crop=crop,
            village=village,
            district=district,
            search=search,
            category=category,
            availability_type=availability_type,
            limit=page_size,
            offset=offset,
            assigned_admin_id=ctx.admin.id,
            include_all_assignments=self._procurement_override(ctx),
        )
        status_map = await self.repo.procurement_status_map([r.offer_id for r in rows])
        case_map = await self.repo.procurement_case_map([r.offer_id for r in rows])
        facts = await self.queries.procurement_facts(
            assigned_admin_id=ctx.admin.id,
            include_all_assignments=self._procurement_override(ctx),
        )
        analytics = procurement_analytics(facts)
        await self._audit(ctx, AuditAction.VIEW_PROCUREMENT)
        items = [
            {
                "row": r,
                "case": case_map.get(str(r.offer_id)),
                "admin_status": (
                    case_map[str(r.offer_id)].status
                    if str(r.offer_id) in case_map
                    else status_map.get(str(r.offer_id), ProcurementStatus.NEW.value)
                ),
            }
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
        if status in {"confirmed", "collected"}:
            raise InvalidProcurementStatusError(
                f"Legacy procurement transition '{status}' is retired."
            )
        normalized = normalize_procurement_status(status)
        try:
            payload = ProcurementCaseUpdateIn(status=normalized)
        except Exception as exc:
            raise InvalidProcurementStatusError() from exc
        case = await self.update_procurement_case(ctx, offer_id, payload)
        return case.status

    async def update_procurement_case(
        self,
        ctx: AdminContext,
        offer_id: uuid.UUID,
        data: ProcurementCaseUpdateIn,
    ) -> ProcurementCase:
        """Create/update the internal assisted-sales case for a farmer offer."""
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        locked_offer = await self.session.scalar(
            select(ProduceOffer).where(ProduceOffer.id == offer_id).with_for_update()
        )
        if locked_offer is None:
            raise OfferNotFoundError()
        case = await self._require_procurement_scope(ctx, offer_id, allow_claim=True)
        if case is None:
            legacy_status = await self.repo.procurement_status_of(offer_id)
            initial_status = (
                legacy_status
                if legacy_status in {status.value for status in ProcurementStatus}
                else ProcurementStatus.NEW.value
            )
            case = ProcurementCase(
                offer_id=offer_id,
                status=initial_status,
                assigned_admin_id=(None if self._procurement_override(ctx) else ctx.admin.id),
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(case)
                    await self.session.flush()
            except IntegrityError as exc:
                case = await self.repo.procurement_case_of(offer_id)
                if case is None:
                    raise
                if not self._procurement_override(ctx) and case.assigned_admin_id != ctx.admin.id:
                    raise PermissionDeniedError(
                        "This procurement case was claimed by another admin."
                    ) from exc
        fields = data.model_dump(exclude_unset=True)
        commercial_fields = {
            "buyer_name",
            "buyer_contact",
            "buyer_offer_quantity",
            "buyer_offer_price",
            "transport_cost",
            "commission_rate",
            "currency",
            "price_unit",
        }
        if case.frozen_at is not None and commercial_fields.intersection(fields):
            raise InvalidProcurementStatusError("Frozen buyer offer terms cannot be edited.")
        assignee_id = fields.get("assigned_admin_id")
        if not self._procurement_override(ctx):
            if assignee_id not in {None, ctx.admin.id}:
                raise PermissionDeniedError(
                    "Procurement admins may only assign cases to themselves."
                )
            fields["assigned_admin_id"] = ctx.admin.id
        if assignee_id is not None:
            assignee = await self.session.get(AdminUser, assignee_id)
            if (
                assignee is None
                or assignee.status != AdminUserStatus.ACTIVE.value
                or AdminPermission.MANAGE_PROCUREMENT.value not in permissions_for(assignee.role)
            ):
                raise PermissionDeniedError("Assignee must be an active procurement admin.")
        requested = fields.pop("status", None)
        if requested is not None:
            requested = requested.value if hasattr(requested, "value") else requested
            requested = normalize_procurement_status(requested)
            current_status = normalize_procurement_status(case.status)
            allowed = {
                ProcurementStatus.NEW.value: {
                    ProcurementStatus.UNDER_REVIEW.value,
                    ProcurementStatus.FARMER_CONTACTED.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.UNDER_REVIEW.value: {
                    ProcurementStatus.FARMER_CONTACTED.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.FARMER_CONTACTED.value: {
                    ProcurementStatus.FINDING_BUYERS.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.FINDING_BUYERS.value: {
                    ProcurementStatus.BUYER_INTERESTED.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.BUYER_INTERESTED.value: {
                    ProcurementStatus.OFFER_RECEIVED.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.OFFER_RECEIVED.value: {
                    ProcurementStatus.FARMER_APPROVAL_PENDING.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.FARMER_APPROVAL_PENDING.value: {
                    ProcurementStatus.FINDING_BUYERS.value,
                    ProcurementStatus.CANCELLED.value,
                },
                ProcurementStatus.FARMER_ACCEPTED.value: set(),
                ProcurementStatus.FARMER_REJECTED.value: {
                    ProcurementStatus.FINDING_BUYERS.value,
                    ProcurementStatus.CANCELLED.value,
                },
            }
            if requested != current_status and requested not in allowed.get(current_status, set()):
                raise InvalidProcurementStatusError(
                    f"Invalid procurement status transition: {current_status} -> {requested}"
                )
        offer = await self.session.get(ProduceOffer, offer_id)
        proposed = lambda name: fields.get(name, getattr(case, name))  # noqa: E731
        if requested == ProcurementStatus.BUYER_INTERESTED.value and not proposed("buyer_name"):
            raise InvalidProcurementStatusError("Buyer interested requires buyer identity.")
        commercial = (
            bool(proposed("buyer_name"))
            and proposed("buyer_offer_quantity") is not None
            and proposed("buyer_offer_quantity") > 0
            and proposed("buyer_offer_price") is not None
            and proposed("buyer_offer_price") > 0
            and bool(proposed("currency"))
            and bool(proposed("price_unit"))
        )
        if requested == ProcurementStatus.OFFER_RECEIVED.value:
            if (
                offer
                and offer.available_quantity is not None
                and proposed("buyer_offer_quantity")
                and proposed("buyer_offer_quantity") > offer.available_quantity
            ):
                raise InvalidProcurementStatusError(
                    "Buyer offer quantity exceeds available quantity."
                )
            if not commercial:
                raise InvalidProcurementStatusError(
                    "Offer received requires a complete commercial offer."
                )
        if requested == ProcurementStatus.FARMER_APPROVAL_PENDING.value and not commercial:
            raise InvalidProcurementStatusError("Farmer approval requires a commercial offer.")
        if requested == ProcurementStatus.FARMER_APPROVAL_PENDING.value:
            snapshot = {
                "offer_id": str(offer_id),
                "buyer_name": str(proposed("buyer_name")),
                "quantity": str(proposed("buyer_offer_quantity")),
                "unit_price": str(proposed("buyer_offer_price")),
                "currency": str(proposed("currency")),
                "price_unit": str(proposed("price_unit")),
                "transport_cost": str(proposed("transport_cost") or 0),
                "commission_rate": str(proposed("commission_rate") or 0),
            }
            canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
            case.frozen_terms = snapshot
            case.frozen_terms_hash = hashlib.sha256(canonical.encode()).hexdigest()
            case.frozen_at = self._now_dt()
        elif requested == ProcurementStatus.FINDING_BUYERS.value and case.frozen_at is not None:
            case.frozen_terms = None
            case.frozen_terms_hash = None
            case.frozen_at = None
        for key, value in fields.items():
            setattr(case, key, value)
        if requested is not None:
            case.status = requested
        await self._audit(
            ctx,
            AuditAction.PROCUREMENT_STATUS_CHANGED,
            target="procurement_case",
            target_id=str(offer_id),
            meta={"status": case.status, "changed_fields": sorted(data.model_fields_set)},
        )
        await self.session.flush()
        return case

    async def reveal_buyer_contact(self, ctx: AdminContext, offer_id: uuid.UUID) -> str:
        """Reveal one buyer contact with explicit permission and record-level audit."""
        self._require(ctx, AdminPermission.REVEAL_BUYER_CONTACT)
        case = await self._require_procurement_scope(ctx, offer_id)
        if case is None or not case.buyer_contact:
            raise OfferNotFoundError()
        await self._audit(
            ctx,
            AuditAction.BUYER_CONTACT_REVEALED,
            target="procurement_case",
            target_id=str(offer_id),
            meta={"record_level": True},
        )
        await self.session.flush()
        return case.buyer_contact

    async def record_pickup(self, ctx: AdminContext, offer_id: uuid.UUID, data: PickupLedgerIn):
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        case = await self._require_procurement_scope(ctx, offer_id)
        if case is None or case.status != ProcurementStatus.FARMER_ACCEPTED.value:
            raise InvalidProcurementStatusError("Pickup requires an accepted farmer offer.")
        if data.status == "completed" and data.occurred_at is None:
            raise InvalidProcurementStatusError("Completed pickup requires occurred_at.")
        entry = PickupLedgerEntry(
            case_id=case.id, recorded_by_admin_id=ctx.admin.id, **data.model_dump()
        )
        self.session.add(entry)
        await self._audit(
            ctx,
            AuditAction.PICKUP_LEDGER_RECORDED,
            target="pickup_ledger",
            target_id=str(offer_id),
            meta={"status": data.status},
        )
        await self.session.flush()
        return entry

    async def record_transaction(self, ctx: AdminContext, offer_id: uuid.UUID, data: TransactionIn):
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        case = await self._require_procurement_scope(ctx, offer_id)
        if (
            case is None
            or case.status != ProcurementStatus.FARMER_ACCEPTED.value
            or not case.frozen_terms
        ):
            raise InvalidProcurementStatusError("Transaction requires an accepted frozen offer.")
        existing = (
            await self.session.execute(
                select(ProcurementTransaction).where(ProcurementTransaction.case_id == case.id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        quantity = Decimal(str(case.frozen_terms["quantity"]))
        price = Decimal(str(case.frozen_terms["unit_price"]))
        transaction = ProcurementTransaction(
            case_id=case.id,
            quantity=float(quantity),
            unit_price=price,
            gross_amount=quantity * price,
            currency=str(case.frozen_terms["currency"]),
            terms_hash=case.frozen_terms_hash,
            occurred_at=data.occurred_at,
            recorded_by_admin_id=ctx.admin.id,
        )
        self.session.add(transaction)
        await self._audit(
            ctx,
            AuditAction.TRANSACTION_RECORDED,
            target="procurement_transaction",
            target_id=str(offer_id),
            meta={"terms_hash": case.frozen_terms_hash},
        )
        await self.session.flush()
        return transaction

    async def record_payment(
        self, ctx: AdminContext, transaction_id: uuid.UUID, data: PaymentLedgerIn
    ):
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        transaction = await self.session.get(ProcurementTransaction, transaction_id)
        if transaction is None:
            raise OfferNotFoundError()
        case = await self.session.get(ProcurementCase, transaction.case_id)
        if case is None:
            raise OfferNotFoundError()
        await self._require_procurement_scope(ctx, case.offer_id)
        entry = PaymentLedgerEntry(
            transaction_id=transaction_id,
            recorded_by_admin_id=ctx.admin.id,
            **data.model_dump(),
        )
        self.session.add(entry)
        await self._audit(
            ctx,
            AuditAction.PAYMENT_LEDGER_RECORDED,
            target="payment_ledger",
            target_id=str(transaction_id),
            meta={"entry_type": data.entry_type, "amount": str(data.amount)},
        )
        await self.session.flush()
        return entry

    async def record_commission(
        self, ctx: AdminContext, transaction_id: uuid.UUID, data: CommissionLedgerIn
    ):
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        transaction = await self.session.get(ProcurementTransaction, transaction_id)
        if transaction is None:
            raise OfferNotFoundError()
        case = await self.session.get(ProcurementCase, transaction.case_id)
        if case is not None:
            await self._require_procurement_scope(ctx, case.offer_id)
        if case is None or not case.frozen_terms:
            raise InvalidProcurementStatusError("Frozen terms are unavailable.")
        if data.entry_type == "earned":
            received = await self.session.scalar(
                select(func.coalesce(func.sum(PaymentLedgerEntry.amount), 0)).where(
                    PaymentLedgerEntry.transaction_id == transaction_id,
                    PaymentLedgerEntry.entry_type == "buyer_receipt",
                )
            )
            if Decimal(str(received)) < transaction.gross_amount:
                raise InvalidProcurementStatusError(
                    "Commission is earned only after full buyer receipt."
                )
            prior = (
                await self.session.execute(
                    select(CommissionLedgerEntry).where(
                        CommissionLedgerEntry.transaction_id == transaction_id,
                        CommissionLedgerEntry.entry_type == "earned",
                    )
                )
            ).scalar_one_or_none()
            if prior is not None:
                return prior
        rate = Decimal(str(case.frozen_terms.get("commission_rate") or 0))
        amount = (transaction.gross_amount * rate / Decimal("100")).quantize(Decimal("0.01"))
        entry = CommissionLedgerEntry(
            transaction_id=transaction_id,
            entry_type=data.entry_type,
            base_amount=transaction.gross_amount,
            rate=rate,
            amount=amount,
            currency=transaction.currency,
            occurred_at=data.occurred_at,
            recorded_by_admin_id=ctx.admin.id,
        )
        self.session.add(entry)
        await self._audit(
            ctx,
            AuditAction.COMMISSION_LEDGER_RECORDED,
            target="commission_ledger",
            target_id=str(transaction_id),
            meta={"entry_type": data.entry_type, "amount": str(amount)},
        )
        await self.session.flush()
        return entry

    async def commerce_summary(self, ctx: AdminContext, offer_id: uuid.UUID) -> dict:
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        case = await self._require_procurement_scope(ctx, offer_id)
        if case is None:
            raise OfferNotFoundError()
        transaction = (
            await self.session.execute(
                select(ProcurementTransaction).where(ProcurementTransaction.case_id == case.id)
            )
        ).scalar_one_or_none()
        pickups = (
            (
                await self.session.execute(
                    select(PickupLedgerEntry)
                    .where(PickupLedgerEntry.case_id == case.id)
                    .order_by(PickupLedgerEntry.created_at)
                )
            )
            .scalars()
            .all()
        )
        payments = []
        commissions = []
        if transaction is not None:
            payments = (
                (
                    await self.session.execute(
                        select(PaymentLedgerEntry)
                        .where(PaymentLedgerEntry.transaction_id == transaction.id)
                        .order_by(PaymentLedgerEntry.created_at)
                    )
                )
                .scalars()
                .all()
            )
            commissions = (
                (
                    await self.session.execute(
                        select(CommissionLedgerEntry)
                        .where(CommissionLedgerEntry.transaction_id == transaction.id)
                        .order_by(CommissionLedgerEntry.created_at)
                    )
                )
                .scalars()
                .all()
            )
        await self._audit(
            ctx,
            AuditAction.VIEW_PROCUREMENT,
            target="commerce_ledger",
            target_id=str(offer_id),
        )
        return {
            "offer_id": str(offer_id),
            "case_status": case.status,
            "transaction": (
                {
                    "id": str(transaction.id),
                    "quantity": transaction.quantity,
                    "unit_price": str(transaction.unit_price),
                    "gross_amount": str(transaction.gross_amount),
                    "currency": transaction.currency,
                    "occurred_at": transaction.occurred_at,
                }
                if transaction
                else None
            ),
            "pickups": [
                {
                    "id": str(item.id),
                    "status": item.status,
                    "scheduled_at": item.scheduled_at,
                    "occurred_at": item.occurred_at,
                    "location": item.location,
                    "note": item.note,
                    "created_at": item.created_at,
                }
                for item in pickups
            ],
            "payments": [
                {
                    "id": str(item.id),
                    "entry_type": item.entry_type,
                    "amount": str(item.amount),
                    "currency": item.currency,
                    "reference": item.reference,
                    "occurred_at": item.occurred_at,
                }
                for item in payments
            ],
            "commissions": [
                {
                    "id": str(item.id),
                    "entry_type": item.entry_type,
                    "base_amount": str(item.base_amount),
                    "rate": str(item.rate),
                    "amount": str(item.amount),
                    "currency": item.currency,
                    "occurred_at": item.occurred_at,
                }
                for item in commissions
            ],
        }

    async def procurement_item(self, ctx: AdminContext, offer_id: uuid.UUID) -> dict:
        self._require(ctx, AdminPermission.MANAGE_PROCUREMENT)
        row = await self.queries.procurement_offer(offer_id)
        if row is None:
            raise OfferNotFoundError()
        case = await self._require_procurement_scope(ctx, offer_id)
        return {
            "row": row,
            "case": case,
            "admin_status": case.status if case else ProcurementStatus.NEW.value,
        }

    # ----------------------------------------------------------------- #
    # AI monitoring
    # ----------------------------------------------------------------- #
    async def ai_monitoring(self, ctx: AdminContext) -> dict:
        self._require(ctx, AdminPermission.VIEW_AI)
        data = await self.metrics.ai_monitoring()
        await self._audit(ctx, AuditAction.VIEW_AI)
        return data

    async def ai_costs(self, ctx: AdminContext, *, window_days: int = 30) -> dict:
        """Real AI spend per model and per module over a window (Phase 1).

        Daily/weekly series and per-model/per-module totals are computed from the
        ``token_usage`` ledger. Nothing is fabricated: unknown token counts cost 0.
        """
        self._require(ctx, AdminPermission.VIEW_AI_COSTS)
        repo = TokenUsageRepository(self.session)
        since = self._now_dt() - timedelta(days=window_days)
        by_model = await repo.by_model(since=since)
        by_module = await repo.by_module(since=since)
        daily = await repo.daily(since=since)
        await self._audit(ctx, AuditAction.VIEW_AI)
        return {
            "window_days": window_days,
            "total_requests": sum(r.requests for r in by_model),
            "total_cost_inr": round(sum(r.cost_inr for r in by_model), 6),
            "by_model": by_model,
            "by_module": by_module,
            "daily": daily,
            "weekly": _roll_up_weekly(daily),
            "generated_at": self._now_dt(),
        }

    # ----------------------------------------------------------------- #
    # Notification management
    # ----------------------------------------------------------------- #
    async def notifications_overview(self, ctx: AdminContext, *, page: int, page_size: int) -> dict:
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
            delivered = await self.broadcast_provider.deliver(self.session, broadcast, recipients)
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

    async def announcements(self, ctx: AdminContext, *, page: int, page_size: int) -> PaginatedData:
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
