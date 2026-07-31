"""Fail-closed crop-domain authorization boundary.

User selection and disease-model confidence are not crop-identity evidence.
Until a verified crop-identification or crop-domain artifact is installed, no
crop-specific disease runtime may accept an image.
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class CropDomainDecision:
    verified: bool
    reason_code: str


class CropIdentityUncertainError(ValueError):
    reason_code = "CROP_IDENTITY_UNCERTAIN"


def assess_crop_domain(image: Image.Image, requested_crop_id: str) -> CropDomainDecision:
    """Return the only evidence-backed decision available in this repository."""
    del image, requested_crop_id
    return CropDomainDecision(False, CropIdentityUncertainError.reason_code)


def require_verified_crop_domain(image: Image.Image, requested_crop_id: str) -> None:
    decision = assess_crop_domain(image, requested_crop_id)
    if not decision.verified:
        raise CropIdentityUncertainError(decision.reason_code)
