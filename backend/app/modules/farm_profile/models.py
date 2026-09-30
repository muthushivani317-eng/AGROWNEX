"""What a farmer grows / rears / produces, declared at onboarding (Crops step)."""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class FarmerFarmItem(UUIDMixin, TimestampMixin, Base):
    """One catalog item a farmer has, with its own production details.

    The farmer's list is replaced as a whole (PUT /farmers/me/farm-items), so
    rows are hard-replaced rather than soft-deleted.
    """

    __tablename__ = "farmer_farm_items"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    item_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    custom_name: Mapped[str | None] = mapped_column(String(80))
    harvest_months: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approx_quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(16))
    area_acres: Mapped[float | None] = mapped_column(Float)
    available_for_sale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
