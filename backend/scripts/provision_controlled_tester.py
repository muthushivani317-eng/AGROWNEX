"""Dry-run-first server-side controlled tester provisioning utility."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.auth.constants import RoleName
from app.modules.auth.rbac_models import Role, UserRole
from app.modules.auth.repository import UserRepository
from sqlalchemy import delete, select

ALLOWED_ASSIGNMENTS = {
    RoleName.FARMER.value,
    RoleName.INTERNAL_TESTER.value,
    RoleName.PILOT_TESTER.value,
    RoleName.KVK_REVIEWER.value,
}
CONTROLLED_ROLES = {
    RoleName.INTERNAL_TESTER.value,
    RoleName.PILOT_TESTER.value,
    RoleName.KVK_REVIEWER.value,
}


def validate_request(firebase_uid: str, role: str) -> None:
    if not firebase_uid.strip() or "*" in firebase_uid:
        raise ValueError("EXPLICIT_USER_IDENTIFIER_REQUIRED")
    if role not in ALLOWED_ASSIGNMENTS:
        raise ValueError("INVALID_ROLE")


async def provision(
    firebase_uid: str,
    role_name: str,
    *,
    apply: bool,
) -> dict:
    validate_request(firebase_uid, role_name)
    async with SessionLocal() as session:
        user = await UserRepository(session).get_by_firebase_uid(firebase_uid)
        if user is None:
            raise ValueError("UNKNOWN_USER")
        roles = {
            row.role_name: row
            for row in (
                await session.execute(
                    select(Role).where(
                        Role.role_name.in_(ALLOWED_ASSIGNMENTS)
                    )
                )
            )
            .scalars()
            .all()
        }
        if role_name not in roles:
            raise ValueError("ROLE_NOT_SEEDED")
        if apply:
            controlled_ids = [
                roles[name].id for name in CONTROLLED_ROLES if name in roles
            ]
            if controlled_ids:
                await session.execute(
                    delete(UserRole).where(
                        UserRole.user_id == user.id,
                        UserRole.role_id.in_(controlled_ids),
                    )
                )
            if role_name in CONTROLLED_ROLES:
                session.add(
                    UserRole(user_id=user.id, role_id=roles[role_name].id)
                )
            await session.commit()
        return {
            "document_type": "controlled_tester_role_change_receipt",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "subject_hash": hashlib.sha256(str(user.id).encode()).hexdigest()[:16],
            "requested_role": role_name,
            "operation": "REVOKE_TO_FARMER"
            if role_name == RoleName.FARMER.value
            else "ASSIGN_CONTROLLED_ROLE",
            "applied": apply,
            "dry_run": not apply,
            "secrets_recorded": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--firebase-uid", required=True)
    parser.add_argument("--role", required=True, choices=sorted(ALLOWED_ASSIGNMENTS))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = asyncio.run(
        provision(args.firebase_uid, args.role, apply=args.apply)
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
