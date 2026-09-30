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
intelligence -- no invented inventory).
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
from app.modules.farms.models import Farm, FarmLocation
from app.modules.organic_inputs.constants import BatchStatus
from app.modules.organic_inputs.models import MarketplaceProductType as ProductType
from app.modules.organic_inputs.models import ProductionBatch, SupplierProfile
from app.modules.organic_mvp.models import OrganicPartnerFarmerLink
from app.modules.produce.constants import ProduceAvailabilityType, ProduceStatus
from app.modules.produce.models import ProduceOffer

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

FARMER_CSV_COLUMNS = ["farmer_ref", "name", "phone", "village", "district", "crops", "products"]


def _acres(hectares: float | None) -> float:
    return round((hectares or 0.0) * HECTARE_TO_ACRE, 2)


def _key(name: str | None) -> str:
    return (name or "").strip().lower()


def _label(name: str | None) -> str:
    text = (name or "").strip()
    return text[:1].upper() + text[1:] if text else "Unknown"


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


async def _load(session: AsyncSession, organization_id: uuid.UUID) -> _Data:
    farmers = {
        user.id: user
        for user in (
            await session.scalars(
                select(User)
                .join(OrganicPartnerFarmerLink, OrganicPartnerFarmerLink.farmer_user_id == User.id)
                .where(
                    OrganicPartnerFarmerLink.organization_id == organization_id,
                    OrganicPartnerFarmerLink.status == "active",
                    User.deleted_at.is_(None),
                )
            )
        ).unique()
    }
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


async def build_board(session: AsyncSession, organization_id: uuid.UUID, *, today: date | None = None) -> dict:
    today = today or date.today()
    data = await _load(session, organization_id)

    crops: dict[str, dict] = {}
    for farm in data.farms:
        if not farm.crop:
            continue
        entry = crops.setdefault(
            _key(farm.crop),
            {"crop": _label(farm.crop), "farmers": set(), "farm_count": 0, "area_acres": 0.0, "villages": {}, "varieties": set()},
        )
        entry["farmers"].add(farm.user_id)
        entry["farm_count"] += 1
        entry["area_acres"] += _acres(farm.area_hectares)
        if farm.crop_variety:
            entry["varieties"].add(farm.crop_variety)
        village = entry["villages"].setdefault(_village(data, farm), {"farmers": set(), "area_acres": 0.0})
        village["farmers"].add(farm.user_id)
        village["area_acres"] += _acres(farm.area_hectares)

    produce_by_crop: dict[str, list[_Item]] = {}
    for item in data.items:
        if item.source == "produce":
            produce_by_crop.setdefault(_key(item.name), []).append(item)

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
    return {
        "generated_on": today,
        "summary": {
            "farmer_count": len(data.farmers),
            "farmers_without_farm": len(set(data.farmers) - farmers_with_farm),
            "farm_count": len(data.farms),
            "total_area_acres": round(sum(_acres(f.area_hectares) for f in data.farms), 2),
            "crop_count": len(crop_rows),
            "product_count": len(product_rows),
        },
        "crops": crop_rows,
        "products": product_rows,
    }


def _sum_by_unit(items: list[_Item]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        totals[item.unit] = round(totals.get(item.unit, 0.0) + item.quantity, 3)
    return totals


async def farmer_rows(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    crop: str | None = None,
    product: str | None = None,
) -> list[dict]:
    """One row per consented farmer: who they are, what they grow, what they have."""
    data = await _load(session, organization_id)
    farms_by_farmer: dict[uuid.UUID, list[Farm]] = {}
    for farm in data.farms:
        farms_by_farmer.setdefault(farm.user_id, []).append(farm)
    items_by_farmer: dict[uuid.UUID, list[_Item]] = {}
    for item in data.items:
        items_by_farmer.setdefault(item.farmer_id, []).append(item)

    crop_key, product_key = _key(crop), _key(product)
    rows = []
    for farmer_id, user in data.farmers.items():
        farms = farms_by_farmer.get(farmer_id, [])
        items = items_by_farmer.get(farmer_id, [])
        if crop_key and not (
            any(_key(f.crop) == crop_key for f in farms)
            or any(i.source == "produce" and _key(i.name) == crop_key for i in items)
        ):
            continue
        if product_key and not any(_key(i.name) == product_key for i in items):
            continue
        profile = data.profiles.get(farmer_id)
        location = next((data.locations.get(f.id) for f in farms if data.locations.get(f.id)), None)
        rows.append(
            {
                "farmer_ref": user.farmer_ref,
                "name": profile.full_name if profile else None,
                "phone": user.phone_number,
                "village": (location.village if location and location.village else None) or (profile.village if profile else None),
                "district": (location.district if location and location.district else None) or (profile.district if profile else None),
                "crops": [
                    {
                        "crop": _label(f.crop),
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
        writer.writerow([row["farmer_ref"], row["name"] or "", row["phone"] or "", row["village"] or "", row["district"] or "", crops, products])
    return buffer.getvalue()
