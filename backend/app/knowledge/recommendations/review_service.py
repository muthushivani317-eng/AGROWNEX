from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VERIFY = "VERIFY_AGAINST_OFFICIAL_SOURCE"


@dataclass(frozen=True)
class RetrievalRequest:
    crop_id: str
    runtime_label_exact: str
    model_confidence: float
    crop_identity_status: Literal["accepted", "uncertain", "unsupported"]
    plant_quality_status: Literal["accepted", "rejected", "non_plant"]
    language: Literal["ta", "en"]
    crop_match: bool


def blocked(reason_code: str) -> dict:
    return {
        "recommendation_available": False,
        "status": "BLOCKED",
        "reason_code": reason_code,
        "farmer_message_ta": "TAMIL_TRANSLATION_REVIEW_REQUIRED",
        "farmer_message_en": "Recommendation is not available for this result.",
        "verify_against_official_source": True,
        "verification_label": VERIFY,
        "recommendation": None,
    }


class ControlledRecommendationService:
    """Strict review-aware retrieval boundary; it does not infer approvals."""

    def __init__(
        self,
        *,
        registered_labels: dict[str, list[dict]],
        calibrated_thresholds: dict[tuple[str, str], float],
        approved_records: dict[tuple[str, str], dict] | None = None,
    ) -> None:
        self.registered_labels = registered_labels
        self.calibrated_thresholds = calibrated_thresholds
        self.approved_records = approved_records or {}

    def retrieve(self, request: RetrievalRequest) -> dict:
        if request.plant_quality_status != "accepted":
            return blocked("CROP_IDENTITY_UNCERTAIN")
        if request.crop_identity_status != "accepted":
            return blocked("CROP_IDENTITY_UNCERTAIN")
        if not request.crop_match:
            return blocked("CROP_MISMATCH")
        labels = self.registered_labels.get(request.crop_id)
        if labels is None:
            return blocked("RUNTIME_LABEL_NOT_REGISTERED")
        exact = next(
            (
                row for row in labels
                if row["runtime_label_exact"] == request.runtime_label_exact
            ),
            None,
        )
        if exact is None:
            return blocked("RUNTIME_LABEL_NOT_REGISTERED")
        if exact["is_healthy"]:
            return blocked("HEALTHY_NO_TREATMENT_REQUIRED")
        threshold = self.calibrated_thresholds.get(
            (request.crop_id, request.runtime_label_exact)
        )
        if threshold is None:
            return blocked("CALIBRATED_THRESHOLD_MISSING")
        if request.model_confidence < threshold:
            return blocked("LOW_CONFIDENCE")
        record = self.approved_records.get(
            (request.crop_id, request.runtime_label_exact)
        )
        if record is None:
            return blocked("DISEASE_MAPPING_PENDING_REVIEW")
        if record.get("unresolved_conflicts"):
            return blocked("SOURCE_CONFLICT_UNRESOLVED")
        if not record.get("source_references_complete"):
            return blocked("OFFICIAL_SOURCE_CITATION_MISSING")
        if request.language == "ta" and record.get("tamil_review_status") != "HUMAN_APPROVED":
            return blocked("TAMIL_TRANSLATION_NOT_APPROVED")
        return {
            "recommendation_available": True,
            "status": "AVAILABLE",
            "reason_code": "RECOMMENDATION_AVAILABLE",
            "verify_against_official_source": True,
            "verification_label": VERIFY,
            "recommendation": record,
        }
