"""AI provider — Google Gemini (finalized stack) behind a small interface.

Isolated so the service can be tested with a fake (no network) and so
timeout/retry policy lives in one place. When no API key is configured a
deterministic mock is used, mirroring the app's mock-provider pattern.
API keys never leave the backend (docs/SECURITY.md).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

import httpx

from app.core.http import get_http_client
from app.core.logging import get_logger
from app.modules.ai.constants import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_CHAT_MODEL,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MAX_RETRIES,
    GEMINI_TEMPERATURE,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_VISION_MODEL,
)
from app.modules.ai.exceptions import AIUnavailableError

logger = get_logger("ai.provider")


class ChatTurn(TypedDict):
    role: str  # "user" | "model"
    content: str


@dataclass
class AIResult:
    text: str
    model: str
    tokens: int | None = None  # total tokens (backward-compatible)
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    provider: str = "gemini"
    is_sample: bool = False


class AIProvider(Protocol):
    async def generate(
        self, *, system: str, history: list[ChatTurn], message: str
    ) -> AIResult: ...


class GeminiClient:
    """Google Gemini generateContent client with timeout + bounded retries."""

    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_CHAT_MODEL,
        base_url: str = GEMINI_BASE_URL,
        timeout: float = GEMINI_TIMEOUT_SECONDS,
        max_retries: int = GEMINI_MAX_RETRIES,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _body(
        self, system: str, history: list[ChatTurn], message: str
    ) -> dict[str, Any]:
        contents: list[dict[str, Any]] = [
            {"role": turn["role"], "parts": [{"text": turn["content"]}]}
            for turn in history
        ]
        contents.append({"role": "user", "parts": [{"text": message}]})
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "temperature": GEMINI_TEMPERATURE,
                "maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS,
            },
        }

    async def generate(
        self, *, system: str, history: list[ChatTurn], message: str
    ) -> AIResult:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        body = self._body(system, history, message)
        last_error: Exception | None = None
        started = time.monotonic()

        for attempt in range(1, self.max_retries + 1):
            try:
                client = get_http_client()
                response = await client.post(
                    url, params={"key": self.api_key}, json=body, timeout=self.timeout
                )
                response.raise_for_status()
                latency_ms = int((time.monotonic() - started) * 1000)
                return self._parse(response.json(), latency_ms)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    logger.warning("Gemini client error %s", exc.response.status_code)
                    raise AIUnavailableError() from exc
                last_error = exc

            if attempt < self.max_retries:
                await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 4.0))

        logger.warning("Gemini failed after %s attempts", self.max_retries)
        raise AIUnavailableError() from last_error

    def _parse(self, data: dict[str, Any], latency_ms: int | None = None) -> AIResult:
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise AIUnavailableError() from exc
        usage = data.get("usageMetadata", {}) or {}
        return AIResult(
            text=text,
            model=self.model,
            tokens=usage.get("totalTokenCount"),
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            latency_ms=latency_ms,
        )


_MOCK_TA = (
    '**சுருக்கம்:** உங்கள் கேள்விக்கு ("{question}") உதவ நான் இங்கே இருக்கிறேன்.\n'
    "**பரிந்துரை:** உங்கள் பயிர், மண் மற்றும் தற்போதைய வானிலைக்கு ஏற்ப செயல்படுங்கள்.\n"
    "**எச்சரிக்கை:** உறுதியில்லாத நிலையில் உள்ளூர் வேளாண் அலுவலரை அணுகவும்.\n"
    "**அடுத்த படி:** மேலும் துல்லியமான ஆலோசனைக்கு உங்கள் பண்ணை விவரங்களைச் சேர்க்கவும்.\n"
    "(டெமோ பதில்)"
)
_MOCK_EN = (
    '**Summary:** I am here to help with your question ("{question}").\n'
    "**Recommendation:** Act based on your crop, soil and the current weather.\n"
    "**Precaution:** If you are unsure, consult your local agriculture officer.\n"
    "**Next step:** Add your farm details for more precise advice.\n"
    "(demo response)"
)


class RoutedChatProvider:
    """Chat routing with cost control + reliability (docs: Flash for chat, Pro fallback).

    Conversational chat runs on the cheaper Flash model. If Flash returns an empty /
    unparseable response twice, the request escalates once to the Pro model and the
    escalation is logged — so a farmer never gets a blank answer to save a few paise.
    """

    def __init__(
        self,
        *,
        primary: AIProvider | None = None,
        fallback: AIProvider | None = None,
    ) -> None:
        self.primary = primary or GeminiClient(model=GEMINI_CHAT_MODEL)
        self.fallback = fallback or GeminiClient(model=GEMINI_VISION_MODEL)

    @property
    def model(self) -> str:
        return getattr(self.primary, "model", GEMINI_CHAT_MODEL)

    async def generate(
        self, *, system: str, history: list[ChatTurn], message: str
    ) -> AIResult:
        # Two attempts on the primary (Flash); an empty body is a soft failure.
        for attempt in (1, 2):
            try:
                result = await self.primary.generate(
                    system=system, history=history, message=message
                )
            except AIUnavailableError:
                break  # hard failure → escalate immediately
            if result.text.strip():
                return result
            logger.info("chat primary returned empty text (attempt %s)", attempt)

        logger.warning("chat escalating to fallback model %s", self.fallback.model)
        return await self.fallback.generate(
            system=system, history=history, message=message
        )


class MockAIProvider:
    """Deterministic, offline provider used until a Gemini key is configured."""

    model = "mock-gemini"
    provider = "mock"

    async def generate(
        self, *, system: str, history: list[ChatTurn], message: str
    ) -> AIResult:
        template = _MOCK_TA if "Tamil" in system else _MOCK_EN
        return AIResult(
            text=template.format(question=message.strip()[:120]),
            model=self.model,
            tokens=None,
            provider="mock",
            is_sample=True,
        )


def get_default_provider() -> AIProvider:
    if GEMINI_API_KEY:
        logger.info(
            "AI provider: Gemini chat=%s fallback=%s",
            GEMINI_CHAT_MODEL,
            GEMINI_VISION_MODEL,
        )
        return RoutedChatProvider()
    logger.info("AI provider: mock (no GEMINI_API_KEY configured)")
    return MockAIProvider()
