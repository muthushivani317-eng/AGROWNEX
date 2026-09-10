"""Layer 5 -- Evidence Pack generator.

Assembles an `EvidencePackContent` from data AgrowAI already has (satellite
pre/post-event history, weather rainfall context, farmer photos/voice notes)
plus whatever the farmer submits. Two hard requirements drive every design
choice here:

  1. Must work even when a rendered/PDF export is unavailable -- the pack
     degrades to a text/data-only record (still fully readable in the app),
     never fails outright. This mirrors the same fails-closed pattern the
     satellite module itself uses for image rendering.
  2. Must never say more than the underlying signals support -- the mandatory
     disclaimer and cautious standing-water wording are baked into
     `schemas.EvidencePackContent` itself, not left to an editable template.

Known integration limitation (documented, not silently swallowed): no
Tamil-capable font file exists anywhere in this repo (checked
`agrow-ai/assets/fonts/` -- only `SpaceMono-Regular.ttf`, Latin-only). The
in-app pack view renders the full Tamil content correctly (it uses the
device's own system font, like the rest of the app); the PDF export uses
reportlab's built-in Helvetica, which cannot shape Tamil glyphs, so the PDF
is generated in English only from `EvidencePackContent`'s English fields.
Bundling a Noto Sans Tamil TTF and registering it with reportlab would
remove this limitation without any other code change -- see the delivery
report's "Remaining risks" section.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

from app.modules.auth.models import User
from app.modules.daily_task.constants import EvidencePackConfidence, EvidencePackStatus
from app.modules.daily_task.models import EvidencePack
from app.modules.daily_task.repository import DailyTaskRepository
from app.modules.daily_task.schemas import EvidencePackContent, EvidencePackTriggerRequest
from app.modules.disease.storage import ObjectStorage, StorageError, StorageUnavailableError
from app.modules.farms.models import Farm
from app.modules.satellite.service import SatelliteService
from app.modules.weather.service import WeatherService

_VEGETATION_TA = {
    "excellent": "மிகச் சிறந்தது",
    "good": "நல்லது",
    "moderate": "நடுத்தரமானது",
    "poor": "பலவீனமானது",
    "unknown": "கிடைக்கவில்லை",
}


class EvidencePackService:
    def __init__(
        self,
        repo: DailyTaskRepository,
        satellite_service: SatelliteService,
        weather_service: WeatherService,
        storage: ObjectStorage,
    ) -> None:
        self._repo = repo
        self._satellite = satellite_service
        self._weather = weather_service
        self._storage = storage

    async def generate(
        self, user: User, farm: Farm, request: EvidencePackTriggerRequest
    ) -> EvidencePack:
        pre_row, post_row = await self._surrounding_history_rows(
            user, farm.id, request.event_date_start
        )

        pre_trend_ta = self._trend_summary_ta(pre_row, "before")
        post_trend_ta = self._trend_summary_ta(post_row, "after") if post_row else None

        standing_water_ta = None
        if request.event_type in ("heavy_rain", "cyclone"):
            assessment = await self._satellite.latest_waterlogging(user, farm.id)
            if assessment is not None and assessment.decision not in (
                None,
                "insufficient_data",
                "clear",
            ):
                # Cautious wording ONLY -- see schemas.EvidencePackContent
                # docstring. Never rendered as a flood confirmation.
                standing_water_ta = (
                    "சாத்தியமான தண்ணீர் தேக்க மாற்றம் கண்டறியப்பட்டது. இது இறுதி வெள்ள உறுதிப்படுத்தல் அல்ல."
                )

        rain_context_ta = await self._weather_context_ta(user, farm.id, request.event_date_start)

        confidence = self._compute_confidence(pre_row, post_row)
        status = (
            EvidencePackStatus.READY
            if post_row is not None or request.event_date_end is not None
            else EvidencePackStatus.PENDING_POST_EVENT_DATA
        )

        boundary = getattr(farm, "boundary", None)
        content = EvidencePackContent(
            farmer_name=farm.name or "விவசாயி",
            farm_id=farm.id,
            field_polygon_geojson=boundary.geojson if boundary else None,
            event_type=request.event_type,
            event_date_start=request.event_date_start,
            event_date_end=request.event_date_end,
            pre_event_scan_date=(
                datetime.combine(pre_row.capture_date, datetime.min.time(), tzinfo=UTC)
                if pre_row and pre_row.capture_date
                else None
            ),
            post_event_scan_date=(
                datetime.combine(post_row.capture_date, datetime.min.time(), tzinfo=UTC)
                if post_row and post_row.capture_date
                else None
            ),
            pre_event_trend_summary_ta=pre_trend_ta,
            post_event_trend_summary_ta=post_trend_ta
            or "அடுத்த கிடைக்கக்கூடிய செயற்கைக்கோள் தகவலுக்காக காத்திருக்கிறது.",
            standing_water_note_ta=standing_water_ta,
            weather_context_ta=rain_context_ta,
            farmer_photo_object_ids=[],
            farmer_voice_note_object_ids=[],
            confidence_level=confidence,
        )

        pdf_url, degraded_reason = await self._render_and_store_pdf(content)

        pack = await self._repo.create_evidence_pack(
            id=uuid.uuid4(),
            farm_id=farm.id,
            user_id=farm.user_id,
            event_type=request.event_type,
            event_date_start=request.event_date_start,
            event_date_end=request.event_date_end,
            confidence_level=confidence.value,
            # See module docstring: rendered-image lookup is not wired at MVP.
            has_pre_event_imagery=False,
            has_post_event_imagery=False,
            imagery_degraded_reason=degraded_reason,
            content=content.model_dump(mode="json"),
            pdf_object_url=pdf_url,
            status=status.value,
            version=1,
        )
        return pack

    async def attach_farmer_media(
        self, pack: EvidencePack, *, photo_object_id: str | None, voice_note_object_id: str | None
    ) -> EvidencePack:
        content = EvidencePackContent.model_validate(pack.content)
        if photo_object_id:
            content.farmer_photo_object_ids.append(photo_object_id)
        if voice_note_object_id:
            content.farmer_voice_note_object_ids.append(voice_note_object_id)
        await self._repo.update_evidence_pack_content(
            pack.id, content=content.model_dump(mode="json")
        )
        return pack

    # ------------------------------------------------------------------ #
    async def _surrounding_history_rows(self, user: User, farm_id, event_start: datetime):
        """Finds the closest satellite history rows before/after the event
        date, reusing `SatelliteService.history()` (paginated, newest first)
        rather than adding a new satellite-module query method.
        """
        page = await self._satellite.history(user, farm_id, page=1, page_size=50)
        rows = sorted(
            [r for r in page.items if r.capture_date is not None],
            key=lambda r: r.capture_date,
        )
        event_date = event_start.date()
        pre_row = None
        post_row = None
        for row in rows:
            if row.capture_date <= event_date:
                pre_row = row
            elif post_row is None:
                post_row = row
        return pre_row, post_row

    def _trend_summary_ta(self, row, phase: str) -> str:
        if row is None:
            return "இந்த காலகட்டத்திற்கு செயற்கைக்கோள் தகவல் கிடைக்கவில்லை."
        health = _VEGETATION_TA.get(row.vegetation_health or "unknown", "கிடைக்கவில்லை")
        return f"பயிர் ஆரோக்கிய நிலை: {health}."

    async def _weather_context_ta(self, user: User, farm_id, start: datetime) -> str:
        try:
            bundle = await self._weather.get_by_farm(user, farm_id)
        except Exception:  # noqa: BLE001 -- weather context is best-effort, never blocking
            bundle = None
        if not bundle or not bundle.daily:
            return "இந்த காலகட்டத்திற்கான வானிலை தகவல் கிடைக்கவில்லை."
        target = start.date().isoformat()
        for point in bundle.daily:
            if point.date == target and point.precipitation_sum_mm is not None:
                return f"இந்த நாளில் பதிவான மழையளவு: {point.precipitation_sum_mm:.0f} மி.மீ."
        return "இந்த காலகட்டத்திற்கான வானிலை தகவல் கிடைக்கவில்லை."

    def _compute_confidence(self, pre_row, post_row) -> EvidencePackConfidence:
        if pre_row and post_row:
            return EvidencePackConfidence.MEDIUM
        if pre_row or post_row:
            return EvidencePackConfidence.LIMITED
        return EvidencePackConfidence.LIMITED

    async def _render_and_store_pdf(
        self, content: EvidencePackContent
    ) -> tuple[str | None, str | None]:
        """Returns (pdf_url, degraded_reason). Never raises -- any render or
        upload failure degrades the pack to text/data-only, per the module
        docstring's requirement #1.
        """
        from app.core.config import settings

        if not settings.evidence_pack_pdf_enabled:
            return None, "pdf_export_disabled"
        try:
            pdf_bytes = render_evidence_pack_pdf(content)
            filename = f"{content.event_date_start.date()}-{uuid.uuid4().hex[:8]}.pdf"
            key = f"evidence_pack/{content.farm_id}/{filename}"
            url = await self._storage.put(key=key, data=pdf_bytes, content_type="application/pdf")
            return url, None
        except (StorageError, StorageUnavailableError):
            return None, "storage_unavailable"
        except Exception:  # noqa: BLE001 -- any other render failure degrades, never propagates
            return None, "render_failed"


def render_evidence_pack_pdf(content: EvidencePackContent) -> bytes:
    """Renders an English-language summary PDF using reportlab (already an
    app dependency, see requirements.txt -- no new dependency added). English
    only: see the module docstring for why Tamil text cannot currently be
    shaped in the PDF (no Tamil-capable font file exists in the repo). The
    in-app pack view (mobile) always shows the full Tamil content regardless
    of whether a PDF was generated.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 20 * mm
    y = height - 20 * mm

    def line(text: str, *, size: int = 11, gap: float = 7 * mm, bold: bool = False) -> None:
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(left, y, text[:110])
        y -= gap

    line("AgrowAI -- Field Evidence Pack", size=16, bold=True, gap=10 * mm)
    line(f"Farm: {content.farmer_name}")
    event_date = content.event_date_start.date().isoformat()
    line(f"Event type: {content.event_type}   Event date: {event_date}")
    line(f"Confidence: {content.confidence_level.value}")
    y -= 4 * mm
    line("Before the event:", bold=True)
    pre_scan_date = (
        content.pre_event_scan_date.date().isoformat()
        if content.pre_event_scan_date
        else "not available"
    )
    line(f"Scan date: {pre_scan_date}")
    y -= 4 * mm
    line("After the event:", bold=True)
    post_scan_date = (
        content.post_event_scan_date.date().isoformat()
        if content.post_event_scan_date
        else "not available"
    )
    line(f"Scan date: {post_scan_date}")
    if content.standing_water_note_ta:
        y -= 4 * mm
        line("Note: a possible standing-water change was detected near this date.", bold=True)
        line("This is NOT a final flood confirmation.")
    y -= 6 * mm
    line("Disclaimer:", bold=True)
    for chunk in _wrap(content.disclaimer_en, 95):
        line(chunk, size=9)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
