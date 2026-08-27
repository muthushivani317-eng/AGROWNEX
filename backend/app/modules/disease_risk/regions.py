from __future__ import annotations

import re


def _normalize(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", value.casefold())
    return normalized.removesuffix("district")


# Disease-risk packs currently released to farmers are scoped to Tamil Nadu.
# Match only known district names (including common official spelling variants)
# so an absent or foreign district can never inherit Tamil Nadu guidance.
_TAMIL_NADU_DISTRICTS = frozenset(
    _normalize(name)
    for name in (
        "Ariyalur",
        "Chengalpattu",
        "Chennai",
        "Coimbatore",
        "Cuddalore",
        "Dharmapuri",
        "Dindigul",
        "Erode",
        "Kallakurichi",
        "Kancheepuram",
        "Kanchipuram",
        "Kanniyakumari",
        "Kanyakumari",
        "Karur",
        "Krishnagiri",
        "Madurai",
        "Mayiladuthurai",
        "Nagapattinam",
        "Namakkal",
        "Nilgiris",
        "The Nilgiris",
        "Perambalur",
        "Pudukkottai",
        "Ramanathapuram",
        "Ranipet",
        "Salem",
        "Sivaganga",
        "Tenkasi",
        "Thanjavur",
        "Theni",
        "Thoothukudi",
        "Tuticorin",
        "Tiruchirappalli",
        "Trichy",
        "Tirunelveli",
        "Tirupathur",
        "Tiruppur",
        "Tiruvallur",
        "Thiruvallur",
        "Tiruvannamalai",
        "Thiruvannamalai",
        "Tiruvarur",
        "Thiruvarur",
        "Vellore",
        "Viluppuram",
        "Villupuram",
        "Virudhunagar",
    )
)


def resolve_rule_region(district: str | None) -> str | None:
    """Return a verified rule-region code, or ``None`` when it is unknown."""
    if district is None or not district.strip():
        return None
    return "IN-TN" if _normalize(district) in _TAMIL_NADU_DISTRICTS else None
