"""Server-only Google Cloud Speech-to-Text V1 adapter for Groundnut symptoms."""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any

import httpx

from app.core.config import settings

_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_ENDPOINT = "https://speech.googleapis.com/v1/speech:recognize"
_ENCODING = {
    "audio/amr": "AMR",
    "audio/mpeg": "MP3",
    "audio/ogg": "OGG_OPUS",
    "audio/webm": "WEBM_OPUS",
}


class GroundnutSpeechError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class GroundnutSpeechService:
    def _credentials(self):
        if not settings.groundnut_stt_enabled:
            raise GroundnutSpeechError("GROUNDNUT_STT_UNCONFIGURED")
        try:
            import google.auth
            from google.oauth2 import service_account
        except ImportError as exc:
            raise GroundnutSpeechError("GROUNDNUT_STT_UNAVAILABLE") from exc

        raw = settings.google_cloud_stt_credentials_json.strip()
        adc_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if raw:
            try:
                info = json.loads(raw)
                return service_account.Credentials.from_service_account_info(
                    info, scopes=[_SCOPE]
                )
            except (TypeError, ValueError, KeyError) as exc:
                raise GroundnutSpeechError("GROUNDNUT_STT_UNCONFIGURED") from exc
        if not adc_path:
            raise GroundnutSpeechError("GROUNDNUT_STT_UNCONFIGURED")
        try:
            credentials, _ = google.auth.default(scopes=[_SCOPE])
            return credentials
        except Exception as exc:
            raise GroundnutSpeechError("GROUNDNUT_STT_UNCONFIGURED") from exc

    async def transcribe(self, audio: bytes, *, content_type: str, language: str) -> str:
        credentials = self._credentials()
        try:
            from google.auth.transport.requests import Request

            await asyncio.to_thread(credentials.refresh, Request())
            config: dict[str, Any] = {
                "languageCode": language,
                "model": "latest_short",
                "enableAutomaticPunctuation": True,
            }
            encoding = _ENCODING.get(content_type)
            if encoding:
                config["encoding"] = encoding
            async with httpx.AsyncClient(timeout=settings.groundnut_stt_timeout_seconds) as client:
                response = await client.post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {credentials.token}"},
                    json={
                        "config": config,
                        "audio": {"content": base64.b64encode(audio).decode("ascii")},
                    },
                )
            response.raise_for_status()
            body = response.json()
        except GroundnutSpeechError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise GroundnutSpeechError("GROUNDNUT_STT_UNAVAILABLE") from exc

        transcripts = [
            str(result["alternatives"][0]["transcript"]).strip()
            for result in body.get("results", [])
            if result.get("alternatives") and result["alternatives"][0].get("transcript")
        ]
        transcript = " ".join(part for part in transcripts if part).strip()
        if not transcript:
            raise GroundnutSpeechError("GROUNDNUT_STT_NO_SPEECH")
        return transcript[:4000]


_service = GroundnutSpeechService()


def get_groundnut_speech_service() -> GroundnutSpeechService:
    return _service
