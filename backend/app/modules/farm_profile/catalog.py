"""Standard onboarding catalog: what a farmer grows/rears/produces and needs.

The app shows these as searchable multi-select lists; the backend stores only
the ``code`` so FPO/KVK boards group farmers reliably (no "Tomato"/"tomatoes"
/"தக்காளி" splits). Anything not listed goes in as ``other`` with a
custom_name.
"""
from __future__ import annotations

CATEGORIES: dict[str, dict] = {
    "crops": {"en": "Crops", "ta": "பயிர்கள்"},
    "vegetables": {"en": "Vegetables", "ta": "காய்கறிகள்"},
    "fruits": {"en": "Fruits", "ta": "பழங்கள்"},
    "plantation": {"en": "Plantation crops", "ta": "தோட்டப் பயிர்கள்"},
    "livestock": {"en": "Livestock", "ta": "கால்நடைகள்"},
    "other_products": {"en": "Other farm products", "ta": "பிற பண்ணை பொருட்கள்"},
}

UNITS: dict[str, dict] = {
    "kg": {"en": "kg", "ta": "கிலோ"},
    "quintal": {"en": "quintal", "ta": "குவிண்டால்"},
    "tonne": {"en": "tonne", "ta": "டன்"},
    "bag": {"en": "bag", "ta": "மூட்டை"},
    "litre": {"en": "litre", "ta": "லிட்டர்"},
    "nos": {"en": "numbers", "ta": "எண்ணிக்கை"},
    "head": {"en": "animals", "ta": "கால்நடை எண்ணிக்கை"},
}

# (code, category, English, Tamil, default unit)
_ITEMS: list[tuple[str, str, str, str, str]] = [
    # crops (field crops, grains, pulses, oilseeds, fibre)
    ("paddy", "crops", "Paddy", "நெல்", "quintal"),
    ("maize", "crops", "Maize", "மக்காச்சோளம்", "quintal"),
    ("sorghum", "crops", "Sorghum (Cholam)", "சோளம்", "quintal"),
    ("pearl_millet", "crops", "Pearl millet (Kambu)", "கம்பு", "quintal"),
    ("finger_millet", "crops", "Finger millet (Ragi)", "கேழ்வரகு", "quintal"),
    ("black_gram", "crops", "Black gram", "உளுந்து", "quintal"),
    ("green_gram", "crops", "Green gram", "பாசிப்பயறு", "quintal"),
    ("red_gram", "crops", "Red gram", "துவரை", "quintal"),
    ("groundnut", "crops", "Groundnut", "நிலக்கடலை", "quintal"),
    ("sesame", "crops", "Sesame", "எள்", "quintal"),
    ("cotton", "crops", "Cotton", "பருத்தி", "quintal"),
    ("sugarcane", "crops", "Sugarcane", "கரும்பு", "tonne"),
    ("turmeric", "crops", "Turmeric", "மஞ்சள்", "quintal"),
    ("chilli", "crops", "Chilli", "மிளகாய்", "quintal"),
    # vegetables
    ("tomato", "vegetables", "Tomato", "தக்காளி", "kg"),
    ("brinjal", "vegetables", "Brinjal", "கத்தரி", "kg"),
    ("okra", "vegetables", "Okra (Ladies finger)", "வெண்டை", "kg"),
    ("onion", "vegetables", "Onion", "வெங்காயம்", "kg"),
    ("small_onion", "vegetables", "Small onion", "சின்ன வெங்காயம்", "kg"),
    ("green_chilli", "vegetables", "Green chilli", "பச்சை மிளகாய்", "kg"),
    ("cucumber", "vegetables", "Cucumber", "வெள்ளரி", "kg"),
    ("bitter_gourd", "vegetables", "Bitter gourd", "பாகற்காய்", "kg"),
    ("snake_gourd", "vegetables", "Snake gourd", "புடலங்காய்", "kg"),
    ("bottle_gourd", "vegetables", "Bottle gourd", "சுரைக்காய்", "kg"),
    ("pumpkin", "vegetables", "Pumpkin", "பூசணி", "kg"),
    ("drumstick", "vegetables", "Drumstick", "முருங்கை", "kg"),
    ("beans", "vegetables", "Beans", "பீன்ஸ்", "kg"),
    ("cabbage", "vegetables", "Cabbage", "முட்டைக்கோஸ்", "kg"),
    ("carrot", "vegetables", "Carrot", "கேரட்", "kg"),
    ("potato", "vegetables", "Potato", "உருளைக்கிழங்கு", "kg"),
    ("tapioca", "vegetables", "Tapioca", "மரவள்ளி", "tonne"),
    ("greens", "vegetables", "Greens (Keerai)", "கீரை", "kg"),
    # fruits
    ("banana", "fruits", "Banana", "வாழை", "tonne"),
    ("mango", "fruits", "Mango", "மா", "kg"),
    ("guava", "fruits", "Guava", "கொய்யா", "kg"),
    ("papaya", "fruits", "Papaya", "பப்பாளி", "kg"),
    ("jackfruit", "fruits", "Jackfruit", "பலா", "nos"),
    ("lemon", "fruits", "Lemon", "எலுமிச்சை", "kg"),
    ("pomegranate", "fruits", "Pomegranate", "மாதுளை", "kg"),
    ("sapota", "fruits", "Sapota", "சப்போட்டா", "kg"),
    ("watermelon", "fruits", "Watermelon", "தர்பூசணி", "tonne"),
    ("amla", "fruits", "Amla (Gooseberry)", "நெல்லி", "kg"),
    # plantation
    ("coconut", "plantation", "Coconut", "தென்னை", "nos"),
    ("arecanut", "plantation", "Arecanut", "பாக்கு", "kg"),
    ("cashew", "plantation", "Cashew", "முந்திரி", "kg"),
    ("tea", "plantation", "Tea", "தேயிலை", "kg"),
    ("coffee", "plantation", "Coffee", "காபி", "kg"),
    ("rubber", "plantation", "Rubber", "ரப்பர்", "kg"),
    ("pepper", "plantation", "Pepper", "மிளகு", "kg"),
    ("cardamom", "plantation", "Cardamom", "ஏலக்காய்", "kg"),
    ("palmyra", "plantation", "Palmyra", "பனை", "nos"),
    # livestock
    ("cow", "livestock", "Cow", "பசு", "head"),
    ("buffalo", "livestock", "Buffalo", "எருமை", "head"),
    ("goat", "livestock", "Goat", "வெள்ளாடு", "head"),
    ("sheep", "livestock", "Sheep", "செம்மறி ஆடு", "head"),
    ("poultry", "livestock", "Poultry (Country chicken)", "நாட்டுக் கோழி", "head"),
    ("duck", "livestock", "Duck", "வாத்து", "head"),
    ("fish", "livestock", "Fish farming", "மீன் வளர்ப்பு", "kg"),
    ("bee", "livestock", "Bee keeping", "தேனீ வளர்ப்பு", "nos"),
    # other farm products
    ("milk", "other_products", "Milk", "பால்", "litre"),
    ("eggs", "other_products", "Eggs", "முட்டை", "nos"),
    ("honey", "other_products", "Honey", "தேன்", "kg"),
    ("jaggery", "other_products", "Jaggery", "வெல்லம்", "kg"),
    ("palm_jaggery", "other_products", "Palm jaggery", "கருப்பட்டி", "kg"),
    ("vermicompost", "other_products", "Vermicompost", "மண்புழு உரம்", "kg"),
    ("farmyard_manure", "other_products", "Farmyard manure", "தொழு உரம்", "tonne"),
    ("panchagavya", "other_products", "Panchagavya", "பஞ்சகவ்யா", "litre"),
    ("seeds", "other_products", "Farm-saved seeds", "விதைகள்", "kg"),
    ("flowers", "other_products", "Flowers", "பூக்கள்", "kg"),
    ("coir", "other_products", "Coir / husk", "தேங்காய் நார்", "kg"),
]

ITEMS: dict[str, dict] = {
    code: {"code": code, "category": category, "en": en, "ta": ta, "default_unit": unit}
    for code, category, en, ta, unit in _ITEMS
}
OTHER_CODE = "other"

FARMER_TYPES: dict[str, dict] = {
    "full_time_farmer": {"en": "Full-time farmer", "ta": "முழு நேர விவசாயி"},
    "part_time_farmer": {"en": "Part-time farmer", "ta": "பகுதி நேர விவசாயி"},
    "tenant_farmer": {"en": "Tenant farmer", "ta": "குத்தகை விவசாயி"},
    "livestock_farmer": {"en": "Livestock farmer", "ta": "கால்நடை வளர்ப்பவர்"},
    "farm_labourer": {"en": "Farm labourer", "ta": "விவசாயத் தொழிலாளி"},
    "agri_entrepreneur": {"en": "Agri entrepreneur", "ta": "வேளாண் தொழில்முனைவோர்"},
    "other": {"en": "Other", "ta": "பிற"},
}

NEEDS: dict[str, dict] = {
    "quality_seeds": {"en": "Quality seeds", "ta": "தரமான விதைகள்"},
    "organic_inputs": {"en": "Organic inputs", "ta": "இயற்கை இடுபொருட்கள்"},
    "fertilizer": {"en": "Fertilizer", "ta": "உரம்"},
    "machinery": {"en": "Machinery on rent", "ta": "வாடகை இயந்திரங்கள்"},
    "irrigation": {"en": "Irrigation / water", "ta": "நீர்ப்பாசனம்"},
    "labour": {"en": "Farm labour", "ta": "விவசாயத் தொழிலாளர்"},
    "credit": {"en": "Loan / credit", "ta": "கடன் உதவி"},
    "insurance": {"en": "Crop insurance", "ta": "பயிர் காப்பீடு"},
    "buyers": {"en": "Buyers for my produce", "ta": "விளைபொருளுக்கு வாங்குபவர்"},
    "storage": {"en": "Storage", "ta": "சேமிப்பு வசதி"},
    "soil_testing": {"en": "Soil testing", "ta": "மண் பரிசோதனை"},
    "training": {"en": "Training", "ta": "பயிற்சி"},
    "govt_schemes": {"en": "Government schemes", "ta": "அரசு திட்டங்கள்"},
    "veterinary": {"en": "Veterinary care", "ta": "கால்நடை மருத்துவம்"},
    "organic_certification": {"en": "Organic certification", "ta": "இயற்கை சான்றிதழ்"},
}

MONTHS = list(range(1, 13))


def item_label(code: str, custom_name: str | None = None) -> str:
    if code == OTHER_CODE:
        return (custom_name or "Other").strip() or "Other"
    item = ITEMS.get(code)
    return item["en"] if item else code


def catalog_payload() -> dict:
    return {
        "version": 1,
        "categories": [{"code": code, **names} for code, names in CATEGORIES.items()],
        "items": list(ITEMS.values()),
        "other_code": OTHER_CODE,
        "units": [{"code": code, **names} for code, names in UNITS.items()],
        "farmer_types": [{"code": code, **names} for code, names in FARMER_TYPES.items()],
        "needs": [{"code": code, **names} for code, names in NEEDS.items()],
        "months": MONTHS,
    }
