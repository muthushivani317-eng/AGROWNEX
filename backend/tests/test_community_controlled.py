from __future__ import annotations

import uuid

import pytest
from app.modules.auth.dependencies import TesterContext as ControlledTesterContext
from app.modules.auth.models import User
from app.modules.community.models import CommunityQuestion
from app.modules.community.router import (
    create_answer,
    create_question,
    get_question,
    list_questions,
    report_content,
)
from app.modules.community.schemas import AnswerCreate, QuestionCreate, ReportCreate


async def make_tester(
    db_session, role: str = "pilot_tester"
) -> ControlledTesterContext:
    user = User(firebase_uid=f"community-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    return ControlledTesterContext(user=user, role=role)


@pytest.mark.asyncio
async def test_question_and_answers_are_pseudonymous_and_never_expert_verified(db_session):
    author = await make_tester(db_session)
    responder = await make_tester(db_session, "kvk_reviewer")
    question = (
        await create_question(
            QuestionCreate(
                title="How did this irrigation method work?",
                body="Please share field experience with this irrigation method.",
                crop="paddy",
            ),
            author,
            db_session,
        )
    ).data
    assert question.author_alias.startswith("Farmer-")
    assert question.expert_verified is False

    answer = (
        await create_answer(
            question.id,
            AnswerCreate(body="This is my own field experience, not expert advice."),
            responder,
            db_session,
        )
    ).data
    assert answer.expert_verified is False
    detail = (await get_question(question.id, author, db_session)).data
    assert detail.test_mode is True
    assert len(detail.answers) == 1
    assert "not verified" in detail.disclaimer


@pytest.mark.asyncio
async def test_three_distinct_reports_remove_question_from_active_feed(db_session):
    author = await make_tester(db_session)
    question = (
        await create_question(
            QuestionCreate(
                title="Unverified chemical claim",
                body="This intentionally unsafe-looking claim should be reviewed.",
            ),
            author,
            db_session,
        )
    ).data
    for _ in range(3):
        reporter = await make_tester(db_session)
        await report_content(
            ReportCreate(
                target_type="question",
                target_id=question.id,
                reason="unsafe_advice",
            ),
            reporter,
            db_session,
        )
    row = await db_session.get(CommunityQuestion, question.id)
    assert row.moderation_status == "under_review"
    page = (await list_questions(author, db_session, None, 1, 20)).data
    assert page.items == []
