from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class SupportTicket(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "support_tickets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True, nullable=False)
    app_version: Mapped[str | None] = mapped_column(String(40))
    device_context: Mapped[str | None] = mapped_column(String(160))

    messages: Mapped[list[SupportTicketMessage]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportTicketMessage.created_at",
    )


class SupportTicketMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "support_ticket_messages"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_type: Mapped[str] = mapped_column(String(16), nullable=False)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    author_admin_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("admin_users.id"))
    message: Mapped[str] = mapped_column(Text, nullable=False)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")
