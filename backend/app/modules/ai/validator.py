"""Response safety validator (docs/AI_PROMPTS.md → SAFETY, RESPONSE VALIDATOR).

Deterministic post-processing of the model output. Content-level safety is
enforced primarily by the system prompt (GLOBAL_SYSTEM_PROMPT's "Safety rules
(never break these)" in prompts.py); this module is the server-side layer that
doesn't depend on the model actually following those instructions every time.

Previously this only guarded against empty/oversized output (2026-08
pre-release audit: raw Gemini output otherwise reached the farmer with no
verification at all that it honored its own safety rules). It now also
deterministically screens for violations of the two hardest promises in the
system prompt -- a guaranteed-yield claim, or advice to exceed label dosage /
skip protective equipment -- and replaces the response with the existing
safe, uncertainty-honest fallback if either is found.

This is intentionally narrow and best-effort, not exhaustive: pattern
matching over free-form model text has low recall by nature (it only catches
phrasing close to what's listed below) and doesn't attempt to validate
specific pesticide/chemical names, which would need a maintained,
authoritative source rather than a hardcoded list here. It is a defense-in-
depth layer, not a replacement for the system prompt. Pure — unit-tested.
"""
from __future__ import annotations

import re

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

# Bilingual, deterministic red flags for the two GLOBAL_SYSTEM_PROMPT safety
# rules most likely to cause real-world harm if the model ever drifts from
# them: a guaranteed-yield/profit claim, or advice to exceed the recommended
# pesticide dose or skip protective equipment.
_UNSAFE_PATTERNS: list[re.Pattern[str]] = [
    # "guarantee(d) ... yield/harvest/profit" / "100% yield increase" (English).
    re.compile(r"\bguarantee[sd]?\b[^.\n]{0,40}\b(yield|harvest|profit)\b", re.IGNORECASE),
    re.compile(
        r"\b(100%|hundred\s*percent)[^.\n]{0,30}"
        r"\b(yield|harvest|profit)\s*(increase|boost)?\b",
        re.IGNORECASE,
    ),
    # "exceed / more than / double the recommended / label dose" (English).
    re.compile(
        r"\b(exceed|more than|double|triple)\b[^.\n]{0,40}\b(recommended|label)\b[^.\n]{0,20}\bdos",
        re.IGNORECASE,
    ),
    # "no need for protective gear / mask / gloves" (English).
    re.compile(
        r"\bno need\b[^.\n]{0,30}\b(protective|safety)\b"
        r"[^.\n]{0,20}\b(gear|equipment|mask|gloves)\b",
        re.IGNORECASE,
    ),
    # விளைச்சல்/லாபம் ... உறுதி/உத்தரவாதம் -- guaranteed yield/profit (Tamil).
    # Word stems here deliberately drop the trailing pulli consonant (ல், ம்)
    # so this still matches case-inflected forms (e.g. விளைச்சலுக்கு), where
    # Tamil sandhi replaces the bare pulli with the case suffix.
    re.compile(r"(விளைச்சல|லாப)[^.\n]{0,20}(உறுதி|உத்தரவாதம்)"),
    # பரிந்துரைக்கப்பட்ட அளவை மீறி / இரட்டிப்பு -- exceed/double the recommended dose (Tamil).
    re.compile(r"பரிந்துரைக்கப்பட்ட[^.\n]{0,15}அளவை[^.\n]{0,15}(மீறி|இரட்டிப்பு)"),
]


def contains_unsafe_advice(text: str) -> bool:
    """True if `text` matches one of the deterministic safety red flags above."""
    return any(pattern.search(text) for pattern in _UNSAFE_PATTERNS)


def validate_response(text: str | None, language: str) -> str:
    """Return safe, trimmed response text (or a language-appropriate fallback)."""
    cleaned = (text or "").strip()
    if not cleaned or contains_unsafe_advice(cleaned):
        return _FALLBACK.get(language, _FALLBACK["en"])
    if len(cleaned) > MAX_RESPONSE_CHARS:
        cleaned = cleaned[:MAX_RESPONSE_CHARS].rstrip()
    return cleaned
