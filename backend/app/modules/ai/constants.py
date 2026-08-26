"""AI module constants (docs/AI_PROMPTS.md, docs/AI_DECISION_MATRIX.md)."""
from __future__ import annotations

import os
from enum import StrEnum

# --- Provider (finalized stack: Google Gemini) ---
# Per-task model routing (docs/AI_DECISION_MATRIX.md): expensive Pro for vision/OCR,
# cheaper Flash for conversational chat. Everything env-configured with sane defaults —
# never hardcoded at the call site.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Kept for backward compatibility; the vision model is the historical default.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", GEMINI_MODEL)
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
)
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
GEMINI_TEMPERATURE = 0.4
GEMINI_MAX_OUTPUT_TOKENS = 800

# Explicit per-category safety thresholds sent with every generateContent call
# (2026-08 pre-release audit: previously unset, so every chat silently relied
# on Gemini's undocumented default thresholds instead of an explicit,
# reviewable choice). BLOCK_MEDIUM_AND_ABOVE blocks medium/high-probability
# harmful content while still allowing ordinary agricultural discussion
# (pesticide names, pest/disease descriptions) through.
GEMINI_SAFETY_SETTINGS: list[dict[str, str]] = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Cost control (docs: cost table in constants, env-overridable) ---
# Estimated price in INR per 1,000 tokens. Defaults are conservative approximations of
# Google's published USD list prices at ~₹85/USD; override per deployment via env so the
# admin cost dashboard reflects the real contract without a code change.
def _price(env: str, default: str) -> float:
    return float(os.getenv(env, default))


MODEL_COST_INR_PER_1K: dict[str, dict[str, float]] = {
    "gemini-2.5-pro": {
        "input": _price("COST_PRO_INPUT_INR_PER_1K", "0.106"),
        "output": _price("COST_PRO_OUTPUT_INR_PER_1K", "0.850"),
    },
    "gemini-2.5-flash": {
        "input": _price("COST_FLASH_INPUT_INR_PER_1K", "0.026"),
        "output": _price("COST_FLASH_OUTPUT_INR_PER_1K", "0.213"),
    },
}
# Fallback pricing for an unrecognised model — never silently free.
DEFAULT_COST_INR_PER_1K = {
    "input": _price("COST_DEFAULT_INPUT_INR_PER_1K", "0.100"),
    "output": _price("COST_DEFAULT_OUTPUT_INR_PER_1K", "0.500"),
}


def estimate_cost_inr(
    model: str, input_tokens: int | None, output_tokens: int | None
) -> float:
    """Estimated INR cost for a single AI call (0 when token counts are unknown)."""
    rate = MODEL_COST_INR_PER_1K.get(model, DEFAULT_COST_INR_PER_1K)
    cost = (input_tokens or 0) / 1000 * rate["input"] + (
        output_tokens or 0
    ) / 1000 * rate["output"]
    return round(cost, 6)

# --- Conversation policy ---
SUPPORTED_LANGUAGES = ("ta", "en")
DEFAULT_LANGUAGE = "ta"
MAX_MESSAGE_CHARS = 2000
MAX_RESPONSE_CHARS = 4000
# How many prior turns to send as context (docs/AI_PROMPTS.md → conversation history).
HISTORY_WINDOW = 12
TITLE_MAX_CHARS = 60


class Sender(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


# Gemini uses "user"/"model" role names in its content list.
GEMINI_ROLE = {Sender.USER.value: "user", Sender.ASSISTANT.value: "model"}
