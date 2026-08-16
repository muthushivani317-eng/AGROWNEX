from __future__ import annotations

import asyncio
import base64
from typing import Any, Protocol

import httpx

from app.core.http import get_http_client
from app.modules.ai.constants import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MAX_RETRIES,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_VISION_MODEL,
)

from .prompt import SYSTEM_PROMPT, USER_PROMPT
from .schemas import GeminiCropIdentification


class CropIdentificationProviderError(RuntimeError):
    pass


class CropIdentificationProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    async def identify(self, image: bytes, mime_type: str) -> str: ...


class GeminiCropIdentificationProvider:
    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_VISION_MODEL,
        base_url: str = GEMINI_BASE_URL,
        timeout: float = GEMINI_TIMEOUT_SECONDS,
        max_retries: int = GEMINI_MAX_RETRIES,
    ) -> None:
        if not api_key or not model:
            raise CropIdentificationProviderError("GEMINI_CONFIGURATION_MISSING")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max(0, min(max_retries, 3))

    @property
    def model_name(self) -> str:
        return self._model

    async def identify(self, image: bytes, mime_type: str) -> str:
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": USER_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image).decode("ascii"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": GeminiCropIdentification.model_json_schema(),
                "maxOutputTokens": 500,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        url = f"{self._base_url}/models/{self._model}:generateContent"
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await get_http_client().post(
                    url, params={"key": self._api_key}, json=body, timeout=self._timeout
                )
                if response.status_code == 429:
                    raise CropIdentificationProviderError("GEMINI_RATE_LIMITED")
                response.raise_for_status()
                parts = response.json()["candidates"][0]["content"]["parts"]
                return "".join(part.get("text", "") for part in parts)
            except CropIdentificationProviderError as exc:
                last_error = exc
            except httpx.TimeoutException as exc:
                last_error = CropIdentificationProviderError("GEMINI_TIMEOUT")
                last_error.__cause__ = exc
            except (httpx.HTTPError, TimeoutError, KeyError, IndexError, TypeError) as exc:
                last_error = CropIdentificationProviderError("GEMINI_REQUEST_FAILED")
                last_error.__cause__ = exc
            if attempt < self._max_retries:
                await asyncio.sleep(0.2 * (2**attempt))
        assert last_error is not None
        raise last_error


def get_crop_identification_provider() -> CropIdentificationProvider:
    return GeminiCropIdentificationProvider()
