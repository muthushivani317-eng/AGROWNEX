"""One-time, server-side bootstrap for the immutable first Admin owner.

Run only from the deployment shell after the target user has authenticated once.
The command refuses to create a second owner or replace an existing Admin role.
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.database import SessionLocal
from app.modules.admin.constants import AdminRole, AdminUserStatus
from app.modules.admin.models import AdminUser, AuditLog
from app.modules.admin.seed import seed_admin_reference
from app.modules.auth.models import User
from sqlalchemy import select


async def bootstrap(firebase_uid: str) -> None:
    async with SessionLocal() as session:
        existing_owner = await session.scalar(
            select(AdminUser.id).where(
                AdminUser.role == AdminRole.OWNER.value,
                AdminUser.is_deleted.is_(False),
            )
        )
        if existing_owner:
            raise RuntimeError("An owner already exists; bootstrap is permanently closed.")
        user = await session.scalar(select(User).where(User.firebase_uid == firebase_uid))
        if user is None or user.is_deleted:
            raise RuntimeError("The target must be an existing active AgrowAI user.")
        existing_admin = await session.scalar(
            select(AdminUser).where(AdminUser.user_id == user.id)
        )
        if existing_admin:
            if (
                existing_admin.role != AdminRole.SUPER_ADMIN.value
                or existing_admin.status != AdminUserStatus.ACTIVE.value
            ):
                raise RuntimeError("Only an active bootstrap Super Admin can become owner.")
            existing_admin.role = AdminRole.OWNER.value
            await seed_admin_reference(session)
            session.add(
                AuditLog(
                    admin_id=existing_admin.id,
                    role=AdminRole.OWNER.value,
                    action="owner_bootstrapped",
                    target="admin",
                    target_id=str(existing_admin.id),
                    meta={"controlled_bootstrap": True},
                )
            )
            await session.commit()
            print("Existing Super Admin promoted to owner. Verify MFA immediately.")
            return
        await seed_admin_reference(session)
        admin = AdminUser(
                user_id=user.id,
                role=AdminRole.OWNER.value,
                full_name=None,
                email=user.email,
                status=AdminUserStatus.ACTIVE.value,
            )
        session.add(admin)
        await session.flush()
        session.add(
            AuditLog(
                admin_id=admin.id,
                role=admin.role,
                action="owner_bootstrapped",
                target="admin",
                target_id=str(admin.id),
                meta={"controlled_bootstrap": True},
            )
        )
        await session.commit()
        print("Owner created. Disable access to this deployment shell and verify MFA.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--firebase-uid", required=True)
    args = parser.parse_args()
    asyncio.run(bootstrap(args.firebase_uid))


if __name__ == "__main__":
    main()
