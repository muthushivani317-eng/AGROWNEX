"""Notification Engine (docs: Repository → Service → Notification Engine → Provider).

The deterministic core of the event center. Given ``CandidateEvent``s produced by
the pure per-source collectors, it looks up each event's rule in ``constants.RULES``
and materializes a ``NotificationDraft`` (localization keys, severity, priority,
resolved action route, expiry). No AI, no I/O, no side effects — every notification
is explainable and reproducible. The service does the I/O (fetching source data and
persisting); this module only *decides*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.modules.notifications.constants import get_rule


@dataclass(frozen=True)
class CandidateEvent:
    """A source-agnostic event emitted by a collector, before rule resolution."""

    module: str
    event_type: str
    dedup_key: str
    payload: dict = field(default_factory=dict)
    farm_id: str | None = None
    scheduled_for: datetime | None = None  # future events go to the queue


@dataclass(frozen=True)
class NotificationDraft:
    """A fully-resolved notification ready to persist (still storage-agnostic)."""

    module: str
    event_type: str
    dedup_key: str
    title_key: str
    message_key: str
    severity: str
    priority: str
    payload: dict
    farm_id: str | None
    action_route: str | None
    scheduled_for: datetime | None
    expires_at: datetime | None


def _resolve_route(template: str | None, payload: dict) -> str | None:
    """Fill ``{placeholder}`` slots in an action route from the payload.

    A missing placeholder is left as-is rather than raising — the route stays a
    best-effort deep link and never breaks notification generation.
    """
    if not template:
        return None
    try:
        return template.format(**payload)
    except (KeyError, IndexError):
        return template


def draft_from_candidate(
    candidate: CandidateEvent, *, now: datetime
) -> NotificationDraft | None:
    """Resolve one candidate against the rule table. ``None`` if no rule matches."""
    rule = get_rule(candidate.module, candidate.event_type)
    if rule is None:
        return None

    expires_at = (
        now + timedelta(hours=rule.expires_after_hours)
        if rule.expires_after_hours is not None
        else None
    )
    return NotificationDraft(
        module=rule.module,
        event_type=rule.event_type,
        dedup_key=candidate.dedup_key,
        title_key=rule.title_key,
        message_key=rule.message_key,
        severity=rule.severity,
        priority=rule.priority,
        payload=dict(candidate.payload),
        farm_id=candidate.farm_id,
        action_route=_resolve_route(rule.action_route, candidate.payload),
        scheduled_for=candidate.scheduled_for,
        expires_at=expires_at,
    )


def build_drafts(
    candidates: list[CandidateEvent], *, now: datetime | None = None
) -> list[NotificationDraft]:
    """Resolve many candidates, dropping any without a rule (pure)."""
    reference = now or datetime.now(UTC)
    drafts = [draft_from_candidate(c, now=reference) for c in candidates]
    return [d for d in drafts if d is not None]
