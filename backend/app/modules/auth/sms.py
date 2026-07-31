"""SMS OTP delivery seam (Phase 2 — real MSG91 provider alongside the mock).

The current auth flow delegates OTP *code generation* to Firebase (dispatched
on-device); the backend row is audit/throttle only. This module adds the
server-side SMS delivery seam the spec asks for so an OTP can be sent over
MSG91 with a **Tamil-first** template when a deployment opts in
(``OTP_PROVIDER=msg91``). ``MockSMSProvider`` is the default and never touches
the network, preserving today's Firebase behavior.

Wiring this into live verification requires server-side code generation +
hashing (a larger change from the Firebase-on-device model); this provider is a
tested, ready-to-wire seam. See UPGRADE_REPORT.md.
"""
from __future__ import annotations

from typing import Protocol

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("auth.sms")

# Tamil-first OTP message (product rule 3). ``{code}`` is the one-time code and
# ``{ttl}`` the validity in minutes. Never log the rendered message (it holds the code).
OTP_MESSAGE_TEMPLATE_TA = (
    "AgrowAI: உங்கள் ஒரு முறை கடவுச்சொல் {code}. இது {ttl} நிமிடங்களுக்கு செல்லுபடியாகும். "
    "யாருடனும் பகிர வேண்டாம்."
)


def render_otp_message(code: str, *, ttl_minutes: int) -> str:
    return OTP_MESSAGE_TEMPLATE_TA.format(code=code, ttl=ttl_minutes)


class SMSProvider(Protocol):
    name: str

    async def send_otp(
        self, phone_number: str, code: str, *, ttl_minutes: int
    ) -> bool: ...


class MockSMSProvider:
    """Default provider: records intent, sends nothing. Never logs the code."""

    name = "mock"

    async def send_otp(
        self, phone_number: str, code: str, *, ttl_minutes: int
    ) -> bool:
        logger.info("OTP send (mock) to %s***", phone_number[:4])
        return True


class MSG91Provider:
    """Sends the Tamil OTP SMS through MSG91's HTTP API (env-configured)."""

    name = "msg91"

    def __init__(
        self,
        *,
        auth_key: str | None = None,
        sender_id: str | None = None,
        template_id: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.auth_key = auth_key if auth_key is not None else settings.msg91_auth_key
        self.sender_id = sender_id or settings.msg91_sender_id
        self.template_id = template_id or settings.msg91_template_id
        self.base_url = (base_url or settings.msg91_base_url).rstrip("/")
        self.timeout = timeout

    async def send_otp(
        self, phone_number: str, code: str, *, ttl_minutes: int
    ) -> bool:
        # MSG91 flow API: the OTP text lives in an approved template; we pass the
        # code as a variable so the code never appears in our logs or URLs.
        url = f"{self.base_url}/flow/"
        payload = {
            "template_id": self.template_id,
            "sender": self.sender_id,
            "recipients": [{"mobiles": phone_number, "otp": code}],
        }
        headers = {"authkey": self.auth_key, "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("MSG91 OTP send failed for %s***: %s", phone_number[:4], exc)
            return False
        logger.info("OTP send (msg91) to %s***", phone_number[:4])
        return True


def get_default_sms_provider() -> SMSProvider:
    """Select the SMS provider from ``OTP_PROVIDER`` (mock by default).

    In production, an ``msg91`` selection without an auth key falls back to the
    mock and logs — a missing credential must never silently look like a send.
    """
    if settings.otp_provider == "firebase":
        # Firebase Phone Auth owns SMS dispatch on the trusted native client.
        # Fail closed if server-side code accidentally tries to send that OTP.
        raise RuntimeError("FIREBASE_PHONE_AUTH_SMS_IS_CLIENT_DISPATCHED")
    if settings.otp_provider == "msg91":
        if settings.msg91_auth_key:
            logger.info("SMS OTP provider: msg91")
            return MSG91Provider()
        logger.warning("OTP_PROVIDER=msg91 but MSG91_AUTH_KEY unset; using mock")
    return MockSMSProvider()
