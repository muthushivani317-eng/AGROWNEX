"""Output safety validator (2026-08 pre-release audit): Gemini's raw output
previously reached the farmer with no server-side check that it honored the
system prompt's own safety rules. These are pure unit tests for the
deterministic, bilingual pattern check added in app/modules/ai/validator.py.
"""
from app.modules.ai.validator import contains_unsafe_advice, validate_response


def test_ordinary_advice_passes_through_unchanged():
    text = "Water your paddy field every 3 days. Watch for yellowing leaves."
    assert contains_unsafe_advice(text) is False
    assert validate_response(text, "en") == text


def test_flags_guaranteed_yield_claim_english():
    assert contains_unsafe_advice("This fertilizer will guarantee a higher yield.")
    assert contains_unsafe_advice("Using this method gives 100% yield increase.")


def test_flags_guaranteed_yield_claim_tamil():
    assert contains_unsafe_advice("இந்த முறை விளைச்சலுக்கு உத்தரவாதம் அளிக்கிறது.")


def test_flags_exceeding_recommended_dose_english():
    assert contains_unsafe_advice(
        "You can double the recommended dose for faster results."
    )
    assert contains_unsafe_advice("It is fine to exceed the label dose slightly.")


def test_flags_exceeding_recommended_dose_tamil():
    assert contains_unsafe_advice(
        "பரிந்துரைக்கப்பட்ட அளவை மீறி பயன்படுத்தலாம்."
    )


def test_flags_skipping_protective_equipment():
    assert contains_unsafe_advice(
        "There is no need for protective gear when spraying this."
    )


def test_validate_response_substitutes_fallback_when_unsafe():
    unsafe = "This will guarantee your yield doubles this season."
    result = validate_response(unsafe, "en")
    assert result != unsafe
    assert "agriculture officer" in result


def test_validate_response_substitutes_tamil_fallback_when_unsafe():
    unsafe = "இந்த மருந்து விளைச்சலுக்கு உத்தரவாதம் அளிக்கிறது."
    result = validate_response(unsafe, "ta")
    assert result != unsafe
    assert "வேளாண் அலுவலர" in result


def test_validate_response_still_handles_empty_and_oversized_text():
    assert "agriculture officer" in validate_response(None, "en")
    assert "agriculture officer" in validate_response("   ", "en")
    long_text = "a" * 5000
    result = validate_response(long_text, "en")
    assert len(result) <= 4000
