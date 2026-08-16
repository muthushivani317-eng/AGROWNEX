"""Hand-curated, individually-verified real government farmer schemes.

Why this file exists (2026-08 pre-release audit follow-up): the schemes module
previously had no real data source in non-test environments -- it correctly
failed closed (``UnavailableSchemeProvider``) rather than fabricate anything,
because no dynamic government API with usable eligibility-rules data could be
found (``data.gov.in``'s PM-KISAN/PMFBY datasets are aggregate statistics, not
eligibility rules; no public API exists for myscheme.gov.in; a candidate bulk
dataset turned out to be ~700 unlabeled, duplicated PDFs unsuitable for
reliable ingestion).

Instead of bulk-ingesting unverifiable data, every scheme below was looked up
individually on its own official government page (or, where the scheme's own
site is JavaScript-rendered and didn't yield readable content, a corroborating
Press Information Bureau / state-government factsheet) and entered by hand.
This mirrors the same "static, reviewed-in-repository, real, dated, sourced"
approach already used for ``app/disease_recommendations/registry.py`` -- not a
live feed, but real content, not a guess. Every field below was checked
against SCHEME_SOURCES; anything a source didn't clearly state (e.g. exact
current PMFBY premium rates, or a specific state-wide enrollment cut-off date)
was left out rather than guessed, consistent with the rest of this app's
"never fabricate agricultural/financial content" standard.

Numbers, deadlines and portal URLs for government schemes change. Farmers are
always shown official_url and told to verify before applying (see
docs/PRODUCT_RULES.md rule 4 and DISCLAIMER below) -- and LAST_VERIFIED_DATE /
is_curated_data_stale() make the provider fail closed again if this file goes
too long without a human re-checking it against SCHEME_SOURCES.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.modules.schemes.constants import (
    ANY,
    SOURCE_CURATED,
    FarmerCategory,
    SchemeCategory,
)
from app.modules.schemes.provider_types import ProviderDocument, ProviderScheme

DISCLAIMER = "VERIFY AGAINST OFFICIAL SOURCE BEFORE APPLYING"

# The date every entry in CURATED_SCHEMES below was last manually checked
# against SCHEME_SOURCES. Bump this by hand only when someone actually
# re-reviews the content -- never auto-set to "today". Scheme deadlines,
# subsidy percentages and portal URLs move faster than the agronomic content
# in disease_recommendations, so the staleness window here is shorter (six
# months, not a year).
LAST_VERIFIED_DATE = "2026-08-16"
LAST_VERIFIED_STALE_AFTER_DAYS = 180


def is_curated_data_stale(*, as_of: date | None = None) -> bool:
    today = as_of or datetime.now().date()
    verified = date.fromisoformat(LAST_VERIFIED_DATE)
    return (today - verified).days > LAST_VERIFIED_STALE_AFTER_DAYS


# --------------------------------------------------------------------------- #
# Citation registry -- every source actually read while building
# CURATED_SCHEMES below. `source_date` is the *document's own* date where one
# was stated on the page; `None` where the page didn't give one (a live portal
# has no fixed "publish date") -- never guessed.
# --------------------------------------------------------------------------- #
SCHEME_SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "pmkisan_portal",
        "publisher": "Department of Agriculture & Farmers Welfare, Government of India",
        "title": "PM-KISAN official portal",
        "url": "https://pmkisan.gov.in",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pmfby_portal",
        "publisher": "Ministry of Agriculture & Farmers Welfare, Government of India",
        "title": "PMFBY / National Crop Insurance Portal",
        "url": "https://pmfby.gov.in",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pib_pmfby_factsheet",
        "publisher": "Press Information Bureau, Government of India",
        "title": "Empowering Annadatas: Pradhan Mantri Fasal Bima Yojana (Factsheet)",
        "url": "https://www.pib.gov.in/FactsheetDetails.aspx?Id=149055",
        "source_date": "2024-02-15",
        "official": True,
    },
    {
        "source_id": "pib_rwbcis_cabinet",
        "publisher": "Press Information Bureau, Government of India",
        "title": "Cabinet approval for continuation of PMFBY and RWBCIS",
        "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2089249",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pib_kcc_factsheet",
        "publisher": "Press Information Bureau, Government of India",
        "title": "Kisan Credit Card (KCC) Factsheet",
        "url": "https://www.pib.gov.in/FactsheetDetails.aspx?Id=148600",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pib_soil_health_card",
        "publisher": "Press Information Bureau, Government of India",
        "title": "Celebrating a Decade of Soil Health Cards",
        "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2104403",
        "source_date": "2025-02-01",
        "official": True,
    },
    {
        "source_id": "pib_pmkusum_factsheet",
        "publisher": "Press Information Bureau, Government of India",
        "title": "PM-KUSUM Factsheet",
        "url": "https://www.pib.gov.in/FactsheetDetails.aspx?Id=148576",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pib_pkvy",
        "publisher": "Press Information Bureau, Government of India",
        "title": "Paramparagat Krishi Vikas Yojana (PKVY): Nurturing Organic Farming in India",
        "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2099756",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pgsindia_ncof",
        "publisher": "National Centre of Organic and Natural Farming, Government of India",
        "title": "PGS-India (Participatory Guarantee System) portal",
        "url": "https://pgsindia-ncof.gov.in",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "nfsm_portal",
        "publisher": "Department of Agriculture & Farmers Welfare, Government of India",
        "title": "National Food Security Mission official portal",
        "url": "https://www.nfsm.gov.in",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "pib_nfsm",
        "publisher": "Press Information Bureau, Government of India",
        "title": "National Food Security Mission",
        "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2114891",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "tn_aed_smam",
        "publisher": "Agricultural Engineering Department, Government of Tamil Nadu",
        "title": "Sub-Mission on Agricultural Mechanisation (Tamil Nadu)",
        "url": "https://aed.tn.gov.in/en/schemes/agricultural-mechanisation/sub-mission-on-agricultural-mechanisation/",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "tn_horticulture_micro_irrigation",
        "publisher": "Horticulture and Plantation Crops Department, Government of Tamil Nadu",
        "title": "Micro Irrigation subsidy under PMKSY (Per Drop More Crop) -- confirmed via "
        "Tiruvannamalai District Horticulture page",
        "url": "https://tnhorticulture.tn.gov.in",
        "source_date": None,
        "official": True,
    },
    {
        "source_id": "tn_land_reforms_farmers_security",
        "publisher": "Commissionerate of Land Reforms, Government of Tamil Nadu",
        "title": "Chief Minister's Uzhavar Pathukappu Thittam (Farmers' Security Scheme)",
        "url": "https://landreforms.tn.gov.in/UPT.html",
        "source_date": None,
        "official": True,
    },
]

_SOURCE_BY_ID = {s["source_id"]: s for s in SCHEME_SOURCES}


# --------------------------------------------------------------------------- #
# Verified real schemes (central + Tamil Nadu). Each docstring-style comment
# names the SCHEME_SOURCES entr(ies) it was built from.
# --------------------------------------------------------------------------- #
CURATED_SCHEMES: list[ProviderScheme] = [
    # Source: pmkisan_portal (fetched 2026-08-16; exclusion list quoted
    # verbatim from the official eligibility page).
    ProviderScheme(
        slug="pm-kisan",
        title="PM-KISAN Samman Nidhi",
        category=SchemeCategory.INCOME_SUPPORT.value,
        description=(
            "Central Sector scheme providing direct income support to eligible "
            "landholding farmer families across India."
        ),
        benefits=(
            "₹6,000 per year, paid in three equal instalments of ₹2,000 directly "
            "to the farmer's bank account (DBT)."
        ),
        eligibility_summary=(
            "Landholding farmer families (husband, wife and minor children). "
            "Not eligible: institutional landholders; holders of constitutional "
            "posts; serving or retired government officers/employees; pensioners "
            "earning ₹10,000+ per month; anyone who paid income tax in the last "
            "assessment year; and licensed professionals (doctors, engineers, "
            "lawyers, chartered accountants, architects)."
        ),
        application_steps=[
            "Register as a new farmer via pmkisan.gov.in or your nearest Common "
            "Service Centre (CSC).",
            "Provide Aadhaar, land ownership records and bank account details.",
            "Complete e-KYC (required to receive instalments).",
            "Check status anytime with 'Know Your Status' on the portal.",
        ],
        departments=["Department of Agriculture & Farmers Welfare"],
        official_url="https://pmkisan.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land ownership records"),
            ProviderDocument("Bank account passbook"),
        ],
        source=SOURCE_CURATED,
    ),
    # Sources: pmfby_portal, pib_pmfby_factsheet. Deliberately no `last_date` --
    # PMFBY enrollment cut-offs are set per season/state on the live portal,
    # not a single fixed date; showing a guessed date here would be worse than
    # showing none (see docs/CLAUDE.md -- never fabricate a deadline).
    ProviderScheme(
        slug="pmfby",
        title="Pradhan Mantri Fasal Bima Yojana (Crop Insurance)",
        category=SchemeCategory.INSURANCE.value,
        description=(
            "Government crop insurance covering yield and production losses from "
            "non-preventable natural risks (drought, flood, pest and disease "
            "attack, and more) from pre-sowing through post-harvest stages."
        ),
        benefits=(
            "Low, uniform-premium insurance cover for notified crops, with claims "
            "increasingly assessed using remote sensing, drones and geotagged "
            "photography rather than manual yield surveys alone."
        ),
        eligibility_summary=(
            "All farmers growing a notified crop in a notified area, including "
            "tenant farmers and sharecroppers. Enrollment is voluntary for every "
            "farmer. Exact premium share and the enrollment window are set per "
            "season and state -- confirm current dates on pmfby.gov.in or with "
            "your bank/CSC before the cut-off."
        ),
        application_steps=[
            "Apply through your bank, Common Service Centre, or the National "
            "Crop Insurance Portal (pmfby.gov.in) before your state's notified "
            "cut-off date for the season.",
            "Submit land records/tenancy proof and sowing details.",
            "Loanee farmers with a crop loan are enrolled by their bank unless "
            "they opt out in writing; non-loanee farmers enroll directly.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://pmfby.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records / tenancy proof"),
            ProviderDocument("Bank account passbook"),
            ProviderDocument("Sowing certificate", required=False),
        ],
        source=SOURCE_CURATED,
    ),
    # Sources: pmfby_portal, pib_rwbcis_cabinet -- RWBCIS runs on the same
    # National Crop Insurance Portal as PMFBY, as a weather-index alternative
    # to it in notified areas with a Reference Weather Station.
    ProviderScheme(
        slug="rwbcis",
        title="Restructured Weather Based Crop Insurance Scheme (RWBCIS)",
        category=SchemeCategory.INSURANCE.value,
        description=(
            "Insurance payout triggered by adverse weather (rainfall, "
            "temperature, humidity, etc.) measured at a Reference Weather "
            "Station, rather than by a manually assessed crop yield loss -- runs "
            "alongside PMFBY as a weather-index option in notified areas."
        ),
        benefits=(
            "Faster claim settlement based on weather-station data instead of "
            "field-by-field yield assessment."
        ),
        eligibility_summary=(
            "Farmers growing a notified crop in a notified area covered by a "
            "Reference Weather Station. Same enrollment channel as PMFBY."
        ),
        application_steps=[
            "Apply through your bank, Common Service Centre, or the National "
            "Crop Insurance Portal (pmfby.gov.in) -- same portal as PMFBY.",
            "Submit land and sowing details before the notified cut-off date.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://pmfby.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records / tenancy proof"),
            ProviderDocument("Bank account passbook"),
        ],
        source=SOURCE_CURATED,
    ),
    # Source: pib_kcc_factsheet.
    ProviderScheme(
        slug="kcc",
        title="Kisan Credit Card (KCC)",
        category=SchemeCategory.LOAN.value,
        description=(
            "Short-term credit from the banking system for cultivation, "
            "post-harvest expenses and farm investment needs, at a concessional "
            "interest rate."
        ),
        benefits=(
            "Short-term crop loans up to ₹3 lakh benefit from the Government's "
            "Interest Subvention Scheme. Marginal farmers can get a simplified "
            "'Flexi KCC' of ₹10,000-₹50,000 without land valuation; other "
            "farmers' limits are based on cultivated area and the district's "
            "crop scale of finance."
        ),
        eligibility_summary=(
            "Individual or joint owner-cultivators, tenant farmers, oral "
            "lessees and sharecroppers, plus Self Help Groups and Joint "
            "Liability Groups of farmers."
        ),
        application_steps=[
            "Visit your bank branch (or a Common Service Centre) with a simple "
            "one-page KCC application form, available from the bank or "
            "agriculture ministry websites.",
            "Submit a copy of your land records and details of crops sown.",
            "Bank verifies and issues the card/limit.",
        ],
        departments=["Department of Financial Services"],
        official_url="https://www.myscheme.gov.in/schemes/kcc",
        documents=[
            ProviderDocument("Identity proof (Aadhaar/Voter ID)"),
            ProviderDocument("Land ownership documents"),
            ProviderDocument("Passport-size photograph"),
        ],
        source=SOURCE_CURATED,
    ),
    # Source: pib_soil_health_card (explicitly dated "as of February 2025" on
    # the page). Note: merged into Rashtriya Krishi Vikas Yojana since 2022-23.
    ProviderScheme(
        slug="soil-health-card",
        title="Soil Health Card Scheme",
        category=SchemeCategory.OTHER.value,
        description=(
            "Free soil testing that gives farmers a report on 12 soil "
            "parameters (N, P, K, sulphur; zinc, iron, copper, manganese, "
            "boron; pH, EC and organic carbon) with crop-wise fertilizer-dosage "
            "recommendations. Implemented since 2022-23 under the Rashtriya "
            "Krishi Vikas Yojana."
        ),
        benefits=(
            "A soil health card, renewed roughly every farming cycle, with "
            "tailored nutrient/fertilizer guidance to improve soil health and "
            "yield."
        ),
        eligibility_summary="All farmers with cultivable land.",
        application_steps=[
            "Register with your local agriculture office / village-level Soil "
            "Testing Lab.",
            "Provide a soil sample from your field (typically collected twice a "
            "year or when the field is fallow).",
            "Collect your Soil Health Card, or check it on the mobile app.",
        ],
        departments=["Department of Agriculture & Farmers Welfare"],
        official_url="https://soilhealth.dac.gov.in",
        documents=[ProviderDocument("Land records"), ProviderDocument("Aadhaar card")],
        source=SOURCE_CURATED,
    ),
    # Source: pib_pmkusum_factsheet. Component B (individual off-grid solar
    # pump) is the piece most relevant to a farmer -- the actual central+state
    # subsidy is 30%+30% (60% total), not a flat "40-50%".
    ProviderScheme(
        slug="pm-kusum",
        title="PM-KUSUM Solar Pump Subsidy",
        category=SchemeCategory.IRRIGATION.value,
        description=(
            "Subsidy scheme to replace diesel irrigation pumps with solar "
            "pumps (Component B) and to solarise existing grid-connected pumps "
            "(Component C), reducing diesel dependence and giving farmers "
            "reliable daytime power for irrigation."
        ),
        benefits=(
            "For individual off-grid solar pumps (Component B): Central "
            "Financial Assistance of 30% of the benchmark cost plus a further "
            "30% state subsidy -- the farmer pays about 40% (higher Central "
            "assistance of 50% applies in North-Eastern and hilly states). "
            "Feeder solarisation (Component C) is subsidised at 30% (50% in "
            "special-category regions)."
        ),
        eligibility_summary="Farmers with cultivable land needing an irrigation pump.",
        application_steps=[
            "For an individual pump: apply through your state's renewable "
            "energy implementing agency.",
            "Submit land records and details of your existing pump/electrical "
            "connection, if any.",
        ],
        departments=["Ministry of New and Renewable Energy"],
        official_url="https://pmkusum.mnre.gov.in",
        documents=[
            ProviderDocument("Land records"),
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Bank account passbook"),
        ],
        source=SOURCE_CURATED,
    ),
    # Sources: pib_pkvy, pgsindia_ncof.
    ProviderScheme(
        slug="pkvy",
        title="Paramparagat Krishi Vikas Yojana (PKVY)",
        category=SchemeCategory.ORGANIC.value,
        description=(
            "Cluster-based support for farmer groups transitioning to organic, "
            "chemical-free farming, covering inputs, certification and market "
            "linkage over three years."
        ),
        benefits=(
            "₹31,500 per hectare over 3 years, paid via bank transfer: ₹15,000 "
            "for organic inputs, ₹4,500 for marketing/packaging/branding/value "
            "addition, ₹3,000 for certification and residue testing, and "
            "₹9,000 for training."
        ),
        eligibility_summary=(
            "Farmers willing to join an organic-farming cluster in their area "
            "(the scheme is cluster-based, not an individual application)."
        ),
        application_steps=[
            "Approach your Regional Council or district agriculture office to "
            "join (or help form) an organic cluster.",
            "Enroll for PGS-India (Participatory Guarantee System) organic "
            "certification at pgsindia-ncof.gov.in.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://pgsindia-ncof.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records"),
        ],
        source=SOURCE_CURATED,
    ),
    # Sources: nfsm_portal, pib_nfsm. Kept deliberately general (rice, wheat,
    # pulses, coarse cereals) -- the old mock's pulses-only framing and its
    # specific land/income ceilings were never independently confirmed, so
    # they're not repeated here rather than guessed.
    ProviderScheme(
        slug="nfsm",
        title="National Food Security Mission (NFSM)",
        category=SchemeCategory.SEEDS.value,
        description=(
            "Central mission to raise production and productivity of rice, "
            "wheat, pulses and coarse cereals in a sustainable way, implemented "
            "through the states."
        ),
        benefits=(
            "Assistance for certified seed of newly released varieties/hybrids, "
            "crop demonstrations, integrated pest management training, and "
            "other production-technology incentives -- exact assistance amounts "
            "are set by each state's action plan."
        ),
        eligibility_summary=(
            "Farmers growing rice, wheat, pulses or coarse cereals in a "
            "district covered by the state's NFSM action plan."
        ),
        application_steps=[
            "Register with your district agriculture office.",
            "Collect certified seed / inputs from the notified distribution "
            "centre for your area.",
        ],
        departments=["Department of Agriculture & Farmers Welfare"],
        official_url="https://www.nfsm.gov.in",
        documents=[
            ProviderDocument("Land records"),
            ProviderDocument("Aadhaar card"),
        ],
        source=SOURCE_CURATED,
    ),
    # Source: tn_aed_smam (Tamil Nadu's own SMAM page -- used instead of a
    # national-average figure since we have the state's actual percentages).
    ProviderScheme(
        slug="tn-farm-mechanization",
        title="Sub-Mission on Agricultural Mechanisation (Tamil Nadu)",
        category=SchemeCategory.EQUIPMENT.value,
        description=(
            "Subsidy on farm machinery -- tractors, rotavators, power tillers "
            "(8 BHP+), paddy transplanters, power weeders and similar "
            "implements -- to bring mechanization to small and marginal "
            "farmers in Tamil Nadu."
        ),
        benefits=(
            "50% subsidy for SC/ST, small, marginal and women farmers; 40% for "
            "other farmers (funded 60% by the Union Government and 40% by the "
            "Tamil Nadu Government)."
        ),
        eligibility_summary="All Tamil Nadu farmers, in all districts except Chennai.",
        application_steps=[
            "Contact the Assistant Executive Engineer (Agricultural "
            "Engineering Department) in your project district.",
            "Submit land records and bank details for verification.",
        ],
        departments=["Agricultural Engineering Department, Government of Tamil Nadu"],
        official_url="https://aed.tn.gov.in/en/schemes/agricultural-mechanisation/sub-mission-on-agricultural-mechanisation/",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records"),
            ProviderDocument("Bank account passbook"),
        ],
        source=SOURCE_CURATED,
        state="Tamil Nadu",
        states=["Tamil Nadu"],
        # No farmer_categories restriction: every category qualifies, just at
        # a different subsidy rate (50% vs 40%) -- not a hard eligibility gate.
        farmer_categories=[ANY],
    ),
    # Source: tn_horticulture_micro_irrigation (subsidy % confirmed via the
    # Tiruvannamalai District Horticulture Department page, same content as
    # published centrally by the Horticulture Dept for the PMKSY-PDMC scheme).
    ProviderScheme(
        slug="tn-drip-subsidy",
        title="Tamil Nadu Micro Irrigation (Drip) Subsidy",
        category=SchemeCategory.IRRIGATION.value,
        description=(
            "Subsidy on drip/sprinkler micro-irrigation systems for Tamil Nadu "
            "farmers under PMKSY's Per Drop More Crop component, to improve "
            "water-use efficiency."
        ),
        benefits=(
            "100% subsidy for small and marginal farmers, 75% for other "
            "farmers, for up to 5 hectares."
        ),
        eligibility_summary="Tamil Nadu farmers, for holdings up to 5 hectares.",
        application_steps=[
            "Register on TNHORTNET and apply through the Horticulture "
            "Department's Micro Irrigation (MIMIS) portal.",
            "Submit land records (Chitta and Adangal), an FMB sketch, water "
            "source and soil-test details, and bank passbook copy.",
            "Field inspection by the local Horticulture Officer before "
            "installation.",
        ],
        departments=["Horticulture and Plantation Crops Department, Government of Tamil Nadu"],
        official_url="https://tnhorticulture.tn.gov.in",
        documents=[
            ProviderDocument("Land records (Chitta and Adangal)"),
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Water source proof"),
            ProviderDocument("Bank account passbook"),
        ],
        source=SOURCE_CURATED,
        state="Tamil Nadu",
        states=["Tamil Nadu"],
        max_land_hectares=5.0,
    ),
    # Source: tn_land_reforms_farmers_security (fetched directly, 2026-08-16).
    # New addition -- not in the old mock data. A real, verifiable Tamil Nadu
    # welfare scheme that fits this app's farmer base well.
    ProviderScheme(
        slug="tn-farmers-security-scheme",
        title="Chief Minister's Uzhavar Pathukappu Thittam (Farmers' Security Scheme)",
        category=SchemeCategory.OTHER.value,
        description=(
            "Tamil Nadu welfare scheme (since September 2011) providing "
            "financial assistance to registered small/marginal farmers and "
            "agricultural labourers, and their dependents, covering accidents, "
            "old age, illness and death."
        ),
        benefits=(
            "For the member: old-age pension (₹1,000/month), accident relief "
            "(₹20,000-₹1,00,000 depending on severity), natural death "
            "assistance (₹20,000), funeral expenses (₹2,500), monthly support "
            "during serious illness (₹1,000), and marriage assistance "
            "(₹8,000-₹10,000). Dependents (non-earning spouse, children, "
            "parents) are covered for marriage assistance, educational grants, "
            "orphan support and funeral expenses."
        ),
        eligibility_summary=(
            "Small or marginal farmers, or agricultural labourers, aged 18-65, "
            "engaged in farming, horticulture, sericulture, dairy, poultry or "
            "inland fishing."
        ),
        application_steps=[
            "Register with your Village Administrative Officer / Taluk Office "
            "under the Revenue Administration Department.",
            "File a claim through the same office when an eligible event "
            "(accident, illness, death, marriage) occurs.",
        ],
        departments=["Revenue Administration and Disaster Management Department, Government of Tamil Nadu"],
        official_url="https://landreforms.tn.gov.in/UPT.html",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records / labourer registration"),
        ],
        source=SOURCE_CURATED,
        state="Tamil Nadu",
        states=["Tamil Nadu"],
        farmer_categories=[FarmerCategory.MARGINAL.value, FarmerCategory.SMALL.value],
    ),
]
