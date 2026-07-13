"""Expert Connect API routes (docs: brief's endpoint list; reuse response envelope).

    GET  /experts                      (list verified experts; filter + paginate)
    GET  /experts/{id}                 (expert profile)
    POST /consultations                (create + auto-assign a consultation)
    GET  /consultations                (the farmer's consultations; filter/paginate)
    GET  /consultations/pending        (open consultations)
    GET  /consultations/history        (resolved / closed / cancelled)
    GET  /consultations/{id}           (full detail + conversation timeline)
    POST /consultations/{id}/reply     (append a farmer message)
    POST /consultations/{id}/attachments (attach an uploaded photo)
    PUT  /consultations/{id}/status    (resolve / cancel)

Thin routes — assignment, lifecycle and validation live in ``ExpertService``.
Static routes precede ``/{consultation_id}``. All endpoints are authenticated.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.experts.constants import ConsultationCategory, ConsultationStatus, ExpertType
from app.modules.experts.dependencies import CurrentUser, ExpertServiceDep
from app.modules.experts.schemas import (
    AttachmentIn,
    ConsultationCreate,
    ConsultationDetailOut,
    ConsultationListFilters,
    ConsultationSummaryOut,
    ExpertDetailOut,
    ExpertListFilters,
    ExpertSummaryOut,
    ReplyIn,
    StatusUpdateIn,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

experts_router = APIRouter(prefix="/experts", tags=["experts"])
consultations_router = APIRouter(prefix="/consultations", tags=["consultations"])


def _consult_page(page) -> PaginatedData[ConsultationSummaryOut]:
    return PaginatedData(
        items=[ConsultationSummaryOut.from_consultation(c) for c in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        total_pages=page.total_pages,
    )


# --------------------------------------------------------------------------- #
# Experts
# --------------------------------------------------------------------------- #
@experts_router.get("", response_model=SuccessResponse[PaginatedData[ExpertSummaryOut]])
async def list_experts(
    current_user: CurrentUser,
    service: ExpertServiceDep,
    category: ConsultationCategory | None = Query(None),
    crop: str | None = Query(None, max_length=80),
    district: str | None = Query(None, max_length=80),
    language: str | None = Query(None, max_length=8),
    expert_type: ExpertType | None = Query(None),
    search: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List verified agricultural experts, filterable by category/crop/district."""
    filters = ExpertListFilters(
        category=category,
        crop=crop,
        district=district,
        language=language,
        expert_type=expert_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    page_data = await service.list_experts(filters)
    return success(
        PaginatedData(
            items=[ExpertSummaryOut.from_expert(e) for e in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@experts_router.get("/{expert_id}", response_model=SuccessResponse[ExpertDetailOut])
async def get_expert(
    expert_id: uuid.UUID,
    current_user: CurrentUser,
    service: ExpertServiceDep,
):
    """A verified expert's full profile (specializations, coverage, availability)."""
    expert = await service.get_expert(expert_id)
    return success(ExpertDetailOut.from_expert_detail(expert))


# --------------------------------------------------------------------------- #
# Consultations
# --------------------------------------------------------------------------- #
@consultations_router.post(
    "",
    response_model=SuccessResponse[ConsultationDetailOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_consultation(
    payload: ConsultationCreate,
    current_user: CurrentUser,
    service: ExpertServiceDep,
):
    """Submit a question; it is auto-assigned to the best verified expert desk."""
    consultation = await service.create_consultation(current_user, payload)
    return success(
        ConsultationDetailOut.from_consultation_detail(consultation),
        message="Consultation submitted",
    )


@consultations_router.get(
    "", response_model=SuccessResponse[PaginatedData[ConsultationSummaryOut]]
)
async def list_consultations(
    current_user: CurrentUser,
    service: ExpertServiceDep,
    status_filter: ConsultationStatus | None = Query(None, alias="status"),
    category: ConsultationCategory | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List the farmer's consultations, filterable by status/category."""
    filters = ConsultationListFilters(
        status=status_filter, category=category, page=page, page_size=page_size
    )
    page_data = await service.list_consultations(current_user, filters)
    return success(_consult_page(page_data))


@consultations_router.get(
    "/pending", response_model=SuccessResponse[PaginatedData[ConsultationSummaryOut]]
)
async def pending_consultations(
    current_user: CurrentUser,
    service: ExpertServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Open (unresolved) consultations."""
    page_data = await service.pending(current_user, page=page, page_size=page_size)
    return success(_consult_page(page_data))


@consultations_router.get(
    "/history", response_model=SuccessResponse[PaginatedData[ConsultationSummaryOut]]
)
async def consultation_history(
    current_user: CurrentUser,
    service: ExpertServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Concluded consultations (resolved / closed / cancelled)."""
    page_data = await service.history(current_user, page=page, page_size=page_size)
    return success(_consult_page(page_data))


@consultations_router.get(
    "/{consultation_id}", response_model=SuccessResponse[ConsultationDetailOut]
)
async def get_consultation(
    consultation_id: uuid.UUID,
    current_user: CurrentUser,
    service: ExpertServiceDep,
):
    """Full consultation detail with the immutable conversation timeline."""
    consultation = await service.get_consultation(current_user, consultation_id)
    return success(ConsultationDetailOut.from_consultation_detail(consultation))


@consultations_router.post(
    "/{consultation_id}/reply",
    response_model=SuccessResponse[ConsultationDetailOut],
    status_code=status.HTTP_201_CREATED,
)
async def reply_consultation(
    consultation_id: uuid.UUID,
    payload: ReplyIn,
    current_user: CurrentUser,
    service: ExpertServiceDep,
):
    """Append a farmer message to the consultation thread."""
    consultation = await service.reply(current_user, consultation_id, payload)
    return success(
        ConsultationDetailOut.from_consultation_detail(consultation),
        message="Reply sent",
    )


@consultations_router.post(
    "/{consultation_id}/attachments",
    response_model=SuccessResponse[ConsultationDetailOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_attachment(
    consultation_id: uuid.UUID,
    payload: AttachmentIn,
    current_user: CurrentUser,
    service: ExpertServiceDep,
):
    """Attach an uploaded photo (S3/R2 URL + metadata) to the consultation."""
    consultation = await service.add_attachment(current_user, consultation_id, payload)
    return success(
        ConsultationDetailOut.from_consultation_detail(consultation),
        message="Attachment added",
    )


@consultations_router.put(
    "/{consultation_id}/status", response_model=SuccessResponse[ConsultationDetailOut]
)
async def update_status(
    consultation_id: uuid.UUID,
    payload: StatusUpdateIn,
    current_user: CurrentUser,
    service: ExpertServiceDep,
):
    """Resolve or cancel a consultation (every change is logged)."""
    consultation = await service.update_status(current_user, consultation_id, payload)
    return success(
        ConsultationDetailOut.from_consultation_detail(consultation),
        message="Status updated",
    )
