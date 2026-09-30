from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, File, Form, Header, Query, Response, UploadFile, status

from app.modules.action_verification.schemas import ActionOut
from app.modules.admin.dependencies import AdminContextDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.disease.storage import get_private_storage
from app.modules.organic.dependencies import OrganicAdminServiceDep, OrganicServiceDep
from app.modules.organic.schemas import (
    CertificationDocumentCreate,
    CertificationDocumentOut,
    CertificationReviewIn,
    DiseaseOrganicPlanOut,
    OrganicCatalogueCoverageOut,
    OrganicFarmSummaryOut,
    OrganicInputOut,
    OrganicInputPromotionIn,
    OrganicInputReviewItemOut,
    OrganicPlanBundleOut,
    OrganicProfileOut,
    OrganicProfileWrite,
    OrganicUploadAttestationOut,
    RegisterPlanActionIn,
    SoilOrganicMatterPlanOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(tags=["organic"])


@router.get("/admin/organic-certification-documents/{document_id}/content")
async def review_certification_document_content(
    document_id: uuid.UUID,
    admin_context: AdminContextDep,
    service: OrganicAdminServiceDep,
):
    data, mime_type, file_name = await service.certification_document_bytes(
        admin_context, document_id, get_private_storage()
    )
    safe_name = file_name.replace('"', "")
    return Response(
        content=data,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/farms/{farm_id}/organic-uploads",
    response_model=SuccessResponse[OrganicUploadAttestationOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_organic_evidence(
    farm_id: uuid.UUID,
    current_user: CurrentUser,
    service: OrganicServiceDep,
    purpose: str = Form(...),
    file: UploadFile = File(...),
):
    data = await file.read(15_000_001)
    suffix = (file.filename or "upload.bin").rsplit(".", 1)[-1]
    row, receipt = await service.upload_and_attest(
        current_user,
        farm_id,
        purpose=purpose,
        data=data,
        mime_type=file.content_type or "application/octet-stream",
        file_suffix=suffix,
        storage=get_private_storage(),
    )
    return success(
        OrganicUploadAttestationOut(
            id=row.id,
            purpose=row.purpose,
            object_version=row.object_version,
            issued_at=row.issued_at,
            expires_at=row.expires_at,
            mime_type=row.mime_type,
            file_size=row.file_size,
            sha256=row.sha256,
            upload_receipt=receipt,
        )
    )


@router.get(
    "/admin/organic-inputs/review-queue",
    response_model=SuccessResponse[list[OrganicInputReviewItemOut]],
)
async def organic_inputs_review_queue(
    admin_context: AdminContextDep, service: OrganicAdminServiceDep
):
    rows = await service.inputs_awaiting_review(admin_context)
    return success([OrganicInputReviewItemOut.model_validate(row) for row in rows])


@router.post(
    "/admin/organic-inputs/{input_id}/promote", response_model=SuccessResponse[OrganicInputOut]
)
async def promote_organic_input(
    input_id: uuid.UUID,
    payload: OrganicInputPromotionIn,
    admin_context: AdminContextDep,
    service: OrganicAdminServiceDep,
):
    return success(
        OrganicInputOut.model_validate(
            await service.promote_input(admin_context, input_id, reason=payload.reason)
        )
    )


@router.get("/organic-inputs/coverage", response_model=SuccessResponse[OrganicCatalogueCoverageOut])
async def organic_catalogue_coverage(current_user: CurrentUser, service: OrganicServiceDep):
    del current_user
    return success(await service.catalogue_coverage())


@router.get(
    "/farms/{farm_id}/organic-plan",
    response_model=SuccessResponse[OrganicPlanBundleOut],
)
async def organic_plan(farm_id: uuid.UUID, current_user: CurrentUser, service: OrganicServiceDep):
    plan = await service.farm_plan(current_user, farm_id)
    return success(OrganicPlanBundleOut.model_validate(plan))


@router.post(
    "/admin/organic-certifications/{profile_id}/review",
    response_model=SuccessResponse[OrganicProfileOut],
)
async def review_organic_certification(
    profile_id: uuid.UUID,
    payload: CertificationReviewIn,
    admin_context: AdminContextDep,
    service: OrganicAdminServiceDep,
):
    profile = await service.review_certification(
        admin_context,
        profile_id,
        decision=payload.decision,
        reason=payload.reason,
        expected_plan_version=payload.expected_plan_version,
    )
    return success(OrganicProfileOut.model_validate(profile), message="Certification reviewed")


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


@router.get("/organic-inputs/{input_id:uuid}", response_model=SuccessResponse[OrganicInputOut])
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


@router.post(
    "/disease-reports/{report_id}/organic-actions",
    response_model=SuccessResponse[ActionOut],
)
async def register_disease_action(
    report_id: uuid.UUID,
    payload: RegisterPlanActionIn,
    current_user: CurrentUser,
    service: OrganicServiceDep,
):
    row = await service.register_disease_action(
        current_user, report_id, payload.action_code, payload.source_record_id
    )
    return success(ActionOut.from_row(row))


@router.post(
    "/farms/{farm_id}/soil-organic-actions",
    response_model=SuccessResponse[ActionOut],
)
async def register_soil_action(
    farm_id: uuid.UUID,
    payload: RegisterPlanActionIn,
    current_user: CurrentUser,
    service: OrganicServiceDep,
):
    row = await service.register_soil_action(
        current_user, farm_id, payload.action_code, payload.source_record_id
    )
    return success(ActionOut.from_row(row))
