from __future__ import annotations

# Versioned notice artifacts are intentionally kept as exact single string literals.
# ruff: noqa: E501
import hashlib
from dataclasses import dataclass

NOTICE_VERSION = "2026-08-v1"
TEXTS = {
    (
        "optional_product_analytics",
        "en",
    ): "Allow AgrowAI to use optional feature activity to improve the product. Operational security and aggregate administration metrics are not controlled by this optional consent.",
    (
        "optional_product_analytics",
        "ta",
    ): "AgrowAI தயாரிப்பை மேம்படுத்த விருப்ப அம்சப் பயன்பாட்டைப் பயன்படுத்த அனுமதிக்கிறேன். செயல்பாட்டு பாதுகாப்பு மற்றும் தொகுக்கப்பட்ட நிர்வாக அளவீடுகள் இந்த விருப்ப ஒப்புதலால் கட்டுப்படுத்தப்படாது.",
    (
        "buyer_contact_sharing",
        "en",
    ): "Allow AgrowAI to share my name and phone number with a buyer only for a produce enquiry I accept.",
    (
        "buyer_contact_sharing",
        "ta",
    ): "நான் ஏற்றுக்கொள்ளும் விளைபொருள் விசாரணைக்காக மட்டும் எனது பெயர் மற்றும் தொலைபேசி எண்ணை வாங்குபவருடன் பகிர AgrowAI-ஐ அனுமதிக்கிறேன்.",
    (
        "marketing",
        "en",
    ): "Allow AgrowAI to send optional marketing messages about relevant products and services.",
    (
        "marketing",
        "ta",
    ): "தொடர்புடைய தயாரிப்புகள் மற்றும் சேவைகள் குறித்த விருப்ப சந்தைப்படுத்தல் செய்திகளை அனுப்ப AgrowAI-ஐ அனுமதிக்கிறேன்.",
    (
        "precise_location",
        "en",
    ): "Allow AgrowAI to use my farm's precise location for location-specific optional services.",
    (
        "precise_location",
        "ta",
    ): "இடம் சார்ந்த விருப்ப சேவைகளுக்காக எனது பண்ணையின் துல்லியமான இருப்பிடத்தைப் பயன்படுத்த AgrowAI-ஐ அனுமதிக்கிறேன்.",
}


@dataclass(frozen=True)
class Notice:
    version: str
    locale: str
    text: str
    sha256: str


def resolve_notice(purpose: str, locale: str, version: str) -> Notice:
    text = TEXTS.get((purpose, locale))
    if version != NOTICE_VERSION or text is None:
        raise ValueError("NOTICE_NOT_SUPPORTED")
    return Notice(version, locale, text, hashlib.sha256(text.encode("utf-8")).hexdigest())
