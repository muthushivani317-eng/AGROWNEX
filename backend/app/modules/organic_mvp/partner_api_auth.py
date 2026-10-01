"""Partner API key authentication for the external FPO data feed.

Resolves a request's `X-Partner-Api-Key` header to exactly one
organization_id, server-side. organization_id is NEVER accepted as a
client-supplied parameter anywhere in partner_feed_router -- this dependency
is the single place that decides which organization a key belongs to, which
is what guarantees one FPO can never read another FPO's data, including by
tampering with a URL or query parameter.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import UnauthorizedError
from app.modules.auth.security import verify_token
from app.modules.organic_mvp.models import OrganicPartnerApiKey, OrganicPartnerOrganization

# Keys are long-lived bearer secrets that live on partner servers; force a
# rotation at least twice a year so a silently leaked key stops working.
PARTNER_API_KEY_MAX_AGE_DAYS = 180


@dataclass(frozen=True)
class PartnerApiKeyContext:
    organization_id: uuid.UUID
    organization_name: str
    key_id: uuid.UUID


async def get_partner_api_key_context(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_partner_api_key: Annotated[str | None, Header()] = None,
) -> PartnerApiKeyContext:
    if not x_partner_api_key or "." not in x_partner_api_key:
        raise UnauthorizedError(
            "A valid partner API key is required.",
            error_code="PARTNER_API_KEY_REQUIRED",
        )
    prefix, _, secret = x_partner_api_key.partition(".")
    key = await session.scalar(
        select(OrganicPartnerApiKey).where(
            OrganicPartnerApiKey.key_prefix == prefix,
            OrganicPartnerApiKey.revoked_at.is_(None),
        )
    )
    if key is None or not verify_token(secret, key.key_hash):
        raise UnauthorizedError(
            "Invalid or revoked partner API key.",
            error_code="PARTNER_API_KEY_INVALID",
        )
    created = key.created_at if key.created_at.tzinfo else key.created_at.replace(tzinfo=UTC)
    if datetime.now(UTC) - created > timedelta(days=PARTNER_API_KEY_MAX_AGE_DAYS):
        raise UnauthorizedError(
            "This partner API key has expired. Ask AgrowNex for a new key.",
            error_code="PARTNER_API_KEY_EXPIRED",
        )
    organization = await session.get(OrganicPartnerOrganization, key.organization_id)
    if organization is None:
        raise UnauthorizedError(
            "Invalid or revoked partner API key.",
            error_code="PARTNER_API_KEY_INVALID",
        )
    key.last_used_at = datetime.now(UTC)
    await session.commit()
    return PartnerApiKeyContext(
        organization_id=key.organization_id,
        organization_name=organization.name,
        key_id=key.id,
    )


PartnerApiKeyDep = Annotated[PartnerApiKeyContext, Depends(get_partner_api_key_context)]


def record_partner_read(
    session: AsyncSession, partner: PartnerApiKeyContext, action: str, rows: int, target_id: str | None = None
) -> None:
    """Audit every partner-feed read (which key, what, how many rows).

    Added to the session; the caller's commit persists it.
    """
    from app.modules.admin.models import AuditLog

    session.add(
        AuditLog(
            action=action,
            target="organic_partner_org",
            target_id=target_id or str(partner.organization_id),
            meta={"key_id": str(partner.key_id), "organization_id": str(partner.organization_id), "rows": rows},
        )
    )
