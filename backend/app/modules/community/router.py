from __future__ import annotations

import hashlib
import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import ControlledTester
from app.modules.community.models import CommunityAnswer, CommunityQuestion, CommunityReport
from app.modules.community.schemas import (
    AnswerCreate,
    AnswerOut,
    QuestionCreate,
    QuestionDetailOut,
    QuestionOut,
    ReportCreate,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/community-controlled", tags=["community-controlled"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
DISCLAIMER = (
    "Community answers are user-generated and not verified expert or KVK advice. "
    "Do not act on pesticide, treatment, financial, or safety claims without "
    "qualified verification."
)


def alias(user_id: uuid.UUID) -> str:
    return f"Farmer-{hashlib.sha256(str(user_id).encode()).hexdigest()[:6].upper()}"


def question_out(row: CommunityQuestion, count: int) -> QuestionOut:
    return QuestionOut(
        id=row.id,
        author_alias=alias(row.author_user_id),
        title=row.title,
        body=row.body,
        crop=row.crop,
        language=row.language,
        answer_count=count,
        created_at=row.created_at,
    )


def answer_out(row: CommunityAnswer) -> AnswerOut:
    return AnswerOut(
        id=row.id,
        author_alias=alias(row.author_user_id),
        body=row.body,
        language=row.language,
        created_at=row.created_at,
    )


async def visible_question(session: AsyncSession, question_id: uuid.UUID):
    row = await session.get(CommunityQuestion, question_id)
    if row is None or row.is_deleted or row.moderation_status != "active":
        raise HTTPException(404, detail={"code": "COMMUNITY_QUESTION_NOT_FOUND"})
    return row


@router.get("", response_model=SuccessResponse[PaginatedData[QuestionOut]])
async def list_questions(
    _: ControlledTester,
    session: SessionDep,
    crop: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    filters = [
        CommunityQuestion.is_deleted.is_(False),
        CommunityQuestion.moderation_status == "active",
    ]
    if crop:
        filters.append(CommunityQuestion.crop == crop)
    count_query = select(func.count()).select_from(CommunityQuestion).where(*filters)
    total = int((await session.execute(count_query)).scalar_one())
    answer_count = (
        select(func.count(CommunityAnswer.id))
        .where(
            CommunityAnswer.question_id == CommunityQuestion.id,
            CommunityAnswer.is_deleted.is_(False),
            CommunityAnswer.moderation_status == "active",
        )
        .correlate(CommunityQuestion)
        .scalar_subquery()
    )
    result = await session.execute(
        select(CommunityQuestion, answer_count)
        .where(*filters)
        .order_by(CommunityQuestion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return success(
        PaginatedData(
            items=[question_out(row, count) for row, count in result.all()],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size),
        )
    )


@router.post("", response_model=SuccessResponse[QuestionOut], status_code=201)
async def create_question(payload: QuestionCreate, tester: ControlledTester, session: SessionDep):
    row = CommunityQuestion(author_user_id=tester.user.id, **payload.model_dump())
    session.add(row)
    await session.flush()
    return success(question_out(row, 0), message="Community question posted")


@router.get("/{question_id}", response_model=SuccessResponse[QuestionDetailOut])
async def get_question(question_id: uuid.UUID, _: ControlledTester, session: SessionDep):
    row = await visible_question(session, question_id)
    answers = (
        (
            await session.execute(
                select(CommunityAnswer)
                .where(
                    CommunityAnswer.question_id == question_id,
                    CommunityAnswer.is_deleted.is_(False),
                    CommunityAnswer.moderation_status == "active",
                )
                .order_by(CommunityAnswer.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    base = question_out(row, len(answers))
    return success(
        QuestionDetailOut(
            **base.model_dump(), answers=[answer_out(a) for a in answers], disclaimer=DISCLAIMER
        )
    )


@router.post("/{question_id}/answers", response_model=SuccessResponse[AnswerOut], status_code=201)
async def create_answer(
    question_id: uuid.UUID, payload: AnswerCreate, tester: ControlledTester, session: SessionDep
):
    await visible_question(session, question_id)
    row = CommunityAnswer(
        question_id=question_id, author_user_id=tester.user.id, **payload.model_dump()
    )
    session.add(row)
    await session.flush()
    return success(answer_out(row), message="Community answer posted")


@router.post("/reports", response_model=SuccessResponse[None], status_code=201)
async def report_content(payload: ReportCreate, tester: ControlledTester, session: SessionDep):
    model = CommunityQuestion if payload.target_type == "question" else CommunityAnswer
    target = await session.get(model, payload.target_id)
    if target is None or target.is_deleted:
        raise HTTPException(404, detail={"code": "COMMUNITY_CONTENT_NOT_FOUND"})
    session.add(CommunityReport(reporter_user_id=tester.user.id, **payload.model_dump()))
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(409, detail={"code": "COMMUNITY_ALREADY_REPORTED"}) from exc
    target.report_count += 1
    if target.report_count >= 3:
        target.moderation_status = "under_review"
    await session.flush()
    return success(None, message="Content reported for review")
