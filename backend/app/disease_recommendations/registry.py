"""Fail-closed six-crop disease explanation registry.

All content is static and reviewed-in-repository.  Chemical treatments are deliberately
withheld until crop/disease-specific registration, dose and withholding-period evidence
has been independently verified from the applicable official regulator.

DISEASE_CONTENT below adds real, source-grounded symptom/cause/management content for
most of the 20 labels, extracted from the government/ICAR/IRRI extension publications
listed in EXTENSION_SOURCES (see docs/reference-library at D:\\AgrowAI\\Reference_books_pdf
on the maintainer's machine -- these are local reference PDFs, not yet published at a
stable public URL, so EXTENSION_SOURCES entries carry `url: None`).  Every field in
DISEASE_CONTENT was checked against its source PDF; fields the sources genuinely do not
cover (e.g. no source in the library names Cordana musae or Pestalotiopsis for banana at
all) are simply omitted rather than guessed, and get_recommendation() falls back to the
original generic placeholder text for exactly those omitted fields. No chemical product,
active-ingredient dose, or brand name is included anywhere in DISEASE_CONTENT, even where
a source PDF recommends one -- only cultural and biological (living-organism) practices,
consistent with CHEMICAL_WITHHELD below.

Tamil translation note (2026-08 pre-release audit follow-up): every ``*_ta`` field below
is a direct, meaning-preserving Tamil translation of the corresponding ``*_en`` field --
no new facts, doses, or claims are introduced that are not already in the English text
above it. It was produced by Claude (an AI assistant), not a certified agricultural
translator, so treat it the same way LAST_VERIFIED_DATE treats the English content: good
enough to ship rather than leave Tamil-reading farmers with English-only or
disclaimer-prefixed-English text, but due for a qualified human Tamil agricultural
translator to review before being treated as final. Where no ``*_ta`` field is present for
a given ``*_en`` field, get_recommendation() falls back to ``_ta()``, which prefixes the
untranslated English with a Tamil "verify against the official source" disclaimer rather
than silently showing English as if it were reviewed Tamil content.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any

VERSION = "1.1.0"
DISCLAIMER = "VERIFY AGAINST OFFICIAL SOURCE"

# The date DISEASE_CONTENT was last manually checked against OFFICIAL_SOURCES /
# EXTENSION_SOURCES. This is a historical checkpoint, not a live clock -- it must
# only be bumped by hand when someone actually re-reviews the content against the
# source PDFs, never auto-set to "today" (that would silently claim a review that
# never happened). LAST_VERIFIED_STALE_AFTER_DAYS lets callers/tests detect when
# this checkpoint has aged past its useful shelf life instead of it silently
# rotting with no signal (docs/CLAUDE.md pre-release audit, 2026-08).
LAST_VERIFIED_DATE = "2026-08-15"
LAST_VERIFIED_STALE_AFTER_DAYS = 365

STATUS_PARTIAL = "RECOMMENDATION_PARTIAL"
STATUS_UNVERIFIED = "RECOMMENDATION_NOT_VERIFIED"
STATUS_UNMAPPED = "RUNTIME_LABEL_UNMAPPED"
CHEMICAL_WITHHELD = "CHEMICAL_RECOMMENDATION_WITHHELD"

# Category-level conventional-treatment guidance, keyed by the same
# `category` tag every LABELS entry already carries (fungal/bacterial/viral/
# healthy -- no pest/insect category exists in the current 20-label set).
# Names common, real active-ingredient examples for that category (e.g.
# propiconazole for a systemic fungicide) -- this is standard, widely-known
# agronomic classification, not a per-crop+disease dose recommendation --
# but still never a specific commercial brand or a dose, consistent with
# CHEMICAL_WITHHELD above (exact product + dose per crop+disease hasn't been
# independently verified against the official regulator). Always paired
# with a line sending the farmer to their local Agriculture Officer / KVK for
# the actual product and dose.
_CONVENTIONAL_CATEGORY_EN: dict[str, str] = {
    "fungal": (
        "A protectant or systemic fungicide labelled for this crop and "
        "disease is commonly used -- such as one containing propiconazole, "
        "hexaconazole, or mancozeb. Ask your local Agriculture Officer or "
        "Krishi Vigyan Kendra (KVK) for the specific product and dose."
    ),
    "bacterial": (
        "A copper-based bactericide labelled for this crop is commonly "
        "used -- such as one containing copper oxychloride or copper "
        "hydroxide -- though bacterial diseases are harder to cure "
        "chemically once established -- removing infected material matters "
        "as much as any spray. Ask your local Agriculture Officer or KVK "
        "for the specific product and dose."
    ),
    "viral": (
        "No chemical product cures a viral disease. Conventional management "
        "instead controls the insect vector that spreads it (for example an "
        "insecticide against whitefly or leafhopper) and removes infected "
        "plants. Ask your local Agriculture Officer or KVK which vector "
        "control fits this crop."
    ),
}

# Direct Tamil translations of the English text above (not the generic
# "verify against official source" _ta() fallback used for untranslated
# per-disease PDF content -- these are original, hand-written sentences with
# no PDF source to verify against, so a disclaimer prefix would be
# misleading rather than honest).
_CONVENTIONAL_CATEGORY_TA: dict[str, str] = {
    "fungal": (
        "இந்தப் பயிருக்கும் நோய்க்கும் ஏற்ற பாதுகாப்பு (protectant) அல்லது "
        "உட்புகு (systemic) பூஞ்சைக்கொல்லி பொதுவாகப் பயன்படுத்தப்படுகிறது -- "
        "எடுத்துக்காட்டாக propiconazole, hexaconazole, அல்லது mancozeb "
        "கொண்டவை. குறிப்பிட்ட பொருள் மற்றும் அளவுக்கு உங்கள் உள்ளூர் வேளாண் "
        "அலுவலர் அல்லது கிருஷி விஞ்ஞான கேந்திரத்தை (KVK) அணுகவும்."
    ),
    "bacterial": (
        "இந்தப் பயிருக்கு ஏற்ற காப்பர் அடிப்படையிலான பாக்டீரியாக் கொல்லி "
        "(bactericide) பொதுவாகப் பயன்படுத்தப்படுகிறது -- எடுத்துக்காட்டாக "
        "copper oxychloride அல்லது copper hydroxide கொண்டவை; எனினும் "
        "பாக்டீரியா நோய்கள் ஏற்கனவே பரவிவிட்டால் மருந்தால் மட்டும் "
        "குணப்படுத்துவது கடினம் -- பாதிக்கப்பட்ட பகுதிகளை அகற்றுவதும் அதே "
        "அளவு முக்கியம். குறிப்பிட்ட பொருள் மற்றும் அளவுக்கு உங்கள் உள்ளூர் "
        "வேளாண் அலுவலர் அல்லது KVK-ஐ அணுகவும்."
    ),
    "viral": (
        "வைரஸ் நோய்க்கு எந்த மருந்தும் குணப்படுத்தாது. இதைப் பரப்பும் "
        "பூச்சியைக் கட்டுப்படுத்துவதே (எடுத்துக்காட்டாக வெள்ளை ஈ அல்லது "
        "இலைத்தத்துப் பூச்சிக்கு எதிரான பூச்சிக்கொல்லி) மற்றும் பாதிக்கப்பட்ட "
        "செடிகளை அகற்றுவதே வழக்கமான நிர்வாகம். இந்தப் பயிருக்கு எந்த பூச்சிக் "
        "கட்டுப்பாடு பொருந்தும் என்பதை உங்கள் உள்ளூர் வேளாண் அலுவலர் அல்லது "
        "KVK-இடம் கேட்கவும்."
    ),
}

OFFICIAL_SOURCES = [
    {
        "source_id": "icar_crop_management_11",
        "publisher": "Indian Council of Agricultural Research (ICAR)",
        "title": "Crop Management",
        "url": "https://www.icar.gov.in/sites/default/files/inline-files/CROP-MANAGEMENT-11.pdf",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "icar_deans_disease_management",
        "publisher": "Indian Council of Agricultural Research (ICAR)",
        "title": "Diseases of Field and Horticultural Crops and their Management",
        "url": "https://www.icar.gov.in/sites/default/files/2026-06/SIXTH%20DEANS%20COMMITTEE%20VOL%201%20FINAL%207-3-2026.pdf",
        "source_date": "2026-06-01",
        "official": True,
    },
]

# Government/ICAR/IRRI extension publications used to populate DISEASE_CONTENT.
# These are physical/local reference-library PDFs without a confirmed stable public URL,
# so `url` is left None rather than guessed -- cite by title/publisher instead.
EXTENSION_SOURCES: dict[str, dict[str, Any]] = {
    "tn_ipm_banana_2011": {
        "source_id": "tn_ipm_banana_2011",
        "publisher": "National Horticulture Mission",
        "title": "Integrated Pest Management Package for Banana (Revised, Sept 2011)",
        "url": None,
        "source_date": "2011-09-01",
        "official": True,
    },
    "goi_ipm_banana": {
        "source_id": "goi_ipm_banana",
        "publisher": "Directorate of Plant Protection, Quarantine & Storage, Government of India",
        "title": "Integrated Pest Management Package for Banana",
        "url": None,
        "source_date": None,
        "official": True,
    },
    "icar_nrcb_vision2050": {
        "source_id": "icar_nrcb_vision2050",
        "publisher": "ICAR-National Research Centre for Banana (ICAR-NRCB)",
        "title": "Vision 2050",
        "url": None,
        "source_date": None,
        "official": True,
    },
    "tnau_agriculture_guide": {
        "source_id": "tnau_agriculture_guide",
        "publisher": "Government of Tamil Nadu / Tamil Nadu Agricultural University (TNAU)",
        "title": "Crop Production Guide - Agriculture (2020)",
        "url": None,
        "source_date": "2020-01-01",
        "official": True,
    },
    "tn_pest_forecast_2026_01": {
        "source_id": "tn_pest_forecast_2026_01",
        "publisher": "Tamil Nadu Agriculture Department / TNAU",
        "title": "Pest and Disease Forecast (January 2026)",
        "url": None,
        "source_date": "2026-01-01",
        "official": True,
    },
    "irri_rice_steps": {
        "source_id": "irri_rice_steps",
        "publisher": "International Rice Research Institute (IRRI)",
        "title": "Steps Required for Successful Rice Production",
        "url": None,
        "source_date": None,
        "official": True,
    },
    "goi_pest_management_sop": {
        "source_id": "goi_pest_management_sop",
        "publisher": "Government of India",
        "title": "Integrated Pest Management - Standard Operating Procedures",
        "url": None,
        "source_date": None,
        "official": True,
    },
    "goi_ipm_chilli_capsicum": {
        "source_id": "goi_ipm_chilli_capsicum",
        "publisher": "Directorate of Plant Protection, Quarantine & Storage, Government of India",
        "title": "Integrated Pest Management Package for Chillies and Capsicum",
        "url": None,
        "source_date": None,
        "official": True,
    },
    "icar_iisr_chilli_gap": {
        "source_id": "icar_iisr_chilli_gap",
        "publisher": "ICAR-Indian Institute of Spices Research",
        "title": "Good Agricultural Practices for Chilli Cultivation",
        "url": None,
        "source_date": None,
        "official": True,
    },
    "goi_ipm_pigeonpea": {
        "source_id": "goi_ipm_pigeonpea",
        "publisher": "Directorate of Plant Protection, Quarantine & Storage, Government of India",
        "title": "Integrated Pest Management Package for Pigeonpea",
        "url": None,
        "source_date": "2001-01-01",
        "official": True,
    },
    "tnau_agritech_paddy_expert_system": {
        "source_id": "tnau_agritech_paddy_expert_system",
        "publisher": "Tamil Nadu Agricultural University (TNAU) Agritech Portal",
        "title": "Expert System - Paddy - Brown Spot",
        "url": "https://agritech.tnau.ac.in/expert_system/paddy/cpdisbrownspot.html",
        "source_date": None,
        "official": True,
    },
    "tnau_agritech_cotton_diseases": {
        "source_id": "tnau_agritech_cotton_diseases",
        "publisher": "Tamil Nadu Agricultural University (TNAU) Agritech Portal",
        "title": "Crop Protection - Cotton Diseases",
        "url": "https://agritech.tnau.ac.in/crop_protection/cotton_diseases/cotton_d2.html",
        "source_date": None,
        "official": True,
    },
    "tnau_agritech_chilli_diseases": {
        "source_id": "tnau_agritech_chilli_diseases",
        "publisher": "Tamil Nadu Agricultural University (TNAU) Agritech Portal",
        "title": "Crop Protection - Chilli Diseases",
        "url": "https://agritech.tnau.ac.in/crop_protection/chilli_diseases_4.html",
        "source_date": None,
        "official": True,
    },
    "legume_research_2018_pigeonpea_alternaria": {
        "source_id": "legume_research_2018_pigeonpea_alternaria",
        "publisher": "Legume Research (NAAS-accredited Indian journal), not a government/extension body",
        "title": "Balai, Singh, Sinha & Yadav (2018), \"Evaluation of different fungicides and antagonists In vitro and In vivo condition against Alternaria blight of pigeonpea\", Legume Research 43(2):268-275",
        "url": None,
        "source_date": "2018-01-01",
        "official": False,
    },
}

# Exact frozen runtime labels.  A label missing here is never given a recommendation.
LABELS: dict[str, tuple[str, str, str, str, str]] = {
    "banana__healthy": ("banana", "banana_healthy", "Healthy banana plant", "வாழை செடி ஆரோக்கியமாக உள்ளது", "healthy"),
    "banana__cordana_leaf_spot": ("banana", "banana_cordana_leaf_spot", "Cordana leaf spot", "கோர்டானா இலைப்புள்ளி", "fungal"),
    "banana__pestalotiopsis_leaf_spot": ("banana", "banana_pestalotiopsis_leaf_spot", "Pestalotiopsis leaf spot", "பெஸ்டலோட்டியாப்சிஸ் இலைப்புள்ளி", "fungal"),
    "banana__sigatoka_leaf_spot": ("banana", "banana_sigatoka_leaf_spot", "Sigatoka leaf spot", "சிகடோகா இலைப்புள்ளி", "fungal"),
    "paddy_healthy": ("paddy", "paddy_healthy", "Healthy paddy plant", "நெல் செடி ஆரோக்கியமாக உள்ளது", "healthy"),
    "rice_blast": ("paddy", "paddy_blast", "Rice blast", "நெல் குலைநோய்", "fungal"),
    "rice_brown_leaf_spot": ("paddy", "paddy_brown_spot", "Rice brown spot", "நெல் பழுப்பு இலைப்புள்ளி", "fungal"),
    "rice_tungro": ("paddy", "paddy_tungro", "Rice tungro", "நெல் டங்ரோ நோய்", "viral"),
    "cotton_fusarium_wilt": ("cotton", "cotton_fusarium_wilt", "Fusarium wilt", "பருத்தி ஃபியூசேரியம் வாடல்", "fungal"),
    "cotton_healthy": ("cotton", "cotton_healthy", "Healthy cotton plant", "பருத்தி செடி ஆரோக்கியமாக உள்ளது", "healthy"),
    "cotton_verticillium_wilt": ("cotton", "cotton_verticillium_wilt", "Verticillium wilt", "பருத்தி வெர்டிசில்லியம் வாடல்", "fungal"),
    "groundnut_healthy": ("groundnut", "groundnut_healthy", "Healthy groundnut plant", "நிலக்கடலை செடி ஆரோக்கியமாக உள்ளது", "healthy"),
    "groundnut_rust": ("groundnut", "groundnut_rust", "Groundnut rust", "நிலக்கடலை துரு நோய்", "fungal"),
    "chilli__bacterial_spot": ("chilli", "chilli_bacterial_spot", "Bacterial spot", "மிளகாய் பாக்டீரியா இலைப்புள்ளி", "bacterial"),
    "chilli__cercospora_leaf_spot": ("chilli", "chilli_cercospora_leaf_spot", "Cercospora leaf spot", "மிளகாய் செர்கோஸ்போரா இலைப்புள்ளி", "fungal"),
    "chilli__healthy": ("chilli", "chilli_healthy", "Healthy chilli plant", "மிளகாய் செடி ஆரோக்கியமாக உள்ளது", "healthy"),
    "chilli__leaf_curl_virus": ("chilli", "chilli_leaf_curl_virus", "Chilli leaf curl virus", "மிளகாய் இலைச்சுருள் வைரஸ்", "viral"),
    "redgram__healthy": ("redgram", "redgram_healthy", "Healthy redgram plant", "துவரை செடி ஆரோக்கியமாக உள்ளது", "healthy"),
    "redgram__leaf_spot": ("redgram", "redgram_leaf_spot", "Redgram leaf spot", "துவரை இலைப்புள்ளி", "fungal"),
    "redgram__sterility_mosaic": ("redgram", "redgram_sterility_mosaic", "Sterility mosaic disease", "துவரை மலட்டுத் தேமல் நோய்", "viral"),
}

RESTRICTED_CROPS = frozenset({"chilli", "redgram"})

# Real, source-grounded content keyed by canonical_disease_id (LABELS[...][1]).
# A field that a source genuinely doesn't cover is OMITTED here (never guessed) --
# get_recommendation() falls back to the original generic text for that field only.
DISEASE_CONTENT: dict[str, dict[str, Any]] = {
    "banana_healthy": {
        "symptoms_en": [
            "Full green leaf canopy with no brown streaking, spotting, or premature drying (roughly 17-20 green leaves during the vegetative phase, 12-15 at flowering, 7-10 at harvest is normal)",
            "Pseudostem and corm are firm, without weevil tunnels, oozing, or discoloration",
            "Bunch fills out normally with no small/stunted fingers or premature ripening",
        ],
        "why_it_occurs_en": [
            "Planting healthy, disease-free suckers/rhizomes from clean plantations",
            "Recommended spacing, planting time, drainage, and balanced fertilizer/manure application",
            "Regular field sanitation and pest/disease monitoring",
        ],
        "cultural_management_en": [
            "Select and plant healthy, infestation-free suckers from disease-free plantations",
            "Maintain recommended spacing and plant in the recommended planting months",
            "Ensure good field drainage and regular sanitation (remove dried leaves and plant debris)",
            "Apply recommended manures/fertilizers -- trials with organic inputs (compost, vermicompost, neem cake, poultry manure) were linked to more vigorous growth and higher yield",
        ],
        "prevention_en": [
            "Regular field scouting/monitoring to catch problems early",
            "Field sanitation -- remove and destroy dried leaves, plant debris, and post-harvest crop residues",
            "Balanced nutrition and proper drainage/irrigation to keep the plant vigorous",
        ],
        "symptoms_ta": [
            "பச்சை இலைகள் நிறைந்த முழுமையான இலைக்கூடாரம், பழுப்பு கோடுகள், புள்ளிகள் அல்லது முன்கூட்டியே உலர்தல் இல்லாமல் (வளர்ச்சி நிலையில் தோராயமாக 17-20 பச்சை இலைகள், பூக்கும் நிலையில் 12-15, அறுவடை நேரத்தில் 7-10 இலைகள் இருப்பது இயல்பானது)",
            "தண்டு (போலித்தண்டு) மற்றும் கிழங்கு உறுதியாக இருக்கும்; வண்டு துளைகள், கசிவு அல்லது நிறமாற்றம் இல்லாமல் இருக்கும்",
            "குலை இயல்பாக நிரம்பும்; சிறிய/வளர்ச்சி குன்றிய விரல்கள் அல்லது முன்கூட்டியே பழுத்தல் இருக்காது",
        ],
        "why_it_occurs_ta": [
            "சுத்தமான தோட்டங்களில் இருந்து ஆரோக்கியமான, நோயற்ற கன்று/கிழங்குகளை நடுதல்",
            "பரிந்துரைக்கப்பட்ட இடைவெளி, நடும் காலம், வடிகால் மற்றும் சமச்சீரான உர/எரு பயன்பாடு",
            "தொடர்ச்சியான வயல் சுத்தம் மற்றும் பூச்சி/நோய் கண்காணிப்பு",
        ],
        "cultural_management_ta": [
            "நோயற்ற தோட்டங்களில் இருந்து ஆரோக்கியமான, பாதிப்பில்லாத கன்றுகளைத் தேர்ந்தெடுத்து நடவும்",
            "பரிந்துரைக்கப்பட்ட இடைவெளியைப் பராமரித்து, பரிந்துரைக்கப்பட்ட நடவு மாதங்களில் நடவும்",
            "வயலில் நல்ல வடிகால் மற்றும் தொடர் சுத்தத்தை உறுதி செய்யவும் (உலர்ந்த இலைகள் மற்றும் தாவர எச்சங்களை அகற்றவும்)",
            "பரிந்துரைக்கப்பட்ட எரு/உரங்களைப் பயன்படுத்தவும் -- இயற்கை உரங்கள் (கம்போஸ்ட், மண்புழு உரம், வேப்பம் பிண்ணாக்கு, கோழி எரு) பயன்படுத்திய சோதனைகளில் அதிக வளர்ச்சி மற்றும் அதிக விளைச்சல் கண்டறியப்பட்டது",
        ],
        "prevention_ta": [
            "பிரச்சனைகளை முன்கூட்டியே கண்டறிய தொடர்ந்து வயல் கண்காணிப்பு செய்யவும்",
            "வயல் சுத்தம் -- உலர்ந்த இலைகள், தாவர எச்சங்கள் மற்றும் அறுவடைக்குப் பிந்தைய பயிர் கழிவுகளை அகற்றி அழிக்கவும்",
            "செடியின் வலிமையைப் பராமரிக்க சமச்சீர் ஊட்டச்சத்து மற்றும் சரியான வடிகால்/பாசனம் தேவை",
        ],
        "_source_ids": ["tn_ipm_banana_2011", "goi_ipm_banana", "icar_nrcb_vision2050"],
        "_source_note": "IPM-Banana-Revised-Sept2011.pdf p.1,7-8; pest_management_for_banana.pdf p.1,3-4,9; vision2050.pdf p.2",
    },
    "banana_sigatoka_leaf_spot": {
        "symptoms_en": [
            "Light green, narrow specks about 1 mm long on the upper surface of older leaves",
            "Spots turn brown and the tissue dies, causing extensive defoliation",
            "In severe cases the whole leaf dries starting from the tip; bunches show small fingers, premature ripening, and peel splitting",
        ],
        "cause_en": "Fungal leaf-spot disease caused by Mycosphaerella species -- M. fijiensis (Black Sigatoka), M. musicola (Yellow Sigatoka), and M. eumusae (Septoria leaf spot).",
        "why_it_occurs_en": [
            "Closer plant spacing increases disease severity",
            "Poor drainage/water-logging raises humidity, which favours infection",
            "Lack of regular field sanitation and year-round (rather than seasonal) banana planting",
        ],
        "cultural_management_en": [
            "Regular field sanitation and removal/destruction of infected leaves (burn outside the field or bury in a manure pit), starting 2 months after planting and repeated monthly",
            "Plant at recommended wider spacing (about 1.5 x 1.5 m) in the recommended planting months",
            "Ensure proper drainage to prevent water-logging",
            "Timely sucker removal, weed-free cultivation, and balanced fertilizer/organic nutrition (compost, vermicompost, neem cake, poultry manure) were associated with significantly less Sigatoka in trials",
        ],
        "prevention_en": [
            "Plant in the recommended months at recommended spacing with recommended manure/fertilizer doses",
            "Avoid using diseased leaves to wrap banana bunches or as packing material -- this spreads the fungus, along with wind-borne and water-borne spores",
            "Maintain ongoing field sanitation and good drainage throughout the crop cycle",
        ],
        "symptoms_ta": [
            "பழைய இலைகளின் மேற்பரப்பில் சுமார் 1 மி.மீ நீளமுள்ள வெளிர் பச்சை, குறுகிய புள்ளிகள்",
            "புள்ளிகள் பழுப்பு நிறமாக மாறி திசு இறந்து, பரவலான இலை உதிர்தலை ஏற்படுத்தும்",
            "கடுமையான நிலைகளில் இலை முழுவதும் நுனியில் இருந்து உலர ஆரம்பிக்கும்; குலைகளில் சிறிய விரல்கள், முன்கூட்டிய பழுத்தல் மற்றும் தோல் வெடிப்பு தென்படும்",
        ],
        "cause_ta": "Mycosphaerella இனத்தைச் சேர்ந்த பூஞ்சைகளால் ஏற்படும் இலைப்புள்ளி நோய் -- M. fijiensis (கருப்பு சிகடோகா), M. musicola (மஞ்சள் சிகடோகா), மற்றும் M. eumusae (செப்டோரியா இலைப்புள்ளி).",
        "why_it_occurs_ta": [
            "நெருக்கமான நடவு இடைவெளி நோயின் தீவிரத்தை அதிகரிக்கிறது",
            "மோசமான வடிகால்/நீர் தேங்குதல் ஈரப்பதத்தை அதிகரித்து, நோய்த்தொற்றுக்கு உகந்ததாக இருக்கும்",
            "தொடர் வயல் சுத்தம் இல்லாமை மற்றும் பருவகால நடவுக்கு பதிலாக ஆண்டு முழுவதும் வாழை நடுதல்",
        ],
        "cultural_management_ta": [
            "தொடர் வயல் சுத்தம் மற்றும் பாதிக்கப்பட்ட இலைகளை அகற்றி அழித்தல் (வயலுக்கு வெளியே எரித்தல் அல்லது எருக் குழியில் புதைத்தல்), நடவு செய்த 2 மாதங்களுக்குப் பிறகு தொடங்கி மாதந்தோறும் மீண்டும் செய்யவும்",
            "பரிந்துரைக்கப்பட்ட நடவு மாதங்களில் பரந்த இடைவெளியில் (சுமார் 1.5 x 1.5 மீ) நடவும்",
            "நீர் தேங்குவதைத் தடுக்க சரியான வடிகாலை உறுதி செய்யவும்",
            "சரியான நேரத்தில் கன்று அகற்றுதல், களை இல்லாத பயிரிடல் மற்றும் சமச்சீர் உரம்/இயற்கை ஊட்டச்சத்து (கம்போஸ்ட், மண்புழு உரம், வேப்பம் பிண்ணாக்கு, கோழி எரு) ஆகியவை சோதனைகளில் குறிப்பிடத்தக்க அளவு குறைவான சிகடோகாவுடன் தொடர்புடையதாக இருந்தது",
        ],
        "prevention_ta": [
            "பரிந்துரைக்கப்பட்ட மாதங்களில், பரிந்துரைக்கப்பட்ட இடைவெளியில், பரிந்துரைக்கப்பட்ட எரு/உர அளவுகளுடன் நடவும்",
            "வாழைக் குலைகளைப் போர்த்தவோ அல்லது பேக்கிங் பொருளாகவோ நோய்வாய்ப்பட்ட இலைகளைப் பயன்படுத்த வேண்டாம் -- இது காற்று மற்றும் நீர் மூலம் பரவும் வித்துகளுடன் சேர்ந்து பூஞ்சையைப் பரப்பும்",
            "பயிர் சுழற்சி முழுவதும் தொடர்ந்து வயல் சுத்தம் மற்றும் நல்ல வடிகாலைப் பராமரிக்கவும்",
        ],
        "_source_ids": ["tn_ipm_banana_2011", "goi_ipm_banana", "icar_nrcb_vision2050"],
        "_source_note": "IPM-Banana-Revised-Sept2011.pdf p.6-8; pest_management_for_banana.pdf p.9-10; vision2050.pdf p.2",
    },
    "paddy_healthy": {
        "symptoms_en": [
            "Uniform, healthy-looking crop stand with green foliage and no yellowing, spotting, or wilting",
            "Vigorous, even-sized seedlings/tillers with no discoloration",
            "Well-filled grains at maturity, same colour, with no cracks or spotting",
        ],
        "why_it_occurs_en": [
            "Field was well-prepared and levelled, giving a uniform crop able to compete with weeds",
            "Clean, pure, certified seed used, with nitrogen applied in split doses rather than over-applied",
            "Crop planted on time / in sync with neighbouring fields, reducing pest and disease pressure",
        ],
        "cultural_management_en": [
            "Use clean, pure, certified seed and resistant varieties suited to the season",
            "Maintain a well-levelled, weed-free field with well-constructed bunds",
            "Plant at the same time as neighbouring fields to minimise pest/disease pressure",
            "Follow split nitrogen application rather than over-applying fertilizer",
        ],
        "prevention_en": [
            "Practice good field/equipment sanitation between seasons (manage stubbles and ratoons, maintain bunds)",
            "Avoid unnecessary pesticide use so natural enemies of pests are conserved",
            "Rogue out off-type or clearly diseased plants during vegetative, flowering, and grain-filling stages",
        ],
        "symptoms_ta": [
            "பச்சை இலைகளுடன் ஒரே சீரான, ஆரோக்கியமான பயிர் தோற்றம்; மஞ்சள் நிறமாதல், புள்ளிகள் அல்லது வாடல் இல்லாமல்",
            "நிறமாற்றம் இல்லாத வலிமையான, சீரான அளவிலான நாற்று/பிளவுகள்",
            "முதிர்ச்சியில் நன்கு நிரம்பிய தானியங்கள், ஒரே நிறத்தில், விரிசல் அல்லது புள்ளிகள் இல்லாமல்",
        ],
        "why_it_occurs_ta": [
            "வயல் நன்கு தயார் செய்யப்பட்டு சமன் செய்யப்பட்டதால், களைகளுடன் போட்டியிட வல்ல சீரான பயிர் கிடைத்தது",
            "சுத்தமான, தூய, சான்றளிக்கப்பட்ட விதை பயன்படுத்தப்பட்டது; நைட்ரஜன் அதிகமாகப் பயன்படுத்தப்படாமல் பிரிவு அளவுகளாக இடப்பட்டது",
            "அருகிலுள்ள வயல்களுடன் ஒத்திசைவாக/சரியான நேரத்தில் பயிர் நடப்பட்டதால், பூச்சி மற்றும் நோய் அழுத்தம் குறைந்தது",
        ],
        "cultural_management_ta": [
            "சுத்தமான, தூய, சான்றளிக்கப்பட்ட விதை மற்றும் பருவத்திற்கு ஏற்ற எதிர்ப்புத் திறன் கொண்ட ரகங்களைப் பயன்படுத்தவும்",
            "நன்கு சமன் செய்யப்பட்ட, களை இல்லாத வயலை நன்கு கட்டமைக்கப்பட்ட வரம்புகளுடன் பராமரிக்கவும்",
            "பூச்சி/நோய் அழுத்தத்தைக் குறைக்க அருகிலுள்ள வயல்களுடன் அதே நேரத்தில் நடவும்",
            "உரத்தை அதிகமாகப் பயன்படுத்துவதற்குப் பதிலாக நைட்ரஜனைப் பிரிவு அளவுகளாக இடவும்",
        ],
        "prevention_ta": [
            "பருவங்களுக்கு இடையே நல்ல வயல்/கருவி சுத்தத்தைக் கடைப்பிடிக்கவும் (தாள்/மறுமுளைப் பயிரை நிர்வகித்தல், வரம்புகளைப் பராமரித்தல்)",
            "பூச்சிகளின் இயற்கை எதிரிகளைப் பாதுகாக்க தேவையற்ற பூச்சிக்கொல்லி பயன்பாட்டைத் தவிர்க்கவும்",
            "வளர்ச்சி, பூக்கும் மற்றும் தானிய நிரப்பும் நிலைகளில் மாறுபட்ட அல்லது தெளிவாக நோய்வாய்ப்பட்ட செடிகளை அகற்றவும்",
        ],
        "_source_ids": ["irri_rice_steps", "tnau_agriculture_guide"],
        "_source_note": "Steps-Required-for-Successful-Rice-Production.pdf p.8,10,12,22; AGRICULTURE.pdf (seedling retention guidance)",
    },
    "paddy_blast": {
        "symptoms_en": [
            "Occurs in two recognised forms: leaf blast and neck/panicle blast, sometimes appearing together with other diseases as a combined infection",
        ],
        "cause_en": "Caused by the fungus Pyricularia grisea (teleomorph Magnaporthe grisea).",
        "why_it_occurs_en": [
            "Regional outbreaks linked to prevailing weather conditions",
            "Excess nitrogen application increases disease incidence",
            "Some released varieties remain susceptible (e.g. Improved White Ponni is noted as blast-susceptible)",
        ],
        "cultural_management_en": [
            "Remove collateral weed hosts from bunds and channels",
            "Use only disease-free seedlings",
            "Avoid excess nitrogen; apply in three split doses (50% basal, 25% at tillering, 25% at panicle initiation)",
            "Use resistant or moderately resistant varieties in blast-endemic areas",
        ],
        "biological_options_en": [
            "Seed treatment with a Pseudomonas fluorescens formulation",
            "Seedling root-dip in a Pseudomonas fluorescens formulation",
            "Soil application and/or foliar spray of a Pseudomonas fluorescens formulation",
        ],
        "prevention_en": [
            "Plant resistant/moderately resistant varieties, especially in known blast-endemic areas",
            "Avoid excess nitrogen and follow split-dose fertilizer schedules",
            "Use disease-free seedlings and remove weed hosts from bunds/channels before the season",
        ],
        "symptoms_ta": [
            "இரண்டு அறியப்பட்ட வடிவங்களில் ஏற்படுகிறது: இலை குலைநோய் மற்றும் கழுத்து/கதிர் குலைநோய், சில நேரங்களில் மற்ற நோய்களுடன் இணைந்த தொற்றாகவும் தோன்றலாம்",
        ],
        "cause_ta": "Pyricularia grisea (Magnaporthe grisea) என்ற பூஞ்சையால் ஏற்படுகிறது.",
        "why_it_occurs_ta": [
            "பிராந்திய வெடிப்புகள் நிலவும் வானிலை நிலைமைகளுடன் தொடர்புடையவை",
            "அதிகப்படியான நைட்ரஜன் பயன்பாடு நோய் ஏற்படும் வாய்ப்பை அதிகரிக்கிறது",
            "வெளியிடப்பட்ட சில ரகங்கள் இன்னும் பாதிப்புக்கு உட்பட்டவையாக உள்ளன (எ.கா. இம்ப்ரூவ்டு வெள்ளை பொன்னி குலைநோய்க்கு பாதிக்கப்படக்கூடியதாகக் குறிப்பிடப்படுகிறது)",
        ],
        "cultural_management_ta": [
            "வரம்புகள் மற்றும் வாய்க்கால்களில் இருந்து இடையக களை புரவலன்களை அகற்றவும்",
            "நோயற்ற நாற்றுகளை மட்டுமே பயன்படுத்தவும்",
            "அதிகப்படியான நைட்ரஜனைத் தவிர்க்கவும்; மூன்று பிரிவு அளவுகளாக இடவும் (50% அடிப்படை, 25% பிளவு நிலையில், 25% கதிர் தொடக்க நிலையில்)",
            "குலைநோய் பாதிப்பு அதிகம் உள்ள பகுதிகளில் எதிர்ப்புத் திறன் கொண்ட அல்லது மிதமான எதிர்ப்புத் திறன் கொண்ட ரகங்களைப் பயன்படுத்தவும்",
        ],
        "biological_options_ta": [
            "Pseudomonas fluorescens கலவையுடன் விதை நேர்த்தி செய்யவும்",
            "Pseudomonas fluorescens கலவையில் நாற்று வேரை நனைத்தல்",
            "Pseudomonas fluorescens கலவையை மண்ணில் இடுதல் மற்றும்/அல்லது இலைகளில் தெளித்தல்",
        ],
        "prevention_ta": [
            "குறிப்பாக குலைநோய் பாதிப்பு அதிகம் உள்ள பகுதிகளில் எதிர்ப்புத் திறன்/மிதமான எதிர்ப்புத் திறன் கொண்ட ரகங்களை நடவும்",
            "அதிகப்படியான நைட்ரஜனைத் தவிர்த்து, பிரிவு அளவு உர அட்டவணையைப் பின்பற்றவும்",
            "பருவத்திற்கு முன் நோயற்ற நாற்றுகளைப் பயன்படுத்தி, வரம்புகள்/வாய்க்கால்களில் இருந்து களை புரவலன்களை அகற்றவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide", "tn_pest_forecast_2026_01"],
        "_source_note": "AGRICULTURE.pdf disease-management table + variety notes; PEST FORECAST.pdf (Jan 2026) p.1",
    },
    "paddy_brown_spot": {
        "cause_en": "Caused by the fungus Drechslera oryzae (teleomorph Cochliobolus miyabeanus).",
        "cultural_management_en": [
            "Use clean, pure, certified seed",
            "Avoid over-applying nitrogen fertilizer; follow recommended doses",
            "Practice field sanitation between seasons (manage stubbles/ratoons, maintain bunds)",
        ],
        "biological_options_en": [
            "Seed treatment with Pseudomonas fluorescens (about 10 g per kg of seed), followed by a seedling dip in a Pseudomonas fluorescens solution before transplanting",
        ],
        "prevention_en": [
            "Follow balanced/split fertilizer recommendations rather than over-applying nitrogen",
            "Use clean, certified seed each season",
            "Seek prompt diagnosis, since brown spot is also documented occurring together with blast",
        ],
        "cause_ta": "Drechslera oryzae (Cochliobolus miyabeanus) என்ற பூஞ்சையால் ஏற்படுகிறது.",
        "cultural_management_ta": [
            "சுத்தமான, தூய, சான்றளிக்கப்பட்ட விதையைப் பயன்படுத்தவும்",
            "நைட்ரஜன் உரத்தை அதிகமாகப் பயன்படுத்துவதைத் தவிர்த்து, பரிந்துரைக்கப்பட்ட அளவுகளைப் பின்பற்றவும்",
            "பருவங்களுக்கு இடையே வயல் சுத்தத்தைக் கடைப்பிடிக்கவும் (தாள்/மறுமுளைப் பயிரை நிர்வகித்தல், வரம்புகளைப் பராமரித்தல்)",
        ],
        "biological_options_ta": [
            "Pseudomonas fluorescens உடன் விதை நேர்த்தி செய்யவும் (சுமார் 10 கிராம் ஒரு கிலோ விதைக்கு), நடவு செய்வதற்கு முன் நாற்றுகளை Pseudomonas fluorescens கரைசலில் நனைக்கவும்",
        ],
        "prevention_ta": [
            "நைட்ரஜனை அதிகமாகப் பயன்படுத்துவதற்குப் பதிலாக சமச்சீர்/பிரிவு உர பரிந்துரைகளைப் பின்பற்றவும்",
            "ஒவ்வொரு பருவத்திலும் சுத்தமான, சான்றளிக்கப்பட்ட விதையைப் பயன்படுத்தவும்",
            "பழுப்பு புள்ளி நோய் குலைநோயுடன் இணைந்தும் ஏற்படுவதாக ஆவணப்படுத்தப்பட்டுள்ளதால், உடனடியாக நோய் கண்டறிதலைப் பெறவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide", "tnau_agritech_paddy_expert_system"],
        "_source_note": "AGRICULTURE.pdf disease-management table (cause and general seed/fertilizer guidance); TNAU Agritech Portal Expert System - Paddy - Brown Spot page (biological seed-treatment/seedling-dip protocol)",
    },
    "paddy_tungro": {
        "cause_en": "Caused by Rice tungro Bacilliform virus and Rice tungro Spherical virus, transmitted by green leafhopper vectors.",
        "why_it_occurs_en": [
            "Driven by green leafhopper vector populations feeding on the crop and spreading the virus",
            "Risk is elevated in known tungro-endemic areas, where the vector monitoring threshold is set lower than in non-endemic areas",
        ],
        "cultural_management_en": [
            "Set up light traps to attract, monitor, and reduce the leafhopper vector population",
            "Monitor green leafhopper numbers regularly, especially in tungro-endemic areas",
        ],
        "prevention_en": [
            "Monitor and manage green leafhopper vector populations proactively, particularly in tungro-endemic areas",
            "Use light traps to track and reduce vector activity",
            "Use short-duration/resistant cultivars and synchronised, community-wide planting to reduce vector and virus pressure",
        ],
        "cause_ta": "பச்சை தத்துப்பூச்சி வாகக பூச்சிகள் மூலம் பரவும் Rice tungro Bacilliform வைரஸ் மற்றும் Rice tungro Spherical வைரஸால் ஏற்படுகிறது.",
        "why_it_occurs_ta": [
            "பயிரை உண்டு வைரஸைப் பரப்பும் பச்சை தத்துப்பூச்சி எண்ணிக்கையால் இயக்கப்படுகிறது",
            "டங்ரோ நோய் அதிகமுள்ள பகுதிகளில் ஆபத்து அதிகரிக்கிறது; அங்கு வாகக பூச்சி கண்காணிப்பு வரம்பு பாதிக்கப்படாத பகுதிகளை விட குறைவாக அமைக்கப்பட்டுள்ளது",
        ],
        "cultural_management_ta": [
            "தத்துப்பூச்சி வாகக பூச்சி எண்ணிக்கையை ஈர்க்க, கண்காணிக்க மற்றும் குறைக்க ஒளிப் பொறிகளை அமைக்கவும்",
            "குறிப்பாக டங்ரோ நோய் அதிகமுள்ள பகுதிகளில் பச்சை தத்துப்பூச்சி எண்ணிக்கையை தொடர்ந்து கண்காணிக்கவும்",
        ],
        "prevention_ta": [
            "குறிப்பாக டங்ரோ நோய் அதிகமுள்ள பகுதிகளில் வாகக பூச்சி எண்ணிக்கையை முன்கூட்டியே கண்காணித்து நிர்வகிக்கவும்",
            "வாகக பூச்சி செயல்பாட்டைக் கண்காணிக்க மற்றும் குறைக்க ஒளிப் பொறிகளைப் பயன்படுத்தவும்",
            "வாகக பூச்சி மற்றும் வைரஸ் அழுத்தத்தைக் குறைக்க குறுகிய கால/எதிர்ப்புத் திறன் கொண்ட ரகங்கள் மற்றும் ஒத்திசைவான, சமூக அளவிலான நடவை பயன்படுத்தவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide"],
        "_source_note": "AGRICULTURE.pdf disease-management table (Physical/vector-monitoring methods only; no symptom description in this source)",
    },
    "cotton_healthy": {
        "symptoms_en": [
            "Uniform, vigorous stand with normal seedling vigour and no wilting, spotting, or stunting",
        ],
        "cultural_management_en": [
            "Retain only one healthy, vigorous seedling per hill when thinning",
            "Adopt proper crop rotation; remove and dispose of crop residues promptly after harvest rather than stacking stalks in the field",
            "Synchronise village-wide sowing dates and grow one variety throughout the area where possible",
        ],
        "prevention_en": [
            "Use recommended, locally-adapted varieties and proper seed treatment before sowing",
            "Maintain optimum irrigation and fertilizer schedules for each crop-growth stage",
        ],
        "symptoms_ta": [
            "இயல்பான நாற்று வலிமையுடன் சீரான, வலிமையான பயிர் தோற்றம்; வாடல், புள்ளிகள் அல்லது வளர்ச்சி குன்றுதல் இல்லாமல்",
        ],
        "cultural_management_ta": [
            "நேர்த்தி செய்யும்போது ஒவ்வொரு குழியிலும் ஒரு ஆரோக்கியமான, வலிமையான நாற்றை மட்டும் விட்டு வையுங்கள்",
            "சரியான பயிர் சுழற்சியை மேற்கொள்ளவும்; வயலில் தண்டுகளைக் குவிப்பதற்குப் பதிலாக அறுவடைக்குப் பிறகு உடனடியாக பயிர் எச்சங்களை அகற்றி அப்புறப்படுத்தவும்",
            "கிராமம் முழுவதும் நடவு தேதிகளை ஒத்திசைத்து, முடிந்தவரை பகுதி முழுவதும் ஒரே ரகத்தை வளர்க்கவும்",
        ],
        "prevention_ta": [
            "பரிந்துரைக்கப்பட்ட, உள்ளூருக்கு ஏற்ற ரகங்களைப் பயன்படுத்தி விதைப்பதற்கு முன் சரியான விதை நேர்த்தி செய்யவும்",
            "ஒவ்வொரு பயிர் வளர்ச்சி நிலையிலும் உகந்த பாசனம் மற்றும் உர அட்டவணையைப் பராமரிக்கவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide", "goi_pest_management_sop"],
        "_source_note": "AGRICULTURE.pdf p.265,266,271 (Cotton crop management/protection); Pest_management.pdf p.12-13 ('Grow a Healthy Crop' IPM principle)",
    },
    "cotton_fusarium_wilt": {
        "cause_en": "Fusarium oxysporum f. sp. vasinfectum, listed alongside Rhizoctonia solani (the damping-off agent) under this crop's combined disease-management entry.",
        "why_it_occurs_en": [
            "Land history matters -- sowing is advised against on land with a recent history of wilt disease",
        ],
        "cultural_management_en": [
            "Avoid sowing on land with a recent history of wilt disease; do not repeat the same variety/crop on affected land without certification",
            "Adopt proper crop rotation; remove and dispose of crop residues promptly after harvest rather than leaving/stacking stalks in the field",
            "Sanitation -- remove, destroy, or deep-bury diseased plant material and burn crop residue to reduce carryover between crops",
        ],
        "biological_options_en": [
            "Seed treatment with a Pseudomonas fluorescens + Bacillus subtilis + Trichoderma asperellum mixture, with soil application of the same mixture at sowing and again at 90 days after sowing",
        ],
        "prevention_en": [
            "Ensure planting land is free of volunteer plants and known wilt-disease history before sowing",
            "Use seed-/soil-applied biocontrol treatment at sowing",
            "Practice crop rotation and prompt residue removal after harvest",
        ],
        "cause_ta": "Fusarium oxysporum f. sp. vasinfectum, Rhizoctonia solani (நாற்று அழுகல் காரணி) உடன் இணைந்து இப்பயிரின் ஒருங்கிணைந்த நோய் மேலாண்மைப் பதிவில் பட்டியலிடப்பட்டுள்ளது.",
        "why_it_occurs_ta": [
            "நிலத்தின் வரலாறு முக்கியமானது -- சமீபத்திய வாடல் நோய் வரலாறு உள்ள நிலத்தில் விதைப்பது பரிந்துரைக்கப்படவில்லை",
        ],
        "cultural_management_ta": [
            "சமீபத்திய வாடல் நோய் வரலாறு உள்ள நிலத்தில் விதைப்பதைத் தவிர்க்கவும்; சான்றளிப்பு இல்லாமல் பாதிக்கப்பட்ட நிலத்தில் அதே ரகம்/பயிரை மீண்டும் விதைக்க வேண்டாம்",
            "சரியான பயிர் சுழற்சியை மேற்கொள்ளவும்; வயலில் தண்டுகளை விட்டு வைப்பதற்கு/குவிப்பதற்குப் பதிலாக அறுவடைக்குப் பிறகு உடனடியாக பயிர் எச்சங்களை அகற்றி அப்புறப்படுத்தவும்",
            "சுத்தம் -- பயிர்களுக்கு இடையே பரவுவதைக் குறைக்க நோய்வாய்ப்பட்ட தாவரப் பொருட்களை அகற்றி, அழித்து அல்லது ஆழமாகப் புதைத்து, பயிர் எச்சங்களை எரிக்கவும்",
        ],
        "biological_options_ta": [
            "Pseudomonas fluorescens + Bacillus subtilis + Trichoderma asperellum கலவையுடன் விதை நேர்த்தி செய்து, விதைக்கும் நேரத்திலும் விதைத்த 90 நாட்களுக்குப் பிறகும் அதே கலவையை மண்ணில் இடவும்",
        ],
        "prevention_ta": [
            "விதைப்பதற்கு முன் நடவு நிலம் தானாக முளைத்த செடிகள் மற்றும் அறியப்பட்ட வாடல் நோய் வரலாறு இல்லாமல் இருப்பதை உறுதி செய்யவும்",
            "விதைப்பின்போது விதை/மண் மூலம் இடப்படும் உயிரியல் கட்டுப்பாட்டு சிகிச்சையைப் பயன்படுத்தவும்",
            "பயிர் சுழற்சியை மேற்கொண்டு, அறுவடைக்குப் பிறகு உடனடியாக எச்சங்களை அகற்றவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide", "goi_pest_management_sop"],
        "_source_note": "AGRICULTURE.pdf p.271,278,280,281 (disease-management table + seed-production land requirement); Pest_management.pdf p.25,105 (general sanitation/Trichoderma principles, not cotton-specific). No source describes visible symptoms of this disease.",
    },
    "cotton_verticillium_wilt": {
        "cultural_management_en": [
            "Choose a Verticillium-wilt-resistant variety where the disease is a known local concern",
        ],
        "biological_options_en": [
            "Seed treatment with Bacillus subtilis (about 10 g per kg of seed) or Trichoderma asperellum (about 4 g per kg of seed)",
            "Trichoderma asperellum applied to the soil at sowing and again about 90 days after sowing",
        ],
        "prevention_en": [
            "Use resistant varieties as the primary defence, alongside seed-/soil-applied biocontrol treatment",
        ],
        "cultural_management_ta": [
            "இந்நோய் உள்ளூரில் அறியப்பட்ட பிரச்சனையாக இருக்கும் இடங்களில் Verticillium வாடல் நோய் எதிர்ப்புத் திறன் கொண்ட ரகத்தைத் தேர்ந்தெடுக்கவும்",
        ],
        "biological_options_ta": [
            "Bacillus subtilis உடன் விதை நேர்த்தி செய்யவும் (சுமார் 10 கிராம் ஒரு கிலோ விதைக்கு) அல்லது Trichoderma asperellum (சுமார் 4 கிராம் ஒரு கிலோ விதைக்கு)",
            "விதைக்கும் நேரத்திலும் விதைத்த சுமார் 90 நாட்களுக்குப் பிறகும் Trichoderma asperellum-ஐ மண்ணில் இடவும்",
        ],
        "prevention_ta": [
            "எதிர்ப்புத் திறன் கொண்ட ரகங்களை முதன்மை பாதுகாப்பாகப் பயன்படுத்தவும், விதை/மண் மூலம் இடப்படும் உயிரியல் கட்டுப்பாட்டு சிகிச்சையுடன் சேர்த்து",
        ],
        "_source_ids": ["tnau_agriculture_guide", "tnau_agritech_cotton_diseases"],
        "_source_note": "AGRICULTURE.pdf p.256 (variety table notes one variety as Verticillium-wilt-resistant); TNAU Agritech Portal Crop Protection - Cotton Diseases page (Bacillus subtilis / Trichoderma asperellum seed and soil treatment) -- no symptom or causal-species detail is available from any source on hand.",
    },
    "groundnut_healthy": {
        "symptoms_en": [
            "Uniform stand with a single healthy, vigorous seedling retained per hole after thinning",
        ],
        "cultural_management_en": [
            "Retain only one healthy, vigorous seedling per hole when thinning",
            "Use composted coir pith / organic matter to improve moisture availability and drainage in heavy-textured soils",
            "Select varieties suited to local conditions with known pest/disease tolerance",
        ],
        "biological_options_en": [
            "Seed treatment with Trichoderma asperellum or Pseudomonas fluorescens",
        ],
        "prevention_en": [
            "Choose varieties with documented tolerance/resistance to common foliar diseases (rust, late leaf spot)",
            "Ensure good field drainage, especially in heavy soils, and follow the recommended stage-wise irrigation schedule",
        ],
        "symptoms_ta": [
            "நேர்த்தி செய்த பிறகு ஒவ்வொரு துளையிலும் ஒரு ஆரோக்கியமான, வலிமையான நாற்று மட்டும் இருக்கும் சீரான பயிர் தோற்றம்",
        ],
        "cultural_management_ta": [
            "நேர்த்தி செய்யும்போது ஒவ்வொரு துளையிலும் ஒரு ஆரோக்கியமான, வலிமையான நாற்றை மட்டும் விட்டு வையுங்கள்",
            "கனமான மண் வகைகளில் ஈரப்பதம் மற்றும் வடிகாலை மேம்படுத்த கம்போஸ்ட் செய்யப்பட்ட தென்னை நார் சக்கை / இயற்கை பொருட்களைப் பயன்படுத்தவும்",
            "அறியப்பட்ட பூச்சி/நோய் தாங்கும் திறன் கொண்ட, உள்ளூர் நிலைமைகளுக்கு ஏற்ற ரகங்களைத் தேர்ந்தெடுக்கவும்",
        ],
        "biological_options_ta": [
            "Trichoderma asperellum அல்லது Pseudomonas fluorescens உடன் விதை நேர்த்தி செய்யவும்",
        ],
        "prevention_ta": [
            "பொதுவான இலை நோய்களுக்கு (துரு, தாமதமான இலைப்புள்ளி) பதிவு செய்யப்பட்ட தாங்கும் திறன்/எதிர்ப்புத் திறன் கொண்ட ரகங்களைத் தேர்ந்தெடுக்கவும்",
            "குறிப்பாக கனமான மண்ணில் நல்ல வயல் வடிகாலை உறுதி செய்து, பரிந்துரைக்கப்பட்ட நிலைவாரியான பாசன அட்டவணையைப் பின்பற்றவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide", "goi_pest_management_sop"],
        "_source_note": "AGRICULTURE.pdf p.183-184,192,194,218; Pest_management.pdf p.12-13",
    },
    "groundnut_rust": {
        "cause_en": "Puccinia arachidis, a fungal rust pathogen.",
        "why_it_occurs_en": [
            "Susceptibility differs by variety -- several released varieties are documented as (moderately) resistant/tolerant to rust, implying non-resistant varieties are more prone to the disease",
        ],
        "cultural_management_en": [
            "Select rust-tolerant/moderately-resistant varieties suited to the region",
            "Practice crop rotation and sanitation (removal/destruction of diseased plant material, burning crop residue) to reduce carry-over inoculum between seasons",
        ],
        "prevention_en": [
            "Grow a rust-tolerant/resistant variety appropriate to the region",
            "Follow recommended seed treatment ahead of the cropping season as part of overall disease management",
        ],
        "cause_ta": "Puccinia arachidis என்ற பூஞ்சை துரு நோய் காரணி.",
        "why_it_occurs_ta": [
            "ரகத்திற்கு ஏற்ப பாதிப்பு வேறுபடுகிறது -- வெளியிடப்பட்ட பல ரகங்கள் துருவுக்கு (மிதமான) எதிர்ப்புத் திறன்/தாங்கும் திறன் கொண்டவை என ஆவணப்படுத்தப்பட்டுள்ளன, இது எதிர்ப்புத் திறன் இல்லாத ரகங்கள் நோய்க்கு அதிக வாய்ப்புள்ளவை என்பதைக் குறிக்கிறது",
        ],
        "cultural_management_ta": [
            "பிராந்தியத்திற்கு ஏற்ற துரு-தாங்கும் திறன்/மிதமான எதிர்ப்புத் திறன் கொண்ட ரகங்களைத் தேர்ந்தெடுக்கவும்",
            "பருவங்களுக்கு இடையே தொற்று சேர்க்கையைக் குறைக்க பயிர் சுழற்சி மற்றும் சுத்தத்தை (நோய்வாய்ப்பட்ட தாவரப் பொருட்களை அகற்றி அழித்தல், பயிர் எச்சங்களை எரித்தல்) மேற்கொள்ளவும்",
        ],
        "prevention_ta": [
            "பிராந்தியத்திற்கு ஏற்ற துரு-தாங்கும்/எதிர்ப்புத் திறன் கொண்ட ரகத்தை வளர்க்கவும்",
            "ஒட்டுமொத்த நோய் மேலாண்மையின் ஒரு பகுதியாக பயிர் பருவத்திற்கு முன் பரிந்துரைக்கப்பட்ட விதை நேர்த்தியைப் பின்பற்றவும்",
        ],
        "_source_ids": ["tnau_agriculture_guide"],
        "_source_note": "AGRICULTURE.pdf p.194 (disease-management table), p.183-184 (variety resistance notes). No source describes visible rust symptoms (pustule appearance/colour); no biological control agent is named against rust specifically.",
    },
    "chilli_healthy": {
        "symptoms_en": [
            "Uniform deep-green, unspotted foliage",
            "Vigorous, upright growth with no wilting, leaf curling, or yellowing",
            "Normal flowering and fruit set with no leaf distortion",
        ],
        "cultural_management_en": [
            "Use certified, clean/disease-free planting material",
            "Practice crop rotation and destroy crop residues and volunteer/alternate host plants after harvest",
            "Adopt raised nursery beds and soil solarisation to prevent soil-borne problems",
            "Maintain balanced fertilization, timely planting, and recommended spacing",
        ],
        "biological_options_en": [
            "Seed treatment with Trichoderma viride or Pseudomonas fluorescens as a preventive measure",
            "Conserve natural enemies (predatory beetles, spiders, parasitic wasps) by avoiding unnecessary sprays",
        ],
        "prevention_en": [
            "Conduct weekly field scouting to catch pest or disease problems early",
            "Install yellow pan/sticky traps to monitor whitefly and thrips populations",
            "Keep the field weed-free and ensure proper drainage / avoid water stagnation",
        ],
        "symptoms_ta": [
            "சீரான அடர் பச்சை, புள்ளிகள் இல்லாத இலைகள்",
            "வாடல், இலைச்சுருள் அல்லது மஞ்சள் நிறமாதல் இல்லாமல் வலிமையான, நிமிர்ந்த வளர்ச்சி",
            "இலை உருமாற்றம் இல்லாமல் இயல்பான பூக்கும் மற்றும் காய் பிடித்தல்",
        ],
        "cultural_management_ta": [
            "சான்றளிக்கப்பட்ட, சுத்தமான/நோயற்ற நடவுப் பொருளைப் பயன்படுத்தவும்",
            "பயிர் சுழற்சியை மேற்கொண்டு, அறுவடைக்குப் பிறகு பயிர் எச்சங்கள் மற்றும் தானாக முளைத்த/மாற்று புரவல் தாவரங்களை அழிக்கவும்",
            "மண் தொடர்பான பிரச்சனைகளைத் தடுக்க உயர்த்தப்பட்ட நாற்றங்கால் மேடைகள் மற்றும் மண் சூரிய கிருமி நீக்கத்தை மேற்கொள்ளவும்",
            "சமச்சீர் உரமிடுதல், சரியான நேரத்தில் நடவு மற்றும் பரிந்துரைக்கப்பட்ட இடைவெளியைப் பராமரிக்கவும்",
        ],
        "biological_options_ta": [
            "தடுப்பு நடவடிக்கையாக Trichoderma viride அல்லது Pseudomonas fluorescens உடன் விதை நேர்த்தி செய்யவும்",
            "தேவையற்ற தெளிப்புகளைத் தவிர்த்து இயற்கை எதிரிகளை (இரை வண்டுகள், சிலந்திகள், ஒட்டுண்ணி குளவிகள்) பாதுகாக்கவும்",
        ],
        "prevention_ta": [
            "பூச்சி அல்லது நோய் பிரச்சனைகளை முன்கூட்டியே கண்டறிய வாராந்திர வயல் கண்காணிப்பு செய்யவும்",
            "வெள்ளை ஈ மற்றும் நுளம்பு எண்ணிக்கையைக் கண்காணிக்க மஞ்சள் பான்/ஒட்டும் பொறிகளை நிறுவவும்",
            "வயலை களை இல்லாமல் வைத்து சரியான வடிகாலை உறுதி செய்யவும் / நீர் தேங்குவதைத் தவிர்க்கவும்",
        ],
        "_source_ids": ["goi_ipm_chilli_capsicum", "icar_iisr_chilli_gap"],
        "_source_note": "ChilliesCapsicum.pdf p.7-11; cultivation_practices-Chillli-1.pdf p.5-11",
    },
    "chilli_bacterial_spot": {
        "cultural_management_en": [
            "Use certified/clean, pathogen-free planting material and general field phytosanitation",
            "Destroy crop residues/debris and volunteer/alternate host plants after final harvest",
            "Practice crop rotation",
        ],
        "biological_options_en": [
            "Copper oxychloride spray -- TNAU documents this as the standard spray for chilli bacterial spot, and copper-based compounds are permitted inputs under India's organic farming standard (NPOP), so this is usable under organic management even though TNAU itself frames it as a chemical/mineral spray rather than a biological agent. No living bioagent (Pseudomonas/Bacillus) is documented against this disease by any official Indian source.",
        ],
        "prevention_en": [
            "Use certified/pathogen-free seed",
            "Follow field sanitation/phytosanitation to reduce carryover of inoculum between seasons",
        ],
        "cultural_management_ta": [
            "சான்றளிக்கப்பட்ட/சுத்தமான, நோய்க்கிருமி இல்லாத நடவுப் பொருள் மற்றும் பொது வயல் தாவர சுகாதாரத்தைப் பயன்படுத்தவும்",
            "இறுதி அறுவடைக்குப் பிறகு பயிர் எச்சங்கள்/கழிவுகள் மற்றும் தானாக முளைத்த/மாற்று புரவல் தாவரங்களை அழிக்கவும்",
            "பயிர் சுழற்சியை மேற்கொள்ளவும்",
        ],
        "biological_options_ta": [
            "காப்பர் ஆக்ஸிகுளோரைடு தெளிப்பு -- மிளகாய் பாக்டீரியா இலைப்புள்ளிக்கு TNAU இதை நிலையான தெளிப்பாகக் குறிப்பிடுகிறது; காப்பர் அடிப்படையிலான கலவைகள் இந்தியாவின் இயற்கை வேளாண் தரநிலையின் (NPOP) கீழ் அனுமதிக்கப்பட்ட உள்ளீடுகள் என்பதால், TNAU இதை ஒரு உயிரியல் முகவிக்கு பதிலாக ஒரு இரசாயன/கனிம தெளிப்பாகக் கருதினாலும், இயற்கை முறையில் இதைப் பயன்படுத்தலாம். இந்நோய்க்கு எதிராக எந்த உயிருள்ள உயிரியல் முகவும் (Pseudomonas/Bacillus) எந்த அதிகாரப்பூர்வ இந்திய ஆதாரத்திலும் ஆவணப்படுத்தப்படவில்லை.",
        ],
        "prevention_ta": [
            "சான்றளிக்கப்பட்ட/நோய்க்கிருமி இல்லாத விதையைப் பயன்படுத்தவும்",
            "பருவங்களுக்கு இடையே தொற்று சேர்க்கையைக் குறைக்க வயல் சுத்தம்/தாவர சுகாதாரத்தைப் பின்பற்றவும்",
        ],
        "_source_ids": ["goi_ipm_chilli_capsicum", "tnau_agritech_chilli_diseases"],
        "_source_note": "ChilliesCapsicum.pdf p.7 (disease named only, cultural guidance is the source's GENERAL disease-reduction guidance, not specific to bacterial spot); TNAU Agritech Portal Crop Protection - Chilli Diseases page (copper oxychloride/Bordeaux mixture spray, framed by TNAU as chemical control -- organic-permitted status under NPOP is this app's own characterization, not TNAU's). No causal organism or symptom description is available from any source on hand.",
    },
    "chilli_cercospora_leaf_spot": {
        "symptoms_en": [
            "Circular to irregular leaf spots with a light tan/grey centre and a dark brown-to-purple margin (a 'frog-eye' appearance)",
            "Multiple spots scattered across the leaf surface",
        ],
        "cause_en": "A fungal pathogen of the genus Cercospora.",
        "why_it_occurs_en": [
            "Occurs mainly at the flowering and fruiting stage",
            "Leaf-disease pressure is reduced where soils have active organic matter, implying organic-matter-poor soils favour more leaf disease",
        ],
        "cultural_management_en": [
            "Destroy crop residues/debris and alternate host plants after harvest",
            "Maintain soil organic matter (e.g. via green manuring/compost)",
            "Avoid water stagnation and ensure proper field drainage",
            "Practice crop rotation",
        ],
        "biological_options_en": [
            "Seed treatment with Trichoderma viride or Pseudomonas fluorescens to help prevent seed/soil-borne fungal infection",
        ],
        "prevention_en": [
            "Use disease-free/certified seed and phytosanitation",
            "Conduct weekly field scouting, recording leaf-spot symptoms and the percentage of leaf area affected",
            "Avoid excess irrigation/humidity and ensure proper drainage",
        ],
        "symptoms_ta": [
            "வெளிர் தான்/சாம்பல் நிற மையம் மற்றும் அடர் பழுப்பு-முதல்-ஊதா நிற ஓரத்துடன் வட்டமான முதல் ஒழுங்கற்ற இலைப் புள்ளிகள் ('தவளைக் கண்' தோற்றம்)",
            "இலை மேற்பரப்பு முழுவதும் பல புள்ளிகள் சிதறியிருக்கும்",
        ],
        "cause_ta": "Cercospora இனத்தைச் சேர்ந்த ஒரு பூஞ்சை நோய்க்கிருமி.",
        "why_it_occurs_ta": [
            "முக்கியமாக பூக்கும் மற்றும் காய்க்கும் நிலையில் ஏற்படுகிறது",
            "மண்ணில் செயலில் உள்ள கரிமப் பொருள் இருக்கும் இடங்களில் இலை நோய் அழுத்தம் குறைவாக இருப்பதால், கரிமப் பொருள் குறைந்த மண் அதிக இலை நோய்க்கு உகந்ததாக இருக்கிறது என்பதைக் குறிக்கிறது",
        ],
        "cultural_management_ta": [
            "அறுவடைக்குப் பிறகு பயிர் எச்சங்கள்/கழிவுகள் மற்றும் மாற்று புரவல் தாவரங்களை அழிக்கவும்",
            "மண் கரிமப் பொருளைப் பராமரிக்கவும் (எ.கா. பசுந்தாள் உரம்/கம்போஸ்ட் மூலம்)",
            "நீர் தேங்குவதைத் தவிர்த்து சரியான வயல் வடிகாலை உறுதி செய்யவும்",
            "பயிர் சுழற்சியை மேற்கொள்ளவும்",
        ],
        "biological_options_ta": [
            "விதை/மண் மூலம் பரவும் பூஞ்சைத் தொற்றைத் தடுக்க உதவும் வகையில் Trichoderma viride அல்லது Pseudomonas fluorescens உடன் விதை நேர்த்தி செய்யவும்",
        ],
        "prevention_ta": [
            "நோயற்ற/சான்றளிக்கப்பட்ட விதை மற்றும் தாவர சுகாதாரத்தைப் பயன்படுத்தவும்",
            "இலைப்புள்ளி அறிகுறிகள் மற்றும் பாதிக்கப்பட்ட இலைப் பரப்பின் சதவீதத்தைப் பதிவு செய்து வாராந்திர வயல் கண்காணிப்பு செய்யவும்",
            "அதிகப்படியான பாசனம்/ஈரப்பதத்தைத் தவிர்த்து சரியான வடிகாலை உறுதி செய்யவும்",
        ],
        "_source_ids": ["icar_iisr_chilli_gap", "goi_ipm_chilli_capsicum"],
        "_source_note": "cultivation_practices-Chillli-1.pdf p.5,9,10,11 (incl. photo captioned 'Cercospora leaf spot'); ChilliesCapsicum.pdf p.7,9-11,21-22",
    },
    "chilli_leaf_curl_virus": {
        "symptoms_en": [
            "Upward curling and crinkling/puckering of leaves",
            "Mottled pale-green and dark-green leaf pattern with an overall stunted, bushy plant appearance",
        ],
        "cause_en": "A begomovirus (Gemini virus group), transmitted by whitefly.",
        "why_it_occurs_en": [
            "Transmitted by whitefly, the source's stated vector for this disease",
            "Whitefly populations build up and are monitored via yellow sticky traps -- higher vector pressure raises disease risk",
        ],
        "cultural_management_en": [
            "Raise seedlings under insect-proof net in the nursery to exclude whitefly and produce healthy, virus-free seedlings before transplanting",
            "Grow border/guard crops (e.g. sorghum, maize) around the field to check whitefly movement into the main crop",
            "Raise green-manure crops (Crotalaria or Sesbania), which the source links to reduced thrips, aphid, and whitefly incidence",
            "Use sprinkler irrigation at the pre-flowering stage to help check whitefly/thrips infestation",
        ],
        "biological_options_en": [
            "Conserve natural enemies of sucking pests (predatory beetles, spiders, parasitic wasps) by avoiding unnecessary sprays",
        ],
        "prevention_en": [
            "Use insect-proof net in the nursery to raise vector-free seedlings",
            "Install yellow pan/sticky traps for early whitefly detection and monitoring",
            "Practice phytosanitation -- remove volunteer plants and destroy crop residues after harvest",
        ],
        "symptoms_ta": [
            "இலைகள் மேல்நோக்கி சுருண்டு, சுருக்கம்/முடக்கமடைதல்",
            "வெளிர் பச்சை மற்றும் அடர் பச்சை கலந்த புள்ளி வடிவ இலை மற்றும் ஒட்டுமொத்தமாக குட்டையான, புதர் தோற்றம்",
        ],
        "cause_ta": "வெள்ளை ஈ மூலம் பரவும் ஒரு பீகோமோ வைரஸ் (ஜெமினி வைரஸ் குழு).",
        "why_it_occurs_ta": [
            "இந்நோய்க்கான ஆதாரம் குறிப்பிடும் வாகக பூச்சியான வெள்ளை ஈ மூலம் பரவுகிறது",
            "வெள்ளை ஈ எண்ணிக்கை அதிகரித்து, மஞ்சள் ஒட்டும் பொறிகள் மூலம் கண்காணிக்கப்படுகிறது -- அதிக வாகக பூச்சி அழுத்தம் நோய் ஆபத்தை அதிகரிக்கிறது",
        ],
        "cultural_management_ta": [
            "நாற்றங்கால்களில் பூச்சி-தடுப்பு வலையின் கீழ் நாற்றுகளை வளர்த்து, வெள்ளை ஈயைத் தவிர்த்து நடவு செய்வதற்கு முன் ஆரோக்கியமான, வைரஸ் இல்லாத நாற்றுகளை உற்பத்தி செய்யவும்",
            "வெள்ளை ஈ முதன்மைப் பயிரில் நுழைவதைக் கட்டுப்படுத்த வயலைச் சுற்றி எல்லைப்/பாதுகாப்பு பயிர்களை (சோளம், மக்காச்சோளம் போன்றவை) வளர்க்கவும்",
            "நுளம்பு, பேன் மற்றும் வெள்ளை ஈ பாதிப்பைக் குறைப்பதாக ஆதாரம் தெரிவிக்கும் பசுந்தாள் உரப் பயிர்களை (குரோட்டலேரியா அல்லது சேவை) வளர்க்கவும்",
            "பூப்பதற்கு முன் நிலையில் வெள்ளை ஈ/நுளம்பு பாதிப்பைக் கட்டுப்படுத்த ஸ்பிரிங்க்ளர் பாசனத்தைப் பயன்படுத்தவும்",
        ],
        "biological_options_ta": [
            "தேவையற்ற தெளிப்புகளைத் தவிர்த்து சூப்பும் பூச்சிகளின் இயற்கை எதிரிகளை (இரை வண்டுகள், சிலந்திகள், ஒட்டுண்ணி குளவிகள்) பாதுகாக்கவும்",
        ],
        "prevention_ta": [
            "நாற்றங்கால்களில் பூச்சி-தடுப்பு வலையைப் பயன்படுத்தி வாகக பூச்சி இல்லாத நாற்றுகளை வளர்க்கவும்",
            "முன்கூட்டிய வெள்ளை ஈ கண்டறிதல் மற்றும் கண்காணிப்புக்காக மஞ்சள் பான்/ஒட்டும் பொறிகளை நிறுவவும்",
            "தாவர சுகாதாரத்தைப் பின்பற்றவும் -- தானாக முளைத்த செடிகளை அகற்றி, அறுவடைக்குப் பிறகு பயிர் எச்சங்களை அழிக்கவும்",
        ],
        "_source_ids": ["icar_iisr_chilli_gap", "goi_ipm_chilli_capsicum"],
        "_source_note": "cultivation_practices-Chillli-1.pdf p.5,7,10,12 (incl. photo captioned 'Leaf curl begomo virus'); ChilliesCapsicum.pdf p.9-11",
    },
    "redgram_healthy": {
        "symptoms_en": [
            "Uniform, green foliage across the field with no wilted or blighted plants",
            "No sterility-mosaic-affected (bushy, non-flowering) plants present",
        ],
        "why_it_occurs_en": [
            "Follows recommended pre-sowing and vegetative-stage cultural practices (deep summer ploughing, farmyard manure/neem cake, resistant-variety selection, timely weeding)",
            "Supported by regular monitoring (roving surveys, weekly field scouting) that allows early detection and action",
        ],
        "cultural_management_en": [
            "Deep-plough the field in summer and apply farmyard manure or neem cake before sowing",
            "Select resistant/tolerant varieties suited to the region",
            "Keep the field weed-free for the first 6-8 weeks via timely inter-culture and hand weeding",
            "Conduct regular (weekly) field scouting to monitor plant health",
        ],
        "biological_options_en": [
            "Seed treatment with Trichoderma viride",
            "Conserve natural enemies (spiders, parasitic wasps, predatory bugs, birds) by avoiding indiscriminate pesticide use",
        ],
        "prevention_en": [
            "Avoid growing pigeonpea/redgram in the same wilt-infected field for at least 3 years",
            "Use only recommended/resistant varieties for the area, especially in disease-prone pockets",
            "Maintain a regular monitoring schedule throughout the season",
        ],
        "symptoms_ta": [
            "வயல் முழுவதும் சீரான, பச்சையான இலைகள்; வாடிய அல்லது கருகிய செடிகள் இல்லாமல்",
            "மலட்டுத் தேமல் பாதிப்புள்ள (புதர் போன்ற, பூக்காத) செடிகள் இல்லாமல்",
        ],
        "why_it_occurs_ta": [
            "பரிந்துரைக்கப்பட்ட விதைப்புக்கு முந்தைய மற்றும் வளர்ச்சி நிலை பயிர் நடைமுறைகளைப் பின்பற்றுகிறது (கோடையில் ஆழ் உழவு, தொழு உரம்/வேப்பம் பிண்ணாக்கு, எதிர்ப்புத் திறன் கொண்ட ரகத் தேர்வு, சரியான நேரத்தில் களை எடுத்தல்)",
            "முன்கூட்டிய கண்டறிதல் மற்றும் நடவடிக்கை எடுக்க உதவும் வழக்கமான கண்காணிப்பால் (சுற்றுப் பயண ஆய்வுகள், வாராந்திர வயல் கண்காணிப்பு) ஆதரிக்கப்படுகிறது",
        ],
        "cultural_management_ta": [
            "கோடையில் வயலை ஆழமாக உழுது, விதைப்பதற்கு முன் தொழு உரம் அல்லது வேப்பம் பிண்ணாக்கு இடவும்",
            "பிராந்தியத்திற்கு ஏற்ற எதிர்ப்புத் திறன்/தாங்கும் திறன் கொண்ட ரகங்களைத் தேர்ந்தெடுக்கவும்",
            "முதல் 6-8 வாரங்களில் சரியான நேரத்தில் இடைப்பயிர் செய்தல் மற்றும் கை களையெடுப்பு மூலம் வயலைக் களை இல்லாமல் வைக்கவும்",
            "செடியின் ஆரோக்கியத்தைக் கண்காணிக்க வழக்கமான (வாராந்திர) வயல் கண்காணிப்பு செய்யவும்",
        ],
        "biological_options_ta": [
            "Trichoderma viride உடன் விதை நேர்த்தி செய்யவும்",
            "தேவையற்ற பூச்சிக்கொல்லி பயன்பாட்டைத் தவிர்த்து இயற்கை எதிரிகளை (சிலந்திகள், ஒட்டுண்ணி குளவிகள், இரை பூச்சிகள், பறவைகள்) பாதுகாக்கவும்",
        ],
        "prevention_ta": [
            "வாடல் நோய் பாதிப்புள்ள அதே வயலில் குறைந்தது 3 ஆண்டுகளுக்கு துவரையை மீண்டும் வளர்ப்பதைத் தவிர்க்கவும்",
            "குறிப்பாக நோய் பாதிப்பு அதிகமுள்ள பகுதிகளில் அப்பகுதிக்கு பரிந்துரைக்கப்பட்ட/எதிர்ப்புத் திறன் கொண்ட ரகங்களை மட்டும் பயன்படுத்தவும்",
            "பருவம் முழுவதும் வழக்கமான கண்காணிப்பு அட்டவணையைப் பராமரிக்கவும்",
        ],
        "_source_ids": ["goi_ipm_pigeonpea"],
        "_source_note": "Pigeonpea.pdf p.6,9,12,18,20",
    },
    "redgram_leaf_spot": {
        "cause_en": "The nearest matching foliar disease in the available source is documented as 'Alternaria blight' (an Alternaria sp. fungus); the source does not use the term 'leaf spot' specifically or name a species.",
        "why_it_occurs_en": [
            "Managed in the source via resistant varieties 'in endemic pockets', implying regional/variety-linked occurrence",
            "Resistant varieties for this disease are recommended specifically for Eastern Uttar Pradesh, Bihar, Assam and West Bengal, suggesting higher prevalence there",
        ],
        "cultural_management_en": [
            "Grow Alternaria-blight-resistant varieties, particularly in endemic pockets of Eastern Uttar Pradesh, Bihar, Assam and West Bengal",
        ],
        "biological_options_en": [
            "A Trichoderma-based biocontrol (Hypocrea rufa, in the same genus group as Trichoderma viride) has shown real field-trial reduction of Alternaria blight severity in a peer-reviewed Indian study -- note this is not a government extension recommendation, and in that same study the strongest field result came from combining it with the fungicide Mancozeb, not from the biocontrol alone, so treat this as a supplementary option rather than a standalone proven cure.",
        ],
        "prevention_en": [
            "Select and sow only resistant varieties recommended for Alternaria-blight-endemic regions",
            "Include disease-incidence recording as part of regular field scouting",
        ],
        "cause_ta": "கிடைக்கும் ஆதாரத்தில் நெருங்கிய பொருந்தும் இலை நோயாக 'Alternaria blight' (ஒரு Alternaria இனப் பூஞ்சை) என ஆவணப்படுத்தப்பட்டுள்ளது; ஆதாரம் குறிப்பாக 'இலைப்புள்ளி' என்ற சொல்லைப் பயன்படுத்தவில்லை அல்லது இனத்தைக் குறிப்பிடவில்லை.",
        "why_it_occurs_ta": [
            "ஆதாரத்தில் 'பாதிப்புள்ள பகுதிகளில்' எதிர்ப்புத் திறன் கொண்ட ரகங்கள் மூலம் நிர்வகிக்கப்படுகிறது, இது பிராந்திய/ரக தொடர்பான ஏற்படுதலைக் குறிக்கிறது",
            "இந்நோய்க்கான எதிர்ப்புத் திறன் கொண்ட ரகங்கள் குறிப்பாக கிழக்கு உத்தரப்பிரதேசம், பீகார், அசாம் மற்றும் மேற்கு வங்காளத்திற்குப் பரிந்துரைக்கப்படுகின்றன, அங்கு அதிக பாதிப்பு இருக்கலாம் என்பதைக் குறிக்கிறது",
        ],
        "cultural_management_ta": [
            "குறிப்பாக கிழக்கு உத்தரப்பிரதேசம், பீகார், அசாம் மற்றும் மேற்கு வங்காளத்தின் பாதிப்புள்ள பகுதிகளில் Alternaria blight-க்கு எதிர்ப்புத் திறன் கொண்ட ரகங்களை வளர்க்கவும்",
        ],
        "biological_options_ta": [
            "Trichoderma அடிப்படையிலான உயிரியல் கட்டுப்பாடு (Hypocrea rufa, Trichoderma viride-உடன் இணைந்த இனக் குழு) ஒரு இந்திய ஆய்வில் Alternaria blight தீவிரத்தை உண்மையான வயல் சோதனையில் குறைத்துக் காட்டியுள்ளது -- இது அரசு விரிவாக்க பரிந்துரை அல்ல என்பதை கவனிக்கவும்; அதே ஆய்வில், சிறந்த வயல் முடிவு உயிரியல் கட்டுப்பாடு மட்டும் அல்ல, Mancozeb பூஞ்சைக்கொல்லியுடன் இணைந்தபோதே கிடைத்தது -- எனவே இதை ஒரு தனித்த நிரூபிக்கப்பட்ட குணப்படுத்தலாக அல்லாமல், ஒரு துணை விருப்பமாகக் கருதவும்.",
        ],
        "prevention_ta": [
            "Alternaria blight பாதிப்புள்ள பகுதிகளுக்குப் பரிந்துரைக்கப்பட்ட எதிர்ப்புத் திறன் கொண்ட ரகங்களை மட்டும் தேர்ந்தெடுத்து விதைக்கவும்",
            "வழக்கமான வயல் கண்காணிப்பின் ஒரு பகுதியாக நோய் ஏற்படும் அளவைப் பதிவு செய்யவும்",
        ],
        "_source_ids": ["goi_ipm_pigeonpea", "legume_research_2018_pigeonpea_alternaria"],
        "_source_note": "Pigeonpea.pdf p.7,9,20 (cultural/resistant-variety content; no symptom description given). Biological option from Balai, Singh, Sinha & Yadav (2018), Legume Research 43(2):268-275 -- a peer-reviewed field-trial study, not a government extension source; best verified result was Hypocrea rufa combined with Mancozeb fungicide, not standalone.",
    },
    "redgram_sterility_mosaic": {
        "cause_en": "Named in the source as caused by 'Sterility Mosaic Virus'; the source does not specify the transmitting vector.",
        "why_it_occurs_en": [
            "Monitored specifically at the flowering stage via weekly counts of affected plants",
            "Incidence is addressed through resistant varieties recommended for specific endemic pockets (Andhra Pradesh, Tamil Nadu, Karnataka, Orissa, Maharashtra, Madhya Pradesh, Gujarat, Bundelkhand-UP), implying susceptible varieties in these areas are more affected",
        ],
        "cultural_management_en": [
            "Remove and destroy (rogue) sterility-mosaic-affected plants as soon as identified",
            "If sterility mosaic incidence is noted, grow only resistant varieties in the following season",
            "Conduct weekly field monitoring during the flowering stage to detect and rogue infected plants early",
        ],
        "prevention_en": [
            "Grow resistant varieties suited to the region from the outset in known sterility-mosaic-endemic pockets",
            "Undertake regular weekly field scouting at the flowering stage to detect and rogue affected plants before further spread",
        ],
        "cause_ta": "ஆதாரத்தில் 'Sterility Mosaic Virus' எனக் காரணமாகக் குறிப்பிடப்பட்டுள்ளது; பரப்பும் வாகக பூச்சியை ஆதாரம் குறிப்பிடவில்லை.",
        "why_it_occurs_ta": [
            "பூக்கும் நிலையில் பாதிக்கப்பட்ட செடிகளின் வாராந்திர எண்ணிக்கை மூலம் குறிப்பாகக் கண்காணிக்கப்படுகிறது",
            "குறிப்பிட்ட பாதிப்புள்ள பகுதிகளுக்குப் (ஆந்திரப் பிரதேசம், தமிழ்நாடு, கர்நாடகா, ஒரிசா, மகாராஷ்டிரா, மத்தியப் பிரதேசம், குஜராத், பண்டேல்கண்ட்-உ.பி.) பரிந்துரைக்கப்பட்ட எதிர்ப்புத் திறன் கொண்ட ரகங்கள் மூலம் பாதிப்பு நிவர்த்தி செய்யப்படுகிறது, இது இப்பகுதிகளில் பாதிப்புக்கு உட்பட்ட ரகங்கள் அதிகம் பாதிக்கப்படுகின்றன என்பதைக் குறிக்கிறது",
        ],
        "cultural_management_ta": [
            "மலட்டுத் தேமல் பாதிப்புள்ள செடிகளை கண்டறிந்தவுடன் அகற்றி அழிக்கவும் (ரோகிங்)",
            "மலட்டுத் தேமல் ஏற்படுவது கவனிக்கப்பட்டால், அடுத்த பருவத்தில் எதிர்ப்புத் திறன் கொண்ட ரகங்களை மட்டும் வளர்க்கவும்",
            "பாதிக்கப்பட்ட செடிகளை முன்கூட்டியே கண்டறிந்து அகற்ற பூக்கும் நிலையின் போது வாராந்திர வயல் கண்காணிப்பு செய்யவும்",
        ],
        "prevention_ta": [
            "மலட்டுத் தேமல் பாதிப்பு அதிகமுள்ள பகுதிகளில் ஆரம்பத்திலிருந்தே பிராந்தியத்திற்கு ஏற்ற எதிர்ப்புத் திறன் கொண்ட ரகங்களை வளர்க்கவும்",
            "மேலும் பரவுவதற்கு முன் பாதிக்கப்பட்ட செடிகளைக் கண்டறிந்து அகற்ற பூக்கும் நிலையில் வழக்கமான வாராந்திர வயல் கண்காணிப்பை மேற்கொள்ளவும்",
        ],
        "_source_ids": ["goi_ipm_pigeonpea"],
        "_source_note": "Pigeonpea.pdf p.1,5-6,9-10,20. No symptom description or vector is given in the source for this disease.",
    },
}


def _ta(items: list[str]) -> list[str]:
    # Tamil-first response remains structurally complete while specialist translation is queued.
    return ["அதிகாரப்பூர்வ ஆதாரத்துடன் சரிபார்க்கவும்: " + item for item in items]


def _extension_sources(content: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        deepcopy(EXTENSION_SOURCES[source_id])
        for source_id in content.get("_source_ids", ())
        if source_id in EXTENSION_SOURCES
    ]


def get_recommendation(
    crop_id: str,
    runtime_label: str,
    *,
    diagnosis_accepted: bool,
    controlled_test: bool = False,
) -> dict[str, Any]:
    entry = LABELS.get(runtime_label)
    if entry is None or entry[0] != crop_id:
        return {"outcome": STATUS_UNMAPPED, "runtime_label": runtime_label, "crop_id": crop_id,
                "agricultural_disclaimer": DISCLAIMER}
    if not diagnosis_accepted:
        return {"outcome": "DIAGNOSIS_UNCERTAIN", "runtime_label": runtime_label, "crop_id": crop_id,
                "chemical_recommendation_status": CHEMICAL_WITHHELD,
                "immediate_actions_ta": ["தெளிவான கூடுதல் படங்களை எடுத்து வேளாண் அலுவலரிடம் ஆலோசனை பெறவும்."],
                "immediate_actions_en": ["Take clearer additional images and seek agricultural-officer review."],
                "agricultural_disclaimer": DISCLAIMER}
    if crop_id in RESTRICTED_CROPS and not controlled_test:
        return {"outcome": STATUS_UNVERIFIED, "runtime_label": runtime_label, "crop_id": crop_id,
                "reason": "Restricted runtime results are not enabled for disease recommendations.",
                "chemical_recommendation_status": CHEMICAL_WITHHELD,
                "agricultural_disclaimer": DISCLAIMER}
    crop, canonical_id, name_en, name_ta, category = entry
    healthy = category == "healthy"
    content = DISEASE_CONTENT.get(canonical_id, {})

    default_immediate = (["Continue routine field observation; do not apply a treatment based only on this result."] if healthy
                 else ["Inspect nearby plants and remove only visibly affected fallen plant material where safe.",
                       "Take clear follow-up photos and seek local agricultural-officer review if symptoms spread."])
    default_immediate_ta = (["வழக்கமான வயல் கண்காணிப்பைத் தொடரவும்; இந்த முடிவை மட்டும் வைத்து சிகிச்சை எதையும் மேற்கொள்ள வேண்டாம்."] if healthy
                 else ["அருகிலுள்ள செடிகளை ஆய்வு செய்து, பாதுகாப்பான இடங்களில் மட்டும் தெரிவான பாதிப்புள்ள விழுந்த தாவரப் பொருட்களை அகற்றவும்.",
                       "தெளிவான தொடர் புகைப்படங்களை எடுத்து, அறிகுறிகள் பரவினால் உள்ளூர் வேளாண் அலுவலரின் ஆலோசனையைப் பெறவும்."])
    default_cultural = (["Maintain field sanitation and avoid moving wet plant material between plots.",
                 "Use locally recommended clean planting material and follow the local crop-production package."])
    default_cultural_ta = (["வயல் சுத்தத்தைப் பராமரித்து, ஈரமான தாவரப் பொருட்களை வயல்களுக்கு இடையே நகர்த்துவதைத் தவிர்க்கவும்.",
                 "உள்ளூரில் பரிந்துரைக்கப்பட்ட சுத்தமான நடவுப் பொருளைப் பயன்படுத்தி, உள்ளூர் பயிர் உற்பத்தி வழிமுறையைப் பின்பற்றவும்."])
    default_prevention = (["Monitor regularly, especially after weather favourable to disease.",
                   "Keep tools and hands clean before moving between plots."])
    default_prevention_ta = (["குறிப்பாக நோய்க்கு உகந்த வானிலைக்குப் பிறகு தொடர்ந்து கண்காணிக்கவும்.",
                   "வயல்களுக்கு இடையே நகரும் முன் கருவிகள் மற்றும் கைகளைச் சுத்தமாக வைக்கவும்."])

    symptoms = content.get("symptoms_en") or [
        "This runtime label is a screening result; visually confirm with an agricultural officer."
    ]
    symptoms_ta_fallback = [
        "இது ஒரு தானியங்கி திரையிடல் முடிவு; வேளாண் அலுவலரிடம் நேரில் உறுதிப்படுத்திக் கொள்ளவும்."
    ]
    cause = content.get("cause_en") or "Requires local official confirmation."
    why_it_occurs = content.get("why_it_occurs_en") or [
        "Weather, crop stage and local field conditions require official assessment."
    ]
    why_it_occurs_ta_fallback = [
        "வானிலை, பயிர் வளர்ச்சி நிலை மற்றும் உள்ளூர் வயல் நிலைமைகளுக்கு அதிகாரப்பூர்வ மதிப்பீடு தேவை."
    ]
    cultural = content.get("cultural_management_en") or default_cultural
    biological = content.get("biological_options_en") or []
    prevention = content.get("prevention_en") or default_prevention
    immediate = default_immediate  # always the safe, generic first-response guidance

    sources = deepcopy(OFFICIAL_SOURCES) + _extension_sources(content)

    result = {
        "outcome": STATUS_PARTIAL, "recommendation_version": VERSION,
        "recommendation_id": f"{VERSION}:{canonical_id}", "crop_id": crop,
        "runtime_label": runtime_label, "canonical_disease_id": canonical_id,
        "canonical_disease_name_en": name_en, "canonical_disease_name_ta": name_ta,
        "disease_category": category, "cause_en": cause,
        "cause_ta": (
            "உள்ளூர் அதிகாரப்பூர்வ உறுதிப்படுத்தல் தேவை." if not content.get("cause_en")
            else content.get("cause_ta") or _ta([cause])[0]
        ),
        "why_it_occurs_en": why_it_occurs,
        "why_it_occurs_ta": (
            content.get("why_it_occurs_ta") if content.get("why_it_occurs_en")
            else why_it_occurs_ta_fallback
        ) or _ta(why_it_occurs),
        "symptoms_en": symptoms,
        "symptoms_ta": (
            content.get("symptoms_ta") if content.get("symptoms_en")
            else symptoms_ta_fallback
        ) or _ta(symptoms),
        "immediate_actions_en": immediate, "immediate_actions_ta": default_immediate_ta,
        "cultural_management_en": cultural,
        "cultural_management_ta": (
            content.get("cultural_management_ta") if content.get("cultural_management_en")
            else default_cultural_ta
        ) or _ta(cultural),
        "biological_options_en": biological,
        "biological_options_ta": content.get("biological_options_ta") or _ta(biological),
        "nutrient_correction_en": [], "nutrient_correction_ta": [],
        "chemical_options": [], "chemical_recommendation_status": CHEMICAL_WITHHELD,
        "conventional_category_en": _CONVENTIONAL_CATEGORY_EN.get(category),
        "conventional_category_ta": _CONVENTIONAL_CATEGORY_TA.get(category),
        "prevention_en": prevention,
        "prevention_ta": (
            content.get("prevention_ta") if content.get("prevention_en")
            else default_prevention_ta
        ) or _ta(prevention),
        "escalation_conditions_en": ["Seek expert help promptly if symptoms spread, plants wilt, or yield is at risk."],
        "escalation_conditions_ta": ["அறிகுறிகள் பரவினால், செடிகள் வாடினால் அல்லது மகசூல் பாதிக்கப்படலாம் என்றால் உடனடியாக நிபுணர் உதவி பெறவும்."],
        "official_sources": sources, "verification_status": STATUS_PARTIAL,
        "last_verified_date": LAST_VERIFIED_DATE, "agricultural_disclaimer": DISCLAIMER,
        "content_sourced_from_extension_library": bool(content),
    }
    return result


def is_last_verified_stale(*, as_of: date | None = None) -> bool:
    """True once LAST_VERIFIED_DATE is more than a year old (as of ``as_of``).

    Doesn't change what's shown to farmers -- it's a maintenance signal (e.g. for
    a startup check or a scheduled test) that the registry is due for a human to
    re-check DISEASE_CONTENT against OFFICIAL_SOURCES / EXTENSION_SOURCES and bump
    LAST_VERIFIED_DATE. Never auto-advances the date itself.
    """
    today = as_of or datetime.now().date()
    verified = date.fromisoformat(LAST_VERIFIED_DATE)
    return (today - verified).days > LAST_VERIFIED_STALE_AFTER_DAYS
