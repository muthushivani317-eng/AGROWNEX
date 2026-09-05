"""Layer 4 copy generation -- turns a ranked EvidenceSignal into the exact
Tamil strings a farmer sees. Kept separate from ranking_engine.py (which
never touches language) and models.py (which only stores the already-
rendered result), so one native-speaker review pass covers every
farmer-facing string in the feature.

Every template below follows the guardrail list from the design brief:
cautious verbs only, no technical terms, no exact quantities, no cause
attribution, no definitive flood language.
"""
from __future__ import annotations

from app.modules.daily_task.constants import TaskType, Urgency
from app.modules.daily_task.schemas import EvidenceSignal

_TITLE_TA = "இன்றைய பண்ணை செயல்"
_TITLE_TA_URGENT = "இன்றைய பண்ணை செயல் — அவசரம்"

_URGENCY_TA = {
    Urgency.TODAY: "இன்று",
    Urgency.WITHIN_48H: "48 மணி நேரத்திற்குள்",
    Urgency.BEFORE_RAIN: "மழைக்கு முன்",
    Urgency.THIS_WEEK: "இந்த வாரம்",
}

_ZONE_LABEL_TA = {
    "north": "வடக்கு", "south": "தெற்கு", "east": "கிழக்கு", "west": "மேற்கு",
    "north_east": "வடகிழக்கு", "north_west": "வடமேற்கு",
    "south_east": "தென்கிழக்கு", "south_west": "தென்மேற்கு", "centre": "நடுப்பகுதி",
}

_WHY_TA_SATELLITE_WEATHER = (
    "செயற்கைக்கோள் மற்றும் வானிலை தகவலின்படி இந்த பரிந்துரை தரப்பட்டுள்ளது. "
    "இது ஒரு பரிசோதனை நினைவூட்டல் மட்டுமே."
)
_WHY_TA_CALENDAR = (
    "உங்கள் பயிர் நாட்காட்டி மற்றும் செயற்கைக்கோள் தகவலின்படி இந்த பரிந்துரை தரப்பட்டுள்ளது."
)


class TaskCopy:
    __slots__ = ("title_ta", "task_text_ta", "reason_text_ta", "why_am_i_seeing_this_ta", "urgency")

    def __init__(self, title_ta: str, task_text_ta: str, reason_text_ta: str, why_ta: str, urgency: Urgency) -> None:
        self.title_ta = title_ta
        self.task_text_ta = task_text_ta
        self.reason_text_ta = reason_text_ta
        self.why_am_i_seeing_this_ta = why_ta
        self.urgency = urgency


def render_task_copy(signal: EvidenceSignal) -> TaskCopy:
    task_type = signal.recommended_task_type

    if task_type == TaskType.IRRIGATION_INSPECTION:
        return TaskCopy(
            title_ta=_TITLE_TA,
            task_text_ta="இந்த வயலின் நீர்ப்பாசனத்தை இன்று பாருங்கள்.",
            reason_text_ta="மற்ற பகுதிகளை விட இந்த வயல் பகுதி விரைவாக வறண்டு வருகிறது.",
            why_ta=_WHY_TA_SATELLITE_WEATHER,
            urgency=signal.urgency,
        )

    if task_type == TaskType.UNEVEN_GROWTH_INSPECTION:
        zone_key = signal.evidence_summary.get("zone_label", "centre")
        zone_ta = _ZONE_LABEL_TA.get(zone_key, "ஒரு")
        return TaskCopy(
            title_ta=_TITLE_TA,
            task_text_ta=f"{zone_ta} பகுதியை உரம்/மருந்து இடுவதற்கு முன் பாருங்கள்.",
            reason_text_ta="மற்ற பகுதிகளை விட இந்த பகுதியின் பயிர் வளர்ச்சி குறைவாக உள்ளது.",
            why_ta=_WHY_TA_SATELLITE_WEATHER,
            urgency=signal.urgency,
        )

    if task_type == TaskType.DRAINAGE_INSPECTION:
        return TaskCopy(
            title_ta=_TITLE_TA_URGENT,
            task_text_ta="வடிகால் வசதியை இன்றே சரிபார்க்கவும்.",
            reason_text_ta="கனமழையால் வடிகால் பாதிக்கப்பட்டிருக்கலாம்.",
            why_ta=_WHY_TA_SATELLITE_WEATHER,
            urgency=signal.urgency,
        )

    if task_type == TaskType.SOWING_GERMINATION_CHECK:
        return TaskCopy(
            title_ta=_TITLE_TA,
            task_text_ta="விதை முளைப்பை இன்று சரிபார்க்கவும்.",
            reason_text_ta="எதிர்பார்த்த நேரத்தில் பயிர் வளர்ச்சி தொடங்கவில்லை.",
            why_ta=_WHY_TA_CALENDAR,
            urgency=signal.urgency,
        )

    # Defensive default -- unreachable given the feature-flag gate in
    # ranking_engine.py, but a generic, still-guardrail-safe fallback beats
    # a KeyError reaching a farmer.
    return TaskCopy(
        title_ta=_TITLE_TA,
        task_text_ta="இந்த வயலை பரிசோதிக்கவும்.",
        reason_text_ta="உங்கள் வயலில் கவனிக்க வேண்டிய ஒன்று உள்ளது.",
        why_ta=_WHY_TA_SATELLITE_WEATHER,
        urgency=signal.urgency,
    )


# --------------------------------------------------------------------------- #
# Shared microcopy -- served by mobile via a small bundled constants file
# (see `agrow-ai/features/dailyFarmTask/copy.ta.ts`), never regenerated per
# task since it never varies by signal.
# --------------------------------------------------------------------------- #
SHARED_COPY_TA = {
    "buttons": {
        "done": "சரிபார்த்தேன்",
        "problem_found": "பிரச்சனை உள்ளது",
        "no_issue": "பிரச்சனை இல்லை",
        "need_help": "உதவி வேண்டும்",
    },
    "voice_note_prompt": "10 வினாடி குரல் குறிப்பை பதிவு செய்யுங்கள்.",
    "help_request_confirmation": "உங்கள் கோரிக்கை பண்ணை உதவியாளருக்கு அனுப்பப்பட்டது. விரைவில் தொடர்பு கொள்ளப்படும்.",
    "verification_followup": "பிரச்சனை உண்மையானதா? நடவடிக்கை எடுத்தீர்களா? இப்போது உதவி தேவையா?",
    "empty_state": "இன்று உங்கள் வயலுக்கு புதிய பணி இல்லை. நல்ல நாள்!",
}
