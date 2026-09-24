# Organic Readiness Check — draft question set v1 (2026-09-23)

**Status: UNREVIEWED DRAFT. Do not approve as-is.**

This is a starting point for Phase 1 of the organic-farming blueprint, built
from the topics the owner's blueprint specified (crop/acreage/stage, input
history, soil-test/irrigation availability, FYM/residue/livestock/labour,
contamination exposure, yield/cost/channel awareness, buyer demand +
certification intent). The question wording, point values, risk flags, and
score thresholds below are a reasonable-looking first draft, not verified
agronomic or PGS-India guidance — an agronomist/reviewer must check and edit
this before it goes anywhere near a real farmer, exactly like every other
piece of reviewed content in this codebase (crop calendar schedules, disease
rule packs, etc).

To use it: open admin-web's Organic Content screen, paste `version` and the
`questions` / `scoring` JSON blocks below into the "Save readiness draft"
form, review/edit as needed, then approve. Nothing here reaches a farmer
until that approval happens (`organic_mvp` enforces this server-side).

## `version`

```
readiness-v1-draft-2026-09-23
```

## `questions`

```json
[
  {
    "id": "crop_acreage_stage",
    "title_ta": "எந்த பயிர், எவ்வளவு பரப்பு (ஏக்கர்), எந்த வளர்ச்சி நிலையில் உள்ளது?",
    "title_en": "Which crop, how much area (acres), and what growth stage is it at?",
    "options": {
      "small_early_stage": {"points": 2, "label_ta": "1 ஏக்கருக்கு குறைவு, விதைப்பு/நாற்று நிலை", "label_en": "Under 1 acre, sowing/seedling stage"},
      "medium_stage": {"points": 1, "label_ta": "1-3 ஏக்கர், வளர்ச்சி நிலையில்", "label_en": "1-3 acres, already in a growth stage"},
      "large_established": {"points": 0, "label_ta": "3 ஏக்கருக்கு மேல், அறுவடைக்கு அருகில்", "label_en": "Over 3 acres, close to harvest"}
    }
  },
  {
    "id": "synthetic_input_history",
    "title_ta": "கடந்த 6 மாதங்களில் இரசாயன உரம் அல்லது பூச்சிக்கொல்லி பயன்படுத்தினீர்களா?",
    "title_en": "Have you used any synthetic (chemical) fertilizer or pesticide on this land in the last 6 months?",
    "options": {
      "none_ever": {"points": 2, "label_ta": "இல்லை, ஒருபோதும் இல்லை", "label_en": "No, never on this land"},
      "none_recent": {"points": 1, "label_ta": "6 மாதங்களுக்கு முன் பயன்படுத்தியுள்ளேன்", "label_en": "Not in the last 6 months, but before that yes"},
      "recent": {"points": 0, "risk_flag": "recent_synthetic_input_use", "label_ta": "ஆம், கடந்த 6 மாதங்களில்", "label_en": "Yes, within the last 6 months"}
    }
  },
  {
    "id": "soil_test_availability",
    "title_ta": "இந்த நிலத்திற்கு மண் பரிசோதனை அறிக்கை உள்ளதா?",
    "title_en": "Do you have a soil test report for this land?",
    "options": {
      "recent_report": {"points": 2, "label_ta": "ஆம், கடந்த 12 மாதங்களில்", "label_en": "Yes, within the last 12 months"},
      "old_report": {"points": 1, "label_ta": "ஆம், ஆனால் பழையது", "label_en": "Yes, but it's old"},
      "none": {"points": 0, "risk_flag": "no_soil_baseline", "label_ta": "இல்லை, மண் பரிசோதனை செய்யவில்லை", "label_en": "No soil test has been done"}
    }
  },
  {
    "id": "irrigation_availability",
    "title_ta": "இந்த நிலத்திற்கு நம்பகமான நீர்ப்பாசன ஆதாரம் உள்ளதா?",
    "title_en": "Is there a reliable irrigation source for this land?",
    "options": {
      "reliable": {"points": 2, "label_ta": "ஆம், நம்பகமான ஆதாரம் உள்ளது", "label_en": "Yes, a reliable source"},
      "seasonal": {"points": 1, "label_ta": "பருவகால / மழையை சார்ந்தது", "label_en": "Seasonal / mostly rain-dependent"},
      "unreliable": {"points": 0, "label_ta": "நம்பகமான நீர் ஆதாரம் இல்லை", "label_en": "No reliable water source"}
    }
  },
  {
    "id": "organic_matter_availability",
    "title_ta": "தொழு உரம், பயிர்க்கழிவு அல்லது கால்நடை உரம் உங்களிடம் கிடைக்குமா?",
    "title_en": "Do you have access to farmyard manure, crop residue, or livestock manure?",
    "options": {
      "regular_own_source": {"points": 2, "label_ta": "ஆம், சொந்த ஆதாரத்திலிருந்து தொடர்ந்து கிடைக்கும்", "label_en": "Yes, regularly from my own source"},
      "occasional_bought": {"points": 1, "label_ta": "எப்போதாவது, வாங்க வேண்டும்", "label_en": "Occasionally, would need to buy it in"},
      "none": {"points": 0, "label_ta": "தற்போது கிடைக்கவில்லை", "label_en": "Not currently available"}
    }
  },
  {
    "id": "labour_availability",
    "title_ta": "கூடுதல் கை உழைப்பு தேவைப்படும் இயற்கை பயிர் பராமரிப்புக்கு தொழிலாளர் கிடைப்பார்களா?",
    "title_en": "Is labour available for the extra hand-weeding/composting organic practices usually need?",
    "options": {
      "reliable_family_or_hired": {"points": 2, "label_ta": "ஆம், நம்பகமான குடும்ப/கூலி தொழிலாளர்", "label_en": "Yes, reliable family or hired labour"},
      "sometimes": {"points": 1, "label_ta": "சில நேரங்களில் மட்டும்", "label_en": "Only sometimes"},
      "rarely": {"points": 0, "label_ta": "அரிதாகவே கிடைக்கும்", "label_en": "Rarely available"}
    }
  },
  {
    "id": "contamination_exposure",
    "title_ta": "அருகிலுள்ள நிலங்களில் இருந்து இரசாயன தெளிப்பு/கழிவு நீர் இந்த நிலத்தை அடையும் வாய்ப்பு உள்ளதா?",
    "title_en": "Could spray drift or runoff from a neighbouring farm reach this land?",
    "options": {
      "no_risk": {"points": 2, "label_ta": "இல்லை, தூர இடைவெளி/தடுப்பு உள்ளது", "label_en": "No, there's distance or a buffer"},
      "some_risk": {"points": 1, "label_ta": "சில வாய்ப்பு உள்ளது", "label_en": "Some possibility"},
      "likely": {"points": 0, "risk_flag": "contamination_exposure_risk", "label_ta": "ஆம், அருகில் இரசாயன தெளிப்பு நடக்கிறது", "label_en": "Yes, a neighbouring farm sprays close by"}
    }
  },
  {
    "id": "market_channel_awareness",
    "title_ta": "இயற்கை விளைபொருளை விற்பதற்கான சந்தை/வாங்குபவர் பற்றி உங்களுக்கு தெரியுமா?",
    "title_en": "Do you know a market or buyer channel for organic produce yet?",
    "options": {
      "identified_buyer": {"points": 2, "label_ta": "ஆம், ஒரு வாங்குபவரை அடையாளம் கண்டுள்ளேன்", "label_en": "Yes, I've identified a buyer"},
      "exploring": {"points": 1, "label_ta": "தேடிக்கொண்டிருக்கிறேன்", "label_en": "Still exploring options"},
      "none": {"points": 0, "label_ta": "இதுவரை தெரியவில்லை", "label_en": "Don't know one yet"}
    }
  },
  {
    "id": "certification_intent",
    "title_ta": "PGS-India சான்றிதழ் பெறுவதற்கான செயல்முறையில் ஈடுபட தயாரா?",
    "title_en": "Are you ready to take part in the PGS-India certification process (group meetings, self-declaration, peer inspection)?",
    "options": {
      "ready_now": {"points": 2, "label_ta": "ஆம், இப்போதே தயார்", "label_en": "Yes, ready now"},
      "need_more_info": {"points": 1, "label_ta": "மேலும் தகவல் தேவை", "label_en": "Need more information first"},
      "not_yet": {"points": 0, "label_ta": "இப்போது இல்லை", "label_en": "Not right now"}
    }
  }
]
```

## `scoring`

Max possible score is 18 (9 questions × 2 points); `score_readiness()` scales
this to 0-100. Suggested bands (**thresholds are a guess — an agronomist
should set the real cut-offs**):

```json
{
  "bands": [
    {"min": 0, "max": 30, "pathway": "not_ready",
     "recommendation_ta": "இப்போது மாற்றத்தைத் தொடங்க வேண்டாம். முதலில் இரசாயன உள்ளீடுகளை நிறுத்தி, அடிப்படை பதிவுகளை உருவாக்கவும்.",
     "recommendation_en": "Do not convert yet. Stop synthetic inputs and build basic farm records first."},
    {"min": 31, "max": 55, "pathway": "begin_soil_restoration",
     "recommendation_ta": "மண் மேம்பாட்டு நடைமுறைகளுடன் தொடங்குங்கள் (தொழு உரம், பயிர்சுழற்சி) மாற்றத்திற்கு விண்ணப்பிக்கும் முன்.",
     "recommendation_en": "Begin with soil-restoration practices (composting, crop rotation) before applying for conversion."},
    {"min": 56, "max": 80, "pathway": "start_one_plot",
     "recommendation_ta": "ஒரு காணியில் மட்டும் இயற்கை மாற்றத்தைத் தொடங்குங்கள்; மற்றவை வழக்கம் போல் தொடரலாம்.",
     "recommendation_en": "Start organic conversion on one plot only; keep the rest of the farm conventional for now."},
    {"min": 81, "max": 100, "pathway": "ready_full_conversion",
     "recommendation_ta": "முழு பண்ணை மாற்றத்தைத் தொடங்க தயார். உங்கள் PGS பிராந்திய கவுன்சில் தொடர்பைத் தொடர்பு கொள்ளுங்கள்.",
     "recommendation_en": "Ready to begin full-farm conversion. Contact your PGS regional council."}
  ]
}
```
