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

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.core.logging import get_logger
from app.modules.schemes.constants import (
    ANY,
    SOURCE_MOCK,
    FarmerCategory,
    SchemeCategory,
    SchemeStatus,
)

logger = get_logger("schemes.provider")


@dataclass(frozen=True)
class ProviderDocument:
    name: str
    required: bool = True


@dataclass(frozen=True)
class ProviderScheme:
    """A normalized, verified scheme record, independent of the upstream source."""

    slug: str
    title: str
    category: str
    description: str
    benefits: str
    eligibility_summary: str
    application_steps: list[str]
    departments: list[str]
    official_url: str
    documents: list[ProviderDocument]
    source: str
    state: str = "all"
    start_date: date | None = None
    last_date: date | None = None
    status: str = SchemeStatus.ACTIVE.value
    # Structured rules (["all"] means no constraint).
    states: list[str] = field(default_factory=lambda: [ANY])
    districts: list[str] = field(default_factory=lambda: [ANY])
    crops: list[str] = field(default_factory=lambda: [ANY])
    farmer_categories: list[str] = field(default_factory=lambda: [ANY])
    min_land_hectares: float | None = None
    max_land_hectares: float | None = None
    max_annual_income: int | None = None


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
]


class MockSchemeProvider:
    """Deterministic set of verified central + Tamil Nadu schemes (dev/tests)."""

    source = SOURCE_MOCK

    def __init__(self, *, schemes: list[ProviderScheme] | None = None) -> None:
        self._schemes = schemes if schemes is not None else _MOCK_SCHEMES

    async def fetch_schemes(self) -> list[ProviderScheme]:
        return list(self._schemes)


def get_default_provider() -> GovernmentSchemeProvider:
    """Select the configured provider (mock until a real source is wired in)."""
    logger.info("scheme provider: mock (verified sample schemes)")
    return MockSchemeProvider()
