"""Notification service (docs: Repository → Service → Notification Engine → Provider).

The event center's orchestration layer. It:

* **seeds** the DB rule table + per-user preferences (idempotent),
* **generates** notifications deterministically — pulls events from every module
  via ``NotificationSources``, resolves them through the pure engine, gates them by
  the user's preferences (module + minimum-severity), **deduplicates**, and either
  stores them now or parks future ones in ``future_notification_queue``,
* **promotes** due queued notifications on each sync,
* **delivers** each stored notification through the injectable ``NotificationProvider``
  (in-app now; FCM/OneSignal/SMS/WhatsApp/Email later) and audits every attempt,
* serves reads (list / unread / mark read / dismiss) and preference updates.

Business logic lives here; routes stay thin.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.notifications.constants import (
    DEFAULT_DELIVERY_CHANNELS,
    MODULE_PREFERENCE_FIELDS,
    RULES,
    DeliveryChannel,
    Severity,
    severity_at_least,
)
from app.modules.notifications.engine import (
    CandidateEvent,
    NotificationDraft,
    build_drafts,
    draft_from_candidate,
)
from app.modules.notifications.exceptions import NotificationNotFoundError
from app.modules.notifications.models import (
    DeviceToken,
    FutureNotificationQueue,
    Notification,
    NotificationDeliveryLog,
    NotificationPreferences,
    NotificationTemplate,
)
from app.modules.notifications.provider import (
    DeliveryRequest,
    NotificationProvider,
    get_default_provider,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import NotificationOut, NotificationPreferencesUpdate
from app.modules.notifications.sources import NotificationSources
from app.schemas.response import PaginatedData

logger = get_logger("notifications.service")


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: NotificationProvider | None = None,
        sources: NotificationSources | None = None,
        now: datetime | None = None,
        enable_weather: bool = True,
    ) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.provider = provider or get_default_provider(
            token_lookup=self._lookup_device_tokens
        )
        self._now = now
        self._enable_weather = enable_weather
        self._sources_override = sources

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    async def _lookup_device_tokens(self, user_id: str) -> list[str]:
        """Active FCM tokens for a user id (string) — the FCM provider's lookup."""
        return await self.repo.list_active_tokens(uuid.UUID(user_id))

    def _sources(self, now: datetime) -> NotificationSources:
        return self._sources_override or NotificationSources(
            self.session, now=now, enable_weather=self._enable_weather
        )

    # ----------------------------------------------------------------- #
    # Seeding
    # ----------------------------------------------------------------- #
    async def ensure_templates_seeded(self) -> None:
        """Materialize the rule table into ``notification_templates`` (idempotent).

        Uses a single atomic upsert rather than a per-row check-then-insert --
        this runs on essentially every authenticated read, so two concurrent
        requests hitting an unseeded row at the same time must not be able to
        race each other into an IntegrityError (see
        ``NotificationRepository.upsert_templates``).
        """
        await self.repo.upsert_templates(
            [
                NotificationTemplate(
                    module=module,
                    event_type=event_type,
                    title_key=rule.title_key,
                    message_key=rule.message_key,
                    severity=rule.severity,
                    priority=rule.priority,
                    expires_after_hours=rule.expires_after_hours,
                    action_route=rule.action_route,
                )
                for (module, event_type), rule in RULES.items()
            ]
        )

    async def _get_or_create_preferences(self, user: User) -> NotificationPreferences:
        prefs = await self.repo.get_preferences(user.id)
        if prefs is None:
            prefs = await self.repo.add_preferences(
                NotificationPreferences(user_id=user.id)
            )
        return prefs

    # ----------------------------------------------------------------- #
    # Preference gate
    # ----------------------------------------------------------------- #
    @staticmethod
    def _module_enabled(prefs: NotificationPreferences, module: str) -> bool:
        field = MODULE_PREFERENCE_FIELDS.get(module)
        return bool(getattr(prefs, field, True)) if field else True

    def _passes_preferences(
        self, prefs: NotificationPreferences, draft: NotificationDraft
    ) -> bool:
        if not prefs.in_app_enabled:
            # In-app is currently the only implemented delivery channel (push/
            # sms/whatsapp/email are reserved for future providers -- see
            # _channels_for). A farmer who turns this off should stop
            # receiving notifications altogether, not just miss an audit-log
            # entry -- previously this preference was read in _channels_for
            # but never actually enforced (that method always included
            # "in_app" in the delivery-log channels regardless, and the
            # Notification row itself was created unconditionally), so a
            # farmer who opted out kept getting every notification anyway
            # (2026-08 pre-release audit).
            return False
        if not self._module_enabled(prefs, draft.module):
            return False
        return severity_at_least(draft.severity, prefs.min_severity)

    # ----------------------------------------------------------------- #
    # Generation (the deterministic sync pass)
    # ----------------------------------------------------------------- #
    async def sync(self, user: User) -> int:
        """Generate any new notifications for the user. Returns the number created.

        Deterministic + deduplicated + preference-gated. Safe to call on every read
        (idempotent within a regeneration window).
        """
        now = self._now_dt()
        await self.ensure_templates_seeded()
        prefs = await self._get_or_create_preferences(user)

        created = 0
        created += await self._promote_due_queue(user, prefs, now)

        candidates = await self._sources(now).collect(user)
        for draft in build_drafts(candidates, now=now):
            if not self._passes_preferences(prefs, draft):
                continue
            if draft.scheduled_for is not None and draft.scheduled_for > now:
                await self._enqueue(user, draft)
            elif await self._store(user, draft, now) is not None:
                created += 1
        await self.session.flush()
        return created

    async def emit(self, user: User, candidate: CandidateEvent) -> bool:
        """Persist one explicit event through the normal rules and preference gates."""
        now = self._now_dt()
        await self.ensure_templates_seeded()
        prefs = await self._get_or_create_preferences(user)
        draft = draft_from_candidate(candidate, now=now)
        if draft is None or not self._passes_preferences(prefs, draft):
            return False
        if draft.scheduled_for is not None and draft.scheduled_for > now:
            await self._enqueue(user, draft)
            await self.session.flush()
            return True
        created = await self._store(user, draft, now) is not None
        await self.session.flush()
        return created

    async def _store(
        self, user: User, draft: NotificationDraft, now: datetime
    ) -> Notification | None:
        """Persist a due notification (dedup by key) and deliver it. Idempotent."""
        if await self.repo.get_by_dedup(user.id, draft.dedup_key) is not None:
            return None
        notification = Notification(
            user_id=user.id,
            farm_id=uuid.UUID(draft.farm_id) if draft.farm_id else None,
            module=draft.module,
            event_type=draft.event_type,
            title_key=draft.title_key,
            message_key=draft.message_key,
            payload_json=draft.payload,
            severity=draft.severity,
            priority=draft.priority,
            action_route=draft.action_route,
            dedup_key=draft.dedup_key,
            scheduled_for=draft.scheduled_for,
            expires_at=draft.expires_at,
        )
        await self.repo.add(notification)
        await self._deliver(user, notification, now)
        return notification

    async def _enqueue(self, user: User, draft: NotificationDraft) -> None:
        """Park a future notification in the queue (dedup by key)."""
        if await self.repo.get_queued_by_dedup(user.id, draft.dedup_key) is not None:
            return
        await self.repo.add_queued(
            FutureNotificationQueue(
                user_id=user.id,
                farm_id=uuid.UUID(draft.farm_id) if draft.farm_id else None,
                module=draft.module,
                event_type=draft.event_type,
                title_key=draft.title_key,
                message_key=draft.message_key,
                payload_json=draft.payload,
                severity=draft.severity,
                priority=draft.priority,
                action_route=draft.action_route,
                dedup_key=draft.dedup_key,
                scheduled_for=draft.scheduled_for,
                expires_at=draft.expires_at,
            )
        )

    async def _promote_due_queue(
        self, user: User, prefs: NotificationPreferences, now: datetime
    ) -> int:
        """Move due queued notifications into ``notifications`` (dedup + gated)."""
        promoted = 0
        for queued in await self.repo.list_due_queued(user.id, now=now):
            queued.processed = True
            queued.processed_at = now
            if (
                not prefs.in_app_enabled
                or not self._module_enabled(prefs, queued.module)
                or not severity_at_least(queued.severity, prefs.min_severity)
            ):
                continue
            if await self.repo.get_by_dedup(user.id, queued.dedup_key) is not None:
                continue
            notification = Notification(
                user_id=user.id,
                farm_id=queued.farm_id,
                module=queued.module,
                event_type=queued.event_type,
                title_key=queued.title_key,
                message_key=queued.message_key,
                payload_json=queued.payload_json,
                severity=queued.severity,
                priority=queued.priority,
                action_route=queued.action_route,
                dedup_key=queued.dedup_key,
                expires_at=queued.expires_at,
            )
            await self.repo.add(notification)
            await self._deliver(user, notification, now)
            promoted += 1
        return promoted

    # ----------------------------------------------------------------- #
    # Delivery (provider seam + audit)
    # ----------------------------------------------------------------- #
    def _channels_for(self, prefs: NotificationPreferences) -> tuple[str, ...]:
        # In-app is currently the only implemented delivery channel; push joins
        # only when a real FCM provider is active and the farmer hasn't opted
        # out (mock stays in-app-only, so the audit trail never shows an
        # unconfigured "push" attempt). Notifications are only generated at all
        # when in_app_enabled is True (see _passes_preferences /
        # _promote_due_queue), so in practice this always includes "in_app" --
        # it's still derived from prefs rather than hardcoded, so this stays
        # correct if that gate is ever relaxed.
        channels: list[str] = []
        if prefs.in_app_enabled:
            channels.append(DeliveryChannel.IN_APP.value)
        if getattr(self.provider, "name", "") == "fcm" and prefs.push_enabled:
            channels.append(DeliveryChannel.PUSH.value)
        return tuple(channels)

    async def _deliver(
        self, user: User, notification: Notification, now: datetime
    ) -> None:
        prefs = await self.repo.get_preferences(user.id)
        channels = self._channels_for(prefs) if prefs else DEFAULT_DELIVERY_CHANNELS
        safe = await self.notification_out(user, notification)
        request = DeliveryRequest(
            notification_id=str(notification.id),
            user_id=str(user.id),
            module=safe.module,
            event_type=safe.event_type,
            title_key=safe.title_key,
            message_key=safe.message_key,
            severity=safe.severity,
            priority=safe.priority,
            payload=safe.payload,
            action_route=safe.action_route,
        )
        results = await self.provider.deliver(request, channels=channels)
        delivered = False
        for result in results:
            await self.repo.add_delivery(
                NotificationDeliveryLog(
                    notification_id=notification.id,
                    channel=result.channel,
                    status=result.status,
                    detail=result.detail,
                    sent_at=now,
                    delivered_at=now if result.status == "delivered" else None,
                )
            )
            if result.status == "delivered":
                delivered = True
        if delivered:
            notification.delivered_at = now

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def list_notifications(
        self,
        user: User,
        *,
        module: str | None = None,
        severity: str | None = None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
        sync: bool = True,
    ) -> PaginatedData[Notification]:
        if sync:
            await self.sync(user)
        now = self._now_dt()
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_for_user(
            user.id,
            now=now,
            module=module,
            severity=severity,
            unread_only=unread_only,
            limit=page_size,
            offset=offset,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def notification_out(self, user: User, notification: Notification) -> NotificationOut:
        """Sanitize legacy stored nutrient notifications at the read boundary."""
        restricted = False
        if notification.module == "nutrient" and notification.event_type == "deficiency_detected":
            # A legacy deficiency notification is unsafe until its report proves
            # both ownership and crop provenance. The owned-report repository also
            # excludes soft-deleted rows, so missing, malformed, deleted and
            # cross-user references all fail closed without altering audit storage.
            restricted = True
            raw_id = (notification.payload_json or {}).get("report_id")
            try:
                report_id = uuid.UUID(str(raw_id))
            except (TypeError, ValueError):
                report_id = None
            if report_id is not None:
                from app.modules.nutrient.crops import is_groundnut_nutrient_crop
                from app.modules.nutrient.repository import NutrientRepository

                report = await NutrientRepository(self.session).get_report(report_id, user.id)
                crop = str(report.crop).strip() if report is not None and report.crop else ""
                if crop:
                    restricted = is_groundnut_nutrient_crop(crop)
        return NotificationOut.from_model(
            notification, restrict_groundnut_nutrient=restricted
        )

    async def unread_count(self, user: User, *, sync: bool = True) -> int:
        if sync:
            await self.sync(user)
        return await self.repo.count_unread(user.id, now=self._now_dt())

    # ----------------------------------------------------------------- #
    # Mutations
    # ----------------------------------------------------------------- #
    async def _require(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = await self.repo.get_for_user(notification_id, user.id)
        if notification is None:
            raise NotificationNotFoundError()
        return notification

    async def mark_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = await self._require(user, notification_id)
        if not notification.read:
            notification.read = True
            notification.read_at = self._now_dt()
            await self.session.flush()
        return notification

    async def mark_all_read(self, user: User) -> int:
        updated = await self.repo.mark_all_read(user.id, now=self._now_dt())
        return updated

    async def dismiss(self, user: User, notification_id: uuid.UUID) -> None:
        """Delete = dismiss (docs: notifications are never permanently removed)."""
        notification = await self._require(user, notification_id)
        notification.dismissed = True
        await self.session.flush()

    # ----------------------------------------------------------------- #
    # Preferences
    # ----------------------------------------------------------------- #
    async def get_preferences(self, user: User) -> NotificationPreferences:
        return await self._get_or_create_preferences(user)

    async def update_preferences(
        self, user: User, data: NotificationPreferencesUpdate
    ) -> NotificationPreferences:
        prefs = await self._get_or_create_preferences(user)
        fields = data.model_dump(exclude_unset=True)
        for key, value in fields.items():
            if value is None:
                continue
            setattr(prefs, key, value.value if isinstance(value, Severity) else value)
        await self.session.flush()
        return prefs

    # ----------------------------------------------------------------- #
    # Device tokens (push registration)
    # ----------------------------------------------------------------- #
    async def register_device(
        self, user: User, *, token: str, platform: str
    ) -> DeviceToken:
        """Register (or re-activate) a farmer's push device token for FCM."""
        return await self.repo.upsert_device_token(
            user_id=user.id, token=token, platform=platform
        )

    async def unregister_device(self, user: User, *, token: str) -> bool:
        """Deactivate a device token (e.g. on logout). Returns False if unknown."""
        return await self.repo.deactivate_device_token(user_id=user.id, token=token)
