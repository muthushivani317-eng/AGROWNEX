"""SQLAlchemy 2.0 async models for the Today's Farm Task advisory layer.

Follows the real app conventions in `app/shared/base_model.py`: the portable
`GUID()` type (native UUID on Postgres, CHAR(32) hex on SQLite for tests) and
the `UUIDMixin`/`TimestampMixin`/`SoftDeleteMixin` composition already used by
every other module (see `app/modules/farms/models.py`, `app/modules/satellite/
models.py`). Zone geometry is stored as a JSON GeoJSON dict (matching
`FarmBoundary.geojson`), not a PostGIS `Geometry` column -- the satellite
module itself has no PostGIS geometry columns either (see `aoi.py`), so this
avoids introducing a dependency the rest of the app doesn't use for AOIs.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class DailySignal(UUIDMixin, TimestampMixin, Base):
    """Layer 2 -- the unified, normalized evidence-signal object. One row per
    candidate a signal provider raised, whether or not it ever becomes a
    farmer-facing task. `status` is the only field mutated after creation
    (candidate -> ranked_shown / suppressed_* / expired_stale), so every
    ranking decision is explainable from this table plus
    `DailyTaskAuditLog`.
    """

    __tablename__ = "daily_signals"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )

    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_module: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False)

    # Plain-language-safe facts vs. the raw technical payload -- kept as
    # separate JSON columns so the farmer-facing serializer never has a
    # field capable of leaking a raw index value (see schemas.py).
    evidence_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_technical: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    policy_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommended_task_type: Mapped[str] = mapped_column(String(64), nullable=False)

    dedupe_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)

    # 64, not 32: `status` can be set to a ranking-engine decision string
    # (service.py -> update_signal_status), and some of those --
    # "suppressed_policy_blocked_definitive_flood_claim" is the longest at 48
    # chars -- exceed 32 (see daily_task_audit_log.decision below for the
    # same reason).
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="candidate", index=True)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rank_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    task: Mapped[DailyTask | None] = relationship(back_populates="signal", uselist=False)

    __table_args__ = (
        UniqueConstraint("dedupe_key", "observed_at", name="uq_daily_signal_dedupe_observed"),
        Index("ix_daily_signal_farm_status", "farm_id", "status"),
    )


class DailyTask(UUIDMixin, TimestampMixin, Base):
    """Layer 4 -- the farmer-facing task card. One task per DailySignal shown
    (1:1); a merged-away signal is recorded in `merged_signal_ids`, never as
    a second task.
    """

    __tablename__ = "daily_tasks"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("daily_signals.id"), nullable=False, unique=True
    )
    merged_signal_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = primary, 2 = secondary

    # Rendered at creation time and persisted (not re-rendered on read) so a
    # card's copy never changes under a farmer mid-day, and history shows
    # exactly what was shown even after a later copy-deck change.
    title_ta: Mapped[str] = mapped_column(String(120), nullable=False)
    task_text_ta: Mapped[str] = mapped_column(String(280), nullable=False)
    reason_text_ta: Mapped[str] = mapped_column(String(280), nullable=False)
    why_am_i_seeing_this_ta: Mapped[str] = mapped_column(String(400), nullable=False)
    field_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    verification_followup_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    signal: Mapped[DailySignal] = relationship(back_populates="task")
    responses: Mapped[list[DailyTaskResponse]] = relationship(
        back_populates="task", order_by="DailyTaskResponse.created_at"
    )

    __table_args__ = (
        Index("ix_daily_task_user_status_created", "user_id", "status", "created_at"),
    )


class DailyTaskResponse(UUIDMixin, TimestampMixin, Base):
    """Every farmer state transition is appended here, never overwritten on
    DailyTask -- a full audit trail (e.g. "problem found" then a photo added
    later are two rows, not one overwrite).
    """

    __tablename__ = "daily_task_responses"

    task_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("daily_tasks.id"), nullable=False, index=True
    )
    response_type: Mapped[str] = mapped_column(String(32), nullable=False)
    structured_followup: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    photo_object_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    voice_note_object_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    note_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[DailyTask] = relationship(back_populates="responses")


class DailyTaskZone(UUIDMixin, TimestampMixin, Base):
    """Persisted zone candidates for the Uneven-Growth task type. A zone must
    be re-confirmed across >= ZONE_MIN_CONSECUTIVE_SCANS refresh cycles
    before it can ever produce a signal (see zonal_analysis.py) -- this is
    what makes that requirement possible, since a zone recomputed fresh each
    time would never accumulate a confirmation count.

    `source_zone_id` is the satellite module's own `spatial_variability_zones[
    ].zone_id` (see `app/modules/satellite/provider.py::_fetch_spatial_zones`)
    -- this table tracks confirmation state for an existing satellite-module
    zone, it does not compute a new one (see zonal_analysis.py docstring).
    """

    __tablename__ = "daily_task_zones"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), nullable=False, index=True
    )
    source_zone_id: Mapped[str] = mapped_column(String(64), nullable=False)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    area_fraction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cardinal_label: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="inspect_first")
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consecutive_confirming_scans: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="watching")  # watching | confirmed | resolved

    __table_args__ = (
        UniqueConstraint("farm_id", "source_zone_id", name="uq_daily_task_zone_farm_source"),
    )


class EvidencePack(UUIDMixin, TimestampMixin, Base):
    """Layer 5 output record. The PDF (when generated) lives in object
    storage (see evidence_pack.py); this row is the durable, queryable
    metadata plus a re-openable pointer to it.
    """

    __tablename__ = "evidence_packs"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    triggering_signal_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("daily_signals.id"), nullable=True
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_date_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_date_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    confidence_level: Mapped[str] = mapped_column(String(16), nullable=False)
    has_pre_event_imagery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_post_event_imagery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    imagery_degraded_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    pdf_object_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_post_event_data")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    shared_with: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class DailyTaskAuditLog(UUIDMixin, TimestampMixin, Base):
    """Append-only explainability log: one row per candidate signal per
    ranking run, recording exactly why it was shown or suppressed. Queryable
    (unlike rolling application logs), satisfying the "every ranking
    decision must be explainable" requirement directly from the database.
    """

    __tablename__ = "daily_task_audit_log"

    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    # 64, not 32: ranking_engine._suppressed() writes f"suppressed_{reason}",
    # and several `reason` values push the result past 32 chars -- longest
    # observed is "suppressed_policy_blocked_definitive_flood_claim" (48) and
    # "suppressed_merged_into_sowing_germination_check" (47). Found via a
    # real-Postgres run (StringDataRightTruncationError); SQLite's test
    # fixture doesn't enforce VARCHAR length so this was previously silent.
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
