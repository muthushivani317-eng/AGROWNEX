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
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import UnauthorizedError
from app.modules.auth.security import verify_token
from app.modules.organic_mvp.models import OrganicPartnerApiKey, OrganicPartnerOrganization


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
