"""Notification API routes (docs/API_CONTRACT.md → NOTIFICATIONS).

    GET    /notifications                (list; filter by module/severity/unread)
    GET    /notifications/unread         (unread badge count)
    PUT    /notifications/{id}/read      (mark one read)
    PUT    /notifications/read-all       (mark all read)
    DELETE /notifications/{id}           (dismiss — never hard-deleted)
    GET    /notifications/preferences    (get preferences)
    PUT    /notifications/preferences    (update preferences)
    POST   /notifications/devices        (register a push/FCM device token)
    DELETE /notifications/devices        (deactivate a push token)

Thin routes — generation, dedup, delivery, the queue and preference gating all
live in ``NotificationService``. Static routes precede ``/{notification_id}``. All
endpoints are authenticated.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.modules.notifications.constants import (
    NotificationModule,
    Severity,
)
from app.modules.notifications.dependencies import CurrentUser, NotificationServiceDep
from app.modules.notifications.schemas import (
    DeviceTokenOut,
    DeviceTokenRegister,
    MarkReadResultOut,
    NotificationOut,
    NotificationPreferencesOut,
    NotificationPreferencesUpdate,
    UnreadCountOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _page_out(page, service, user) -> PaginatedData[NotificationOut]:
    return PaginatedData(
        items=[await service.notification_out(user, n) for n in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        total_pages=page.total_pages,
    )


@router.get("", response_model=SuccessResponse[PaginatedData[NotificationOut]])
async def list_notifications(
    current_user: CurrentUser,
    service: NotificationServiceDep,
    module: NotificationModule | None = Query(None),
    severity: Severity | None = Query(None),
    unread: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List the farmer's notifications (generates any new ones first)."""
    page_data = await service.list_notifications(
        current_user,
        module=module.value if module else None,
        severity=severity.value if severity else None,
        unread_only=unread,
        page=page,
        page_size=page_size,
    )
    return success(await _page_out(page_data, service, current_user))


@router.get("/unread", response_model=SuccessResponse[UnreadCountOut])
async def unread_count(
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Unread notification count for the badge (generates any new ones first)."""
    count = await service.unread_count(current_user)
    return success(UnreadCountOut(unread=count))


@router.get("/preferences", response_model=SuccessResponse[NotificationPreferencesOut])
async def get_preferences(
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Get the farmer's notification preferences (created with defaults if absent)."""
    prefs = await service.get_preferences(current_user)
    return success(NotificationPreferencesOut.from_model(prefs))


@router.put("/preferences", response_model=SuccessResponse[NotificationPreferencesOut])
async def update_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Partially update the farmer's notification preferences."""
    prefs = await service.update_preferences(current_user, payload)
    return success(
        NotificationPreferencesOut.from_model(prefs),
        message="Preferences updated",
    )


@router.post(
    "/devices",
    response_model=SuccessResponse[DeviceTokenOut],
    status_code=201,
)
async def register_device(
    payload: DeviceTokenRegister,
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Register this device's push token so the farmer receives FCM notifications."""
    device = await service.register_device(
        current_user, token=payload.token, platform=payload.platform
    )
    return success(DeviceTokenOut.from_model(device), message="Device registered")


@router.delete("/devices", response_model=SuccessResponse[None])
async def unregister_device(
    payload: DeviceTokenRegister,
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Deactivate a push token (e.g. on logout); idempotent."""
    await service.unregister_device(current_user, token=payload.token)
    return success(None, message="Device unregistered")


@router.put("/read-all", response_model=SuccessResponse[MarkReadResultOut])
async def mark_all_read(
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Mark every visible notification as read."""
    updated = await service.mark_all_read(current_user)
    return success(MarkReadResultOut(updated=updated), message="All marked read")


@router.put("/{notification_id}/read", response_model=SuccessResponse[NotificationOut])
async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Mark a single notification as read."""
    notification = await service.mark_read(current_user, notification_id)
    return success(
        await service.notification_out(current_user, notification),
        message="Marked read",
    )


@router.delete("/{notification_id}", response_model=SuccessResponse[None])
async def dismiss_notification(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    service: NotificationServiceDep,
):
    """Dismiss a notification (soft — notifications are never permanently deleted)."""
    await service.dismiss(current_user, notification_id)
    return success(None, message="Notification dismissed")
