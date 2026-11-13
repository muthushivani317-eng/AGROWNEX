"""KVK-supervised review and human-readable Redgram dataset export."""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.schemas import GroundnutPestObservationReviewOut
from app.modules.auth.repositories import UserRepository
from app.modules.notifications.constants import NotificationModule
from app.modules.notifications.engine import CandidateEvent
from app.modules.notifications.service import NotificationService

REDGRAM_REVIEW_LABELS = frozenset(
    {"redgram__healthy", "redgram__leaf_spot", "redgram__sterility_mosaic"}
)

GROUNDNUT_DAMAGE_EXTENTS = frozenset({"few", "several", "widespread"})
GROUNDNUT_SPREAD_SPEEDS = frozenset({"unknown", "stable", "rapid"})
GROUNDNUT_REVIEW_FEEDBACK = frozenset(
    {
        "monitor_field_conditions",
        "submit_clearer_photo",
        "seek_in_person_field_assessment",
        "no_actionable_conclusion_from_photo",
    }
)


def groundnut_pest_observation_for_review(record) -> GroundnutPestObservationReviewOut:  # noqa: ANN001
    raw = record.raw_response if isinstance(record.raw_response, dict) else {}
    reported = raw.get("farmer_reported")
    if raw.get("record_type") != "farmer_pest_damage_observation" or not isinstance(
        reported, dict
    ):
        raise LookupError("GROUNDNUT_PEST_OBSERVATION_NOT_FOUND")
    extent = reported.get("damage_extent")
    spread = reported.get("spread_speed")
    if extent not in GROUNDNUT_DAMAGE_EXTENTS or spread not in GROUNDNUT_SPREAD_SPEEDS:
        raise LookupError("GROUNDNUT_PEST_OBSERVATION_NOT_FOUND")
    return GroundnutPestObservationReviewOut(
        observation_id=record.id,
        damage_extent=extent,
        spread_speed=spread,
        private_photo_available=bool(record.image_key),
        submitted_at=record.created_at,
    )


async def list_pending_groundnut_pest_observations(
    session: AsyncSession, *, limit: int, offset: int
) -> list[GroundnutPestObservationReviewOut]:
    records = await DiseaseReportRepository(session).list_pending_groundnut_pest_observations(
        limit=limit, offset=offset
    )
    return [groundnut_pest_observation_for_review(record) for record in records]


async def get_pending_groundnut_pest_observation(session: AsyncSession, report_id: uuid.UUID):  # noqa: ANN201
    record = await DiseaseReportRepository(session).get_pending_groundnut_pest_observation(
        report_id
    )
    if record is None:
        raise LookupError("GROUNDNUT_PEST_OBSERVATION_NOT_FOUND")
    # Validate the stored evidence envelope before exposing it to a reviewer.
    groundnut_pest_observation_for_review(record)
    return record


async def complete_groundnut_pest_observation(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    feedback: str,
):
    if feedback not in GROUNDNUT_REVIEW_FEEDBACK:
        raise ValueError("INVALID_GROUNDNUT_PEST_REVIEW_FEEDBACK")
    report = await DiseaseReportRepository(
        session
    ).get_groundnut_pest_observation_for_completion(report_id)
    if report is None:
        raise LookupError("GROUNDNUT_PEST_OBSERVATION_NOT_FOUND")
    if report.review_status != "pending":
        raise RuntimeError("GROUNDNUT_PEST_OBSERVATION_ALREADY_COMPLETED")
    # Fail closed if the stored envelope is malformed; never turn it into a label.
    groundnut_pest_observation_for_review(report)
    raw = dict(report.raw_response or {})
    raw["review"] = {
        "feedback": feedback,
        "diagnostic": False,
    }
    report.raw_response = raw
    report.review_status = "reviewed"
    report.reviewer_role = "kvk_officer"
    report.review_timestamp = datetime.now(UTC)
    report.needs_expert_review = False
    report.corrected_label = None

    farmer = await UserRepository(session).get(report.user_id)
    if farmer is None:
        raise LookupError("GROUNDNUT_PEST_OBSERVATION_OWNER_NOT_FOUND")
    await NotificationService(session).emit(
        farmer,
        CandidateEvent(
            module=NotificationModule.DISEASE.value,
            event_type="groundnut_pest_review_completed",
            dedup_key=f"disease:groundnut_pest_review_completed:{report.id}",
            payload={
                "observation_id": str(report.id),
                "feedback": feedback,
            },
        ),
    )
    await session.flush()
    await session.refresh(report)
    return report


async def review_redgram_report(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    correct: bool,
    corrected_label: str | None,
):
    report = await DiseaseReportRepository(session).get_kvk_review_record(report_id)
    if report is None:
        raise LookupError("REVIEW_RECORD_NOT_FOUND")
    if report.review_status not in {"pending", "confirmed", "corrected"}:
        raise ValueError("REVIEW_RECORD_NOT_PENDING")
    if correct:
        corrected_label = None
        report.review_status = "confirmed"
    else:
        if corrected_label not in REDGRAM_REVIEW_LABELS:
            raise ValueError("INVALID_REDGRAM_REVIEW_LABEL")
        report.review_status = "corrected"
    report.corrected_label = corrected_label
    report.reviewer_role = "kvk_officer"
    report.review_timestamp = datetime.now(UTC)
    await session.flush()
    await session.refresh(report)
    return report


async def export_reviewed_redgram(session: AsyncSession) -> dict:
    records = await DiseaseReportRepository(session).list_consented_reviewed_redgram()
    statuses = Counter(record.review_status for record in records)
    classes = Counter((record.corrected_label or record.disease or "unknown") for record in records)
    return {
        "summary": {
            "reviewed_records": len(records),
            "confirmed": statuses["confirmed"],
            "corrected": statuses["corrected"],
            "class_breakdown": dict(sorted(classes.items())),
        },
        "records": [
            {
                "report_id": str(record.id),
                "photo_reference": record.image_url,
                "original_diagnosis": record.disease,
                "confidence": record.confidence,
                "corrected_label": record.corrected_label,
                "review_status": record.review_status,
                "review_timestamp": (
                    record.review_timestamp.isoformat() if record.review_timestamp else None
                ),
                "model_used": record.model_used,
            }
            for record in records
        ],
    }
