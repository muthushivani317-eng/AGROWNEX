"""FPO Crop Board: what an FPO's consented farmers grow and have to sell.

One aggregation shared by the Admin Web page (FPO staff / platform admins)
and the partner API-key feed (the FPO's own software).

Data scope (owner decision 2026-09-30): an FPO sees, for farmers with an
ACTIVE consent link to it, their farms (crop, variety, area, village,
sowing date), their Sell My Produce listings (crop/product, quantity, ready
date) and their organic-input production batches. Farmer name and phone are
included because the farmer explicitly approved the link to this FPO.

Nothing here estimates harvests from a crop calendar: harvest windows count
only dated produce listings the farmer entered (same rule as admin crop
intelligence -- no invented inventory). The onboarding "farm items" (what the
farmer grows/rears, harvest months, rough quantity, for sale or not) are the
farmer's own declaration and are shown as such (``farm_items``,
``harvest_calendar``, ``needs``).
"""
from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farm_profile.catalog import CATEGORIES, FARMER_TYPES, ITEMS, NEEDS, item_label
from app.modules.farm_profile.models import FarmerFarmItem
from app.modules.farms.models import Farm, FarmLocation
from app.modules.organic_inputs.constants import BatchStatus
from app.modules.organic_inputs.models import MarketplaceProductType as ProductType
from app.modules.organic_inputs.models import ProductionBatch, SupplierProfile
from app.modules.organic_mvp.models import OrganicPartnerFarmerLink
from app.modules.produce.constants import ProduceAvailabilityType, ProduceStatus
from app.modules.produce.models import ProduceOffer
from app.shared.csv_safety import safe_row

HECTARE_TO_ACRE = 2.47105
HARVEST_WINDOWS = (30, 60, 90)

# Listings that still represent produce the farmer has or will have.
ACTIVE_PRODUCE_STATUSES = (
    ProduceStatus.SUBMITTED.value,
    ProduceStatus.PLANNED.value,
    ProduceStatus.HARVESTED.value,
)
# Batches that are finished/withdrawn from the farmer's hands are excluded.
INACTIVE_BATCH_STATUSES = (
    BatchStatus.DRAFT.value,
    BatchStatus.REJECTED.value,
    BatchStatus.SOLD_OUT.value,
    BatchStatus.EXPIRED.value,
    BatchStatus.RECALLED.value,
    BatchStatus.RECEIVED.value,
    BatchStatus.QUARANTINED.value,
    BatchStatus.RELEASED_FOR_SALE.value,
)

FARMER_CSV_COLUMNS = [
    "farmer_ref",
    "name",
    "phone",
    "village",
    "district",
    "land_acres",
    "farmer_type",
    "crops",
    "farm_items",
    "products",
    "needs",
    "wants_support",
]
# Farm-item categories that are crops on the land (merged into the crop table).
CROP_CATEGORIES = ("crops", "vegetables", "fruits", "plantation")
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _acres(hectares: float | None) -> float:
    return round((hectares or 0.0) * HECTARE_TO_ACRE, 2)


def _key(name: str | None) -> str:
    return (name or "").strip().lower()


def _label(name: str | None) -> str:
    text = (name or "").strip()
    return text[:1].upper() + text[1:] if text else "Unknown"


def _crop_key(name: str | None) -> str:
    """Catalog code when the free-text crop matches one, else the lower-case name."""
    key = _key(name)
    code = key.replace(" ", "_")
    return code if code in ITEMS else key


def _crop_label(name: str | None) -> str:
    key = _crop_key(name)
    return ITEMS[key]["en"] if key in ITEMS else _label(name)


def _farm_item_key(item: FarmerFarmItem) -> str:
    return item.item_code if item.item_code in ITEMS else _key(item.custom_name)


@dataclass
class _Item:
    """One thing a farmer has: a produce listing or an organic-input batch."""

    name: str
    source: str  # "produce" | "organic_input"
    category: str | None
    quantity: float
    unit: str
    ready_date: date | None
    available_now: bool
    farmer_id: uuid.UUID


@dataclass
class _Data:
    farmers: dict[uuid.UUID, User]
    profiles: dict[uuid.UUID, FarmerProfile]
    farms: list[Farm]
    locations: dict[uuid.UUID, FarmLocation]
    items: list[_Item] = field(default_factory=list)
    farm_items: list[FarmerFarmItem] = field(default_factory=list)


async def _load(session: AsyncSession, organization_id: uuid.UUID | None) -> _Data:
    """``organization_id=None`` = every Agrownex farmer (platform admins only)."""
    if organization_id is None:
        from app.modules.admin.models import AdminUser

        stmt = (
            select(User)
            .join(FarmerProfile, FarmerProfile.user_id == User.id)
            .where(
                User.deleted_at.is_(None),
                FarmerProfile.is_deleted.is_(False),
                User.id.not_in(select(AdminUser.user_id).where(AdminUser.deleted_at.is_(None))),
            )
        )
    else:
        stmt = (
            select(User)
            .join(OrganicPartnerFarmerLink, OrganicPartnerFarmerLink.farmer_user_id == User.id)
            .where(
                OrganicPartnerFarmerLink.organization_id == organization_id,
                OrganicPartnerFarmerLink.status == "active",
                User.deleted_at.is_(None),
            )
        )
    farmers = {user.id: user for user in (await session.scalars(stmt)).unique()}
    ids = list(farmers)
    if not ids:
        return _Data(farmers={}, profiles={}, farms=[], locations={})

    profiles = {
        p.user_id: p
        for p in (
            await session.scalars(
                select(FarmerProfile).where(FarmerProfile.user_id.in_(ids), FarmerProfile.is_deleted.is_(False))
            )
        ).all()
    }
    farm_rows = (
        await session.execute(
            select(Farm, FarmLocation)
            .outerjoin(FarmLocation, FarmLocation.farm_id == Farm.id)
            .where(Farm.user_id.in_(ids), Farm.is_deleted.is_(False))
        )
    ).all()
    farms = [row[0] for row in farm_rows]
    locations = {row[0].id: row[1] for row in farm_rows if row[1] is not None}
    data = _Data(farmers=farmers, profiles=profiles, farms=farms, locations=locations)
    data.farm_items = list(
        (await session.scalars(select(FarmerFarmItem).where(FarmerFarmItem.user_id.in_(ids)))).all()
    )

    offers = (
        await session.scalars(
            select(ProduceOffer).where(
                ProduceOffer.user_id.in_(ids),
                ProduceOffer.is_deleted.is_(False),
                ProduceOffer.status.in_(ACTIVE_PRODUCE_STATUSES),
            )
        )
    ).all()
    for offer in offers:
        quantity = offer.available_quantity if offer.available_quantity is not None else offer.quantity
        data.items.append(
            _Item(
                name=_label(offer.crop_name),
                source="produce",
                category=offer.product_category,
                quantity=float(quantity or 0),
                unit=offer.unit,
                ready_date=offer.expected_harvest_date or offer.available_from,
                available_now=offer.availability_type == ProduceAvailabilityType.AVAILABLE_NOW.value
                or offer.status == ProduceStatus.HARVESTED.value,
                farmer_id=offer.user_id,
            )
        )

    batch_rows = (
        await session.execute(
            select(ProductionBatch, ProductType, SupplierProfile)
            .join(SupplierProfile, SupplierProfile.id == ProductionBatch.supplier_id)
            .join(ProductType, ProductType.id == ProductionBatch.product_type_id)
            .where(
                SupplierProfile.user_id.in_(ids),
                ProductionBatch.is_deleted.is_(False),
                ProductionBatch.status.not_in(INACTIVE_BATCH_STATUSES),
            )
        )
    ).all()
    for batch, product_type, supplier in batch_rows:
        quantity = batch.available_quantity_offered or batch.batch_quantity
        data.items.append(
            _Item(
                name=_label(product_type.name),
                source="organic_input",
                category="organic_input",
                quantity=float(Decimal(quantity)),
                unit=batch.unit,
                ready_date=batch.production_completion_date,
                available_now=batch.production_completion_date is None
                or batch.production_completion_date <= date.today(),
                farmer_id=supplier.user_id,
            )
        )
    return data


def _village(data: _Data, farm: Farm) -> str:
    location = data.locations.get(farm.id)
    if location and location.village:
        return location.village
    profile = data.profiles.get(farm.user_id)
    return (profile.village if profile and profile.village else None) or "Unknown"


async def build_board(session: AsyncSession, organization_id: uuid.UUID | None, *, today: date | None = None) -> dict:
    today = today or date.today()
    data = await _load(session, organization_id)

    crops: dict[str, dict] = {}

    def crop_entry(key: str, label: str) -> dict:
        return crops.setdefault(
            key,
            {"crop": label, "farmers": set(), "farm_count": 0, "area_acres": 0.0, "villages": {}, "varieties": set()},
        )

    for farm in data.farms:
        if not farm.crop:
            continue
        entry = crop_entry(_crop_key(farm.crop), _crop_label(farm.crop))
        entry["farmers"].add(farm.user_id)
        entry["farm_count"] += 1
        entry["area_acres"] += _acres(farm.area_hectares)
        if farm.crop_variety:
            entry["varieties"].add(farm.crop_variety)
        village = entry["villages"].setdefault(_village(data, farm), {"farmers": set(), "area_acres": 0.0})
        village["farmers"].add(farm.user_id)
        village["area_acres"] += _acres(farm.area_hectares)

    # Onboarding farm items add farmers who have not registered a farm for
    # that crop (their declared area counts only then -- no double counting).
    for item in data.farm_items:
        if item.category not in CROP_CATEGORIES:
            continue
        entry = crop_entry(_farm_item_key(item), item_label(item.item_code, item.custom_name))
        if item.user_id in entry["farmers"]:
            continue
        entry["farmers"].add(item.user_id)
        entry["area_acres"] += item.area_acres or 0.0
        profile = data.profiles.get(item.user_id)
        village = entry["villages"].setdefault(
            (profile.village if profile and profile.village else None) or "Unknown", {"farmers": set(), "area_acres": 0.0}
        )
        village["farmers"].add(item.user_id)
        village["area_acres"] += item.area_acres or 0.0

    produce_by_crop: dict[str, list[_Item]] = {}
    for item in data.items:
        if item.source == "produce":
            produce_by_crop.setdefault(_crop_key(item.name), []).append(item)

    crop_rows = []
    for key, entry in crops.items():
        listings = produce_by_crop.get(key, [])
        windows = {}
        for days in HARVEST_WINDOWS:
            end = today + timedelta(days=days)
            in_window = [i for i in listings if i.ready_date is not None and today <= i.ready_date <= end]
            windows[f"within_{days}_days"] = {
                "farmer_count": len({i.farmer_id for i in in_window}),
                "quantity": _sum_by_unit(in_window),
            }
        crop_rows.append(
            {
                "crop": entry["crop"],
                "farmer_count": len(entry["farmers"]),
                "farm_count": entry["farm_count"],
                "area_acres": round(entry["area_acres"], 2),
                "varieties": sorted(entry["varieties"]),
                "villages": sorted(
                    (
                        {"village": name, "farmer_count": len(v["farmers"]), "area_acres": round(v["area_acres"], 2)}
                        for name, v in entry["villages"].items()
                    ),
                    key=lambda v: -v["farmer_count"],
                ),
                "expected_harvest": windows,
            }
        )
    crop_rows.sort(key=lambda r: (-r["farmer_count"], r["crop"]))

    products: dict[tuple[str, str, str], dict] = {}
    for item in data.items:
        entry = products.setdefault(
            (item.source, _key(item.name), item.unit),
            {
                "name": item.name,
                "source": item.source,
                "category": item.category,
                "unit": item.unit,
                "farmers": set(),
                "total_quantity": 0.0,
                "available_now_quantity": 0.0,
                "upcoming_quantity": 0.0,
                "earliest_ready_date": None,
            },
        )
        entry["farmers"].add(item.farmer_id)
        entry["total_quantity"] += item.quantity
        if item.available_now:
            entry["available_now_quantity"] += item.quantity
        else:
            entry["upcoming_quantity"] += item.quantity
            if item.ready_date and (entry["earliest_ready_date"] is None or item.ready_date < entry["earliest_ready_date"]):
                entry["earliest_ready_date"] = item.ready_date
    product_rows = sorted(
        (
            {
                **{k: v for k, v in entry.items() if k != "farmers"},
                "farmer_count": len(entry["farmers"]),
                "total_quantity": round(entry["total_quantity"], 3),
                "available_now_quantity": round(entry["available_now_quantity"], 3),
                "upcoming_quantity": round(entry["upcoming_quantity"], 3),
            }
            for entry in products.values()
        ),
        key=lambda r: (-r["farmer_count"], r["name"]),
    )

    farmers_with_farm = {farm.user_id for farm in data.farms}
    farm_item_rows, calendar = _farm_item_summary(data)
    return {
        "generated_on": today,
        "summary": {
            "farmer_count": len(data.farmers),
            "farmers_without_farm": len(set(data.farmers) - farmers_with_farm),
            "farm_count": len(data.farms),
            "total_area_acres": round(sum(_acres(f.area_hectares) for f in data.farms), 2),
            "crop_count": len(crop_rows),
            "product_count": len(product_rows),
            "total_land_holding_acres": round(
                sum(p.land_holding_acres or 0.0 for p in data.profiles.values() if p.user_id in data.farmers), 2
            ),
            "farmers_with_farm_items": len({i.user_id for i in data.farm_items}),
            "wants_fpo_support": sum(1 for p in data.profiles.values() if p.user_id in data.farmers and p.wants_fpo_support),
            "wants_kvk_support": sum(1 for p in data.profiles.values() if p.user_id in data.farmers and p.wants_kvk_support),
            "farmer_types": _count_codes(
                [p.farmer_type for p in data.profiles.values() if p.user_id in data.farmers and p.farmer_type], FARMER_TYPES
            ),
        },
        "crops": crop_rows,
        "products": product_rows,
        "farm_items": farm_item_rows,
        "harvest_calendar": calendar,
        "needs": _count_codes(
            [code for p in data.profiles.values() if p.user_id in data.farmers for code in (p.needs or [])], NEEDS
        ),
    }


def _count_codes(codes: list[str], names: dict[str, dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for code in codes:
        counts[code] = counts.get(code, 0) + 1
    return sorted(
        (
            {"code": code, "name": names.get(code, {}).get("en", code), "name_ta": names.get(code, {}).get("ta"), "farmer_count": n}
            for code, n in counts.items()
        ),
        key=lambda r: (-r["farmer_count"], r["name"]),
    )


def _farm_item_summary(data: _Data) -> tuple[list[dict], list[dict]]:
    """Per item: farmers, declared area/quantity, harvest months, for-sale share."""
    grouped: dict[str, dict] = {}
    for item in data.farm_items:
        key = _farm_item_key(item)
        entry = grouped.setdefault(
            key,
            {
                "code": item.item_code,
                "name": item_label(item.item_code, item.custom_name),
                "name_ta": ITEMS.get(item.item_code, {}).get("ta"),
                "category": item.category,
                "farmers": set(),
                "for_sale_farmers": set(),
                "area_acres": 0.0,
                "quantity": {},
                "for_sale_quantity": {},
                "harvest_months": {},
            },
        )
        entry["farmers"].add(item.user_id)
        entry["area_acres"] += item.area_acres or 0.0
        if item.approx_quantity and item.unit:
            entry["quantity"][item.unit] = round(entry["quantity"].get(item.unit, 0.0) + item.approx_quantity, 3)
            if item.available_for_sale:
                entry["for_sale_quantity"][item.unit] = round(
                    entry["for_sale_quantity"].get(item.unit, 0.0) + item.approx_quantity, 3
                )
        if item.available_for_sale:
            entry["for_sale_farmers"].add(item.user_id)
        for month in item.harvest_months or []:
            entry["harvest_months"].setdefault(month, set()).add(item.user_id)

    rows = []
    calendar: dict[int, list[dict]] = {m: [] for m in range(1, 13)}
    for entry in grouped.values():
        rows.append(
            {
                "code": entry["code"],
                "name": entry["name"],
                "name_ta": entry["name_ta"],
                "category": entry["category"],
                "category_name": CATEGORIES.get(entry["category"], {}).get("en", entry["category"]),
                "farmer_count": len(entry["farmers"]),
                "for_sale_farmer_count": len(entry["for_sale_farmers"]),
                "area_acres": round(entry["area_acres"], 2),
                "approx_quantity": entry["quantity"],
                "for_sale_quantity": entry["for_sale_quantity"],
                "harvest_months": sorted(entry["harvest_months"]),
            }
        )
        for month, farmers in entry["harvest_months"].items():
            calendar[month].append({"code": entry["code"], "name": entry["name"], "farmer_count": len(farmers)})
    rows.sort(key=lambda r: (-r["farmer_count"], r["name"]))
    calendar_rows = [
        {"month": m, "month_name": MONTH_NAMES[m - 1], "items": sorted(calendar[m], key=lambda i: (-i["farmer_count"], i["name"]))}
        for m in range(1, 13)
    ]
    return rows, calendar_rows


def _sum_by_unit(items: list[_Item]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        totals[item.unit] = round(totals.get(item.unit, 0.0) + item.quantity, 3)
    return totals


async def farmer_rows(
    session: AsyncSession,
    organization_id: uuid.UUID | None,
    *,
    crop: str | None = None,
    product: str | None = None,
    need: str | None = None,
    harvest_month: int | None = None,
    support: str | None = None,
) -> list[dict]:
    """One row per consented farmer: who they are, what they grow, what they have."""
    data = await _load(session, organization_id)
    farms_by_farmer: dict[uuid.UUID, list[Farm]] = {}
    for farm in data.farms:
        farms_by_farmer.setdefault(farm.user_id, []).append(farm)
    items_by_farmer: dict[uuid.UUID, list[_Item]] = {}
    for item in data.items:
        items_by_farmer.setdefault(item.farmer_id, []).append(item)
    farm_items_by_farmer: dict[uuid.UUID, list[FarmerFarmItem]] = {}
    for farm_item in data.farm_items:
        farm_items_by_farmer.setdefault(farm_item.user_id, []).append(farm_item)

    crop_key, product_key = (_crop_key(crop) if crop else ""), _key(product)
    rows = []
    for farmer_id, user in data.farmers.items():
        farms = farms_by_farmer.get(farmer_id, [])
        items = items_by_farmer.get(farmer_id, [])
        declared = farm_items_by_farmer.get(farmer_id, [])
        profile = data.profiles.get(farmer_id)
        if crop_key and not (
            any(_crop_key(f.crop) == crop_key for f in farms)
            or any(i.source == "produce" and _crop_key(i.name) == crop_key for i in items)
            or any(_farm_item_key(d) == crop_key for d in declared)
        ):
            continue
        if product_key and not (
            any(_key(i.name) == product_key for i in items)
            or any(_key(item_label(d.item_code, d.custom_name)) == product_key or d.item_code == product_key for d in declared)
        ):
            continue
        if need and not (profile and need in (profile.needs or [])):
            continue
        if harvest_month and not any(harvest_month in (d.harvest_months or []) for d in declared):
            continue
        if support == "fpo" and not (profile and profile.wants_fpo_support):
            continue
        if support == "kvk" and not (profile and profile.wants_kvk_support):
            continue
        location = next((data.locations.get(f.id) for f in farms if data.locations.get(f.id)), None)
        rows.append(
            {
                "farmer_ref": user.farmer_ref,
                "name": profile.full_name if profile else None,
                "phone": user.phone_number,
                "village": (location.village if location and location.village else None) or (profile.village if profile else None),
                "district": (location.district if location and location.district else None) or (profile.district if profile else None),
                "land_holding_acres": profile.land_holding_acres if profile else None,
                "farmer_type": profile.farmer_type if profile else None,
                "needs": list(profile.needs or []) if profile else [],
                "wants_fpo_support": bool(profile and profile.wants_fpo_support),
                "wants_kvk_support": bool(profile and profile.wants_kvk_support),
                "farm_items": [
                    {
                        "code": d.item_code,
                        "name": item_label(d.item_code, d.custom_name),
                        "category": d.category,
                        "harvest_months": list(d.harvest_months or []),
                        "approx_quantity": d.approx_quantity,
                        "unit": d.unit,
                        "area_acres": d.area_acres,
                        "available_for_sale": d.available_for_sale,
                    }
                    for d in sorted(declared, key=lambda d: (d.category, d.item_code))
                ],
                "crops": [
                    {
                        "crop": _crop_label(f.crop),
                        "variety": f.crop_variety,
                        "area_acres": _acres(f.area_hectares),
                        "sowing_date": f.sowing_date,
                    }
                    for f in farms
                    if f.crop
                ],
                "products": [
                    {
                        "name": i.name,
                        "source": i.source,
                        "quantity": round(i.quantity, 3),
                        "unit": i.unit,
                        "ready_date": i.ready_date,
                        "available_now": i.available_now,
                    }
                    for i in items
                ],
            }
        )
    rows.sort(key=lambda r: ((r["village"] or "~"), r["farmer_ref"]))
    return rows


def rows_to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(FARMER_CSV_COLUMNS)
    for row in rows:
        crops = "; ".join(f"{c['crop']} ({c['area_acres']} ac)" for c in row["crops"])
        products = "; ".join(
            f"{p['name']} {p['quantity']:g} {p['unit']}" + ("" if p["available_now"] or not p["ready_date"] else f" ready {p['ready_date']}")
            for p in row["products"]
        )
        farm_items = "; ".join(
            f"{d['name']}"
            + (f" {d['approx_quantity']:g} {d['unit']}" if d["approx_quantity"] and d["unit"] else "")
            + (f" harvest {'/'.join(MONTH_NAMES[m - 1] for m in d['harvest_months'])}" if d["harvest_months"] else "")
            + (" [for sale]" if d["available_for_sale"] else "")
            for d in row["farm_items"]
        )
        needs = "; ".join(NEEDS.get(code, {}).get("en", code) for code in row["needs"])
        farmer_type = FARMER_TYPES.get(row["farmer_type"] or "", {}).get("en", row["farmer_type"] or "")
        land = "" if row["land_holding_acres"] is None else f"{row['land_holding_acres']:g}"
        writer.writerow(
            safe_row([
                row["farmer_ref"],
                row["name"] or "",
                row["phone"] or "",
                row["village"] or "",
                row["district"] or "",
                land,
                farmer_type,
                crops,
                farm_items,
                products,
                needs,
                "/".join(k for k, v in (("FPO", row["wants_fpo_support"]), ("KVK", row["wants_kvk_support"])) if v),
            ])
        )
    return buffer.getvalue()
