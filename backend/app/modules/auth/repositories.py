"""Auth-domain repositories (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the OTP, session, token, RBAC and profile tables.
Services depend on these; API routes never run SQL.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.auth.models import (
    LoginHistory,
    OtpRequest,
    RefreshToken,
    UserSession,
)
from app.modules.auth.profile_models import FarmerProfile
from app.modules.auth.rbac_models import Role, UserRole
from app.shared.base_repository import BaseRepository


class OtpRepository(BaseRepository[OtpRequest]):
    model = OtpRequest

    async def count_recent_for_phone(self, phone: str, since: datetime) -> int:
        result = await self.session.execute(
            select(OtpRequest).where(
                OtpRequest.phone_number == phone,
                OtpRequest.created_at >= since,
            )
        )
        return len(result.scalars().all())

    async def latest_unverified(self, phone: str) -> OtpRequest | None:
        result = await self.session.execute(
            select(OtpRequest)
            .where(
                OtpRequest.phone_number == phone,
                OtpRequest.verified.is_(False),
            )
            .order_by(OtpRequest.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        # SQLite returns naive datetimes; Postgres returns tz-aware. Normalise
        # to UTC before comparing so expiry checks work on both.
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= datetime.now(UTC):
            return None
        return token

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
        )
        for token in result.scalars().all():
            token.revoked = True


class SessionRepository(BaseRepository[UserSession]):
    model = UserSession


class LoginHistoryRepository(BaseRepository[LoginHistory]):
    model = LoginHistory


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def get_by_name(self, role_name: str) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.role_name == role_name)
        )
        return result.scalar_one_or_none()

    async def get_user_role_names(self, user_id: uuid.UUID) -> list[str]:
        result = await self.session.execute(
            select(Role.role_name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())


class FarmerProfileRepository(BaseRepository[FarmerProfile]):
    model = FarmerProfile

    async def get_by_user_id(self, user_id: uuid.UUID) -> FarmerProfile | None:
        result = await self.session.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
