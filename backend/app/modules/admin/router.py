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

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.modules.admin.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
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
    CostBucketOut,
    DashboardOut,
    FarmerDetailOut,
    FarmerRowOut,
    OverviewCardOut,
    ProcurementAnalyticsOut,
    ProcurementRowOut,
    ProcurementStatusIn,
)
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


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
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
async def get_farmer_detail(
    user_id: uuid.UUID, ctx: AdminContextDep, service: AdminServiceDep
):
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
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Future-harvest produce offers with village/crop/season procurement analytics."""
    data = await service.procurement(
        ctx, crop=crop, village=village, district=district, page=page, page_size=page_size
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
@router.get(
    "/notifications", response_model=SuccessResponse[NotificationsOverviewOut]
)
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
async def send_broadcast(
    payload: BroadcastIn, ctx: AdminContextDep, service: AdminServiceDep
):
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
@router.get(
    "/announcements", response_model=SuccessResponse[PaginatedData[AnnouncementOut]]
)
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
