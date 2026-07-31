from __future__ import annotations

import base64
from typing import Any, Protocol

import httpx

from app.core.http import get_http_client
from app.modules.ai.constants import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_VISION_MODEL,
)

from .prompt import SYSTEM_PROMPT, USER_PROMPT


class PlantIdentifierProviderError(RuntimeError):
    pass


class PlantIdentifierProvider(Protocol):
    async def identify(
        self, image: bytes, mime_type: str, language: str, note: str | None
    ) -> str: ...


class GeminiPlantIdentifierProvider:
    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_VISION_MODEL,
        base_url: str = GEMINI_BASE_URL,
        timeout: float = GEMINI_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key or not model:
            raise PlantIdentifierProviderError("PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def identify(
        self, image: bytes, mime_type: str, language: str, note: str | None
    ) -> str:
        user_text = USER_PROMPT + f"\nPreferred response language: {language}."
        if note:
            user_text += f"\nUser note (untrusted context only): {note}"
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": user_text},
                    {"inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image).decode("ascii"),
                    }},
                ],
            }],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 700,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        try:
            response = await get_http_client().post(
                f"{self._base_url}/models/{self._model}:generateContent",
                params={"key": self._api_key},
                json=body,
                timeout=self._timeout,
            )
            response.raise_for_status()
            parts = response.json()["candidates"][0]["content"]["parts"]
            raw = "".join(part.get("text", "") for part in parts)
            if not raw:
                raise PlantIdentifierProviderError(
                    "PLANT_IDENTIFIER_INVALID_PROVIDER_RESPONSE"
                )
            return raw
        except httpx.TimeoutException as exc:
            raise PlantIdentifierProviderError(
                "PLANT_IDENTIFIER_PROVIDER_TIMEOUT"
            ) from exc
        except httpx.HTTPStatusError as exc:
            code = (
                "PLANT_IDENTIFIER_PROVIDER_RATE_LIMIT"
                if exc.response.status_code == 429
                else "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE"
            )
            raise PlantIdentifierProviderError(code) from exc
        except PlantIdentifierProviderError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise PlantIdentifierProviderError(
                "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE"
            ) from exc


def get_plant_identifier_provider() -> PlantIdentifierProvider:
    return GeminiPlantIdentifierProvider()

