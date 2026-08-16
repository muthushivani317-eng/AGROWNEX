from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class EquipmentListing(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "equipment_listings"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="available", index=True)


class EquipmentRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "equipment_requests"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("equipment_listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    decision_note: Mapped[str | None] = mapped_column(String(500))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
