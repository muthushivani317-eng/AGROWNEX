from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import ControlledTester
from app.modules.produce.models import ProduceTraceBatch, ProduceTraceEvent
from app.modules.produce.repository import ProduceRepository
from app.modules.produce.traceability_schemas import (
    TraceEventCreate,
    TraceEventOut,
    TraceTimelineOut,
)
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/produce", tags=["produce-traceability-controlled"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
DISCLAIMER = (
    "TEST MODE: Events are farmer-declared records and have not been independently "
    "verified. This timeline is not an organic, safety, quality, or origin certificate."
)


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
        await session.execute(
            select(ProduceTraceEvent)
            .where(ProduceTraceEvent.batch_id == batch.id)
            .order_by(ProduceTraceEvent.occurred_at.asc(), ProduceTraceEvent.created_at.asc())
        )
    ).scalars().all()
    return TraceTimelineOut(
        batch_id=batch.id,
        offer_id=batch.offer_id,
        batch_code=batch.batch_code,
        events=[TraceEventOut.model_validate(row, from_attributes=True) for row in events],
        disclaimer=DISCLAIMER,
    )


@router.post(
    "/{offer_id}/traceability-controlled/initialize",
    response_model=SuccessResponse[TraceTimelineOut],
    status_code=201,
)
async def initialize_traceability(
    offer_id: uuid.UUID, tester: ControlledTester, session: SessionDep
):
    await _offer(session, offer_id, tester.user.id)
    batch = await _batch(session, offer_id)
    if batch is None:
        batch = ProduceTraceBatch(
            offer_id=offer_id,
            owner_user_id=tester.user.id,
            batch_code=f"AGW-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4).upper()}",
        )
        session.add(batch)
        await session.flush()
    return success(await _timeline(session, batch), message="Traceability initialized")


@router.get(
    "/{offer_id}/traceability-controlled",
    response_model=SuccessResponse[TraceTimelineOut | None],
)
async def get_traceability(
    offer_id: uuid.UUID, tester: ControlledTester, session: SessionDep
):
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
    if payload.occurred_at.astimezone(UTC) > datetime.now(UTC):
        raise HTTPException(422, detail={"code": "TRACE_EVENT_IN_FUTURE"})
    # Serialize appends for this batch so concurrent requests cannot fork the chain.
    await session.execute(
        select(ProduceTraceBatch)
        .where(ProduceTraceBatch.id == batch.id)
        .with_for_update()
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
            "evidence_url": payload.evidence_url,
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
        **payload.model_dump(),
    )
    session.add(row)
    await session.flush()
    return success(await _timeline(session, batch), message="Traceability event recorded")
