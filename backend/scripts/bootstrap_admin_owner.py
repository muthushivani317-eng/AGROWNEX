"""One-time, server-side bootstrap for the immutable first Admin owner.

Run only from the deployment shell after the target user has authenticated once.
The command refuses to create a second owner or replace an existing Admin role.
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.database import SessionLocal
from app.core.security import ensure_firebase_app
from app.modules.admin.constants import AdminRole, AdminUserStatus
from app.modules.admin.models import AdminUser, AuditLog
from app.modules.admin.seed import seed_admin_reference
from app.modules.auth.models import User
from sqlalchemy import select


def verified_firebase_identity(firebase_uid: str) -> tuple[str, bool]:
    """Resolve a live Firebase account without trusting command-line profile data."""
    from firebase_admin import auth as firebase_auth

    firebase_app = ensure_firebase_app()
    if firebase_app is None:
        raise RuntimeError("Firebase Admin is unavailable; owner bootstrap is closed.")
    firebase_user = firebase_auth.get_user(firebase_uid, app=firebase_app)
    if firebase_user.disabled:
        raise RuntimeError("The target Firebase account is disabled.")
    email = (firebase_user.email or "").strip().lower()
    if not email:
        raise RuntimeError("The first owner must have a Firebase email identity.")
    return email, bool(firebase_user.email_verified)


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
        created_user = False
        if user is None:
            email, email_verified = verified_firebase_identity(firebase_uid)
            user = User(
                firebase_uid=firebase_uid,
                email=email,
                is_email_verified=email_verified,
                status="active",
            )
            session.add(user)
            await session.flush()
            created_user = True
        elif user.is_deleted or user.status != "active":
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
                    meta={"controlled_bootstrap": True, "identity_created": created_user},
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
                meta={"controlled_bootstrap": True, "identity_created": created_user},
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
