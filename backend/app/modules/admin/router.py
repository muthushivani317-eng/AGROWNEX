"""Admin platform API routes (docs/API_CONTRACT.md → ADMIN; team-only).

    GET  /admin/me                          (the caller's admin identity + permissions)
    GET  /admin/dashboard                   (overview cards + procurement status counts)
    GET  /admin/farmers                     (farmer directory; search/filter/paginate)
    GET  /admin/farmers/{user_id}           (one farmer's full profile + activity)
    GET  /admin/analytics                   (distributions + farmer growth)
    GET  /admin/procurement                 (produce offers + procurement analytics)
    PUT  /admin/procurement/{offer_id}/status  (advance the procurement pipeline)
    GET  /admin/ai                          (AI monitoring metrics)
    GET  /admin/notifications               (broadcast history + delivered total)
    POST /admin/broadcast                   (send/schedule a broadcast)
    GET  /admin/announcements               (content management — list)
    POST /admin/announcements               (content management — create)
    GET  /admin/audit                       (immutable audit trail; filter/paginate)

Thin routes — RBAC, auditing, aggregation and delivery all live in ``AdminService``.
Every endpoint is authenticated, resolves an active admin context, and is permission
checked inside the service. Static routes precede the dynamic ``/{...}`` segments.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Request, Response, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_session_cookie, verify_id_token
from app.modules.admin.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ROLE_PERMISSIONS,
    AdminPermission,
)
from app.modules.admin.dependencies import AdminContextDep, AdminServiceDep
from app.modules.admin.schemas import (
    AdminMeOut,
    AICostsOut,
    AIMonitoringOut,
    AnalyticsOut,
    AnnouncementIn,
    AnnouncementOut,
    AuditRowOut,
    BroadcastIn,
    BroadcastOut,
    CloudBillingSpendOut,
    CommissionLedgerIn,
    CostBucketOut,
    CropIntelligenceOut,
    DashboardOut,
    FarmerDetailOut,
    FarmerRowOut,
    OverviewCardOut,
    PaymentLedgerIn,
    PickupLedgerIn,
    ProcurementAnalyticsOut,
    ProcurementCaseUpdateIn,
    ProcurementRowOut,
    ProcurementStatusIn,
    TransactionIn,
)
from app.modules.admin.web_security import InvalidAdminOriginError, require_admin_origin
from app.modules.auth.dependencies import CurrentUser
from app.modules.produce.constants import ProduceAvailabilityType, ProduceCategory
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/admin", tags=["admin"])


# --------------------------------------------------------------------------- #
# Composite response models (thin envelope composition for two endpoints)
# --------------------------------------------------------------------------- #
class ProcurementPageOut(BaseModel):
    page: PaginatedData[ProcurementRowOut]
    analytics: ProcurementAnalyticsOut


class NotificationsOverviewOut(BaseModel):
    broadcasts: PaginatedData[BroadcastOut]
    delivered_total: int


class ProcurementStatusOut(BaseModel):
    offer_id: uuid.UUID
    status: str


class BuyerContactOut(BaseModel):
    offer_id: uuid.UUID
    buyer_contact: str


class AdminInvitationIn(BaseModel):
    email: str
    role: str
    district_scope: str | None = None
    expires_in_hours: int = 48


class AdminInvitationAcceptIn(BaseModel):
    token: str


class AdminStatusIn(BaseModel):
    status: str


@router.post("/invitations", response_model=SuccessResponse[dict], status_code=201)
async def invite_admin(
    payload: AdminInvitationIn, ctx: AdminContextDep, service: AdminServiceDep
):
    invitation, token = await service.invite_admin(
        ctx,
        email=payload.email,
        role=payload.role,
        district_scope=payload.district_scope,
        expires_in_hours=payload.expires_in_hours,
    )
    # The raw token is returned once to the owner; the database retains only its hash.
    return success(
        {"id": str(invitation.id), "token": token, "expires_at": invitation.expires_at},
        message="Admin invitation created",
    )


@router.post("/invitations/accept", response_model=SuccessResponse[dict])
async def accept_admin_invitation(
    payload: AdminInvitationAcceptIn,
    request: Request,
    current_user: CurrentUser,
    service: AdminServiceDep,
):
    authorization = request.headers.get("authorization", "")
    claims = verify_id_token(authorization[7:]) if authorization.startswith("Bearer ") else {}
    if not claims.get("email_verified"):
        raise UnauthorizedError(
            "A verified work email is required.", error_code="admin_email_unverified"
        )
    admin = await service.accept_admin_invitation(current_user, payload.token)
    return success({"admin_id": str(admin.id), "role": admin.role})


@router.put("/team/{admin_id}/status", response_model=SuccessResponse[dict])
async def set_admin_status(
    admin_id: uuid.UUID,
    payload: AdminStatusIn,
    ctx: AdminContextDep,
    service: AdminServiceDep,
):
    admin = await service.set_admin_status(ctx, admin_id, payload.status)
    return success({"admin_id": str(admin.id), "status": admin.status})


@router.get("/team", response_model=SuccessResponse[list[dict]])
async def list_admin_team(ctx: AdminContextDep, service: AdminServiceDep):
    admins = await service.list_admins(ctx)
    return success([
        {
            "id": str(admin.id), "full_name": admin.full_name, "email": admin.email,
            "role": admin.role, "status": admin.status, "created_at": admin.created_at,
            "district_scope": admin.district_scope,
        }
        for admin in admins
    ])


@router.post("/web-session", response_model=SuccessResponse[dict])
async def create_admin_web_session(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    service: AdminServiceDep,
):
    """Exchange a Firebase ID token for an HttpOnly cookie, but only for an admin."""
    try:
        require_admin_origin(request, settings.admin_web_origins)
    except InvalidAdminOriginError as exc:
        raise UnauthorizedError(
            "Admin portal origin is not allowed.", error_code="admin_origin_invalid"
        ) from exc
    # This is the critical farmer-denial check: no active AdminUser, no cookie.
    await service.resolve_admin(current_user)
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Firebase authentication is required.")
    claims = verify_id_token(authorization[7:])
    if settings.admin_require_mfa and not (claims.get("firebase") or {}).get(
        "sign_in_second_factor"
    ):
        raise UnauthorizedError(
            "Multi-factor authentication is required for Admin access.",
            error_code="admin_mfa_required",
        )
    max_age = settings.admin_session_ttl_hours * 60 * 60
    cookie = create_session_cookie(authorization[7:], expires_in_seconds=max_age)
    response.set_cookie(
        settings.admin_session_cookie_name,
        cookie,
        max_age=max_age,
        secure=settings.is_production,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "private, no-store"
    return success({"expires_in": max_age}, message="Secure admin session created")


@router.delete("/web-session", response_model=SuccessResponse[dict])
async def delete_admin_web_session(response: Response, ctx: AdminContextDep):
    """End the current browser session. CSRF/origin checks run in AdminContextDep."""
    response.delete_cookie(
        settings.admin_session_cookie_name,
        secure=settings.is_production,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "private, no-store"
    return success({"signed_out": True})


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
@router.get("/team/access-policy", response_model=SuccessResponse[dict])
async def get_team_access_policy(ctx: AdminContextDep):
    """Read-only policy metadata; never exposes the pinned owner's Firebase UID."""
    if AdminPermission.MANAGE_ADMINS.value not in ctx.permissions or ctx.admin.role != "owner":
        from app.modules.admin.exceptions import PermissionDeniedError
        raise PermissionDeniedError()
    return success({
        "owner_only": bool(settings.admin_owner_firebase_uid),
        "mfa_required": settings.admin_require_mfa,
        "roles": {
            role: [permission.value for permission in permissions]
            for role, permissions in ROLE_PERMISSIONS.items()
        },
    })


@router.get("/me", response_model=SuccessResponse[AdminMeOut])
async def get_me(ctx: AdminContextDep):
    """The caller's admin identity, role and granted permissions."""
    return success(
        AdminMeOut(
            id=ctx.admin.id,
            user_id=ctx.admin.user_id,
            role=ctx.admin.role,
            full_name=ctx.admin.full_name,
            permissions=sorted(ctx.permissions),
            status=ctx.admin.status,
        )
    )


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@router.get("/dashboard", response_model=SuccessResponse[DashboardOut])
async def get_dashboard(ctx: AdminContextDep, service: AdminServiceDep):
    """Operational overview — headline metrics and procurement status counts."""
    data = await service.dashboard(ctx)
    return success(
        DashboardOut(
            cards=[OverviewCardOut.from_card(c) for c in data["cards"]],
            procurement_status_counts=data["procurement_status_counts"],
            generated_at=data["generated_at"],
        )
    )


@router.get("/cloud-billing", response_model=SuccessResponse[CloudBillingSpendOut])
async def get_cloud_billing(ctx: AdminContextDep, service: AdminServiceDep):
    """Actual month-to-date GCP spend from the configured BigQuery billing export."""
    return success(CloudBillingSpendOut(**await service.cloud_billing_spend(ctx)))


# --------------------------------------------------------------------------- #
# Farmer management
# --------------------------------------------------------------------------- #
@router.get("/farmers", response_model=SuccessResponse[PaginatedData[FarmerRowOut]])
async def get_farmers(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    search: str | None = Query(None),
    district: str | None = Query(None),
    crop: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """The farmer directory (read-only), searchable and filterable."""
    page_data = await service.farmers(
        ctx, search=search, district=district, crop=crop, page=page, page_size=page_size
    )
    return success(
        PaginatedData(
            items=[FarmerRowOut.from_row(r) for r in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.get("/farmers/{user_id}", response_model=SuccessResponse[FarmerDetailOut])
async def get_farmer_detail(user_id: uuid.UUID, ctx: AdminContextDep, service: AdminServiceDep):
    """One farmer's full profile, farms and cross-module activity counts."""
    detail = await service.farmer_detail(ctx, user_id)
    return success(FarmerDetailOut.from_detail(user_id, detail))


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #
@router.get("/analytics", response_model=SuccessResponse[AnalyticsOut])
async def get_analytics(ctx: AdminContextDep, service: AdminServiceDep):
    """Platform analytics — real distributions and farmer growth (never fabricated)."""
    data = await service.analytics(ctx)
    return success(AnalyticsOut(**data))


@router.get("/business-dashboard", response_model=SuccessResponse[dict])
async def get_business_dashboard(ctx: AdminContextDep, service: AdminServiceDep):
    return success(await service.business_dashboard(ctx))


@router.get("/crop-intelligence", response_model=SuccessResponse[CropIntelligenceOut])
async def get_crop_intelligence(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    crop: str | None = Query(None, max_length=80),
    district: str | None = Query(None, max_length=80),
    village: str | None = Query(None, max_length=80),
    harvest_days: int = Query(30, ge=1, le=365),
):
    """Recorded crop, acreage, stage, harvest and sale-supply intelligence."""
    return success(
        CropIntelligenceOut(
            **await service.crop_intelligence(
                ctx,
                crop=crop,
                district=district,
                village=village,
                harvest_days=harvest_days,
            )
        )
    )


# --------------------------------------------------------------------------- #
# Procurement
# --------------------------------------------------------------------------- #
@router.get("/procurement", response_model=SuccessResponse[ProcurementPageOut])
async def get_procurement(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    crop: str | None = Query(None),
    village: str | None = Query(None),
    district: str | None = Query(None),
    search: str | None = Query(None),
    category: ProduceCategory | None = Query(None),
    availability_type: ProduceAvailabilityType | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Future-harvest produce offers with village/crop/season procurement analytics."""
    data = await service.procurement(
        ctx,
        crop=crop,
        village=village,
        district=district,
        search=search,
        category=category.value if category else None,
        availability_type=availability_type.value if availability_type else None,
        page=page,
        page_size=page_size,
    )
    page_data = data["page"]
    return success(
        ProcurementPageOut(
            page=PaginatedData(
                items=[ProcurementRowOut.from_item(i) for i in page_data.items],
                page=page_data.page,
                page_size=page_data.page_size,
                total=page_data.total,
                total_pages=page_data.total_pages,
            ),
            analytics=ProcurementAnalyticsOut(**data["analytics"]),
        )
    )


@router.put(
    "/procurement/{offer_id}/status",
    response_model=SuccessResponse[ProcurementStatusOut],
)
async def update_procurement_status(
    offer_id: uuid.UUID,
    payload: ProcurementStatusIn,
    ctx: AdminContextDep,
    service: AdminServiceDep,
):
    """Advance the internal procurement pipeline for an offer (audited, no farmer write)."""
    new_status = await service.update_procurement_status(
        ctx, offer_id, payload.status, note=payload.note
    )
    return success(
        ProcurementStatusOut(offer_id=offer_id, status=new_status),
        message="Procurement status updated",
    )


@router.put("/procurement/{offer_id}/case", response_model=SuccessResponse[ProcurementRowOut])
async def update_procurement_case(
    offer_id: uuid.UUID,
    payload: ProcurementCaseUpdateIn,
    ctx: AdminContextDep,
    service: AdminServiceDep,
):
    """Update internal buyer-search details; inaccessible to farmer APIs."""
    await service.update_procurement_case(ctx, offer_id, payload)
    item = await service.procurement_item(ctx, offer_id)
    return success(ProcurementRowOut.from_item(item), message="Procurement case updated")


@router.post(
    "/procurement/{offer_id}/buyer-contact/reveal",
    response_model=SuccessResponse[BuyerContactOut],
)
async def reveal_buyer_contact(offer_id: uuid.UUID, ctx: AdminContextDep, service: AdminServiceDep):
    contact = await service.reveal_buyer_contact(ctx, offer_id)
    return success(BuyerContactOut(offer_id=offer_id, buyer_contact=contact))


@router.post("/procurement/{offer_id}/pickup", response_model=SuccessResponse[dict])
async def record_pickup(
    offer_id: uuid.UUID, payload: PickupLedgerIn, ctx: AdminContextDep, service: AdminServiceDep
):
    entry = await service.record_pickup(ctx, offer_id, payload)
    return success({"id": str(entry.id), "status": entry.status, "created_at": entry.created_at})


@router.get("/procurement/{offer_id}/ledger", response_model=SuccessResponse[dict])
async def get_commerce_ledger(offer_id: uuid.UUID, ctx: AdminContextDep, service: AdminServiceDep):
    return success(await service.commerce_summary(ctx, offer_id))


@router.post("/procurement/{offer_id}/transaction", response_model=SuccessResponse[dict])
async def record_transaction(
    offer_id: uuid.UUID, payload: TransactionIn, ctx: AdminContextDep, service: AdminServiceDep
):
    row = await service.record_transaction(ctx, offer_id, payload)
    return success(
        {
            "id": str(row.id),
            "gross_amount": str(row.gross_amount),
            "currency": row.currency,
            "created_at": row.created_at,
        }
    )


@router.post(
    "/procurement/transactions/{transaction_id}/payments", response_model=SuccessResponse[dict]
)
async def record_payment(
    transaction_id: uuid.UUID,
    payload: PaymentLedgerIn,
    ctx: AdminContextDep,
    service: AdminServiceDep,
):
    row = await service.record_payment(ctx, transaction_id, payload)
    return success(
        {
            "id": str(row.id),
            "entry_type": row.entry_type,
            "amount": str(row.amount),
            "created_at": row.created_at,
        }
    )


@router.post(
    "/procurement/transactions/{transaction_id}/commissions", response_model=SuccessResponse[dict]
)
async def record_commission(
    transaction_id: uuid.UUID,
    payload: CommissionLedgerIn,
    ctx: AdminContextDep,
    service: AdminServiceDep,
):
    row = await service.record_commission(ctx, transaction_id, payload)
    return success(
        {
            "id": str(row.id),
            "entry_type": row.entry_type,
            "amount": str(row.amount),
            "created_at": row.created_at,
        }
    )


# --------------------------------------------------------------------------- #
# AI monitoring
# --------------------------------------------------------------------------- #
@router.get("/ai", response_model=SuccessResponse[AIMonitoringOut])
async def get_ai_monitoring(ctx: AdminContextDep, service: AdminServiceDep):
    """AI usage metrics — uninstrumented metrics are surfaced as null, never faked."""
    data = await service.ai_monitoring(ctx)
    return success(AIMonitoringOut(**data))


@router.get("/ai-costs", response_model=SuccessResponse[AICostsOut])
async def get_ai_costs(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    window_days: int = Query(30, ge=1, le=365),
):
    """Real AI spend aggregated per model and per module, with daily/weekly series.

    Costs come from the ``token_usage`` ledger via the env-overridable INR cost
    table; requests with unknown token counts contribute 0 (never fabricated).
    """
    data = await service.ai_costs(ctx, window_days=window_days)

    def _buckets(rows) -> list[CostBucketOut]:
        return [
            CostBucketOut(
                key=r.key,
                requests=r.requests,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cost_inr=r.cost_inr,
            )
            for r in rows
        ]

    return success(
        AICostsOut(
            window_days=data["window_days"],
            total_requests=data["total_requests"],
            total_cost_inr=data["total_cost_inr"],
            by_model=_buckets(data["by_model"]),
            by_module=_buckets(data["by_module"]),
            daily=_buckets(data["daily"]),
            weekly=_buckets(data["weekly"]),
            generated_at=data["generated_at"],
        )
    )


# --------------------------------------------------------------------------- #
# Notifications / broadcast
# --------------------------------------------------------------------------- #
@router.get("/notifications", response_model=SuccessResponse[NotificationsOverviewOut])
async def get_notifications(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Broadcast history and the total notifications delivered."""
    data = await service.notifications_overview(ctx, page=page, page_size=page_size)
    page_data = data["broadcasts"]
    return success(
        NotificationsOverviewOut(
            broadcasts=PaginatedData(
                items=[BroadcastOut.from_model(b) for b in page_data.items],
                page=page_data.page,
                page_size=page_data.page_size,
                total=page_data.total,
                total_pages=page_data.total_pages,
            ),
            delivered_total=data["delivered_total"],
        )
    )


@router.post(
    "/broadcast",
    response_model=SuccessResponse[BroadcastOut],
    status_code=status.HTTP_201_CREATED,
)
async def send_broadcast(payload: BroadcastIn, ctx: AdminContextDep, service: AdminServiceDep):
    """Send or schedule a broadcast (delivered via the Notification engine)."""
    broadcast = await service.broadcast(
        ctx,
        title=payload.title,
        body=payload.body,
        language=payload.language,
        target_type=payload.target_type,
        target_value=payload.target_value,
        schedule_type=payload.schedule_type,
        scheduled_for=payload.scheduled_for,
    )
    return success(BroadcastOut.from_model(broadcast), message="Broadcast queued")


# --------------------------------------------------------------------------- #
# Content management (announcements)
# --------------------------------------------------------------------------- #
@router.get("/announcements", response_model=SuccessResponse[PaginatedData[AnnouncementOut]])
async def get_announcements(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """System / farmer announcements (content management)."""
    page_data = await service.announcements(ctx, page=page, page_size=page_size)
    return success(
        PaginatedData(
            items=[AnnouncementOut.from_model(a) for a in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.post(
    "/announcements",
    response_model=SuccessResponse[AnnouncementOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement(
    payload: AnnouncementIn, ctx: AdminContextDep, service: AdminServiceDep
):
    """Create a system / farmer announcement."""
    announcement = await service.create_announcement(
        ctx,
        title=payload.title,
        body=payload.body,
        language=payload.language,
        category=payload.category,
        audience=payload.audience,
    )
    return success(AnnouncementOut.from_model(announcement), message="Announcement created")


# --------------------------------------------------------------------------- #
# Audit trail
# --------------------------------------------------------------------------- #
@router.get("/audit", response_model=SuccessResponse[PaginatedData[AuditRowOut]])
async def get_audit(
    ctx: AdminContextDep,
    service: AdminServiceDep,
    action: str | None = Query(None),
    target: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """The immutable admin audit trail, filterable by action / target."""
    page_data = await service.audit(
        ctx, action=action, target=target, page=page, page_size=page_size
    )
    return success(
        PaginatedData(
            items=[AuditRowOut.from_model(a) for a in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )
