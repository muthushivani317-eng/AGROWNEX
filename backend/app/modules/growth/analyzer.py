"""Growth analysis providers (docs: future compatibility — future models replace Gemini).

``GrowthAnalysisProvider`` is the seam that keeps the service ignorant of *which*
model produced the observation. V1 ships a Gemini 2.5 Pro vision provider and a
deterministic mock. A future **YOLO** / **Growth-Stage** model implements the same
Protocol and is selected in ``get_default_provider`` with no change to the service,
API or frontend.

Nutrient-deficiency and pest models plug in through the small ``NutrientProvider``
seam (and the reused Disease ``AnalysisProvider``) — both return optional results
the service simply attaches, so nothing here fabricates data when a model is absent.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.logging import get_logger
from app.modules.growth.constants import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
    GrowthStage,
    PlantVigor,
)
from app.modules.growth.exceptions import GrowthAnalysisError
from app.modules.growth.prompts import GROWTH_SYSTEM_PROMPT, build_growth_prompt

logger = get_logger("growth.analyzer")


# --------------------------------------------------------------------------- #
# Domain result + request
# --------------------------------------------------------------------------- #
class GrowthAnalysisParseError(ValueError):
    """Raised when the model output is malformed or missing required fields."""


@dataclass
class GrowthAnalysis:
    plant_present: bool
    reject_reason: str | None
    growth_stage: str
    plant_vigor: str
    health_score: int
    confidence: int
    leaf_color_observations: list[str]
    visible_abnormalities: list[str]
    changes_from_previous: list[str]
    recommendations: list[str]
    needs_expert_review: bool
    growth_summary_tamil: str
    growth_summary_english: str
    model_used: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class GrowthAnalysisRequest:
    image_base64: str
    mime_type: str
    crop: str | None
    language: str
    farm_context: str
    previous_context: str | None = None


class GrowthAnalysisProvider(Protocol):
    """Returns a normalized growth observation for one photo. The external seam."""

    model: str

    async def analyze(self, request: GrowthAnalysisRequest) -> GrowthAnalysis: ...


# --------------------------------------------------------------------------- #
# Pure parser (STEP validation) — unit-tested, no network
# --------------------------------------------------------------------------- #
def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise GrowthAnalysisParseError("no JSON object found")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise GrowthAnalysisParseError(str(exc)) from exc
    if not isinstance(data, dict):
        raise GrowthAnalysisParseError("response is not a JSON object")
    return data


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _bounded_int(value: Any, default: int = 0) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return min(100, max(0, number))


def _stage(value: Any) -> str:
    text = str(value).strip().lower()
    valid = {member.value for member in GrowthStage}
    return text if text in valid else GrowthStage.UNKNOWN.value


def _vigor(value: Any) -> str:
    text = str(value).strip().lower()
    valid = {member.value for member in PlantVigor}
    return text if text in valid else PlantVigor.UNKNOWN.value


def parse_growth_analysis(text: str) -> GrowthAnalysis:
    data = _extract_json(text)
    plant_present = bool(data.get("plant_present", True))
    reject = data.get("reject_reason")
    reject_reason = str(reject).strip().lower() if reject else None
    summary_tamil = str(data.get("growth_summary_tamil", "")).strip()
    summary_english = str(data.get("growth_summary_english", "")).strip()

    if not plant_present:
        return GrowthAnalysis(
            plant_present=False,
            reject_reason=reject_reason,
            growth_stage=GrowthStage.UNKNOWN.value,
            plant_vigor=PlantVigor.UNKNOWN.value,
            health_score=0,
            confidence=0,
            leaf_color_observations=[],
            visible_abnormalities=[],
            changes_from_previous=[],
            recommendations=[],
            needs_expert_review=True,
            growth_summary_tamil=summary_tamil,
            growth_summary_english=summary_english,
            raw=data,
        )

    return GrowthAnalysis(
        plant_present=True,
        reject_reason=None,
        growth_stage=_stage(data.get("growth_stage")),
        plant_vigor=_vigor(data.get("plant_vigor")),
        health_score=_bounded_int(data.get("health_score")),
        confidence=_bounded_int(data.get("confidence")),
        leaf_color_observations=_str_list(data.get("leaf_color_observations")),
        visible_abnormalities=_str_list(data.get("visible_abnormalities")),
        changes_from_previous=_str_list(data.get("changes_from_previous")),
        recommendations=_str_list(data.get("recommendations")),
        needs_expert_review=bool(data.get("needs_expert_review", False)),
        growth_summary_tamil=summary_tamil,
        growth_summary_english=summary_english,
        raw=data,
    )


# --------------------------------------------------------------------------- #
# Gemini vision provider
# --------------------------------------------------------------------------- #
class GeminiGrowthProvider:
    """Gemini 2.5 Pro multimodal growth analysis with structured parsing + one retry."""

    model = GEMINI_MODEL

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

    def _body(self, request: GrowthAnalysisRequest) -> dict[str, Any]:
        prompt = build_growth_prompt(
            request.crop,
            request.language,
            request.farm_context,
            request.previous_context,
        )
        return {
            "systemInstruction": {"parts": [{"text": GROWTH_SYSTEM_PROMPT}]},
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
            },
        }

    async def analyze(self, request: GrowthAnalysisRequest) -> GrowthAnalysis:
        last_error: Exception | None = None
        for attempt in range(2):  # retry once on parse failure
            raw = await self._generate(request)
            try:
                result = parse_growth_analysis(raw)
                result.model_used = self.model
                return result
            except GrowthAnalysisParseError as exc:
                last_error = exc
                logger.info("growth parse failed (attempt %s): %s", attempt + 1, exc)
        raise GrowthAnalysisError() from last_error

    async def _generate(self, request: GrowthAnalysisRequest) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        body = self._body(request)
        last_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        url, params={"key": self.api_key}, json=body
                    )
                    response.raise_for_status()
                    return self._text(response.json())
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise GrowthAnalysisError() from exc
                last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * attempt)
        raise GrowthAnalysisError() from last_error

    def _text(self, data: dict[str, Any]) -> str:
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise GrowthAnalysisError() from exc


# --------------------------------------------------------------------------- #
# Deterministic mock (offline / dev / tests)
# --------------------------------------------------------------------------- #
class MockGrowthProvider:
    """Deterministic growth observation — returns a normalized result directly."""

    model = "mock-gemini-growth"

    async def analyze(self, request: GrowthAnalysisRequest) -> GrowthAnalysis:
        tamil = request.language == "ta"
        improving = request.previous_context is not None
        return GrowthAnalysis(
            plant_present=True,
            reject_reason=None,
            growth_stage=GrowthStage.VEGETATIVE.value,
            plant_vigor=PlantVigor.GOOD.value,
            health_score=78,
            confidence=70,
            leaf_color_observations=(
                ["இலைகள் பச்சையாக உள்ளன", "நல்ல வளர்ச்சி"]
                if tamil
                else ["Leaves are healthy green", "Good canopy"]
            ),
            visible_abnormalities=(
                ["சில இலைகளில் மஞ்சள்"] if tamil else ["Slight yellowing on a few leaves"]
            ),
            changes_from_previous=(
                (["முந்தைய வாரத்தை விட உயரம் அதிகரித்துள்ளது"] if tamil else ["Taller than last week"])
                if improving
                else []
            ),
            recommendations=(
                ["தொடர்ந்து நீர்ப்பாசனம் செய்யவும்", "களைகளை அகற்றவும்"]
                if tamil
                else ["Continue regular irrigation", "Remove weeds around the crop"]
            ),
            needs_expert_review=False,
            growth_summary_tamil=(
                "பயிர் நல்ல வளர்ச்சியில் உள்ளது. இது டெமோ பதில்."
            ),
            growth_summary_english=(
                "The crop is growing well and looks healthy. This is a demo response."
            ),
            model_used=self.model,
            raw={"source": "mock"},
        )


def get_default_provider() -> GrowthAnalysisProvider:
    if GEMINI_API_KEY:
        logger.info("growth analysis provider: Gemini (%s)", GEMINI_MODEL)
        return GeminiGrowthProvider()
    logger.info("growth analysis provider: mock (no GEMINI_API_KEY)")
    return MockGrowthProvider()


# --------------------------------------------------------------------------- #
# Optional nutrient-deficiency seam (future model plugs in here)
# --------------------------------------------------------------------------- #
class NutrientProvider(Protocol):
    """Future nutrient-deficiency model. Returns a structured result or ``None``."""

    async def analyze(
        self, request: GrowthAnalysisRequest
    ) -> dict[str, Any] | None: ...


class NullNutrientProvider:
    """Default: no nutrient model configured — returns ``None`` (never fabricates)."""

    async def analyze(self, request: GrowthAnalysisRequest) -> dict[str, Any] | None:
        return None
