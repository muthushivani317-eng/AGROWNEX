"""Farmer service — business logic for profile, preferences and languages.

Sits between the API layer and the repositories (docs/BACKEND_ARCHITECTURE.md):
the API never touches a repository directly, repositories never contain business
rules. Identity/session logic lives in the auth module and is not duplicated
here — this service only owns the farmer's profile data.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.exceptions import ProfileNotFoundError
from app.modules.auth.models import User
from app.modules.auth.profile_models import (
    FarmerLanguage,
    FarmerPreference,
    FarmerProfile,
)
from app.modules.auth.repositories import FarmerProfileRepository
from app.modules.farm_profile.service import apply_app_farm_products, apply_onboarding_fields
from app.modules.farmers.constants import DEFAULT_LANGUAGE
from app.modules.farmers.repositories import (
    FarmerLanguageRepository,
    FarmerPreferenceRepository,
)
from app.modules.farmers.schemas import (
    FarmerLanguageIn,
    FarmerMeUpdate,
    LanguagesUpdate,
    PreferencesUpdate,
)

logger = get_logger("farmers.service")


class FarmerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = FarmerProfileRepository(session)
        self.preferences = FarmerPreferenceRepository(session)
        self.languages = FarmerLanguageRepository(session)

    # ----- Profile (/farmers/me) -----
    async def _require_profile(self, user: User) -> FarmerProfile:
        profile = await self.profiles.get_by_user_id(user.id)
        if profile is None:
            raise ProfileNotFoundError()
        return profile

    async def get_me(self, user: User) -> FarmerProfile:
        return await self._require_profile(user)

    async def update_me(self, user: User, data: FarmerMeUpdate) -> FarmerProfile:
        """Create or update the farmer's profile (single row per user)."""
        crops = [c for c in data.preferred_crops if c]
        primary = crops[0] if crops else None
        secondary = crops[1] if len(crops) > 1 else None

        profile = await self.profiles.get_by_user_id(user.id)
        if profile is None:
            profile = FarmerProfile(user_id=user.id)
            self.session.add(profile)

        profile.full_name = data.full_name
        profile.gender = data.gender
        profile.language = data.language
        profile.district = data.district
        profile.block = data.block
        profile.village = data.village
        profile.experience_years = data.experience_years
        profile.education = data.education
        profile.profile_photo = data.profile_photo
        profile.primary_crop = primary
        profile.secondary_crop = secondary
        apply_onboarding_fields(profile, data)
        await apply_app_farm_products(self.session, user.id, data)
        await self.session.flush()

        await self._ensure_defaults(profile)
        # SQLAlchemy expires server-generated/on-update timestamp columns after
        # a flush.  Refresh while we are still in an awaited service method so
        # response serialization cannot trigger implicit async database I/O.
        await self.session.refresh(profile)
        logger.info("Profile saved for user_id=%s", user.id)
        return profile

    async def _ensure_defaults(self, profile: FarmerProfile) -> None:
        """Guarantee the preference + default-language rows exist for a profile."""
        if await self.preferences.get_by_farmer_id(profile.id) is None:
            self.session.add(
                FarmerPreference(
                    farmer_id=profile.id, default_crop=profile.primary_crop
                )
            )
        if not await self.languages.list_for_farmer(profile.id):
            self.session.add(
                FarmerLanguage(
                    farmer_id=profile.id,
                    language_code=profile.language or DEFAULT_LANGUAGE,
                    is_default=True,
                )
            )
        await self.session.flush()

    # ----- Preferences (/farmers/preferences) -----
    async def get_preferences(self, user: User) -> FarmerPreference:
        profile = await self._require_profile(user)
        preference = await self.preferences.get_by_farmer_id(profile.id)
        if preference is None:
            preference = await self.preferences.add(
                FarmerPreference(
                    farmer_id=profile.id, default_crop=profile.primary_crop
                )
            )
        return preference

    async def update_preferences(
        self, user: User, data: PreferencesUpdate
    ) -> FarmerPreference:
        preference = await self.get_preferences(user)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(preference, key, value)
        await self.session.flush()
        return preference

    # ----- Languages (/farmers/languages) -----
    async def get_languages(self, user: User) -> list[FarmerLanguage]:
        profile = await self._require_profile(user)
        rows = await self.languages.list_for_farmer(profile.id)
        if not rows:
            row = await self.languages.add(
                FarmerLanguage(
                    farmer_id=profile.id,
                    language_code=profile.language or DEFAULT_LANGUAGE,
                    is_default=True,
                )
            )
            rows = [row]
        return rows

    async def update_languages(
        self, user: User, data: LanguagesUpdate
    ) -> list[FarmerLanguage]:
        """Replace the farmer's language set and sync the profile default."""
        profile = await self._require_profile(user)
        chosen = self._normalise_languages(data.languages)

        await self.languages.delete_all_for_farmer(profile.id)
        await self.session.flush()
        for item in chosen:
            self.session.add(
                FarmerLanguage(
                    farmer_id=profile.id,
                    language_code=item.language_code,
                    is_default=item.is_default,
                )
            )

        # Keep the profile's primary language aligned with the default choice.
        default = next(item for item in chosen if item.is_default)
        profile.language = default.language_code
        await self.session.flush()
        return await self.languages.list_for_farmer(profile.id)

    @staticmethod
    def _normalise_languages(items: list[FarmerLanguageIn]) -> list[FarmerLanguageIn]:
        """De-duplicate by code and guarantee exactly one default language."""
        unique: list[FarmerLanguageIn] = []
        seen: set[str] = set()
        for item in items:
            if item.language_code in seen:
                continue
            seen.add(item.language_code)
            unique.append(item)

        default_seen = False
        for item in unique:
            if item.is_default and not default_seen:
                default_seen = True
            elif item.is_default:
                item.is_default = False  # collapse extra defaults
        if not default_seen:
            unique[0].is_default = True  # first entry becomes the default
        return unique
