"""Response safety validator (docs/AI_PROMPTS.md → SAFETY, RESPONSE VALIDATOR).

Deterministic post-processing of the model output. Content-level safety is
enforced primarily by the system prompt; this guards against empty/oversized
output and provides a safe, uncertainty-honest fallback. Pure — unit-tested.
"""
from __future__ import annotations

from app.modules.ai.constants import MAX_RESPONSE_CHARS

_FALLBACK = {
    "ta": (
        "மன்னிக்கவும், இப்போது என்னால் தெளிவான பதில் தர முடியவில்லை. "
        "தயவுசெய்து உங்கள் உள்ளூர் வேளாண் அலுவலரை அணுகவும்."
    ),
    "en": (
        "Sorry, I could not give a clear answer right now. "
        "Please consult your local agriculture officer."
    ),
}


def validate_response(text: str | None, language: str) -> str:
    """Return safe, trimmed response text (or a language-appropriate fallback)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return _FALLBACK.get(language, _FALLBACK["en"])
    if len(cleaned) > MAX_RESPONSE_CHARS:
        cleaned = cleaned[:MAX_RESPONSE_CHARS].rstrip()
    return cleaned
