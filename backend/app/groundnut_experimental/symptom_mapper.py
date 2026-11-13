"""Conservative multilingual transcript mapping for Groundnut observations.

This module recognizes explicit farmer-observable phrases only. It does not
infer diseases, expand synonyms with AI, or attach confidence scores.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SUPPORTED_LANGUAGES = frozenset({"en-IN", "ta-IN", "ml-IN"})

_PHRASES: dict[str, dict[str, tuple[str, ...]]] = {
    "en-IN": {
        "dark_leaf_spots": ("dark leaf spots", "dark spots on leaves"),
        "light_leaf_spots": ("light leaf spots", "pale leaf spots"),
        "yellow_halo_around_spots": ("yellow halo around spots", "yellow rings around spots"),
        "rust_colored_leaf_marks": ("rust colored leaf marks", "rust coloured leaf marks"),
        "general_leaf_yellowing": ("general leaf yellowing", "leaves are yellow all over"),
        "yellowing_between_leaf_veins": ("yellowing between leaf veins", "interveinal yellowing"),
        "leaf_curling": ("leaf curling", "leaves are curling", "curled leaves"),
        "wilting": ("plant is wilting", "plants are wilting", "wilted plant"),
        "stunted_growth": ("stunted growth", "plants are stunted"),
        "holes_or_chewed_edges": ("holes in leaves", "chewed leaf edges"),
        "uniform_green_leaves": ("uniform green leaves", "leaves are uniformly green"),
    },
    "ta-IN": {
        "dark_leaf_spots": ("அடர் நிற இலைப்புள்ளிகள்", "இலைகளில் அடர் புள்ளிகள்"),
        "light_leaf_spots": ("வெளிர் நிற இலைப்புள்ளிகள்", "இலைகளில் வெளிர் புள்ளிகள்"),
        "yellow_halo_around_spots": ("புள்ளிகளை சுற்றி மஞ்சள் வளையம்",),
        "rust_colored_leaf_marks": ("இலைகளில் துரு நிற குறிகள்",),
        "general_leaf_yellowing": ("இலை முழுவதும் மஞ்சளாதல்", "இலைகள் முழுவதும் மஞ்சளாக உள்ளன"),
        "yellowing_between_leaf_veins": ("இலை நரம்புகளுக்கு இடையில் மஞ்சளாதல்",),
        "leaf_curling": ("இலை சுருண்டல்", "இலைகள் சுருண்டுள்ளன"),
        "wilting": ("செடி வாடுகிறது", "வாடிய செடி"),
        "stunted_growth": ("வளர்ச்சி குன்றுதல்", "வளர்ச்சி குன்றியுள்ளது"),
        "holes_or_chewed_edges": ("இலைகளில் துளைகள்", "கடிக்கப்பட்ட இலை ஓரங்கள்"),
        "uniform_green_leaves": ("சீரான பச்சை இலைகள்",),
    },
    "ml-IN": {
        "dark_leaf_spots": ("ഇരുണ്ട ഇലപ്പുള്ളികൾ", "ഇലകളിൽ ഇരുണ്ട പുള്ളികൾ"),
        "light_leaf_spots": ("ഇളം നിറത്തിലുള്ള ഇലപ്പുള്ളികൾ", "ഇലകളിൽ ഇളം പുള്ളികൾ"),
        "yellow_halo_around_spots": ("പുള്ളികൾക്ക് ചുറ്റും മഞ്ഞ വലയം",),
        "rust_colored_leaf_marks": ("തുരുമ്പ് നിറത്തിലുള്ള ഇല അടയാളങ്ങൾ",),
        "general_leaf_yellowing": ("ഇലകളുടെ പൊതുവായ മഞ്ഞനിറം", "ഇലകൾ മുഴുവൻ മഞ്ഞയാണ്"),
        "yellowing_between_leaf_veins": ("ഇലഞരമ്പുകൾക്കിടയിലെ മഞ്ഞനിറം",),
        "leaf_curling": ("ഇല ചുരുളൽ", "ഇലകൾ ചുരുണ്ടിരിക്കുന്നു"),
        "wilting": ("ചെടി വാടുന്നു", "വാടിയ ചെടി"),
        "stunted_growth": ("വളർച്ച മുരടിക്കൽ", "വളർച്ച മുരടിച്ചിരിക്കുന്നു"),
        "holes_or_chewed_edges": ("ഇലയിൽ ദ്വാരങ്ങൾ", "കടിച്ച ഇല അരികുകൾ"),
        "uniform_green_leaves": ("ഒരേപോലെ പച്ച ഇലകൾ",),
    },
}

_NEGATION = {
    "en-IN": ("no ", "not ", "without ", "none ", "isn't ", "are not "),
    "ta-IN": ("இல்லை", "அல்ல", "காணவில்லை"),
    "ml-IN": ("ഇല്ല", "അല്ല", "കാണുന്നില്ല"),
}
_UNCERTAIN = {
    "en-IN": ("maybe", "perhaps", "not sure", "unsure"),
    "ta-IN": ("இருக்கலாம்", "தெரியவில்லை", "உறுதியாக இல்லை"),
    "ml-IN": ("ആയിരിക്കാം", "ഉറപ്പില്ല", "അറിയില്ല"),
}


@dataclass(frozen=True)
class TranscriptMapping:
    matched_symptoms: list[str]
    unmatched_text: list[str]
    ambiguous_text: list[str]


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("-", " ").replace("'", " ").replace("’", " ")
    return " ".join(value.split())


def _clauses(transcript: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n,.;!?]+", transcript) if part.strip()]


def map_groundnut_transcript(transcript: str, language: str) -> TranscriptMapping:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("unsupported_language")

    matched: list[str] = []
    unmatched: list[str] = []
    ambiguous: list[str] = []
    for original in _clauses(transcript):
        clause = _normalize(original)
        clause_matches = [
            symptom
            for symptom, phrases in _PHRASES[language].items()
            if any(_normalize(phrase) in clause for phrase in phrases)
        ]
        if not clause_matches:
            unmatched.append(original)
            continue
        if any(marker in clause for marker in _NEGATION[language] + _UNCERTAIN[language]):
            ambiguous.append(original)
            continue
        for symptom in clause_matches:
            if symptom not in matched:
                matched.append(symptom)
    return TranscriptMapping(matched, unmatched, ambiguous)
