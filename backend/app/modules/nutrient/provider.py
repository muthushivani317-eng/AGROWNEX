"""Nutrient analysis provider (docs: PROVIDER ABSTRACTION — future-proof).

``NutrientProvider`` returns a normalized *visual* ``NutrientObservation`` for an
image, so a future YOLO / EfficientNet / ConvNeXt / TensorRT / ONNX model — or a
hybrid ensemble — can replace Gemini with **no frontend change**. V1 ships a Gemini
2.5 Pro vision client (with one parse retry) and a deterministic mock used when no
API key is set. The provider only *observes*; the Nutrient Engine decides the
verdict, so a new model never changes the confirm/not-confirmed logic.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.logging import get_logger
from app.modules.ai.constants import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)
from app.modules.nutrient.constants import (
    AffectedArea,
    NutrientProviderName,
    Severity,
)
from app.modules.nutrient.exceptions import NutrientAnalysisError, NutrientProviderUnavailableError
from app.modules.nutrient.parser import (
    NutrientObservation,
    ObservationParseError,
    parse_observation,
)
from app.modules.nutrient.prompts import (
    NUTRIENT_SYSTEM_PROMPT,
    build_nutrient_prompt,
)

logger = get_logger("nutrient.provider")


@dataclass
class AnalysisInput:
    image_base64: str
    mime_type: str
    crop: str | None
    language: str
    farm_context: str


class NutrientProvider(Protocol):
    name: str
    model: str

    async def analyze(self, request: AnalysisInput) -> NutrientObservation: ...


class GeminiNutrientProvider:
    """Gemini 2.5 Pro multimodal nutrient analysis with structured parsing + retry."""

    name = NutrientProviderName.GEMINI.value

    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_MODEL,
        base_url: str = GEMINI_BASE_URL,
        timeout: float = GEMINI_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _body(self, request: AnalysisInput) -> dict[str, Any]:
        prompt = build_nutrient_prompt(request.crop, request.language, request.farm_context)
        return {
            "systemInstruction": {"parts": [{"text": NUTRIENT_SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": request.mime_type,
                                "data": request.image_base64,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 1000,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

    async def analyze(self, request: AnalysisInput) -> NutrientObservation:
        last_error: Exception | None = None
        for attempt in range(2):  # retry once on a parse failure
            raw = await self._generate(request)
            try:
                result = parse_observation(raw)
                result.model_used = self.model
                return result
            except ObservationParseError as exc:
                last_error = exc
                logger.info("nutrient parse failed (attempt %s): %s", attempt + 1, exc)
        raise NutrientAnalysisError() from last_error

    async def _generate(self, request: AnalysisInput) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        body = self._body(request)
        last_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, params={"key": self.api_key}, json=body)
                    response.raise_for_status()
                    return self._text(response.json())
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise NutrientAnalysisError() from exc
                last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * attempt)
        raise NutrientAnalysisError() from last_error

    def _text(self, data: dict[str, Any]) -> str:
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise NutrientAnalysisError() from exc


class MockNutrientProvider:
    """Deterministic offline observation — a mild nitrogen-deficiency pattern."""

    name = NutrientProviderName.MOCK.value
    model = "mock-nutrient-vision"

    async def analyze(self, request: AnalysisInput) -> NutrientObservation:
        return NutrientObservation(
            plant_present=True,
            reject_reason=None,
            crop=request.crop or "paddy",
            visible_symptoms=["yellowing", "pale_leaf", "older_leaf_first"],
            primary="nitrogen",
            secondary=None,
            visual_confidence=68,
            severity=Severity.MODERATE.value,
            affected_area=AffectedArea.WIDESPREAD.value,
            explanation_tamil=(
                "பழைய இலைகள் மஞ்சளாக மாறுகின்றன — நைட்ரஜன் குறைபாட்டின் அறிகுறி. "
                "இது டெமோ பதில்; உறுதிசெய்ய மண் பரிசோதனை செய்யவும்."
            ),
            explanation_english=(
                "Older leaves are yellowing, a sign of nitrogen deficiency. "
                "This is a demo response; confirm with a soil test."
            ),
            model_used=self.model,
            raw={"source": "mock"},
        )


class UnavailableNutrientProvider:
    name = "unavailable"
    model = "unavailable"

    async def analyze(self, request: AnalysisInput) -> NutrientObservation:
        raise NutrientProviderUnavailableError()


def get_default_provider() -> NutrientProvider:
    if GEMINI_API_KEY:
        logger.info("nutrient provider: Gemini (%s)", GEMINI_MODEL)
        return GeminiNutrientProvider()
    environment = os.getenv("ENVIRONMENT", "development").lower()
    provider = os.getenv("NUTRIENT_PROVIDER", "").lower()
    if provider == "mock" and environment in {"development", "test"}:
        logger.info("nutrient provider: explicit development mock")
        return MockNutrientProvider()
    logger.warning("nutrient provider unavailable: credentials not configured")
    return UnavailableNutrientProvider()
