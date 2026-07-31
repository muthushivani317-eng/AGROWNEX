from __future__ import annotations

from datetime import UTC, datetime

from .schemas import RecommendationContext, RecommendationRecord, RecommendationResponse


class RecommendationService:
    """Fail-closed retrieval downstream of crop/disease safety gates."""

    def __init__(self, records: list[RecommendationRecord] | None = None) -> None:
        self._records = {
            (record.crop_id, record.model_label): record
            for record in (records or [])
            if record.active
        }

    def resolve(self, context: RecommendationContext) -> RecommendationResponse:
        reason = self._blocked_reason(context)
        record = None if reason else self._records.get((context.crop_id, context.model_label))
        if reason is None and record is None:
            reason = "RECOMMENDATION_BLOCKED_NO_SOURCE"
        return RecommendationResponse(
            available=record is not None,
            reason_code=reason or "RECOMMENDATION_AVAILABLE",
            crop_id=context.crop_id,
            model_label=context.model_label,
            record=record,
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    def _blocked_reason(context: RecommendationContext) -> str | None:
        if not context.runtime_integrity_passed:
            return "RECOMMENDATION_BLOCKED_INTEGRITY_FAILURE"
        if context.healthy_result:
            return "HEALTHY_RESULT_NO_TREATMENT_REQUIRED"
        if context.crop_identity_abstained or not context.crop_identity_matched:
            return "RECOMMENDATION_BLOCKED_CROP_UNCERTAIN"
        if context.disease_abstained or not context.confidence_passed or not context.model_label:
            return "RECOMMENDATION_BLOCKED_DISEASE_UNCERTAIN"
        return None
