from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.auth.dependencies import ControlledTester, CurrentUser

from .registry import RESTRICTED_CROPS, get_recommendation

router = APIRouter(prefix="/disease-recommendations", tags=["disease-recommendations"])

class RecommendationRequest(BaseModel):
    crop_id: str = Field(min_length=1, max_length=32)
    runtime_label: str = Field(min_length=1, max_length=128)
    diagnosis_accepted: bool
    crop_confirmed: bool

@router.post("/lookup")
async def lookup(current_user: CurrentUser, payload: RecommendationRequest):
    # Was missing the auth dependency its sibling /lookup-restricted has --
    # this is a lightweight registry lookup, not an AI call, but every other
    # endpoint in the app requires a signed-in farmer, and leaving this one
    # open let anyone on the internet call it unauthenticated (2026-08
    # pre-release audit).
    del current_user
    if not payload.crop_confirmed:
        return {"outcome": "EXPERT_REVIEW_RECOMMENDED", "reason": "FARMER_CROP_CONFIRMATION_REQUIRED"}
    return get_recommendation(payload.crop_id, payload.runtime_label, diagnosis_accepted=payload.diagnosis_accepted)


@router.post("/lookup-restricted")
async def lookup_restricted(tester: ControlledTester, payload: RecommendationRequest):
    del tester
    if payload.crop_id not in RESTRICTED_CROPS:
        raise HTTPException(
            status_code=422,
            detail={"code": "RESTRICTED_CROP_REQUIRED"},
        )
    if not payload.crop_confirmed:
        return {
            "outcome": "EXPERT_REVIEW_RECOMMENDED",
            "reason": "FARMER_CROP_CONFIRMATION_REQUIRED",
        }
    return get_recommendation(
        payload.crop_id,
        payload.runtime_label,
        diagnosis_accepted=payload.diagnosis_accepted,
        controlled_test=True,
    )
