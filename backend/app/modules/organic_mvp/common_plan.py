"""Common week-by-week organic plan used by every crop cycle.

One crop-agnostic plan. No doses are given -- quantities come from the Input
Workshop calculator and official sources. Farmers are told to verify with
official sources before applying anything.

Weeks count from the start of the season; sowing/transplanting is week 6.
When the farmer gives an expected harvest date, the end-of-season steps move
to that date and any growth step that would fall inside the last two weeks
before harvest is skipped, so short crops (e.g. groundnut) still fit.
"""
from __future__ import annotations

from datetime import date, timedelta

COMMON_PLAN_VERSION = "common-v1"

SOWING_WEEK = 6
DEFAULT_HARVEST_WEEK = 19
PRE_HARVEST_STOP_DAYS = 14

NOTICE_TA = "எதையும் இடுவதற்கு முன் அதிகாரப்பூர்வ ஆதாரங்களுடன் (KVK அல்லது வேளாண்மைத் துறை) சரிபார்க்கவும்."
NOTICE_EN = "Verify with official sources (KVK or Agriculture Department) before applying anything."

# phase: "prep" (before sowing), "growth" (after sowing), "harvest" (anchored to harvest)
COMMON_PLAN_TASKS: list[dict] = [
    {"week": 1, "phase": "prep",
     "title_ta": "வயலை சுத்தம் செய்யுங்கள்",
     "body_ta": "களைகள், பழைய பயிர்க் கழிவுகளை அகற்றுங்கள். ரசாயன உரம், பூச்சிக்கொல்லிகளை இனி பயன்படுத்த வேண்டாம். பண்ணை நாட்குறிப்பைத் தொடங்குங்கள்.",
     "title_en": "Clear the field",
     "body_en": "Remove weeds and old crop waste. Stop using chemical fertiliser and pesticides. Start the Farm Diary."},
    {"week": 2, "phase": "prep",
     "title_ta": "ஆழமாக உழவு செய்யுங்கள்",
     "body_ta": "ஆழமாக உழுது, தொழு உரம் அல்லது மட்கிய உரத்தை வயல் முழுவதும் இடுங்கள்.",
     "title_en": "Deep plough",
     "body_en": "Plough deep and apply farmyard manure or compost to the whole field."},
    {"week": 3, "phase": "prep",
     "title_ta": "பசுந்தாள் உரப் பயிர் விதைக்கவும்",
     "body_ta": "நேரம் இருந்தால் சணப்பு அல்லது தக்கைப்பூண்டு விதைக்கவும். இல்லையெனில் மண்புழு உரம் அல்லது மட்கு உரக் குழி தயார் செய்யவும்.",
     "title_en": "Sow green manure",
     "body_en": "If there is time, sow sunhemp or daincha. Otherwise, prepare vermicompost or a compost pit."},
    {"week": 4, "phase": "prep",
     "title_ta": "பசுந்தாள் உரத்தை மடக்கி உழவும்",
     "body_ta": "பசுந்தாள் பயிரை மண்ணில் மடக்கி உழுங்கள். வயலை சமன் செய்து, பாசன வாய்க்கால்களைத் தயார் செய்யுங்கள்.",
     "title_en": "Plough in green manure",
     "body_en": "Plough the green manure into the soil. Level the field and prepare irrigation channels."},
    {"week": 5, "phase": "prep",
     "title_ta": "விதை நேர்த்தி செய்யவும்",
     "body_ta": "டிரைக்கோடெர்மா அல்லது சூடோமோனாஸ் மற்றும் உயிர் உரம் (அசோஸ்பைரில்லம் அல்லது ரைசோபியம்) கொண்டு விதை நேர்த்தி செய்யுங்கள்.",
     "title_en": "Treat the seed",
     "body_en": "Treat seed with Trichoderma or Pseudomonas and a biofertiliser (Azospirillum or Rhizobium)."},
    {"week": 6, "phase": "growth",
     "title_ta": "விதைப்பு / நடவு",
     "body_ta": "விதைக்கவும் அல்லது நடவு செய்யவும். புகைப்படம் எடுத்து நாட்குறிப்பில் பதிவு செய்யுங்கள்.",
     "title_en": "Sow or transplant",
     "body_en": "Sow or transplant. Take a photo and record it in the diary."},
    {"week": 7, "phase": "growth",
     "title_ta": "முதல் களையெடுப்பு",
     "body_ta": "முதல் களையெடுப்பு செய்யுங்கள். வாரம் இருமுறை பூச்சிகளைக் கண்காணியுங்கள்.",
     "title_en": "First weeding",
     "body_en": "Do the first weeding. Check for pests twice a week."},
    {"week": 8, "phase": "growth",
     "title_ta": "தேவைக்கேற்ப நீர் பாய்ச்சவும்",
     "body_ta": "அட்டவணைப்படி அல்ல, மண்ணின் ஈரப்பதம் பார்த்து நீர் பாய்ச்சுங்கள். பூச்சிக் கண்காணிப்பைத் தொடருங்கள்.",
     "title_en": "Water by need",
     "body_en": "Water when the soil needs it, not on a fixed schedule. Keep checking for pests."},
    {"week": 9, "phase": "growth",
     "title_ta": "முதல் மேலுரம்",
     "body_ta": "மண்புழு உரம் அல்லது வேப்பம் புண்ணாக்கை மேலுரமாக இடுங்கள்.",
     "title_en": "First top dressing",
     "body_en": "Top-dress with vermicompost or neem cake."},
    {"week": 10, "phase": "growth",
     "title_ta": "பஞ்சகவ்யா தெளிப்பு, இரண்டாம் களையெடுப்பு",
     "body_ta": "பஞ்சகவ்யா அல்லது ஜீவாமிர்தம் தெளியுங்கள். இரண்டாம் களையெடுப்பு செய்யுங்கள்.",
     "title_en": "Panchagavya spray and second weeding",
     "body_en": "Spray Panchagavya or Jeevamirtham. Do the second weeding."},
    {"week": 11, "phase": "growth",
     "title_ta": "பூச்சிக் கண்காணிப்பு",
     "body_ta": "பூச்சிகளைக் கண்காணியுங்கள். தேவைப்பட்டால் மஞ்சள் ஒட்டுப் பொறி, இனக்கவர்ச்சிப் பொறி வையுங்கள்.",
     "title_en": "Pest check",
     "body_en": "Check for pests. Put up yellow sticky traps or pheromone traps if needed."},
    {"week": 12, "phase": "growth",
     "title_ta": "தேவைப்பட்டால் வேப்பெண்ணெய் தெளிப்பு",
     "body_ta": "பூச்சிகள் தென்பட்டால் மட்டும் வேப்பெண்ணெய் தெளியுங்கள். நாட்குறிப்பில் பதிவு செய்யுங்கள்.",
     "title_en": "Neem oil spray only if needed",
     "body_en": "Spray neem oil only if pests are seen. Record it in the diary."},
    {"week": 13, "phase": "growth",
     "title_ta": "இரண்டாம் மேலுரம்",
     "body_ta": "மண்புழு உரத்தை இரண்டாம் மேலுரமாக இடுங்கள்.",
     "title_en": "Second top dressing",
     "body_en": "Top-dress with vermicompost again."},
    {"week": 14, "phase": "growth",
     "title_ta": "பூக்கும் பருவம்",
     "body_ta": "அதிகமாக நீர் பாய்ச்ச வேண்டாம். நோய் அறிகுறிகளைக் கவனியுங்கள்.",
     "title_en": "Flowering",
     "body_en": "Avoid heavy watering. Watch for signs of disease."},
    {"week": 15, "phase": "growth",
     "title_ta": "மீண்டும் பஞ்சகவ்யா",
     "body_ta": "பஞ்சகவ்யா மீண்டும் தெளியுங்கள்.",
     "title_en": "Panchagavya again",
     "body_en": "Spray Panchagavya again."},
    {"week": 16, "phase": "growth",
     "title_ta": "பூச்சி, நோய் சோதனை",
     "body_ta": "பூச்சி மற்றும் நோய்களைச் சோதித்து, அனைத்தையும் நாட்குறிப்பில் பதிவு செய்யுங்கள்.",
     "title_en": "Pest and disease check",
     "body_en": "Check for pests and disease. Record everything in the diary."},
    {"week": 17, "phase": "harvest", "days_before_harvest": PRE_HARVEST_STOP_DAYS,
     "title_ta": "தெளிப்புகளை நிறுத்தவும்",
     "body_ta": "அனைத்து தெளிப்புகளையும் நிறுத்துங்கள். அறுவடைக்குப் பயிர் தயாரா என்று பாருங்கள்.",
     "title_en": "Stop sprays",
     "body_en": "Stop all sprays. Check whether the crop is ready to harvest."},
    {"week": 19, "phase": "harvest", "days_before_harvest": 0,
     "title_ta": "அறுவடை",
     "body_ta": "அறுவடை செய்து, உலர்த்தி, ரசாயன விளைச்சலுடன் கலக்காமல் தனியாக சேமியுங்கள். மகசூலை நாட்குறிப்பில் பதிவு செய்யுங்கள்.",
     "title_en": "Harvest",
     "body_en": "Harvest, dry and store separately from non-organic produce. Record the yield in the diary."},
]


def build_common_plan(sowing_date: date, harvest_date: date | None = None) -> list[dict]:
    """Date the common plan for one crop cycle. Pure function, no I/O."""
    default_harvest = sowing_date + timedelta(weeks=DEFAULT_HARVEST_WEEK - SOWING_WEEK)
    harvest = harvest_date if harvest_date and harvest_date > sowing_date else default_harvest
    growth_cutoff = harvest - timedelta(days=PRE_HARVEST_STOP_DAYS)
    plan: list[dict] = []
    for task in COMMON_PLAN_TASKS:
        if task["phase"] == "harvest":
            due = harvest - timedelta(days=task["days_before_harvest"])
            if due < sowing_date:
                due = sowing_date
        else:
            due = sowing_date + timedelta(weeks=task["week"] - SOWING_WEEK)
            if task["phase"] == "growth" and task["week"] > SOWING_WEEK and due >= growth_cutoff:
                continue
        plan.append({
            "week": task["week"],
            "due_on": due,
            "title_ta": task["title_ta"], "body_ta": task["body_ta"],
            "title_en": task["title_en"], "body_en": task["body_en"],
        })
    plan.sort(key=lambda item: item["due_on"])
    return plan
