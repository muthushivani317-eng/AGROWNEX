"""Backend binding of the existing frozen diagnosis decision orchestrator.

The decision ordering and wording mirror the reviewed implementation in the
knowledge/model workspace. This module deliberately contains no agricultural
facts and never turns image confidence alone into a confirmed diagnosis.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.disease.capabilities import normalize_crop_id

from .constants import (
    CLASS_TO_CROP,
    CLASS_TO_INDEX,
    CONFIDENCE_THRESHOLD,
    HEALTHY_CLASSES,
    MARGIN_THRESHOLD,
    MODEL_NAME,
    MODEL_VERSION,
    SUPPORTED_CROPS,
    TEMPERATURE,
)
from .runtime import Prediction

LIMITATION = "This is a provisional dataset evaluation, not official Tamil Nadu field accuracy."
VERIFY_EN = "Verify against official source."
VERIFY_TA = "மேலாண்மை பரிந்துரைகளை அதிகாரப்பூர்வ மூலத்துடன் சரிபார்க்கவும்."


def _wording(decision: str, predicted: str | None) -> tuple[str, str]:
    display = (predicted or "").replace("_", " ")
    values = {
        "LIKELY_DIAGNOSIS": (f"{display} இருக்கலாம்", f"Likely {display}"),
        "HEALTHY_LIKELY": ("பயிர் ஆரோக்கியமாக இருக்கலாம்", "Crop likely healthy"),
        "NEEDS_MORE_INFORMATION": ("கூடுதல் தகவல் தேவை", "More information needed"),
        "ABSTAIN_LOW_CONFIDENCE": ("நம்பகத்தன்மை போதவில்லை", "Confidence is insufficient"),
        "CROP_MISMATCH": (
            "தேர்ந்தெடுத்த பயிருடன் முடிவு பொருந்தவில்லை",
            "Prediction does not match selected crop",
        ),
        "UNSUPPORTED_CROP": ("ஆதரிக்கப்படாத பயிர்", "Unsupported crop"),
        "UNSUPPORTED_CLASS": ("ஆதரிக்கப்படாத வகுப்பு", "Unsupported class"),
        "EXPERT_REVIEW_REQUIRED": ("நிபுணர் ஆய்வு தேவை", "Expert review required"),
        "INVALID_INPUT": ("உள்ளீடு செல்லுபடியாகவில்லை", "Invalid input"),
    }
    return values[decision]


def decide(
    *,
    request_id: str,
    selected_crop: str,
    language: str,
    prediction: Prediction,
    symptoms: list[str],
    growth_stage: str | None,
    knowledge_evidence: list[dict[str, Any]],
    image_reference: str | None,
    image_storage_consent: bool,
) -> dict[str, Any]:
    crop = normalize_crop_id(selected_crop)
    predicted = prediction.predicted_class
    compatible: bool | None = None
    evidence_strength = "NONE"
    reasons: list[str] = []
    if crop not in SUPPORTED_CROPS:
        decision = "UNSUPPORTED_CROP"
        predicted_out = None
        reasons = ["selected_crop_not_supported"]
    elif predicted not in CLASS_TO_INDEX:
        decision = "UNSUPPORTED_CLASS"
        predicted_out = predicted
        reasons = ["predicted_class_not_supported"]
    else:
        predicted_out = predicted
        compatible = CLASS_TO_CROP[predicted] == crop
        if not compatible:
            decision = "CROP_MISMATCH"
            reasons = ["prediction_crosses_selected_crop"]
        elif (
            prediction.confidence < CONFIDENCE_THRESHOLD
            or (prediction.confidence - prediction.second_best_confidence) < MARGIN_THRESHOLD
        ):
            decision = "ABSTAIN_LOW_CONFIDENCE"
            reasons = ["confidence_below_frozen_threshold"]
        else:
            supplied = {item.strip().casefold() for item in symptoms if item.strip()}
            matched: set[str] = set()
            conflicting: set[str] = set()
            verified = 0
            stage_conflict = False
            for item in knowledge_evidence:
                if item.get("supports_class") == predicted:
                    matched.update(
                        str(x).strip().casefold() for x in item.get("matched_symptoms", [])
                    )
                    conflicting.update(
                        str(x).strip().casefold() for x in item.get("conflicting_symptoms", [])
                    )
                    verified += int(item.get("verified") is True)
                    stage_conflict = stage_conflict or bool(
                        growth_stage and item.get("growth_stage_match") is False
                    )
            if (conflicting & supplied) or stage_conflict:
                evidence_strength = "CONFLICTING"
            elif not supplied or not knowledge_evidence:
                evidence_strength = "NONE"
            elif len(matched & supplied) >= 2 and verified:
                evidence_strength = "STRONG"
            elif matched & supplied:
                evidence_strength = "MODERATE"
            else:
                evidence_strength = "WEAK"
            reasons = [f"evidence_strength_{evidence_strength.lower()}"]
            if evidence_strength == "CONFLICTING":
                decision = "EXPERT_REVIEW_REQUIRED"
            elif predicted in HEALTHY_CLASSES:
                decision = "HEALTHY_LIKELY"
            elif evidence_strength in {"MODERATE", "STRONG"}:
                decision = "LIKELY_DIAGNOSIS"
            else:
                decision = "NEEDS_MORE_INFORMATION"
                reasons.append("image_confidence_alone_is_insufficient")

    accepted = decision in {"LIKELY_DIAGNOSIS", "HEALTHY_LIKELY"}
    expert = decision == "EXPERT_REVIEW_REQUIRED"
    tamil, english = _wording(decision, predicted_out)
    audit_id = str(
        uuid.uuid5(uuid.UUID("0f5d2b30-7415-4f87-9f01-9e318a8c2e70"), f"{request_id}:{decision}")
    )
    audit = {
        "audit_record_id": audit_id,
        "request_id": request_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "model_version": MODEL_VERSION,
        "selected_crop": crop,
        "top1_class": predicted_out,
        "top1_confidence": prediction.confidence,
        "top2_confidence": prediction.second_best_confidence,
        "margin": prediction.confidence - prediction.second_best_confidence,
        "frozen_temperature": TEMPERATURE,
        "frozen_confidence_threshold": CONFIDENCE_THRESHOLD,
        "frozen_margin_threshold": MARGIN_THRESHOLD,
        "crop_compatible": compatible,
        "evidence_strength": evidence_strength,
        "accepted": accepted,
        "abstained": not accepted,
        "expert_review_required": expert,
        "decision_type": decision,
        "decision_reasons": reasons,
        "image_reference": image_reference if image_storage_consent else None,
        "image_storage_consent": image_storage_consent,
        "official_accuracy_claim": False,
    }
    follow_up = decision in {"NEEDS_MORE_INFORMATION", "EXPERT_REVIEW_REQUIRED"}
    return {
        "request_id": request_id,
        "decision_type": decision,
        "selected_crop": crop,
        "predicted_class": predicted_out,
        "calibrated_confidence": prediction.confidence,
        "second_best_confidence": prediction.second_best_confidence,
        "confidence_margin": prediction.confidence - prediction.second_best_confidence,
        "top3": prediction.top3,
        "accepted": accepted,
        "abstained": not accepted,
        "likely_result_tamil": tamil,
        "likely_result_english": english,
        "explanation_tamil": "இது உறுதிப்படுத்தப்பட்ட நோயறிதல் அல்ல.",
        "explanation_english": "This is not a confirmed diagnosis.",
        "follow_up_questions_tamil": ["அறிகுறி பயிரின் எந்தப் பகுதியில் தெரிகிறது?"]
        if follow_up
        else [],
        "follow_up_questions_english": ["On which part of the crop is the symptom visible?"]
        if follow_up
        else [],
        "expert_review_required": expert,
        "evidence_strength": evidence_strength,
        "decision_reasons": reasons,
        "warnings": [LIMITATION, "Image classification alone is not confirmation."],
        "management_note": {"ta": VERIFY_TA, "en": VERIFY_EN},
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "temperature": TEMPERATURE,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "margin_threshold": MARGIN_THRESHOLD,
        "official_accuracy_claim": False,
        "image_storage_allowed": bool(image_storage_consent and image_reference),
        "audit_record_id": audit_id,
        "audit_record": audit,
    }
