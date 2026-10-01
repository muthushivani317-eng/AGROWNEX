"""Object storage — Cloudflare R2 only, never AWS S3 (docs: Storage).

`ObjectStorage` is a small interface; the R2 client speaks the S3-compatible API
with a dependency-free SigV4 signer. Missing credentials fail closed. The mock
remains available only through explicit test/development opt-in.
"""

from __future__ import annotations

import asyncio
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
    R2_PRIVATE_BUCKET,
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

    async def get(self, *, key: str) -> bytes: ...


class MockStorage:
    """Deterministic storage fixture for explicit development/tests only."""

    base = "https://r2.mock.local"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, *, key: str, data: bytes, content_type: str) -> str:
        logger.info("mock storage put key=%s (%d bytes)", key, len(data))
        self.objects[key] = data
        return f"{self.base}/{key}"

    async def get(self, *, key: str) -> bytes:
        try:
            return self.objects[key]
        except KeyError as exc:
            raise StorageError() from exc

    async def delete(self, *, key: str) -> None:
        self.objects.pop(key, None)


class UnavailableStorage:
    """Production-safe null provider that never fabricates an object URL."""

    async def put(self, *, key: str, data: bytes, content_type: str) -> str:
        raise StorageUnavailableError()

    async def get(self, *, key: str) -> bytes:
        raise StorageUnavailableError()

    async def delete(self, *, key: str) -> None:
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
        require_public_read: bool = True,
    ) -> None:
        self.host = f"{account_id}.r2.cloudflarestorage.com"
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self.public_base_url = public_base_url.rstrip("/")
        self.timeout = timeout
        self.require_public_read = require_public_read

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
            f"PUT\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
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
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
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
            "Authorization": self._authorization(key, data, content_type, amz_date, stamp),
        }
        url = f"https://{self.host}/{quote(f'{self.bucket}/{key}', safe='/')}"
        public_base = self.public_base_url or f"https://{self.host}/{self.bucket}"
        public_url = f"{public_base}/{key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(url, content=data, headers=headers)
                response.raise_for_status()
                # An authenticated PUT can succeed while the configured public
                # domain is wrong/private. Never persist an URL the app cannot read.
                # R2's public/CDN read path can briefly lag the write (2026-09-03:
                # observed a 404 ~1s after a 200 PUT) -- retry a few times before
                # concluding the URL is genuinely unreadable.
                if self.require_public_read:
                    public_response = await client.get(
                        public_url, headers={"Range": "bytes=0-0"}, follow_redirects=True
                    )
                    for attempt in range(2):
                        if public_response.status_code in {200, 206}:
                            break
                        await asyncio.sleep(0.3 * (attempt + 1))
                        public_response = await client.get(
                            public_url, headers={"Range": "bytes=0-0"}, follow_redirects=True
                        )
                    if public_response.status_code not in {200, 206}:
                        raise StorageError()
                    public_type = public_response.headers.get("content-type", "")
                    if public_type and public_type.split(";", 1)[0] != content_type:
                        raise StorageError()
        except httpx.HTTPError as exc:
            logger.warning("R2 upload failed: %s", exc)
            raise StorageError() from exc
        return public_url

    def _signed_empty_request(self, method: str, key: str) -> tuple[str, dict[str, str]]:
        """SigV4 headers for a body-less request (GET/DELETE) on ``key``."""
        now = _dt.datetime.now(_dt.UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(b"").hexdigest()
        canonical_uri = "/" + quote(f"{self.bucket}/{key}", safe="/")
        canonical_headers = (
            f"host:{self.host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        request = f"{method}\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        scope = f"{stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n{hashlib.sha256(request.encode()).hexdigest()}"
        )
        key_date = _sign(f"AWS4{self.secret_key}".encode(), stamp)
        key_region = _sign(key_date, self.region)
        key_service = _sign(key_region, self.service)
        signing_key = _sign(key_service, "aws4_request")
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        headers = {
            "Host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": (
                f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
                f"SignedHeaders={signed_headers}, Signature={signature}"
            ),
        }
        url = f"https://{self.host}/{quote(f'{self.bucket}/{key}', safe='/')}"
        return url, headers

    async def get(self, *, key: str) -> bytes:
        url, headers = self._signed_empty_request("GET", key)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as exc:
            raise StorageError() from exc

    async def delete(self, *, key: str) -> None:
        """Delete one object (idempotent: a missing key is not an error)."""
        url, headers = self._signed_empty_request("DELETE", key)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url, headers=headers)
                if response.status_code not in (200, 204, 404):
                    response.raise_for_status()
        except httpx.HTTPError as exc:
            raise StorageError() from exc


def get_default_storage() -> ObjectStorage:
    has_r2_credentials = bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY)
    has_public_url = R2_PUBLIC_BASE_URL.startswith("https://")
    if has_r2_credentials and has_public_url:
        logger.info("object storage: Cloudflare R2")
        return R2Client()
    if has_r2_credentials and not has_public_url:
        # The S3-compatible cloudflarestorage.com endpoint accepts authenticated
        # uploads but is not a public object URL. Returning it made Android render
        # an empty image frame. Fail closed until an R2 custom domain or r2.dev
        # public base URL is configured.
        logger.warning("object storage unavailable: R2_PUBLIC_BASE_URL must be a public HTTPS URL")
        return UnavailableStorage()
    if test_mocks_enabled():
        logger.info("object storage: explicit development/test mock")
        return MockStorage()
    logger.warning("object storage unavailable: R2 credentials are not configured")
    return UnavailableStorage()


def get_private_storage() -> ObjectStorage:
    """Use a separate non-public bucket; never fall back to the public bucket.

    Operators must disable r2.dev and custom-domain access on this bucket and
    migrate existing private objects before enabling this configuration.
    """
    if R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
        if not R2_PRIVATE_BUCKET or R2_PRIVATE_BUCKET == R2_BUCKET:
            logger.warning("private storage unavailable: separate private bucket required")
            return UnavailableStorage()
        return R2Client(
            account_id=R2_ACCOUNT_ID,
            access_key=R2_ACCESS_KEY_ID,
            secret_key=R2_SECRET_ACCESS_KEY,
            bucket=R2_PRIVATE_BUCKET,
            public_base_url="",
            require_public_read=False,
        )
    if test_mocks_enabled():
        return MockStorage()
    return UnavailableStorage()
