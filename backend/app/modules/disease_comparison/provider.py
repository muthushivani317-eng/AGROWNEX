from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.http import get_http_client

from .schemas import OpenAISecondOpinion


class OpenAIComparisonError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderResult:
    opinion: OpenAISecondOpinion
    model: str
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class ImageEvidence:
    view: str
    image: bytes
    content_type: str


SYSTEM_PROMPT = """You are an observations-first agricultural diagnostic assistant
for a supervised field test. Analyse only observable evidence in the supplied images
for the farmer-confirmed crop. Separate observed symptoms from diagnostic conclusions.
Do not assume the plant is diseased. Valid outcome categories are healthy,
known_disease, abiotic_stress, nutrient_related, pest_damage, physical_injury,
unsupported_disease, and insufficient_evidence. Do not select a disease merely because
it is an available model class. If evidence is insufficient or conflicting, identify
the specific missing photo view. Never prescribe, recommend, or mention any pesticide,
chemical, brand, dosage, treatment, or payment. Do not claim an official diagnosis.
Return only the required JSON schema."""


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
    raise OpenAIComparisonError("OPENAI_OUTPUT_MISSING")


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


class OpenAIDiseaseComparisonProvider:
    def __init__(self) -> None:
        if not settings.openai_disease_comparison_api_key:
            raise OpenAIComparisonError("OPENAI_CONFIGURATION_MISSING")
        if not settings.openai_disease_comparison_model:
            raise OpenAIComparisonError("OPENAI_MODEL_NOT_CONFIGURED")

    async def compare(self, *, image: bytes, content_type: str, crop: str) -> ProviderResult:
        return await self.compare_images(
            images=[ImageEvidence(view="affected_leaf", image=image, content_type=content_type)],
            crop=crop,
        )

    async def compare_images(
        self, *, images: list[ImageEvidence], crop: str
    ) -> ProviderResult:
        if not 1 <= len(images) <= 4:
            raise OpenAIComparisonError("OPENAI_IMAGE_COUNT_INVALID")
        schema = OpenAISecondOpinion.model_json_schema()
        _strict_schema(schema)
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    f"Farmer-confirmed crop: {crop}. Analyse the labelled views "
                    "together as an unverified second opinion."
                ),
            }
        ]
        for evidence in images:
            encoded = base64.b64encode(evidence.image).decode("ascii")
            content.extend(
                [
                    {"type": "input_text", "text": f"Photo view: {evidence.view}"},
                    {
                        "type": "input_image",
                        "image_url": f"data:{evidence.content_type};base64,{encoded}",
                        "detail": "high",
                    },
                ]
            )
        body = {
            "model": settings.openai_disease_comparison_model,
            "input": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "instructions": SYSTEM_PROMPT,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "disease_second_opinion",
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": 500,
        }
        started = time.perf_counter()
        try:
            response = await get_http_client().post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_disease_comparison_api_key}"},
                json=body,
                timeout=settings.openai_disease_comparison_timeout_seconds,
            )
            if response.status_code == 429:
                raise OpenAIComparisonError("OPENAI_RATE_LIMITED")
            response.raise_for_status()
            payload = response.json()
            opinion = OpenAISecondOpinion.model_validate_json(_output_text(payload))
        except OpenAIComparisonError:
            raise
        except httpx.TimeoutException as exc:
            raise OpenAIComparisonError("OPENAI_TIMEOUT") from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise OpenAIComparisonError("OPENAI_RESPONSE_INVALID") from exc
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        return ProviderResult(
            opinion=opinion,
            model=str(payload.get("model") or settings.openai_disease_comparison_model),
            latency_ms=round((time.perf_counter() - started) * 1000),
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )
