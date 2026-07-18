"""Analysis provider (docs: STEP 8 — future-proof).

`AnalysisProvider` returns a normalized ``DiseaseAnalysis`` for an image, so a
future YOLO / custom disease / nutrient / pest model can replace Gemini without
any frontend change. V1 ships a Gemini 2.5 Pro vision client (with one parse
retry — STEP 5) and a deterministic mock used when no API key is set.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.http import get_http_client
from app.core.logging import get_logger
from app.modules.disease.constants import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_VISION_MODEL,
)
from app.modules.disease.exceptions import DiseaseAnalysisError
from app.modules.disease.parser import (
    AnalysisParseError,
    DiseaseAnalysis,
    parse_analysis,
)
from app.modules.disease.prompts import DISEASE_SYSTEM_PROMPT, build_disease_prompt

logger = get_logger("disease.vision")


@dataclass
class AnalysisRequest:
    image_base64: str
    mime_type: str
    crop: str | None
    language: str
    farm_context: str


class AnalysisProvider(Protocol):
    model: str

    async def analyze(self, request: AnalysisRequest) -> DiseaseAnalysis: ...


class GeminiVisionProvider:
    """Gemini 2.5 Pro multimodal analysis with structured parsing + one retry."""

    model = GEMINI_VISION_MODEL

    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_VISION_MODEL,
        base_url: str = GEMINI_BASE_URL,
        timeout: float = GEMINI_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Usage/latency of the most recent real call (Phase 1 cost accounting).
        # Subclasses that override ``_generate`` leave these unset → unknown → cost 0.
        self._last_usage: dict[str, Any] = {}
        self._last_latency_ms: int | None = None

    def _body(self, request: AnalysisRequest) -> dict[str, Any]:
        prompt = build_disease_prompt(
            request.crop, request.language, request.farm_context
        )
        return {
            "systemInstruction": {"parts": [{"text": DISEASE_SYSTEM_PROMPT}]},
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
                "maxOutputTokens": 1200,
                "thinkingConfig": {
                    "thinkingBudget": 0
                },
            },
        }

    async def analyze(self, request: AnalysisRequest) -> DiseaseAnalysis:
        last_error: Exception | None = None
        for attempt in range(2):  # STEP 5: retry once on parse failure
            raw = await self._generate(request)
            try:
                result = parse_analysis(raw)
                result.model_used = self.model
                # AI usage accounting (Phase 1 — cost control). ``_generate`` records
                # the usage/latency of the real call; unknown values stay None.
                result.input_tokens = self._last_usage.get("promptTokenCount")
                result.output_tokens = self._last_usage.get("candidatesTokenCount")
                result.latency_ms = self._last_latency_ms
                return result
            except AnalysisParseError as exc:
                last_error = exc
                logger.info("disease parse failed (attempt %s): %s", attempt + 1, exc)
        raise DiseaseAnalysisError() from last_error

    async def _generate(self, request: AnalysisRequest) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        body = self._body(request)
        last_error: Exception | None = None
        started = time.monotonic()
        for attempt in range(1, 3):
            try:
                client = get_http_client()
                response = await client.post(
                    url, params={"key": self.api_key}, json=body, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                self._last_usage = data.get("usageMetadata", {}) or {}
                self._last_latency_ms = int((time.monotonic() - started) * 1000)
                return self._text(data)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise DiseaseAnalysisError() from exc
                last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * attempt)
        raise DiseaseAnalysisError() from last_error

    def _text(self, data: dict[str, Any]) -> str:
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise DiseaseAnalysisError() from exc


class MockAnalysisProvider:
    """Deterministic offline analysis — returns a normalized result directly."""

    model = "mock-gemini-vision"

    async def analyze(self, request: AnalysisRequest) -> DiseaseAnalysis:
        tamil = request.language == "ta"
        return DiseaseAnalysis(
            plant_present=True,
            reject_reason=None,
            visible_parts=["leaf"],
            crop=request.crop or "paddy",
            crop_confidence=80,
            disease="Leaf spot" if not tamil else "இலைப்புள்ளி நோய்",
            confidence=72,
            severity="moderate",
            symptoms=(
                ["இலைகளில் பழுப்பு புள்ளிகள்", "மஞ்சள் விளிம்புகள்"]
                if tamil
                else ["Brown spots on leaves", "Yellow margins"]
            ),
            causes=(
                ["பூஞ்சை நோய்த்தொற்று", "அதிக ஈரப்பதம்"]
                if tamil
                else ["Fungal infection", "High humidity"]
            ),
            recommendations=(
                ["பாதிக்கப்பட்ட இலைகளை அகற்றவும்", "காற்றோட்டத்தை மேம்படுத்தவும்"]
                if tamil
                else ["Remove affected leaves", "Improve airflow between plants"]
            ),
            prevention=(
                ["விதை நேர்த்தி செய்யவும்", "நீர் தேங்குவதை தவிர்க்கவும்"]
                if tamil
                else ["Treat seeds before sowing", "Avoid waterlogging"]
            ),
            needs_expert_review=False,
            explanation_tamil=(
                "இலைப்புள்ளி நோயின் அறிகுறிகள் தெரிகின்றன. இது டெமோ பதில்."
            ),
            explanation_english=(
                "The leaf shows signs of leaf spot. This is a demo response."
            ),
            model_used=self.model,
            raw={"source": "mock"},
        )


def get_default_provider() -> AnalysisProvider:
    if GEMINI_API_KEY:
        logger.info("disease vision provider: Gemini (%s)", GEMINI_VISION_MODEL)
        return GeminiVisionProvider()
    logger.info("disease vision provider: mock (no GEMINI_API_KEY)")
    return MockAnalysisProvider()
