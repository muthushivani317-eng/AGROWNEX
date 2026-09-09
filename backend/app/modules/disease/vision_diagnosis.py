"""Farmer-facing AI vision diagnosis (docs/API_CONTRACT.md -> DISEASE DETECTION).

Primary diagnosis engine for crops with no field-validated local classifier,
and an independent second read alongside banana/chilli/redgram's local models.
Follows the same strict-schema OpenAI Responses API pattern already used by
``app.modules.disease_comparison.provider`` rather than duplicating the HTTP
plumbing from scratch.
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.http import get_http_client
from app.modules.disease_comparison.schemas import DifferentialDiagnosis


class VisionDiagnosisError(RuntimeError):
    pass


class VisionDiagnosis(BaseModel):
    """Strict output contract for the farmer-facing vision diagnosis call."""

    model_config = ConfigDict(extra="forbid")

    image_usable: bool
    crop_matches_declared: bool
    plant_health: Literal["healthy", "diseased", "stressed", "unclear"]
    primary_diagnosis: str | None = Field(default=None, max_length=120)
    confidence: Literal["low", "medium", "high"]
    differential_diagnoses: list[DifferentialDiagnosis] = Field(
        default_factory=list, max_length=3
    )
    symptoms_observed: list[str] = Field(default_factory=list, max_length=8)
    likely_causes: list[str] = Field(default_factory=list, max_length=6)
    severity: Literal["mild", "moderate", "severe", "unknown"]
    general_care_recommendations: list[str] = Field(default_factory=list, max_length=6)
    prevention_tips: list[str] = Field(default_factory=list, max_length=6)
    # Category-level-only conventional guidance (e.g. "a protectant or
    # systemic fungicide"), never a specific product, brand, or dose --
    # mirrors app.disease_recommendations.registry's CHEMICAL_WITHHELD
    # policy for the six-crop curated registry, applied here to the general
    # (any-crop) AI vision path. Null when plant_health is not "diseased".
    conventional_care_category: str | None = Field(default=None, max_length=300)
    conventional_care_category_tamil: str | None = Field(default=None, max_length=300)
    needs_expert_review: bool
    expert_review_reason: str | None = Field(default=None, max_length=200)
    farmer_summary: str = Field(min_length=1, max_length=600)
    # A faithful Tamil rendering of farmer_summary -- generated in the same
    # call (mirroring app.modules.nutrient.prompts' proven bilingual-JSON
    # pattern) rather than a separate translation request, so Tamil-language
    # farmers get real Tamil explanation text instead of a silent English
    # fallback (found in the 2026-08 pre-release audit: this screen always
    # showed English regardless of app language).
    farmer_summary_tamil: str = Field(min_length=1, max_length=600)


@dataclass(frozen=True)
class VisionDiagnosisResult:
    diagnosis: VisionDiagnosis
    model: str
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None


SYSTEM_PROMPT = """You are an agricultural plant-health assistant helping a
smallholder farmer in Tamil Nadu understand a photo of their crop. Analyse
only what is visibly observable in the supplied image for the farmer-declared
crop. Do not assume the plant is diseased -- healthy is a valid outcome.
Identify visible symptoms, then give your best-guess diagnosis with an honest
confidence level (low/medium/high); if evidence is weak, ambiguous, or the
photo is unusable, say so and set confidence to low or medium and
needs_expert_review to true rather than guessing. When the message lists
known local classifier labels for this crop, prefer one of those exact labels
in primary_diagnosis if it fits; otherwise describe the disease in plain
English. Offer general, non-chemical organic care: cultural practices (remove and
destroy affected leaves/plant parts, improve spacing and airflow, avoid
overhead watering, sanitize tools between plants, rotate crops, use
resistant varieties next season) AND, where genuinely applicable to the
diagnosed problem, well-established biological/organic options such as neem
oil or neem seed kernel extract spray, a Trichoderma or Pseudomonas
fluorescens bio-fungicide, a Beauveria bassiana or NPV bio-pesticide for
an insect pest, releasing or conserving natural predators (ladybird beetles,
parasitic wasps), a garlic-chilli or buttermilk (sour, fermented) spray for
mild fungal issues, or well-decomposed compost/vermicompost to strengthen
the plant's own resistance -- always in general terms (a practice or
biological-agent class, not a specific commercial product name) and only
when it genuinely fits the diagnosis; do not pad the list with irrelevant
options. Never name,
recommend, or imply a dosage for any specific pesticide, fungicide, or
chemical brand -- always defer chemical treatment decisions to the farmer's
local Agriculture Officer or Krishi Vigyan Kendra (KVK). When plant_health is
"diseased", also set conventional_care_category to ONE short sentence naming
only the general CLASS of conventional treatment typically used for that
type of problem (for example "A protectant or systemic fungicide labelled
for this crop and disease is commonly used" for a fungal-looking issue, or
"No chemical product cures a viral infection; conventional management
targets the insect vector that spreads it" for a virus-like pattern) --
still never a specific product, active ingredient, brand, or dose, and still
end by directing the farmer to their local Agriculture Officer or KVK for
the exact product and dose. Leave conventional_care_category null when
plant_health is not "diseased". Write farmer_summary in simple, plain
language a smallholder farmer can act on. Then write farmer_summary_tamil:
the same explanation in simple, natural, plain Tamil -- a faithful rendering
of the same facts and advice for a Tamil-reading smallholder farmer, not a
literal word-for-word translation. When conventional_care_category is set,
also write conventional_care_category_tamil as the same faithful Tamil
rendering of it (null when conventional_care_category is null). All English
fields and their Tamil counterparts must convey identical content; only the
language differs. Return only the required JSON schema."""


def _output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                return content["text"]
    raise VisionDiagnosisError("OPENAI_OUTPUT_MISSING")


def _strict_schema(node: Any) -> None:
    """Apply Responses API strict-object requirements recursively."""
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            node["additionalProperties"] = False
            node["required"] = list(properties)
        for value in node.values():
            _strict_schema(value)
    elif isinstance(node, list):
        for value in node:
            _strict_schema(value)


class OpenAIVisionDiagnosisProvider:
    """Primary farmer-facing diagnosis engine, backed by an OpenAI vision model."""

    def __init__(self) -> None:
        if not settings.openai_vision_diagnosis_api_key:
            raise VisionDiagnosisError("OPENAI_CONFIGURATION_MISSING")
        if not settings.openai_vision_diagnosis_model:
            raise VisionDiagnosisError("OPENAI_MODEL_NOT_CONFIGURED")

    async def diagnose(
        self,
        *,
        image: bytes,
        content_type: str,
        crop: str,
        known_classes: list[str] | None = None,
    ) -> VisionDiagnosisResult:
        schema = VisionDiagnosis.model_json_schema()
        _strict_schema(schema)
        encoded = base64.b64encode(image).decode("ascii")
        prompt_text = f"Farmer-declared crop: {crop}. Diagnose this photo."
        if known_classes:
            prompt_text += " Known local classifier labels for this crop: " + ", ".join(
                known_classes
            )
        body = {
            "model": settings.openai_vision_diagnosis_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt_text},
                        {
                            "type": "input_image",
                            "image_url": f"data:{content_type};base64,{encoded}",
                            "detail": "high",
                        },
                    ],
                }
            ],
            "instructions": SYSTEM_PROMPT,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "farmer_vision_diagnosis",
                    "strict": True,
                    "schema": schema,
                }
            },
            # Raised from 900: the response now also includes farmer_summary_tamil,
            # and Tamil script tokenizes far less efficiently than English (roughly
            # 1 token per 1-2 characters vs ~4 for English), so the old budget risked
            # truncating -- and therefore failing to parse -- the JSON response.
            "max_output_tokens": 1500,
        }
        started = time.perf_counter()
        try:
            response = await get_http_client().post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_vision_diagnosis_api_key}"
                },
                json=body,
                timeout=settings.openai_vision_diagnosis_timeout_seconds,
            )
            if response.status_code == 429:
                raise VisionDiagnosisError("OPENAI_RATE_LIMITED")
            response.raise_for_status()
            payload = response.json()
            diagnosis = VisionDiagnosis.model_validate_json(_output_text(payload))
        except VisionDiagnosisError:
            raise
        except httpx.TimeoutException as exc:
            raise VisionDiagnosisError("OPENAI_TIMEOUT") from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise VisionDiagnosisError("OPENAI_RESPONSE_INVALID") from exc
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        return VisionDiagnosisResult(
            diagnosis=diagnosis,
            model=str(payload.get("model") or settings.openai_vision_diagnosis_model),
            latency_ms=round((time.perf_counter() - started) * 1000),
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )
