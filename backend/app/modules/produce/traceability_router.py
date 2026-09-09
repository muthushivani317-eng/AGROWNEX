from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.modules.auth.dependencies import ControlledTester
from app.modules.produce.models import ProduceTraceBatch, ProduceTraceEvent, ProduceTraceShare
from app.modules.produce.repository import ProduceRepository
from app.modules.produce.traceability_schemas import (
    CultivationClassification,
    PublicTraceEventOut,
    PublicTraceTimelineOut,
    TraceEventCreate,
    TraceEventOut,
    TraceShareCreate,
    TraceShareOut,
    TraceShareRevoke,
    TraceTimelineOut,
)
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/produce", tags=["produce-traceability-controlled"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
DISCLAIMER = (
    "TEST MODE: Events are farmer-declared records and have not been independently "
    "verified. This timeline is not an organic, safety, quality, or origin certificate."
)
PUBLIC_PATH = "/api/v1/produce/traceability/public/"


def _share_token(batch_id: uuid.UUID, key: str) -> str:
    return hmac.new(
        settings.session_secret.encode(),
        f"trace-share:v1:{batch_id}:{key}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _public_base_url() -> str:
    value = settings.public_api_url.rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(503, detail={"code": "PUBLIC_SHARE_URL_NOT_CONFIGURED"})
    return value


async def _offer(session: AsyncSession, offer_id: uuid.UUID, user_id: uuid.UUID):
    offer = await ProduceRepository(session).get_for_user(offer_id, user_id)
    if offer is None:
        raise HTTPException(404, detail={"code": "PRODUCE_OFFER_NOT_FOUND"})
    return offer


async def _batch(session: AsyncSession, offer_id: uuid.UUID):
    return (
        await session.execute(
            select(ProduceTraceBatch).where(ProduceTraceBatch.offer_id == offer_id)
        )
    ).scalar_one_or_none()


async def _timeline(session: AsyncSession, batch: ProduceTraceBatch) -> TraceTimelineOut:
    events = (
        (
            await session.execute(
                select(ProduceTraceEvent)
                .where(ProduceTraceEvent.batch_id == batch.id)
                .order_by(ProduceTraceEvent.occurred_at.asc(), ProduceTraceEvent.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return TraceTimelineOut(
        batch_id=batch.id,
        offer_id=batch.offer_id,
        batch_code=batch.batch_code,
        cultivation_classification=batch.cultivation_classification,
        organic_profile_snapshot=batch.organic_profile_snapshot,
        certification_verified_snapshot=batch.certification_verified_snapshot,
        classification_snapshotted_at=batch.classification_snapshotted_at,
        events=[TraceEventOut.model_validate(row, from_attributes=True) for row in events],
        disclaimer=DISCLAIMER,
    )


@router.post(
    "/{offer_id}/traceability-controlled/initialize",
    response_model=SuccessResponse[TraceTimelineOut],
    status_code=201,
)
async def initialize_traceability(
    offer_id: uuid.UUID,
    tester: ControlledTester,
    session: SessionDep,
    cultivation_classification: CultivationClassification = CultivationClassification.CONVENTIONAL,
):
    offer = await _offer(session, offer_id, tester.user.id)
    batch = await _batch(session, offer_id)
    if batch is None:
        from app.modules.organic.repositories import OrganicRepository

        profile = await OrganicRepository(session).profile_for_farm(offer.farm_id)
        snapshot = None
        verified = False
        if profile is not None:
            verified = bool(
                profile.certification_status == "verified"
                and profile.certification_verified_at is not None
                and profile.certificate_expires_on is not None
                and profile.certificate_expires_on >= datetime.now(UTC).date()
            )
            snapshot = {
                "profile_id": str(profile.id),
                "mode": profile.mode,
                "plan_version": profile.plan_version,
                "certification_status": profile.certification_status,
                "certification_scheme": profile.certification_scheme,
                "certificate_expires_on": (
                    profile.certificate_expires_on.isoformat()
                    if profile.certificate_expires_on
                    else None
                ),
                "certification_verified_at": (
                    profile.certification_verified_at.isoformat()
                    if profile.certification_verified_at
                    else None
                ),
            }
        if (
            cultivation_classification == CultivationClassification.CERTIFIED_ORGANIC
            and not verified
        ):
            raise HTTPException(409, detail={"code": "CERTIFIED_ORGANIC_REQUIRES_VERIFICATION"})
        batch = ProduceTraceBatch(
            offer_id=offer_id,
            owner_user_id=tester.user.id,
            batch_code=f"AGW-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4).upper()}",
            cultivation_classification=cultivation_classification.value,
            organic_profile_snapshot=snapshot,
            certification_verified_snapshot=verified,
            classification_snapshotted_at=datetime.now(UTC),
        )
        session.add(batch)
        await session.flush()
    return success(await _timeline(session, batch), message="Traceability initialized")


@router.get(
    "/{offer_id}/traceability-controlled",
    response_model=SuccessResponse[TraceTimelineOut | None],
)
async def get_traceability(offer_id: uuid.UUID, tester: ControlledTester, session: SessionDep):
    await _offer(session, offer_id, tester.user.id)
    batch = await _batch(session, offer_id)
    return success(await _timeline(session, batch) if batch else None)


@router.post(
    "/{offer_id}/traceability-controlled/events",
    response_model=SuccessResponse[TraceTimelineOut],
    status_code=201,
)
async def add_trace_event(
    offer_id: uuid.UUID,
    payload: TraceEventCreate,
    tester: ControlledTester,
    session: SessionDep,
):
    await _offer(session, offer_id, tester.user.id)
    batch = await _batch(session, offer_id)
    if batch is None:
        raise HTTPException(409, detail={"code": "TRACEABILITY_NOT_INITIALIZED"})
    batch = await session.scalar(
        select(ProduceTraceBatch).where(ProduceTraceBatch.id == batch.id).with_for_update()
    )
    if payload.occurred_at.astimezone(UTC) > datetime.now(UTC):
        raise HTTPException(422, detail={"code": "TRACE_EVENT_IN_FUTURE"})
    # Serialize appends for this batch so concurrent requests cannot fork the chain.
    await session.execute(
        select(ProduceTraceBatch).where(ProduceTraceBatch.id == batch.id).with_for_update()
    )
    previous = (
        await session.execute(
            select(ProduceTraceEvent)
            .where(ProduceTraceEvent.batch_id == batch.id)
            .order_by(ProduceTraceEvent.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    canonical = json.dumps(
        {
            "batch_id": str(batch.id),
            "actor_user_id": str(tester.user.id),
            "event_type": payload.event_type.value,
            "occurred_at": payload.occurred_at.astimezone(UTC).isoformat(),
            "location_text": payload.location_text,
            "notes": payload.notes,
            "evidence_url": str(payload.evidence_url) if payload.evidence_url else None,
            "previous_hash": previous.event_hash if previous else None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    row = ProduceTraceEvent(
        batch_id=batch.id,
        actor_user_id=tester.user.id,
        previous_hash=previous.event_hash if previous else None,
        event_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        event_type=payload.event_type.value,
        occurred_at=payload.occurred_at,
        location_text=payload.location_text,
        notes=payload.notes,
        evidence_url=str(payload.evidence_url) if payload.evidence_url else None,
    )
    session.add(row)
    await session.flush()
    return success(await _timeline(session, batch), message="Traceability event recorded")


@router.post(
    "/{offer_id}/traceability-controlled/share",
    response_model=SuccessResponse[TraceShareOut],
    status_code=201,
)
async def create_trace_share(
    offer_id: uuid.UUID,
    payload: TraceShareCreate,
    tester: ControlledTester,
    session: SessionDep,
):
    await _offer(session, offer_id, tester.user.id)
    batch = await _batch(session, offer_id)
    if batch is None:
        raise HTTPException(409, detail={"code": "TRACEABILITY_NOT_INITIALIZED"})
    batch = await session.scalar(
        select(ProduceTraceBatch).where(ProduceTraceBatch.id == batch.id).with_for_update()
    )
    token = _share_token(batch.id, payload.idempotency_key)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = await session.scalar(
        select(ProduceTraceShare).where(ProduceTraceShare.batch_id == batch.id)
    )
    fields = sorted(set(payload.consent_fields))
    if row is None:
        row = ProduceTraceShare(
            batch_id=batch.id,
            owner_user_id=tester.user.id,
            token_hash=token_hash,
            consent_fields=fields,
            create_idempotency_key=payload.idempotency_key,
        )
        try:
            async with session.begin_nested():
                session.add(row)
                await session.flush()
        except IntegrityError:
            row = await session.scalar(
                select(ProduceTraceShare).where(ProduceTraceShare.batch_id == batch.id)
            )
            if row is None:
                raise
    if row.create_idempotency_key != payload.idempotency_key:
        raise HTTPException(409, detail={"code": "TRACE_SHARE_ALREADY_EXISTS"})
    if row.consent_fields != fields:
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT"})
    if row.revoked_at is not None:
        raise HTTPException(409, detail={"code": "TRACE_SHARE_REVOKED"})
    await session.flush()
    url = f"{_public_base_url()}{PUBLIC_PATH}{token}"
    return success(TraceShareOut(share_url=url, qr_payload=url, consent_fields=fields))


@router.post("/{offer_id}/traceability-controlled/share/revoke", status_code=204)
async def revoke_trace_share(
    offer_id: uuid.UUID,
    payload: TraceShareRevoke,
    tester: ControlledTester,
    session: SessionDep,
):
    await _offer(session, offer_id, tester.user.id)
    batch = await _batch(session, offer_id)
    row = (
        None
        if batch is None
        else await session.scalar(
            select(ProduceTraceShare).where(ProduceTraceShare.batch_id == batch.id)
        )
    )
    if row is None:
        raise HTTPException(404, detail={"code": "TRACE_SHARE_NOT_FOUND"})
    if row.revoke_idempotency_key not in {None, payload.idempotency_key}:
        raise HTTPException(409, detail={"code": "TRACE_SHARE_ALREADY_REVOKED"})
    row.revoke_idempotency_key = payload.idempotency_key
    row.revoked_at = row.revoked_at or datetime.now(UTC)
    await session.flush()


@router.get(
    "/traceability/public/{token}",
    response_model=SuccessResponse[PublicTraceTimelineOut],
)
async def public_traceability(token: str, session: SessionDep):
    if len(token) != 64:
        raise HTTPException(404, detail={"code": "TRACE_SHARE_NOT_FOUND"})
    row = await session.scalar(
        select(ProduceTraceShare).where(
            ProduceTraceShare.token_hash == hashlib.sha256(token.encode()).hexdigest(),
            ProduceTraceShare.revoked_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(404, detail={"code": "TRACE_SHARE_NOT_FOUND"})
    batch = await session.get(ProduceTraceBatch, row.batch_id)
    events = None
    if "events" in row.consent_fields:
        event_rows = (
            (
                await session.execute(
                    select(ProduceTraceEvent)
                    .where(ProduceTraceEvent.batch_id == batch.id)
                    .order_by(ProduceTraceEvent.occurred_at, ProduceTraceEvent.created_at)
                )
            )
            .scalars()
            .all()
        )
        events = [
            PublicTraceEventOut(event_type=e.event_type, occurred_at=e.occurred_at)
            for e in event_rows
        ]
    classification = (
        batch.cultivation_classification if "classification" in row.consent_fields else None
    )
    verified = None
    expires = None
    as_of = None
    if "classification" in row.consent_fields:
        snapshot = batch.organic_profile_snapshot or {}
        expires = snapshot.get("certificate_expires_on")
        as_of = datetime.now(UTC)
        verified = bool(
            batch.certification_verified_snapshot
            and expires
            and datetime.fromisoformat(expires).date() >= as_of.date()
        )
        if classification == CultivationClassification.CERTIFIED_ORGANIC and not verified:
            classification = CultivationClassification.ORGANIC_PRACTICES_UNVERIFIED
    return success(
        PublicTraceTimelineOut(
            batch_code=batch.batch_code,
            cultivation_classification=classification,
            certification_verified=verified,
            certification_as_of=as_of,
            certificate_expires_on=expires,
            certification_current=verified,
            events=events,
            disclaimer=DISCLAIMER,
        )
    )
