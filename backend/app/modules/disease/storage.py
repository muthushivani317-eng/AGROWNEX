"""Object storage — Cloudflare R2 only, never AWS S3 (docs: Storage).

`ObjectStorage` is a small interface; the R2 client speaks the S3-compatible API
with a dependency-free SigV4 signer. Missing credentials fail closed. The mock
remains available only through explicit test/development opt-in.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.provider_policy import test_mocks_enabled
from app.modules.disease.constants import (
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET,
    R2_PUBLIC_BASE_URL,
    R2_REGION,
    R2_SECRET_ACCESS_KEY,
)

logger = get_logger("disease.storage")


class StorageError(AppError):
    status_code = 502
    error_code = "storage_failed"
    message = "Could not store the image. Please try again."


class StorageUnavailableError(AppError):
    status_code = 503
    error_code = "storage_provider_unavailable"
    message = "Image storage is unavailable. Please try again later."


class ObjectStorage(Protocol):
    async def put(self, *, key: str, data: bytes, content_type: str) -> str: ...


class MockStorage:
    """Deterministic storage fixture for explicit development/tests only."""

    base = "https://r2.mock.local"

    async def put(self, *, key: str, data: bytes, content_type: str) -> str:
        logger.info("mock storage put key=%s (%d bytes)", key, len(data))
        return f"{self.base}/{key}"


class UnavailableStorage:
    """Production-safe null provider that never fabricates an object URL."""

    async def put(self, *, key: str, data: bytes, content_type: str) -> str:
        raise StorageUnavailableError()


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


class R2Client:
    """Cloudflare R2 (S3-compatible) uploader with AWS SigV4 (no boto3)."""

    service = "s3"

    def __init__(
        self,
        *,
        account_id: str = R2_ACCOUNT_ID,
        access_key: str = R2_ACCESS_KEY_ID,
        secret_key: str = R2_SECRET_ACCESS_KEY,
        bucket: str = R2_BUCKET,
        region: str = R2_REGION,
        public_base_url: str = R2_PUBLIC_BASE_URL,
        timeout: float = 20.0,
    ) -> None:
        self.host = f"{account_id}.r2.cloudflarestorage.com"
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self.public_base_url = public_base_url.rstrip("/")
        self.timeout = timeout

    def _authorization(
        self, key: str, data: bytes, content_type: str, amz_date: str, stamp: str
    ) -> str:
        canonical_uri = "/" + quote(f"{self.bucket}/{key}", safe="/")
        payload_hash = hashlib.sha256(data).hexdigest()
        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{self.host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
        canonical_request = (
            f"PUT\n{canonical_uri}\n\n{canonical_headers}\n"
            f"{signed_headers}\n{payload_hash}"
        )
        scope = f"{stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = (
            "AWS4-HMAC-SHA256\n"
            f"{amz_date}\n{scope}\n"
            f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        )
        k_date = _sign(f"AWS4{self.secret_key}".encode(), stamp)
        k_region = _sign(k_date, self.region)
        k_service = _sign(k_region, self.service)
        k_signing = _sign(k_service, "aws4_request")
        signature = hmac.new(
            k_signing, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()
        return (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

    async def put(self, *, key: str, data: bytes, content_type: str) -> str:
        now = _dt.datetime.now(_dt.UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(data).hexdigest()
        headers = {
            "Content-Type": content_type,
            "Host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": self._authorization(
                key, data, content_type, amz_date, stamp
            ),
        }
        url = f"https://{self.host}/{quote(f'{self.bucket}/{key}', safe='/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(url, content=data, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("R2 upload failed: %s", exc)
            raise StorageError() from exc

        base = self.public_base_url or f"https://{self.host}/{self.bucket}"
        return f"{base}/{key}"


def get_default_storage() -> ObjectStorage:
    if R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
        logger.info("object storage: Cloudflare R2")
        return R2Client()
    if test_mocks_enabled():
        logger.info("object storage: explicit development/test mock")
        return MockStorage()
    logger.warning("object storage unavailable: R2 credentials are not configured")
    return UnavailableStorage()
