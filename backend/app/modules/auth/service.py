"""Auth service — business logic for authentication and profile setup.

Sits between the API layer and the repositories (docs/BACKEND_ARCHITECTURE.md):
the API never touches a repository directly, and repositories never call the IdP.

Identity is verified by Firebase (docs/SECURITY.md → Firebase JWT). This service
adds server-side session management on top: OTP audit/throttling, login history,
device sessions, refresh-token rotation and RBAC assignment.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import verify_id_token
from app.modules.auth.constants import (
    OTP_RESEND_WINDOW_SECONDS,
    OTP_TTL_SECONDS,
    REFRESH_TOKEN_TTL_DAYS,
    LoginMethod,
    RoleName,
    UserStatus,
)
from app.modules.auth.exceptions import (
    InvalidRefreshTokenError,
    OtpRateLimitError,
    ProfileNotFoundError,
    UserNotFoundError,
)
from app.modules.auth.models import (
    LoginHistory,
    OtpRequest,
    RefreshToken,
    User,
    UserSession,
)
from app.modules.auth.profile_models import (
    FarmerLanguage,
    FarmerPreference,
    FarmerProfile,
)
from app.modules.auth.rbac_models import UserRole
from app.modules.auth.repositories import (
    FarmerProfileRepository,
    LoginHistoryRepository,
    OtpRepository,
    RefreshTokenRepository,
    RoleRepository,
    SessionRepository,
)
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import ProfileUpdateRequest
from app.modules.auth.security import generate_refresh_token, hash_token
from app.modules.farm_profile.service import apply_app_farm_products, apply_onboarding_fields

logger = get_logger("auth.service")


@dataclass
class SessionResult:
    user: User
    profile: FarmerProfile | None
    roles: list[str]
    refresh_token: str
    session_id: uuid.UUID


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.otps = OtpRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.sessions = SessionRepository(session)
        self.logins = LoginHistoryRepository(session)
        self.roles = RoleRepository(session)
        self.profiles = FarmerProfileRepository(session)

    # ----- OTP (audit + throttle; Firebase dispatches the SMS on-device) -----
    async def send_otp(self, phone_number: str) -> int:
        window_start = datetime.now(UTC) - timedelta(seconds=OTP_RESEND_WINDOW_SECONDS)
        recent = await self.otps.count_recent_for_phone(phone_number, window_start)
        if recent >= 1:
            raise OtpRateLimitError()

        await self.otps.add(
            OtpRequest(
                phone_number=phone_number,
                otp_hash=None,  # Firebase owns the code; this row is audit/throttle.
                expires_at=datetime.now(UTC) + timedelta(seconds=OTP_TTL_SECONDS),
                attempt_count=0,
                verified=False,
            )
        )
        logger.info("OTP dispatch recorded")
        return OTP_TTL_SECONDS

    # ----- Session establishment -----
    async def verify_otp(
        self, id_token: str, *, device_name: str | None, device_type: str | None
    ) -> SessionResult:
        result = await self._establish(
            id_token, LoginMethod.PHONE, device_name=device_name, device_type=device_type
        )
        # Mark the pending OTP request for this phone as verified.
        if result.user.phone_number:
            pending = await self.otps.latest_unverified(result.user.phone_number)
            if pending is not None:
                pending.verified = True
                pending.user_id = result.user.id
        return result

    async def login_google(
        self, id_token: str, *, device_name: str | None, device_type: str | None
    ) -> SessionResult:
        return await self._establish(
            id_token, LoginMethod.GOOGLE, device_name=device_name, device_type=device_type
        )

    async def login_apple(
        self, id_token: str, *, device_name: str | None, device_type: str | None
    ) -> SessionResult:
        return await self._establish(
            id_token, LoginMethod.APPLE, device_name=device_name, device_type=device_type
        )

    async def _establish(
        self,
        id_token: str,
        method: LoginMethod,
        *,
        device_name: str | None,
        device_type: str | None,
    ) -> SessionResult:
        stage = "firebase_token_verification"
        try:
            claims = verify_id_token(id_token)
            stage = "user_lookup_or_create"
            user = await self._get_or_create_from_claims(claims)
            stage = "last_login_update"
            await self.users.touch_last_login(user)

            stage = "login_history_creation"
            await self.logins.add(
                LoginHistory(user_id=user.id, login_method=method.value, success=True)
            )
            stage = "session_creation"
            session = await self.sessions.add(
                UserSession(
                    user_id=user.id,
                    device_name=device_name,
                    device_type=device_type,
                    last_active=datetime.now(UTC),
                )
            )
            stage = "refresh_token_persistence"
            refresh_plain = await self._issue_refresh_token(user.id)
            stage = "role_lookup"
            roles = await self.roles.get_user_role_names(user.id)
            stage = "profile_lookup"
            profile = await self.profiles.get_by_user_id(user.id)
            return SessionResult(
                user=user,
                profile=profile,
                roles=roles,
                refresh_token=refresh_plain,
                session_id=session.id,
            )
        except Exception as exc:
            # The outer DB dependency owns rollback. Log only the stable stage and
            # exception class; never tokens, decoded claims, phone numbers or IDs.
            logger.exception(
                "Authentication session establishment failed stage=%s exception=%s",
                stage,
                type(exc).__name__,
            )
            raise

    async def _get_or_create_from_claims(self, claims: dict[str, Any]) -> User:
        firebase_uid = claims["uid"]
        existing = await self.users.get_by_firebase_uid(firebase_uid)
        if existing is not None:
            if existing.status != UserStatus.ACTIVE or existing.deleted_at is not None:
                raise InvalidRefreshTokenError()
            return existing

        user = User(
            firebase_uid=firebase_uid,
            phone_number=claims.get("phone_number"),
            email=claims.get("email"),
            is_phone_verified=bool(claims.get("phone_number")),
            is_email_verified=bool(claims.get("email_verified")),
            status=UserStatus.ACTIVE,
        )
        created = await self.users.add(user)
        await self._assign_default_role(created.id)
        logger.info("Created Firebase-authenticated user")
        return created

    async def _assign_default_role(self, user_id: uuid.UUID) -> None:
        role = await self.roles.get_by_name(RoleName.FARMER.value)
        if role is not None:
            self.session.add(UserRole(user_id=user_id, role_id=role.id))

    async def _issue_refresh_token(self, user_id: uuid.UUID) -> str:
        plaintext, token_hash = generate_refresh_token()
        await self.refresh_tokens.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
                revoked=False,
            )
        )
        return plaintext

    async def refresh_session(self, refresh_token: str) -> tuple[User, str]:
        token = await self.refresh_tokens.get_active_by_hash(hash_token(refresh_token))
        if token is None:
            raise InvalidRefreshTokenError()

        token.revoked = True  # rotate: single-use tokens.
        user = await self.users.get(token.user_id)
        if user is None:
            raise UserNotFoundError()
        # Match the same account-status gate app.modules.auth.dependencies.
        # get_current_user applies to every other authenticated request --
        # previously a deactivated/deleted account's still-valid refresh
        # token could keep minting new sessions indefinitely, since this was
        # the one auth path that never re-checked status after the initial
        # login (2026-08 pre-release audit). Deliberately reuses
        # InvalidRefreshTokenError rather than a more specific "account
        # deactivated" error, so a stolen refresh token doesn't let an
        # attacker distinguish "revoked" from "account disabled".
        if user.status != UserStatus.ACTIVE or user.deleted_at is not None:
            raise InvalidRefreshTokenError()
        new_plain = await self._issue_refresh_token(user.id)
        return user, new_plain

    async def logout(self, user: User, refresh_token: str | None) -> None:
        if refresh_token:
            token = await self.refresh_tokens.get_active_by_hash(
                hash_token(refresh_token)
            )
            if token is not None:
                token.revoked = True
        else:
            await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.logins.add(
            LoginHistory(user_id=user.id, login_method="logout", success=True)
        )

    async def close_account(self, user: User) -> None:
        """Immediately disable access while preserving required audit records."""
        user.status = UserStatus.DELETED
        user.deleted_at = datetime.now(UTC)
        user.is_deleted = True
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.sessions.revoke_all_for_user(user.id)
        await self.logins.add(
            LoginHistory(
                user_id=user.id,
                login_method="account_closure",
                success=True,
            )
        )

    # ----- Profile -----
    async def get_user_by_firebase_uid(self, firebase_uid: str) -> User:
        user = await self.users.get_by_firebase_uid(firebase_uid)
        if user is None:
            raise UserNotFoundError()
        return user

    async def get_profile(self, user: User) -> FarmerProfile:
        profile = await self.profiles.get_by_user_id(user.id)
        if profile is None:
            raise ProfileNotFoundError()
        return profile

    async def upsert_profile(
        self, user: User, data: ProfileUpdateRequest
    ) -> FarmerProfile:
        crops = data.preferred_crops
        primary = crops[0] if crops else None
        secondary = crops[1] if len(crops) > 1 else None

        profile = await self.profiles.get_by_user_id(user.id)
        if profile is None:
            profile = FarmerProfile(user_id=user.id)
            self.session.add(profile)

        profile.full_name = data.full_name
        profile.language = data.language
        profile.district = data.district
        profile.block = data.block
        profile.village = data.village
        profile.experience_years = data.experience_years
        profile.annual_income = data.annual_income
        profile.profile_photo = data.profile_photo
        profile.primary_crop = primary
        profile.secondary_crop = secondary
        apply_onboarding_fields(profile, data)
        await apply_app_farm_products(self.session, user.id, data)
        await self.session.flush()

        await self._ensure_profile_defaults(profile, data.language)
        return profile

    async def _ensure_profile_defaults(
        self, profile: FarmerProfile, language: str
    ) -> None:
        """Create the preference + default-language rows on first save."""
        result = await self.session.execute(
            select(FarmerPreference).where(FarmerPreference.farmer_id == profile.id)
        )
        if result.scalar_one_or_none() is None:
            self.session.add(
                FarmerPreference(farmer_id=profile.id, default_crop=profile.primary_crop)
            )
            self.session.add(
                FarmerLanguage(
                    farmer_id=profile.id, language_code=language, is_default=True
                )
            )
