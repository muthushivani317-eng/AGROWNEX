"""Notification request/response schemas (docs/API_CONTRACT.md → NOTIFICATIONS).

Titles/messages travel as localization *keys* + a payload so the Tamil-first
client renders them (docs/PRODUCT_RULES.md → Tamil default). English text is not
sent — the client owns presentation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.notifications.constants import Severity
from app.modules.notifications.models import (
    DeviceToken,
    Notification,
    NotificationPreferences,
)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class NotificationOut(BaseModel):
    id: uuid.UUID
    module: str
    event_type: str
    farm_id: uuid.UUID | None
    title_key: str
    message_key: str
    payload: dict
    severity: str
    priority: str
    action_route: str | None
    read: bool
    created_at: datetime
    scheduled_for: datetime | None
    expires_at: datetime | None

    @classmethod
    def from_model(
        cls, n: Notification, *, restrict_groundnut_nutrient: bool = False
    ) -> NotificationOut:
        payload = n.payload_json or {}
        event_type = n.event_type
        title_key = n.title_key
        message_key = n.message_key
        if restrict_groundnut_nutrient:
            event_type = "test_recommended"
            title_key = "notifications.nutrient.test_recommended.title"
            message_key = "notifications.nutrient.test_recommended.message"
            payload = {
                key: value
                for key, value in payload.items()
                if key in {"report_id", "farm_id"}
            }
        return cls(
            id=n.id,
            module=n.module,
            event_type=event_type,
            farm_id=n.farm_id,
            title_key=title_key,
            message_key=message_key,
            payload=payload,
            severity=n.severity,
            priority=n.priority,
            action_route=n.action_route,
            read=n.read,
            created_at=n.created_at,
            scheduled_for=n.scheduled_for,
            expires_at=n.expires_at,
        )


class UnreadCountOut(BaseModel):
    unread: int


class DeviceTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    is_active: bool

    @classmethod
    def from_model(cls, d: DeviceToken) -> DeviceTokenOut:
        return cls.model_validate(d)


class MarkReadResultOut(BaseModel):
    updated: int


class NotificationPreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weather_enabled: bool
    disease_enabled: bool
    calendar_enabled: bool
    growth_enabled: bool
    market_enabled: bool
    scheme_enabled: bool
    produce_enabled: bool
    ai_enabled: bool
    system_enabled: bool
    in_app_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool
    email_enabled: bool
    voice_enabled: bool
    min_severity: str
    language: str

    @classmethod
    def from_model(cls, p: NotificationPreferences) -> NotificationPreferencesOut:
        return cls.model_validate(p)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class DeviceTokenRegister(BaseModel):
    """Register a push device token (docs/API_CONTRACT.md → NOTIFICATIONS)."""

    token: str = Field(min_length=8, max_length=255)
    platform: Literal["ios", "android"]


class NotificationPreferencesUpdate(BaseModel):
    """Partial update — only provided fields change."""

    weather_enabled: bool | None = None
    disease_enabled: bool | None = None
    calendar_enabled: bool | None = None
    growth_enabled: bool | None = None
    market_enabled: bool | None = None
    scheme_enabled: bool | None = None
    produce_enabled: bool | None = None
    ai_enabled: bool | None = None
    system_enabled: bool | None = None
    in_app_enabled: bool | None = None
    push_enabled: bool | None = None
    sms_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    email_enabled: bool | None = None
    voice_enabled: bool | None = None
    min_severity: Severity | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)
