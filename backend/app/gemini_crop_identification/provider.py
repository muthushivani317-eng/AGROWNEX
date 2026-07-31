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


class CropIdentificationProviderError(RuntimeError):
    pass


class CropIdentificationProvider(Protocol):
    async def identify(self, image: bytes, mime_type: str) -> str: ...


class GeminiCropIdentificationProvider:
    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_VISION_MODEL,
        base_url: str = GEMINI_BASE_URL,
        timeout: float = GEMINI_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key or not model:
            raise CropIdentificationProviderError("GEMINI_CONFIGURATION_MISSING")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def identify(self, image: bytes, mime_type: str) -> str:
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": USER_PROMPT},
                    {"inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image).decode("ascii"),
                    }},
                ],
            }],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 500,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        url = f"{self._base_url}/models/{self._model}:generateContent"
        try:
            response = await get_http_client().post(
                url, params={"key": self._api_key}, json=body, timeout=self._timeout
            )
            response.raise_for_status()
            parts = response.json()["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (httpx.HTTPError, TimeoutError, KeyError, IndexError, TypeError) as exc:
            raise CropIdentificationProviderError("GEMINI_REQUEST_FAILED") from exc


def get_crop_identification_provider() -> CropIdentificationProvider:
    return GeminiCropIdentificationProvider()
