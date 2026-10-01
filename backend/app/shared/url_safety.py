"""Client-supplied link validation.

Links typed or uploaded by farmers/suppliers are later shown to staff and
other farmers as "Open" buttons. Only plain ``https://`` URLs are accepted:
no ``javascript:``, ``intent:``, ``file:``, ``data:`` or credentials-in-URL
tricks.
"""
from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator


def require_https_url(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or any(ch.isspace() or ord(ch) < 32 for ch in value)
    ):
        raise ValueError("must be an https:// link")
    return value


HttpsUrl = Annotated[str, AfterValidator(require_https_url)]
