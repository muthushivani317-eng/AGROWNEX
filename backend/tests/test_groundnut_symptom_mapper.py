from __future__ import annotations

import pytest

from app.groundnut_experimental.symptom_mapper import map_groundnut_transcript


@pytest.mark.parametrize(
    ("language", "transcript"),
    [
        (
            "en-IN",
            "Dark leaf spots. Light leaf spots. Yellow halo around spots. Rust colored leaf marks. "
            "General leaf yellowing. Yellowing between leaf veins. Leaf curling. Plant is wilting. "
            "Stunted growth. Holes in leaves. Uniform green leaves.",
        ),
        (
            "ta-IN",
            "அடர் நிற இலைப்புள்ளிகள். வெளிர் நிற இலைப்புள்ளிகள். புள்ளிகளை சுற்றி மஞ்சள் வளையம். "
            "இலைகளில் துரு நிற குறிகள். இலை முழுவதும் மஞ்சளாதல். இலை நரம்புகளுக்கு இடையில் மஞ்சளாதல். "
            "இலை சுருண்டல். செடி வாடுகிறது. வளர்ச்சி குன்றுதல். இலைகளில் துளைகள். சீரான பச்சை இலைகள்.",
        ),
        (
            "ml-IN",
            "ഇരുണ്ട ഇലപ്പുള്ളികൾ. ഇളം നിറത്തിലുള്ള ഇലപ്പുള്ളികൾ. പുള്ളികൾക്ക് ചുറ്റും മഞ്ഞ വലയം. "
            "തുരുമ്പ് നിറത്തിലുള്ള ഇല അടയാളങ്ങൾ. ഇലകളുടെ പൊതുവായ മഞ്ഞനിറം. ഇലഞരമ്പുകൾക്കിടയിലെ മഞ്ഞനിറം. "
            "ഇല ചുരുളൽ. ചെടി വാടുന്നു. വളർച്ച മുരടിക്കൽ. ഇലയിൽ ദ്വാരങ്ങൾ. ഒരേപോലെ പച്ച ഇലകൾ.",
        ),
    ],
)
def test_maps_all_explicit_validated_symptoms(language: str, transcript: str) -> None:
    result = map_groundnut_transcript(transcript, language)
    assert len(result.matched_symptoms) == 11
    assert result.unmatched_text == []
    assert result.ambiguous_text == []


@pytest.mark.parametrize(
    ("language", "transcript"),
    [
        ("en-IN", "Maybe there are dark leaf spots"),
        ("ta-IN", "அடர் நிற இலைப்புள்ளிகள் இருக்கலாம்"),
        ("ml-IN", "ഇരുണ്ട ഇലപ്പുള്ളികൾ ആയിരിക്കാം"),
    ],
)
def test_uncertain_explicit_phrases_are_returned_for_review(language: str, transcript: str) -> None:
    result = map_groundnut_transcript(transcript, language)
    assert result.matched_symptoms == []
    assert result.ambiguous_text == [transcript]


def test_disease_name_and_unrecognized_description_are_not_inferred() -> None:
    transcript = "It is rust disease. The plant looks unusual."
    result = map_groundnut_transcript(transcript, "en-IN")
    assert result.matched_symptoms == []
    assert result.unmatched_text == ["It is rust disease", "The plant looks unusual"]
    assert result.ambiguous_text == []


def test_negated_symptom_is_not_matched() -> None:
    result = map_groundnut_transcript("There are no dark leaf spots", "en-IN")
    assert result.matched_symptoms == []
    assert result.ambiguous_text == ["There are no dark leaf spots"]
