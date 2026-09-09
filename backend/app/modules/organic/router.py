from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Header, Query, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.organic.dependencies import OrganicServiceDep
from app.modules.organic.schemas import (
    CertificationDocumentCreate,
    CertificationDocumentOut,
    DiseaseOrganicPlanOut,
    OrganicFarmSummaryOut,
    OrganicInputOut,
    OrganicProfileOut,
    OrganicProfileWrite,
    SoilOrganicMatterPlanOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(tags=["organic"])


@router.get(
    "/farms/{farm_id}/organic-plan-summary",
    response_model=SuccessResponse[OrganicFarmSummaryOut],
)
async def organic_plan_summary(
    farm_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep
):
    return success(
        OrganicFarmSummaryOut.model_validate(await service.farm_summary(current_user, farm_id))
    )


@router.get("/farms/{farm_id}/organic-profile", response_model=SuccessResponse[OrganicProfileOut])
async def get_profile(farm_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep):
    return success(
        OrganicProfileOut.model_validate(await service.get_profile(current_user, farm_id))
    )


@router.put("/farms/{farm_id}/organic-profile", response_model=SuccessResponse[OrganicProfileOut])
async def upsert_profile(
    farm_id: uuid.UUID,
    payload: OrganicProfileWrite,
    current_user: CurrentUser,
    service: OrganicServiceDep,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
):
    profile = await service.upsert_profile(current_user, farm_id, payload, idempotency_key)
    return success(OrganicProfileOut.model_validate(profile), message="Organic farm profile saved")


@router.post(
    "/farms/{farm_id}/organic-certification-documents",
    response_model=SuccessResponse[CertificationDocumentOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_document(
    farm_id: uuid.UUID,
    payload: CertificationDocumentCreate,
    current_user: CurrentUser,
    service: OrganicServiceDep,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
):
    document = await service.add_document(current_user, farm_id, payload, idempotency_key)
    return success(
        CertificationDocumentOut.model_validate(document), message="Certification document recorded"
    )


@router.get(
    "/farms/{farm_id}/organic-certification-documents",
    response_model=SuccessResponse[list[CertificationDocumentOut]],
)
async def list_documents(farm_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep):
    rows = await service.list_documents(current_user, farm_id)
    return success([CertificationDocumentOut.model_validate(row) for row in rows])


@router.get("/organic-inputs", response_model=SuccessResponse[PaginatedData[OrganicInputOut]])
async def list_inputs(
    current_user: CurrentUser,
    service: OrganicServiceDep,
    category: str | None = Query(None, max_length=80),
    crop: str | None = Query(None, max_length=80),
    q: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rows, total = await service.list_inputs(
        category=category, crop=crop, search=q, page=page, page_size=page_size
    )
    return success(
        PaginatedData(
            items=[OrganicInputOut.model_validate(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        )
    )


@router.get("/organic-inputs/{input_id}", response_model=SuccessResponse[OrganicInputOut])
async def get_input(input_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep):
    del current_user
    return success(OrganicInputOut.model_validate(await service.get_input(input_id)))


@router.get(
    "/disease-reports/{report_id}/organic-action-plan",
    response_model=SuccessResponse[DiseaseOrganicPlanOut],
)
async def disease_action_plan(
    report_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep
):
    return success(
        DiseaseOrganicPlanOut.model_validate(await service.disease_plan(current_user, report_id))
    )


@router.get(
    "/farms/{farm_id}/soil-organic-matter-plan",
    response_model=SuccessResponse[SoilOrganicMatterPlanOut],
)
async def soil_organic_matter_plan(
    farm_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep
):
    return success(
        SoilOrganicMatterPlanOut.model_validate(await service.soil_plan(current_user, farm_id))
    )
