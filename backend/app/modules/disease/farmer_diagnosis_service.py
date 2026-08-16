"""Farmer-facing disease diagnosis orchestration (docs/API_CONTRACT.md -> DISEASE).

Unlike the controlled-testing routes (``app.banana_v3``, ``app.restricted_crops``,
``app.legacy_joint`` -- internal/pilot testers and KVK reviewers only), this is
the general-release path: any authenticated farmer may call it. A
purpose-trained local classifier is consulted as a supporting signal when one
exists -- banana (``app.banana_v3``), chilli/redgram (``app.restricted_crops``),
and paddy/cotton/groundnut (``app.legacy_joint``, the frozen nine-class
crop-constrained ONNX model) -- but the OpenAI vision model is always the
primary source of the disease name, explanation, and care guidance shown to
the farmer, because the local models are public-dataset provisional models
that are explicitly not validated on real farmer photos (see their
README/ARTIFACT_CONTRACT under ``model_artifacts/``).
Confidence shown to the farmer always reflects that honestly, rather than
inheriting the local model's own (unvalidated) fail-closed threshold.

For paddy/cotton/groundnut specifically: the general-release runtime
(``get_legacy_joint_runtime``) is gated behind a formal
``app_enablement_allowed`` sign-off in
``reports/crop_constrained_recalibration_decision.json`` that has not been
granted yet, so calling it here would always fail closed. We instead use
``get_legacy_joint_controlled_field_test_runtime``, which still performs the
full artifact hash/parity/preprocessing verification and only skips that one
release-authorization check. That's safe in this context because -- exactly
like banana/chilli/redgram -- its output is never shown to the farmer on its
own; it is only ever a cross-check against an independent OpenAI read, and a
disagreement is surfaced as ``needs_expert_review`` rather than hidden.
"""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Any

from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import QuotaExceededError
from app.core.logging import get_logger
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.ai.repositories import TokenUsageRepository
from app.modules.ai.usage_ledger import record_usage_durable
from app.modules.auth.models import User
from app.modules.disease.capabilities import normalize_crop_id
from app.modules.disease.constants import (
    ALLOWED_MIME_TYPES,
    DISEASE_IMAGE_PREFIX,
    MAX_IMAGE_BYTES,
    Severity,
)
from app.modules.disease.models import DiseaseReport
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.storage import get_default_storage
from app.modules.disease.vision_diagnosis import (
    OpenAIVisionDiagnosisProvider,
    VisionDiagnosisError,
    VisionDiagnosisResult,
)
from app.modules.farms.repositories import FarmRepository

logger = get_logger("disease.farmer_diagnosis")

_CONFIDENCE_SCORE = {"low": 40, "medium": 65, "high": 88}
_SEVERITY_MAP = {
    "mild": Severity.LOW.value,
    "moderate": Severity.MODERATE.value,
    "severe": Severity.HIGH.value,
    "unknown": Severity.NONE.value,
}
# Known local-classifier vocabularies, passed to OpenAI as a hint so its
# primary_diagnosis text lines up with the local model's labels when it can.
_KNOWN_LOCAL_CLASSES: dict[str, list[str]] = {
    "banana": [
        "banana__healthy",
        "banana__cordana_leaf_spot",
        "banana__pestalotiopsis_leaf_spot",
        "banana__sigatoka_leaf_spot",
    ],
    "chilli": [
        "chilli__bacterial_spot",
        "chilli__cercospora_leaf_spot",
        "chilli__healthy",
        "chilli__leaf_curl_virus",
    ],
    "redgram": [
        "redgram__healthy",
        "redgram__leaf_spot",
        "redgram__sterility_mosaic",
    ],
    "paddy": [
        "paddy_healthy",
        "rice_blast",
        "rice_brown_leaf_spot",
        "rice_tungro",
    ],
    "cotton": [
        "cotton_healthy",
        "cotton_fusarium_wilt",
        "cotton_verticillium_wilt",
    ],
    "groundnut": [
        "groundnut_healthy",
        "groundnut_rust",
    ],
}

# app.legacy_joint.runtime.LegacyJointRuntime.predict() keys its crop groups by
# these canonical ids -- notably "rice", not "paddy" (see CROP_FILES in that
# module); the artifact bundle itself and its class ids use "paddy_*"/"rice_*".
_LEGACY_JOINT_RUNTIME_CROP = {
    "paddy": "rice",
    "cotton": "cotton",
    "groundnut": "groundnut",
}

# Crops whose disease_recommendations registry content this general-release path
# will use. Deliberately excludes chilli/redgram -- see the registry lookup
# below for why.
_REGISTRY_ELIGIBLE_CROPS = frozenset({"banana", "paddy", "cotton", "groundnut"})

_banana_service = None


def _get_banana_service():
    global _banana_service
    if _banana_service is None:
        from app.banana_v3.inference_service import InferenceService

        _banana_service = InferenceService()
    return _banana_service


class DiseaseDiagnosisError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _decode_image(payload: bytes, content_type: str | None) -> Image.Image:
    if content_type not in ALLOWED_MIME_TYPES:
        raise DiseaseDiagnosisError("IMAGE_FORMAT_UNSUPPORTED")
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        raise DiseaseDiagnosisError("IMAGE_SIZE_INVALID")
    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
        require_safe_image(image)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DiseaseDiagnosisError("IMAGE_UNUSABLE") from exc
    except UnsafeImageError as exc:
        raise DiseaseDiagnosisError(exc.reason_code) from exc
    return image


async def _local_model_signal(
    crop_id: str, image: Image.Image
) -> tuple[str | None, float | None, str | None]:
    """Best-effort local-model read: (label, confidence 0..1, model_id), or
    all-None. Never raises -- a local runtime problem must not block the
    farmer's OpenAI diagnosis, since OpenAI is the primary signal here.
    """
    try:
        if crop_id == "banana":
            result = _get_banana_service().predict(image)
            if result.status.value == "accepted" and result.result.class_id:
                return result.result.class_id, result.result.confidence, result.model_version
            return None, None, None
        if crop_id in ("chilli", "redgram"):
            from app.restricted_crops.runtime import get_restricted_runtime

            result = get_restricted_runtime(crop_id).predict(image)
            if result.status == "ACCEPTED_RESTRICTED_RESULT" and result.predicted_class:
                return (
                    result.predicted_class,
                    result.calibrated_confidence,
                    f"{crop_id}_mobilenetv3_small_v1_restricted",
                )
            return None, None, None
        if crop_id in _LEGACY_JOINT_RUNTIME_CROP:
            from app.legacy_joint.runtime import (
                get_legacy_joint_controlled_field_test_runtime,
            )

            runtime_crop = _LEGACY_JOINT_RUNTIME_CROP[crop_id]
            result = get_legacy_joint_controlled_field_test_runtime().predict(
                runtime_crop, image, crop_confirmed=True
            )
            if result.accepted and result.class_id:
                return (
                    result.class_id,
                    result.calibrated_confidence,
                    "legacy_joint_v1_crop_constrained",
                )
            return None, None, None
    except Exception:
        logger.warning(
            "local model signal unavailable for crop=%s (continuing with OpenAI only)",
            crop_id,
            exc_info=True,
        )
    return None, None, None


_CROP_LABEL_PREFIXES = (
    "banana",
    "chilli",
    "redgram",
    "paddy",
    "rice",
    "cotton",
    "groundnut",
)


def _normalize_label(value: str) -> str:
    # Local class ids use two conventions -- "crop__disease" (banana/chilli/
    # redgram) and "crop_disease" (the legacy_joint paddy/cotton/groundnut
    # bundle, e.g. "rice_blast", "paddy_healthy") -- while OpenAI's
    # primary_diagnosis is free text ("Rice Blast"). Strip either the "__"
    # separator or a bare leading crop-name token so both sides compare on
    # the disease name alone.
    slug = value.split("__", 1)[-1] if "__" in value else value
    normalized = "".join(ch for ch in slug.lower() if ch.isalnum())
    for prefix in _CROP_LABEL_PREFIXES:
        if normalized.startswith(prefix) and normalized != prefix:
            return normalized[len(prefix) :]
    return normalized


def _labels_agree(local_label: str | None, ai_label: str | None) -> bool | None:
    if not local_label or not ai_label:
        return None
    return _normalize_label(local_label) == _normalize_label(ai_label)


_MODEL_USED_MAX_LENGTH = 60  # must match DiseaseReport.model_used: String(60)


def _fit_model_used(value: str, max_length: int = _MODEL_USED_MAX_LENGTH) -> str:
    """Guard against Postgres rejecting the insert with "value too long for
    type character varying(60)". For chilli/redgram, the combined
    "<local_model_id>+openai:<model>" string runs 63-64 characters -- past
    this column's limit -- and that insert failure would happen on the very
    last step of the request, *after* the OpenAI call already succeeded and
    was billed (found in the 2026-08 pre-release audit). model_used is an
    internal provenance/audit string, never shown to the farmer, so a
    truncation here is preferable to widening the column, which would need a
    new Alembic migration stacked on the repo's currently-unmerged migration
    heads.
    """
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "…"  # ellipsis, counts as 1 char


async def diagnose_for_farmer(
    session: AsyncSession,
    *,
    user: User,
    crop: str,
    farm_id: uuid.UUID | None,
    image_bytes: bytes,
    content_type: str,
) -> DiseaseReport:
    decoded = _decode_image(image_bytes, content_type)
    crop_id = normalize_crop_id(crop)

    if farm_id is not None:
        farm = await FarmRepository(session).get_for_user(farm_id, user.id)
        if farm is None:
            farm_id = None

    usage_repo = TokenUsageRepository(session)
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = await usage_repo.count_today(
        user.id, "disease_farmer_diagnosis", since=day_start
    )
    if used_today >= settings.ai_daily_disease_quota:
        raise QuotaExceededError()

    local_label, local_confidence, local_model_id = await _local_model_signal(crop_id, decoded)

    if not settings.openai_vision_diagnosis_enabled:
        raise DiseaseDiagnosisError("DIAGNOSIS_TEMPORARILY_UNAVAILABLE")

    try:
        result: VisionDiagnosisResult = await OpenAIVisionDiagnosisProvider().diagnose(
            image=image_bytes,
            content_type=content_type,
            crop=crop_id,
            known_classes=_KNOWN_LOCAL_CLASSES.get(crop_id),
        )
    except VisionDiagnosisError as exc:
        logger.warning("OpenAI vision diagnosis failed: %s", exc)
        raise DiseaseDiagnosisError("DIAGNOSIS_TEMPORARILY_UNAVAILABLE") from exc

    diagnosis = result.diagnosis
    await record_usage_durable(
        farmer_id=user.id,
        module="disease_farmer_diagnosis",
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        provider="openai",
    )

    agreement = _labels_agree(local_label, diagnosis.primary_diagnosis)
    local_confirmed = local_label is not None and agreement is True
    # Always show OpenAI's natural-language diagnosis text to the farmer, even
    # when the local model confirms it -- local class ids are internal slugs
    # (e.g. "banana__cordana_leaf_spot", "rice_blast"), not farmer-facing
    # copy. Local agreement only raises how much we trust that text (see
    # confidence_pct / needs_expert_review below), it never replaces it.
    disease_label = diagnosis.primary_diagnosis
    confidence_pct = (
        round(local_confidence * 100)
        if local_confirmed and local_confidence is not None
        else _CONFIDENCE_SCORE.get(diagnosis.confidence, 50)
    )
    needs_expert_review = bool(
        diagnosis.needs_expert_review
        or diagnosis.confidence != "high"
        or not diagnosis.image_usable
        or not diagnosis.crop_matches_declared
        or (local_label is not None and agreement is False)
    )
    model_used = _fit_model_used(
        f"{local_model_id}+openai:{result.model}"
        if local_label is not None
        else f"openai:{result.model}"
    )

    # When the local model and OpenAI independently agree on a disease that has
    # real, source-grounded content in app.disease_recommendations.registry
    # (populated from government/ICAR/IRRI extension publications -- see that
    # module), prefer that curated cultural/biological guidance over OpenAI's
    # free-form recommendations. This deliberately excludes chilli/redgram: the
    # registry itself keeps their content behind controlled_test=True because
    # their local models are still RESTRICTED_INTERNAL_TESTING_ONLY, and this
    # general farmer path has no reason to work around that gate. symptoms and
    # causes stay OpenAI's own text -- those describe THIS photo, whereas the
    # registry describes the disease in general, so they're not a substitute.
    registry_content: dict[str, Any] | None = None
    if local_confirmed and crop_id in _REGISTRY_ELIGIBLE_CROPS:
        try:
            from app.disease_recommendations.registry import get_recommendation

            registry_result = get_recommendation(
                crop_id, local_label, diagnosis_accepted=True, controlled_test=False
            )
            if registry_result.get("content_sourced_from_extension_library"):
                registry_content = registry_result
        except Exception:
            logger.warning(
                "disease-recommendation registry lookup failed for crop=%s label=%s",
                crop_id,
                local_label,
                exc_info=True,
            )

    recommendations = diagnosis.general_care_recommendations
    prevention = diagnosis.prevention_tips
    if registry_content is not None:
        merged_cultural = (
            registry_content["cultural_management_en"] + registry_content["biological_options_en"]
        )
        if merged_cultural:
            recommendations = merged_cultural
        if registry_content["prevention_en"]:
            prevention = registry_content["prevention_en"]

    # official_sources always starts with the 2 base ICAR references (see
    # OFFICIAL_SOURCES in the registry module); anything after that is the
    # extension source(s) matched to this specific disease. Computed once,
    # reused by both the English and Tamil explanation below.
    extension_titles: list[str] = []
    if registry_content is not None:
        extension_titles = [
            source["title"] for source in registry_content["official_sources"][2:] if source.get("title")
        ]

    explanation_parts = [diagnosis.farmer_summary]
    explanation_parts_tamil = [diagnosis.farmer_summary_tamil]
    if not local_confirmed:
        explanation_parts.append(
            "This is an AI-assisted estimate and has not been field-validated. "
            "For chemical or pesticide treatment decisions, please consult your "
            "local Agriculture Officer or Krishi Vigyan Kendra (KVK)."
        )
        explanation_parts_tamil.append(
            "இது AI உதவியுடன் அளிக்கப்பட்ட மதிப்பீடு; இதுவரை வயல்நிலையில் "
            "சரிபார்க்கப்படவில்லை. மருந்து/பூச்சிக்கொல்லி தொடர்பான முடிவுகளுக்கு "
            "உங்கள் உள்ளூர் வேளாண் அலுவலர் அல்லது கிருஷி விஞ்ஞான கேந்திரத்தை "
            "(KVK) அணுகவும்."
        )
    if local_label is not None and agreement is False:
        explanation_parts.append(
            "Our local image classifier suggested a different result than the AI "
            "estimate, so please treat this diagnosis with extra caution and "
            "consider a second photo or expert opinion."
        )
        explanation_parts_tamil.append(
            "எங்கள் உள்ளூர் பட வகைப்பாட்டு மாதிரி, AI மதிப்பீட்டிலிருந்து வேறுபட்ட "
            "முடிவை பரிந்துரைத்தது. எனவே இந்த நோயறிதலை கூடுதல் எச்சரிக்கையுடன் "
            "கருதவும்; மற்றொரு புகைப்படம் எடுத்தோ அல்லது நிபுணர் ஆலோசனை பெற்றோ "
            "உறுதி செய்யவும்."
        )
    if extension_titles:
        explanation_parts.append(
            "Management guidance above is based on: " + "; ".join(extension_titles) + "."
        )
        explanation_parts_tamil.append(
            "மேலே உள்ள மேலாண்மை வழிகாட்டுதல் பின்வரும் ஆதாரங்களை அடிப்படையாகக் "
            "கொண்டது: " + "; ".join(extension_titles) + "."
        )

    image_url = None
    try:
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(
            content_type, "jpg"
        )
        image_url = await get_default_storage().put(
            key=f"{DISEASE_IMAGE_PREFIX}/farmer/{user.id}/{uuid.uuid4().hex}.{extension}",
            data=image_bytes,
            content_type=content_type,
        )
    except Exception:
        logger.warning("disease image storage failed; continuing without image_url", exc_info=True)

    report = DiseaseReport(
        user_id=user.id,
        farm_id=farm_id,
        image_url=image_url,
        capture_method="gallery",
        crop=crop_id,
        disease=disease_label,
        confidence=confidence_pct,
        severity=_SEVERITY_MAP.get(diagnosis.severity, Severity.NONE.value),
        symptoms=diagnosis.symptoms_observed,
        causes=diagnosis.likely_causes,
        recommendations=recommendations,
        prevention=prevention,
        needs_expert_review=needs_expert_review,
        explanation_english=" ".join(explanation_parts),
        explanation_tamil=" ".join(explanation_parts_tamil),
        model_used=model_used,
        raw_response={
            "openai_diagnosis": diagnosis.model_dump(),
            "local_model": {
                "label": local_label,
                "confidence": local_confidence,
                "model_id": local_model_id,
                "agreement": agreement,
            },
            "disease_recommendation_registry": registry_content,
        },
        language="en",
    )
    return await DiseaseReportRepository(session).add(report)
