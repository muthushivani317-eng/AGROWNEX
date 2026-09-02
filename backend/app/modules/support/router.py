from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.modules.admin.constants import AdminPermission
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.exceptions import PermissionDeniedError
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.schemas.response import PaginatedData, SuccessResponse, success

from .models import SupportTicket, SupportTicketMessage
from .schemas import (
    TicketAdminUpdateIn,
    TicketCreateIn,
    TicketMessageIn,
    TicketMessageOut,
    TicketOut,
)

router = APIRouter(prefix="/support/tickets", tags=["support"])
admin_router = APIRouter(prefix="/admin/support-tickets", tags=["admin-support"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _out(ticket: SupportTicket, farmer_ref: str | None = None) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        farmer_ref=farmer_ref,
        category=ticket.category,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        app_version=ticket.app_version,
        device_context=ticket.device_context,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=[
            TicketMessageOut(
                id=m.id, author_type=m.author_type, message=m.message, created_at=m.created_at
            )
            for m in ticket.messages
        ],
    )


async def _owned(session: AsyncSession, ticket_id: uuid.UUID, user_id: uuid.UUID) -> SupportTicket:
    row = (
        await session.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .where(SupportTicket.id == ticket_id, SupportTicket.user_id == user_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "SUPPORT_TICKET_NOT_FOUND"})
    return row


@router.post("", response_model=SuccessResponse[TicketOut], status_code=201)
async def create_ticket(payload: TicketCreateIn, user: CurrentUser, session: SessionDep):
    ticket = SupportTicket(user_id=user.id, **payload.model_dump())
    session.add(ticket)
    await session.flush()
    session.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            author_type="farmer",
            author_user_id=user.id,
            message=payload.description,
        )
    )
    await session.commit()
    return success(_out(await _owned(session, ticket.id, user.id)), "Support ticket created")


@router.get("", response_model=SuccessResponse[list[TicketOut]])
async def list_tickets(user: CurrentUser, session: SessionDep):
    rows = (
        (
            await session.execute(
                select(SupportTicket)
                .options(selectinload(SupportTicket.messages))
                .where(SupportTicket.user_id == user.id)
                .order_by(SupportTicket.updated_at.desc())
            )
        )
        .scalars()
        .unique()
        .all()
    )
    return success([_out(row) for row in rows])


@router.get("/{ticket_id}", response_model=SuccessResponse[TicketOut])
async def get_ticket(ticket_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    return success(_out(await _owned(session, ticket_id, user.id)))


@router.post("/{ticket_id}/messages", response_model=SuccessResponse[TicketOut])
async def add_farmer_message(
    ticket_id: uuid.UUID, payload: TicketMessageIn, user: CurrentUser, session: SessionDep
):
    ticket = await _owned(session, ticket_id, user.id)
    if ticket.status == "closed":
        raise HTTPException(status_code=409, detail={"code": "SUPPORT_TICKET_CLOSED"})
    session.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            author_type="farmer",
            author_user_id=user.id,
            message=payload.message,
        )
    )
    if ticket.status in {"resolved", "waiting_for_farmer"}:
        ticket.status = "open"
    await session.commit()
    return success(_out(await _owned(session, ticket.id, user.id)), "Reply added")


def _require_support(ctx: AdminContextDep) -> None:
    if AdminPermission.MANAGE_SUPPORT.value not in ctx.permissions:
        raise PermissionDeniedError()


@admin_router.get("", response_model=SuccessResponse[PaginatedData[TicketOut]])
async def admin_list_tickets(
    ctx: AdminContextDep,
    session: SessionDep,
    status: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    _require_support(ctx)
    query = select(SupportTicket, User.farmer_ref).join(User, User.id == SupportTicket.user_id)
    count_query = select(func.count()).select_from(SupportTicket)
    if status:
        query, count_query = query.where(SupportTicket.status == status), count_query.where(
            SupportTicket.status == status
        )
    if category:
        query, count_query = query.where(SupportTicket.category == category), count_query.where(
            SupportTicket.category == category
        )
    total = int((await session.execute(count_query)).scalar_one())
    pairs = (
        (
            await session.execute(
                query.options(selectinload(SupportTicket.messages))
                .order_by(SupportTicket.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )
    data = PaginatedData(
        items=[_out(ticket, ref) for ticket, ref in pairs],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
    )
    return success(data)


@admin_router.patch("/{ticket_id}", response_model=SuccessResponse[TicketOut])
async def admin_update_ticket(
    ticket_id: uuid.UUID, payload: TicketAdminUpdateIn, ctx: AdminContextDep, session: SessionDep
):
    _require_support(ctx)
    ticket = (
        await session.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .where(SupportTicket.id == ticket_id)
        )
    ).scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail={"code": "SUPPORT_TICKET_NOT_FOUND"})
    if payload.status is not None:
        ticket.status = payload.status
    if payload.priority is not None:
        ticket.priority = payload.priority
    if payload.response:
        session.add(
            SupportTicketMessage(
                ticket_id=ticket.id,
                author_type="admin",
                author_admin_id=ctx.admin.id,
                message=payload.response,
            )
        )
        if payload.status is None:
            ticket.status = "waiting_for_farmer"
    await session.commit()
    ticket = (
        await session.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .where(SupportTicket.id == ticket_id)
        )
    ).scalar_one()
    return success(_out(ticket), "Support ticket updated")
