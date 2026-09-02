import pytest
from app.modules.admin.constants import AdminPermission, AdminRole, permissions_for
from app.modules.support.schemas import TicketAdminUpdateIn, TicketCreateIn
from pydantic import ValidationError


def test_customer_support_has_explicit_ticket_permission() -> None:
    assert AdminPermission.MANAGE_SUPPORT.value in permissions_for(AdminRole.CUSTOMER_SUPPORT.value)
    assert AdminPermission.MANAGE_SUPPORT.value in permissions_for(AdminRole.OWNER.value)


def test_ticket_input_is_bounded_and_uses_safe_enums() -> None:
    ticket = TicketCreateIn(
        category="market",
        subject="Listing is not visible",
        description="I submitted my produce listing but cannot see its current status.",
    )
    assert ticket.priority == "normal"
    with pytest.raises(ValidationError):
        TicketCreateIn(category="security", subject="bad", description="too short")


def test_admin_updates_are_status_and_priority_scoped() -> None:
    update = TicketAdminUpdateIn(status="waiting_for_farmer", response="Please retry once.")
    assert update.status == "waiting_for_farmer"
    with pytest.raises(ValidationError):
        TicketAdminUpdateIn(status="deleted")
