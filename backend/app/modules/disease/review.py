"""KVK-supervised review and human-readable Redgram dataset export."""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.disease.repositories import DiseaseReportRepository

REDGRAM_REVIEW_LABELS = frozenset(
    {"redgram__healthy", "redgram__leaf_spot", "redgram__sterility_mosaic"}
)


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
