"""User repository — the only layer that queries the users table."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.auth.models import User
from app.shared.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def touch_last_login(self, user: User) -> None:
        user.last_login = datetime.now(UTC)
