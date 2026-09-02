from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["app_issue", "market", "disease", "farm", "account", "other"]
TicketPriority = Literal["normal", "high", "urgent"]
TicketStatus = Literal["open", "in_progress", "waiting_for_farmer", "resolved", "closed"]


class TicketCreateIn(BaseModel):
    category: TicketCategory
    subject: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=10, max_length=4000)
    priority: TicketPriority = "normal"
    app_version: str | None = Field(None, max_length=40)
    device_context: str | None = Field(None, max_length=160)


class TicketMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class TicketAdminUpdateIn(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    response: str | None = Field(None, min_length=1, max_length=4000)


class TicketMessageOut(BaseModel):
    id: uuid.UUID
    author_type: str
    message: str
    created_at: datetime


class TicketOut(BaseModel):
    id: uuid.UUID
    farmer_ref: str | None = None
    category: str
    subject: str
    description: str
    priority: str
    status: str
    app_version: str | None
    device_context: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[TicketMessageOut] = Field(default_factory=list)
