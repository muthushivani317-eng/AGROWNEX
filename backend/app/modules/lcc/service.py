from __future__ import annotations

import base64
import binascii

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository
from app.modules.lcc.analyzer import MAX_IMAGE_BYTES, analyze_leaf_image
from app.modules.lcc.schemas import LccAnalysisOut, LccAnalyzeRequest


class LccService:
    def __init__(self, session: AsyncSession) -> None:
        self.farms = FarmRepository(session)

    async def analyze(self, user: User, payload: LccAnalyzeRequest) -> LccAnalysisOut:
        farm = await self.farms.get_for_user(payload.farm_id, user.id)
        if farm is None:
            raise FarmNotFoundError()
        try:
            image_bytes = base64.b64decode(payload.image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValidationError("Invalid image data.", error_code="lcc_invalid_image") from exc
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ValidationError("Image is too large.", error_code="lcc_image_too_large")

        result = analyze_leaf_image(image_bytes)
        crop = farm.crop.strip() if farm.crop else None
        crop_key = "rice" if crop and crop.lower() in {"rice", "paddy", "நெல்"} else "other"
        guidance_key = (
            f"lcc.guidance.retake.{result.quality_issue}"
            if result.abstained
            else f"lcc.guidance.{crop_key}.{result.nitrogen_status}"
        )
        return LccAnalysisOut(
            farm_id=farm.id,
            crop=crop,
            abstained=result.abstained,
            quality_issue=result.quality_issue,
            panel_number=result.panel_number,
            nitrogen_status=result.nitrogen_status,
            guidance_key=guidance_key,
            average_lab=result.average_lab,
            color_distance=result.color_distance,
            leaf_pixel_ratio=result.leaf_pixel_ratio,
            brightness=result.brightness,
            sharpness=result.sharpness,
        )
