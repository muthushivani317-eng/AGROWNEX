"""Farmer API routes (docs/API_CONTRACT.md → FARMER MODULE).

    GET  /farmers/me           PUT /farmers/me
    GET  /farmers/preferences  PUT /farmers/preferences
    GET  /farmers/languages    PUT /farmers/languages

Every route is authenticated (docs/SECURITY.md → JWT) and thin — all logic lives
in ``FarmerService``. Responses use the standard envelope (docs/API_CONTRACT.md).
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.farm_profile import service as farm_profile_service
from app.modules.farmers.dependencies import CurrentUser, FarmerServiceDep
from app.modules.farmers.schemas import (
    FarmerLanguageOut,
    FarmerMeOut,
    FarmerMeUpdate,
    LanguagesUpdate,
    PreferencesOut,
    PreferencesUpdate,
    preferences_out,
)
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/farmers", tags=["farmers"])


# ----- /farmers/me -----
@router.get("/me", response_model=SuccessResponse[FarmerMeOut])
async def get_me(current_user: CurrentUser, service: FarmerServiceDep):
    """Return the authenticated farmer's profile."""
    profile = await service.get_me(current_user)
    return success(await _me_out(service, profile, current_user))


@router.put("/me", response_model=SuccessResponse[FarmerMeOut])
async def update_me(
    payload: FarmerMeUpdate, current_user: CurrentUser, service: FarmerServiceDep
):
    """Create or update the authenticated farmer's profile."""
    profile = await service.update_me(current_user, payload)
    return success(await _me_out(service, profile, current_user), message="Profile saved")


async def _me_out(service, profile, user) -> FarmerMeOut:
    out = FarmerMeOut.from_profile(profile, user)
    out.farm_products = farm_profile_service.app_products_out(
        await farm_profile_service.list_items(service.session, user.id)
    )
    return out


# ----- /farmers/preferences -----
@router.get("/preferences", response_model=SuccessResponse[PreferencesOut])
async def get_preferences(current_user: CurrentUser, service: FarmerServiceDep):
    """Return the farmer's app preferences (theme, notifications, units…)."""
    preference = await service.get_preferences(current_user)
    return success(preferences_out(preference))


@router.put("/preferences", response_model=SuccessResponse[PreferencesOut])
async def update_preferences(
    payload: PreferencesUpdate, current_user: CurrentUser, service: FarmerServiceDep
):
    """Update the farmer's app preferences."""
    preference = await service.update_preferences(current_user, payload)
    return success(preferences_out(preference), message="Preferences saved")


# ----- /farmers/languages -----
@router.get("/languages", response_model=SuccessResponse[list[FarmerLanguageOut]])
async def get_languages(current_user: CurrentUser, service: FarmerServiceDep):
    """Return the farmer's language list (the default is flagged)."""
    rows = await service.get_languages(current_user)
    return success(FarmerLanguageOut.from_rows(rows))


@router.put("/languages", response_model=SuccessResponse[list[FarmerLanguageOut]])
async def update_languages(
    payload: LanguagesUpdate, current_user: CurrentUser, service: FarmerServiceDep
):
    """Replace the farmer's language list (exactly one default is enforced)."""
    rows = await service.update_languages(current_user, payload)
    return success(FarmerLanguageOut.from_rows(rows), message="Languages saved")
