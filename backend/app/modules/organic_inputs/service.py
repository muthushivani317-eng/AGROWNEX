"""Pure helpers shared by the Organic Inputs Marketplace router.

No session/IO here on purpose -- these are unit-testable in isolation (see
backend/tests/test_organic_inputs_marketplace.py) without a database.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import ValidationError


def generate_batch_code() -> str:
    """A short, unique, farmer-facing batch code (e.g. "PB-A1B2C3D4E5")."""
    return f"PB-{uuid.uuid4().hex[:10].upper()}"


def generate_sample_code() -> str:
    """A short, unique lab-sample code (e.g. "SMP-A1B2C3D4E5")."""
    return f"SMP-{uuid.uuid4().hex[:10].upper()}"


def assert_transition_allowed(current: str, target: str, allowed: dict[str, set[str]]) -> None:
    """Raise unless ``current -> target`` is an edge in ``allowed``.

    ``allowed`` keys/values are expected to be the plain string ``.value`` of
    a StrEnum (SQLAlchemy stores the string, not the enum instance) --
    callers pass e.g. ``{s.value: {t.value for t in targets} ...}``.
    """
    if target not in allowed.get(current, set()):
        raise ValidationError(
            f"Cannot move from '{current}' to '{target}'.",
            error_code="INVALID_STATE_TRANSITION",
        )
