"""Government scheme providers (docs: provider abstraction).

``GovernmentSchemeProvider`` is the seam that keeps the rest of the module
ignorant of *where* verified schemes come from. V1 ships a ``MockSchemeProvider``
seeded with well-known, verified central + Tamil Nadu schemes and their real
eligibility rules. Future providers (Tamil Nadu Government portal, Central
Government APIs, an Admin Portal, a Scraper) implement the same Protocol and are
selected in ``get_default_provider`` with no change to the service, engine, API
or frontend. Only verified schemes are ever returned (docs/PRODUCT_RULES.md rule 4).
"""
from __future__ import annotations

from datetime import date
from typing import Protocol

from app.core.logging import get_logger
from app.core.provider_policy import test_mocks_enabled
from app.modules.schemes.constants import (
    SOURCE_CURATED,
    SOURCE_MOCK,
    FarmerCategory,
    SchemeCategory,
)
from app.modules.schemes.curated_data import (
    CURATED_SCHEMES,
    LAST_VERIFIED_DATE,
    LAST_VERIFIED_STALE_AFTER_DAYS,
    is_curated_data_stale,
)
from app.modules.schemes.exceptions import SchemeDataUnavailableError
from app.modules.schemes.provider_types import ProviderDocument, ProviderScheme

logger = get_logger("schemes.provider")


class GovernmentSchemeProvider(Protocol):
    """Returns the set of verified schemes to store. The single external seam."""

    source: str

    async def fetch_schemes(self) -> list[ProviderScheme]: ...


# --------------------------------------------------------------------------- #
# Verified sample schemes (central + Tamil Nadu). Real programmes + rules.
# --------------------------------------------------------------------------- #
_MOCK_SCHEMES: list[ProviderScheme] = [
    ProviderScheme(
        slug="pm-kisan",
        title="PM-KISAN Samman Nidhi",
        category=SchemeCategory.INCOME_SUPPORT.value,
        description=(
            "Income support of ₹6,000 per year in three instalments to eligible "
            "landholding farmer families."
        ),
        benefits="₹6,000 per year, paid directly to the bank account (DBT).",
        eligibility_summary="All landholding farmer families with cultivable land.",
        application_steps=[
            "Register at your Common Service Centre or pmkisan.gov.in.",
            "Provide Aadhaar, land records and bank account details.",
            "Complete e-KYC.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://pmkisan.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land ownership records"),
            ProviderDocument("Bank account passbook"),
        ],
        source=SOURCE_MOCK,
        last_date=None,
    ),
    ProviderScheme(
        slug="pmfby",
        title="Pradhan Mantri Fasal Bima Yojana (Crop Insurance)",
        category=SchemeCategory.INSURANCE.value,
        description=(
            "Comprehensive crop insurance against non-preventable natural risks "
            "from sowing to post-harvest."
        ),
        benefits="Low-premium insurance cover for notified crops.",
        eligibility_summary="All farmers growing notified crops, including tenants.",
        application_steps=[
            "Apply through your bank, CSC or the National Crop Insurance Portal.",
            "Submit land and sowing details before the cut-off date.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://pmfby.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records / tenancy proof"),
            ProviderDocument("Bank passbook"),
            ProviderDocument("Sowing certificate", required=False),
        ],
        source=SOURCE_MOCK,
        last_date=date(2026, 7, 31),
    ),
    ProviderScheme(
        slug="rwbcis",
        title="Restructured Weather Based Crop Insurance Scheme (RWBCIS)",
        category=SchemeCategory.INSURANCE.value,
        description=(
            "Insurance payout triggered by adverse weather (rainfall, "
            "temperature, humidity) rather than assessed crop yield loss, "
            "covering notified crops."
        ),
        benefits=(
            "Faster claims based on weather-station data instead of manual "
            "yield assessment."
        ),
        eligibility_summary=(
            "Farmers growing notified crops in areas with a Reference Weather Station."
        ),
        application_steps=[
            "Apply through your bank, CSC, or the National Crop Insurance Portal "
            "(same portal as PMFBY).",
            "Submit land and sowing details before the cut-off date.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://pmfby.gov.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records / tenancy proof"),
            ProviderDocument("Bank passbook"),
        ],
        source=SOURCE_MOCK,
    ),
    ProviderScheme(
        slug="kcc",
        title="Kisan Credit Card (KCC)",
        category=SchemeCategory.LOAN.value,
        description=(
            "Short-term credit for cultivation and allied activities at a "
            "concessional interest rate."
        ),
        benefits="Credit up to ₹3 lakh at subsidised interest with timely repayment.",
        eligibility_summary="All farmers — owner cultivators, tenants and sharecroppers.",
        application_steps=[
            "Visit your bank branch with identity and land documents.",
            "Fill the KCC application and submit for verification.",
        ],
        departments=["Department of Financial Services"],
        official_url="https://www.myscheme.gov.in/schemes/kcc",
        documents=[
            ProviderDocument("Identity proof (Aadhaar/Voter ID)"),
            ProviderDocument("Land ownership documents"),
            ProviderDocument("Passport-size photograph"),
        ],
        source=SOURCE_MOCK,
    ),
    ProviderScheme(
        slug="smam",
        title="Sub-Mission on Agricultural Mechanization (SMAM)",
        category=SchemeCategory.EQUIPMENT.value,
        description=(
            "Subsidy on farm machinery — tractors, power tillers, power weeders, "
            "rotavators — to reduce dependence on manual labour and improve "
            "timeliness of operations."
        ),
        benefits=(
            "40-50% subsidy on eligible machinery; higher rate for small, "
            "marginal, and women farmers."
        ),
        eligibility_summary=(
            "Individual farmers, small and marginal farmers, women farmers, "
            "and farmer groups."
        ),
        application_steps=[
            "Register on the central Farm Machinery / DBT portal "
            "(agrimachinery.nic.in) or your state agriculture subsidy portal.",
            "Upload Aadhaar-linked bank details and submit for verification.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://agrimachinery.nic.in",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records"),
            ProviderDocument("Bank passbook"),
        ],
        source=SOURCE_MOCK,
        farmer_categories=[
            FarmerCategory.MARGINAL.value,
            FarmerCategory.SMALL.value,
            FarmerCategory.SEMI_MEDIUM.value,
            FarmerCategory.MEDIUM.value,
        ],
    ),
    ProviderScheme(
        slug="soil-health-card",
        title="Soil Health Card Scheme",
        category=SchemeCategory.OTHER.value,
        description="Free soil testing with crop-wise nutrient recommendations.",
        benefits="A soil health card every cycle with fertilizer guidance.",
        eligibility_summary="All farmers with cultivable land.",
        application_steps=[
            "Register with your local agriculture office.",
            "Provide a soil sample from your field for testing.",
        ],
        departments=["Department of Agriculture & Farmers Welfare"],
        official_url="https://soilhealth.dac.gov.in",
        documents=[ProviderDocument("Land records"), ProviderDocument("Aadhaar card")],
        source=SOURCE_MOCK,
    ),
    ProviderScheme(
        slug="pm-kusum",
        title="PM-KUSUM Solar Pump Subsidy",
        category=SchemeCategory.IRRIGATION.value,
        description=(
            "Subsidy for standalone solar agricultural pumps and solarisation of "
            "existing grid-connected pumps."
        ),
        benefits="Up to 60% subsidy on solar pump installation.",
        eligibility_summary="Farmers with cultivable land needing irrigation pumps.",
        application_steps=[
            "Apply through the state renewable energy agency portal.",
            "Submit land and existing pump/connection details.",
        ],
        departments=["Ministry of New and Renewable Energy"],
        official_url="https://pmkusum.mnre.gov.in",
        documents=[
            ProviderDocument("Land records"),
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Bank passbook"),
        ],
        source=SOURCE_MOCK,
    ),
    ProviderScheme(
        slug="tn-free-electricity",
        title="Tamil Nadu Free Electricity for Farmers",
        category=SchemeCategory.SUBSIDY.value,
        description=(
            "Free electricity for agricultural pump-set connections to farmers in "
            "Tamil Nadu."
        ),
        benefits="100% subsidy on agricultural power for eligible pump-sets.",
        eligibility_summary="Tamil Nadu farmers with an agricultural service connection.",
        application_steps=[
            "Apply at your local TANGEDCO office.",
            "Provide the agricultural service connection and land details.",
        ],
        departments=["TANGEDCO", "Tamil Nadu Agriculture Department"],
        official_url="https://www.tangedco.gov.in",
        documents=[
            ProviderDocument("Agricultural service connection number"),
            ProviderDocument("Land records"),
            ProviderDocument("Aadhaar card"),
        ],
        source=SOURCE_MOCK,
        state="Tamil Nadu",
        states=["Tamil Nadu"],
    ),
    ProviderScheme(
        slug="tn-drip-subsidy",
        title="Tamil Nadu Micro Irrigation (Drip) Subsidy",
        category=SchemeCategory.IRRIGATION.value,
        description=(
            "Subsidy on drip and sprinkler systems under the Tamil Nadu micro "
            "irrigation programme, with higher support for small and marginal farmers."
        ),
        benefits="Up to 100% subsidy for small/marginal farmers, 75% for others.",
        eligibility_summary=(
            "Small and marginal Tamil Nadu farmers growing horticulture or row crops."
        ),
        application_steps=[
            "Apply through the Tamil Nadu Horticulture Department portal.",
            "Submit land, crop and water-source details for inspection.",
        ],
        departments=["Tamil Nadu Horticulture Department"],
        official_url="https://tnhorticulture.tn.gov.in",
        documents=[
            ProviderDocument("Land records"),
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Water source proof"),
            ProviderDocument("Bank passbook"),
        ],
        source=SOURCE_MOCK,
        state="Tamil Nadu",
        states=["Tamil Nadu"],
        crops=["sugarcane", "cotton", "tomato", "banana", "vegetables", "maize"],
        farmer_categories=[
            FarmerCategory.MARGINAL.value,
            FarmerCategory.SMALL.value,
            FarmerCategory.SEMI_MEDIUM.value,
        ],
        max_land_hectares=4.0,
    ),
    ProviderScheme(
        slug="nfsm-pulses",
        title="National Food Security Mission — Pulses",
        category=SchemeCategory.SEEDS.value,
        description=(
            "Assistance for certified pulse seeds, demonstrations and inputs to "
            "raise pulse productivity for low-income farmers."
        ),
        benefits="Subsidised certified seed and input assistance for pulses.",
        eligibility_summary="Small and marginal pulse growers below the income ceiling.",
        application_steps=[
            "Register with your district agriculture office.",
            "Collect certified seed from the notified distribution centre.",
        ],
        departments=["Department of Agriculture & Farmers Welfare"],
        official_url="https://www.nfsm.gov.in",
        documents=[
            ProviderDocument("Land records"),
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Income certificate"),
        ],
        source=SOURCE_MOCK,
        crops=["black gram", "green gram", "red gram", "bengal gram", "pulses"],
        farmer_categories=[FarmerCategory.MARGINAL.value, FarmerCategory.SMALL.value],
        max_land_hectares=2.0,
        max_annual_income=200000,
    ),
    ProviderScheme(
        slug="pkvy",
        title="Paramparagat Krishi Vikas Yojana (PKVY)",
        category=SchemeCategory.ORGANIC.value,
        description=(
            "Cluster-based support for farmers transitioning to organic, "
            "chemical-free farming, including certification and market linkage."
        ),
        benefits=(
            "₹15,000 per hectare paid directly to the farmer via DBT over "
            "3 years, plus certification and market-access support."
        ),
        eligibility_summary=(
            "Farmers willing to join an organic farming cluster in their area."
        ),
        application_steps=[
            "Approach your Regional Council or district agriculture office to join "
            "an organic cluster.",
            "Complete PGS-India organic certification enrollment.",
        ],
        departments=["Ministry of Agriculture & Farmers Welfare"],
        official_url="https://www.myscheme.gov.in/schemes/pkvy",
        documents=[
            ProviderDocument("Aadhaar card"),
            ProviderDocument("Land records"),
        ],
        source=SOURCE_MOCK,
    ),
]


class MockSchemeProvider:
    """Deterministic set of verified central + Tamil Nadu schemes (dev/tests)."""

    source = SOURCE_MOCK

    def __init__(self, *, schemes: list[ProviderScheme] | None = None) -> None:
        self._schemes = schemes if schemes is not None else _MOCK_SCHEMES

    async def fetch_schemes(self) -> list[ProviderScheme]:
        return list(self._schemes)


class CuratedSchemeProvider:
    """Hand-curated, individually-verified real schemes (see curated_data.py).

    Not a live government API -- each scheme was looked up on its own official
    page (or a corroborating PIB/state-government factsheet) and entered by
    hand, the same "static, reviewed-in-repository, real, dated, sourced"
    approach already used for app/disease_recommendations/registry.py. This is
    the default outside test/dev mock mode, unless the data has gone stale
    (see is_curated_data_stale below), in which case the provider fails closed
    again rather than keep serving an unreviewed snapshot.
    """

    source = SOURCE_CURATED

    def __init__(self, *, schemes: list[ProviderScheme] | None = None) -> None:
        self._schemes = schemes if schemes is not None else CURATED_SCHEMES

    async def fetch_schemes(self) -> list[ProviderScheme]:
        return list(self._schemes)


class UnavailableSchemeProvider:
    """Fails closed until a current verified scheme source is configured."""

    source = "unavailable"

    async def fetch_schemes(self) -> list[ProviderScheme]:
        raise SchemeDataUnavailableError()


def get_default_provider() -> GovernmentSchemeProvider:
    """Select the configured provider.

    Explicit dev/test mock first; then the hand-curated real-scheme snapshot,
    unless it has gone stale (nobody has re-checked it against its sources
    within LAST_VERIFIED_STALE_AFTER_DAYS) -- in which case this fails closed
    exactly like it did before curated_data.py existed, rather than silently
    keep serving deadlines/subsidy rates nobody has re-verified.
    """
    if test_mocks_enabled():
        logger.info("scheme provider: explicit development/test mock")
        return MockSchemeProvider()
    if is_curated_data_stale():
        logger.warning(
            "scheme provider unavailable: curated data last verified %s "
            "(older than %s days) -- re-verify app/modules/schemes/"
            "curated_data.py against its official sources and bump "
            "LAST_VERIFIED_DATE before this can serve farmers again",
            LAST_VERIFIED_DATE,
            LAST_VERIFIED_STALE_AFTER_DAYS,
        )
        return UnavailableSchemeProvider()
    logger.info(
        "scheme provider: curated, individually-verified official schemes "
        "(last verified %s)",
        LAST_VERIFIED_DATE,
    )
    return CuratedSchemeProvider()
