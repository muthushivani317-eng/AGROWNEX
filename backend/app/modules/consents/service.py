from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserConsentEvent, UserConsentState
from .notices import resolve_notice

CONSENT_PURPOSES = frozenset(
    {"optional_product_analytics", "buyer_contact_sharing", "marketing", "precise_location"}
)


class ConsentWriteConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConsentState:
    purpose: str
    granted: bool
    version: int
    policy_version: str | None
    notice_hash: str | None
    channel: str | None
    locale: str | None
    decided_at: datetime | None


class ConsentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def current(self, user_id: uuid.UUID) -> list[ConsentState]:
        rows = (
            (
                await self.session.execute(
                    select(UserConsentEvent)
                    .where(UserConsentEvent.user_id == user_id)
                    .order_by(UserConsentEvent.purpose, UserConsentEvent.version.desc())
                )
            )
            .scalars()
            .all()
        )
        latest = {}
        for row in rows:
            latest.setdefault(row.purpose, row)
        return [self._state(p, latest.get(p)) for p in sorted(CONSENT_PURPOSES)]

    async def is_granted(self, user_id: uuid.UUID, purpose: str) -> bool:
        if purpose not in CONSENT_PURPOSES:
            return False
        return {x.purpose: x for x in await self.current(user_id)}[purpose].granted

    async def require_consent(self, user_id: uuid.UUID, purpose: str) -> None:
        """Fail closed; no buyer-contact/precise-location release endpoint exists yet."""
        if not await self.is_granted(user_id, purpose):
            raise PermissionError("CONSENT_REQUIRED")

    async def _replay(self, user_id, purpose, key, granted):
        row = await self.session.scalar(
            select(UserConsentEvent).where(
                UserConsentEvent.user_id == user_id,
                UserConsentEvent.purpose == purpose,
                UserConsentEvent.idempotency_key == key,
            )
        )
        if row and row.granted != granted:
            raise ValueError("IDEMPOTENCY_KEY_REUSED")
        return row

    async def record(
        self,
        user_id: uuid.UUID,
        *,
        purpose: str,
        granted: bool,
        idempotency_key: str,
        locale: str,
        notice_version: str,
    ) -> ConsentState:
        if purpose not in CONSENT_PURPOSES:
            raise ValueError("UNSUPPORTED_CONSENT_PURPOSE")
        notice = resolve_notice(purpose, locale, notice_version)
        if replay := await self._replay(user_id, purpose, idempotency_key, granted):
            return self._state(purpose, replay)
        values = {"user_id": user_id, "purpose": purpose, "last_version": 0}
        dialect = self.session.bind.dialect.name
        stmt = (
            pg_insert(UserConsentState)
            if dialect == "postgresql"
            else sqlite_insert(UserConsentState)
        )
        await self.session.execute(
            stmt.values(**values).on_conflict_do_nothing(index_elements=["user_id", "purpose"])
        )
        counter = await self.session.scalar(
            select(UserConsentState)
            .where(UserConsentState.user_id == user_id, UserConsentState.purpose == purpose)
            .with_for_update()
        )
        if replay := await self._replay(user_id, purpose, idempotency_key, granted):
            return self._state(purpose, replay)
        counter.last_version += 1
        row = UserConsentEvent(
            user_id=user_id,
            purpose=purpose,
            granted=granted,
            version=counter.last_version,
            idempotency_key=idempotency_key,
            policy_version=notice.version,
            notice_hash=notice.sha256,
            channel="farmer_app_api",
            locale=notice.locale,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return self._state(purpose, row)

    @staticmethod
    def _state(purpose, row):
        if row is None:
            return ConsentState(purpose, False, 0, None, None, None, None, None)
        return ConsentState(
            row.purpose,
            row.granted,
            row.version,
            row.policy_version,
            row.notice_hash,
            row.channel,
            row.locale,
            row.created_at,
        )
