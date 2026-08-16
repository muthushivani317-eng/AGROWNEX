from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ReportReason(StrEnum):
    UNSAFE_ADVICE = "unsafe_advice"
    SPAM = "spam"
    ABUSE = "abuse"
    PERSONAL_DATA = "personal_data"
    OTHER = "other"


class QuestionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    body: str = Field(min_length=10, max_length=5000)
    crop: str | None = Field(default=None, max_length=80)
    language: str = Field(default="ta", pattern="^(ta|en)$")


class AnswerCreate(BaseModel):
    body: str = Field(min_length=2, max_length=5000)
    language: str = Field(default="ta", pattern="^(ta|en)$")


class ReportCreate(BaseModel):
    target_type: str = Field(pattern="^(question|answer)$")
    target_id: uuid.UUID
    reason: ReportReason


class AnswerOut(BaseModel):
    id: uuid.UUID
    author_alias: str
    body: str
    language: str
    created_at: datetime
    user_generated: bool = True
    expert_verified: bool = False


class QuestionOut(BaseModel):
    id: uuid.UUID
    author_alias: str
    title: str
    body: str
    crop: str | None
    language: str
    answer_count: int
    created_at: datetime
    user_generated: bool = True
    expert_verified: bool = False


class QuestionDetailOut(QuestionOut):
    answers: list[AnswerOut]
    disclaimer: str
    test_mode: bool = True
