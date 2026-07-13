"""Unit tests for the pure Admin Engine + RBAC mapping (no I/O).

Covers the dashboard overview cards (documented order, honest nulls), the procurement
analytics buckets (village/crop/season/quantity trend using the reused produce kg
normalizer + memory season helper), and the transparent role → permission grants.
"""
from __future__ import annotations

from datetime import date

from app.modules.admin.constants import (
    AdminPermission,
    AdminRole,
    permissions_for,
)
from app.modules.admin.engine import (
    OverviewCard,
    ProcurementFact,
    build_overview,
    procurement_analytics,
)


def test_build_overview_preserves_order_and_nulls():
    counts = {"total_farmers": 10, "total_farms": 25}  # the rest are missing
    cards = build_overview(counts)
    assert cards[0] == OverviewCard(key="total_farmers", value=10)
    assert cards[1] == OverviewCard(key="total_farms", value=25)
    # An untracked metric is surfaced honestly as None, never fabricated.
    assert any(c.value is None for c in cards)
    # Every documented card is present.
    keys = [c.key for c in cards]
    assert "active_users" in keys
    assert "notifications_sent" in keys


def test_procurement_analytics_buckets_and_totals():
    facts = [
        # 2 tonnes = 2000 kg of paddy in Thanjavur, harvest in kharif (July).
        ProcurementFact(
            village="Kabisthalam", crop="paddy", harvest_date=date(2026, 7, 15),
            quantity=2, unit="tonne",
        ),
        # 100 kg of paddy, same village, rabi (December).
        ProcurementFact(
            village="Kabisthalam", crop="paddy", harvest_date=date(2026, 12, 1),
            quantity=100, unit="kg",
        ),
        # 5 quintal = 500 kg of banana, different village, kharif.
        ProcurementFact(
            village="Papanasam", crop="banana", harvest_date=date(2026, 8, 10),
            quantity=5, unit="quintal",
        ),
    ]
    out = procurement_analytics(facts)

    assert out["total_offers"] == 3
    assert out["total_quantity_kg"] == 2600.0

    by_crop = {b["label"]: b for b in out["by_crop"]}
    assert by_crop["paddy"]["count"] == 2
    assert by_crop["paddy"]["quantity_kg"] == 2100.0
    assert by_crop["banana"]["quantity_kg"] == 500.0

    by_village = {b["label"]: b for b in out["by_village"]}
    assert by_village["Kabisthalam"]["count"] == 2

    # Season split uses the shared memory season helper (kharif dominates).
    by_season = {b["label"]: b for b in out["by_season"]}
    assert by_season["kharif"]["count"] == 2

    # Monthly quantity trend is chronologically sorted.
    labels = [p["label"] for p in out["quantity_trend"]]
    assert labels == sorted(labels)


def test_procurement_analytics_handles_unknowns_and_unconvertible_units():
    facts = [
        # A "bag" is not convertible to kg → contributes 0 kg but still counts.
        ProcurementFact(village=None, crop=None, harvest_date=None, quantity=3, unit="bag"),
    ]
    out = procurement_analytics(facts)
    assert out["total_offers"] == 1
    assert out["total_quantity_kg"] == 0.0
    assert out["by_village"][0]["label"] == "unknown"
    assert out["by_crop"][0]["label"] == "unknown"
    # No harvest date → bucketed as "unknown" season, never guessed.
    assert out["by_season"][0]["label"] == "unknown"
    # …and excluded entirely from the dated monthly trend.
    assert out["quantity_trend"] == []


def test_super_admin_has_every_permission():
    perms = set(permissions_for(AdminRole.SUPER_ADMIN.value))
    assert perms == {p.value for p in AdminPermission}


def test_least_privilege_roles():
    procurement = set(permissions_for(AdminRole.PROCUREMENT_MANAGER.value))
    assert AdminPermission.MANAGE_PROCUREMENT.value in procurement
    assert AdminPermission.MANAGE_FARMERS.value not in procurement
    assert AdminPermission.VIEW_AUDIT.value not in procurement

    support = set(permissions_for(AdminRole.CUSTOMER_SUPPORT.value))
    assert AdminPermission.MANAGE_FARMERS.value in support
    assert AdminPermission.MANAGE_PROCUREMENT.value not in support


def test_unknown_role_has_no_permissions():
    assert permissions_for("emperor") == ()
