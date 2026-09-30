"""Farmer account deletion kept in step with Firebase Authentication.

Two directions:
- Admin deletes a farmer -> the Firebase account is deleted first (so the
  person can no longer sign in), then the Agrownex account is closed.
- Someone deletes the account in the Firebase console -> the worker's
  reconciliation job (and the admin "Sync with Firebase" button) finds
  Agrownex users whose Firebase account no longer exists and closes them.

"Closed" matches the farmer's own in-app account closure (auth.service
.close_account): the user, profile and farms are soft-deleted, sessions and
refresh tokens revoked, FPO consent links revoked. Rows are kept (soft
delete) so audit, ledger and procurement history stay intact.

Admin users are never touched here -- an Owner cannot delete themselves or
another admin from the farmer directory.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.security import ensure_firebase_app
from app.modules.admin.models import AdminUser, AuditLog
from app.modules.auth.constants import UserStatus
from app.modules.auth.models import RefreshToken, User, UserSession
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farms.models import Farm
from app.modules.organic_mvp.models import OrganicPartnerFarmerLink

logger = get_logger("admin.farmer_deletion")

# Reconciliation safety: never auto-close more than this share of the users
# checked in one run (a Firebase outage or wrong project must not wipe users).
MAX_SYNC_DELETE_SHARE = 0.5
MIN_USERS_FOR_SHARE_GUARD = 5
FIREBASE_BATCH = 100


class FirebaseUnavailableError(AppError):
    status_code = 503
    error_code = "firebase_unavailable"
    message = "Firebase is not configured on the server."


@dataclass
class SyncResult:
    checked: int
    missing_in_firebase: int
    closed: int
    skipped_admins: int
    aborted: bool = False
    # Farmer refs (non-admin) whose Firebase account is gone -- shown to the
    # Owner so an aborted run can be confirmed knowingly.
    missing_refs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _firebase_auth():
    app = ensure_firebase_app()
    if app is None:
        raise FirebaseUnavailableError()
    from firebase_admin import auth as firebase_auth

    return app, firebase_auth


def delete_firebase_account(firebase_uid: str) -> bool:
    """Delete the Firebase user. Returns False if it was already gone."""
    app, firebase_auth = _firebase_auth()
    try:
        firebase_auth.delete_user(firebase_uid, app=app)
        return True
    except firebase_auth.UserNotFoundError:
        return False


def firebase_missing_uids(uids: list[str]) -> set[str]:
    """UIDs (from ``uids``) that no longer exist in Firebase Authentication."""
    app, firebase_auth = _firebase_auth()
    missing: set[str] = set()
    for start in range(0, len(uids), FIREBASE_BATCH):
        batch = uids[start : start + FIREBASE_BATCH]
        result = firebase_auth.get_users([firebase_auth.UidIdentifier(uid) for uid in batch], app=app)
        missing.update(identifier.uid for identifier in result.not_found)
    return missing


async def _is_admin(session: AsyncSession, user_id: uuid.UUID) -> bool:
    return (
        await session.scalar(select(AdminUser.id).where(AdminUser.user_id == user_id, AdminUser.deleted_at.is_(None)))
    ) is not None


async def close_farmer_account(session: AsyncSession, user: User, *, now: datetime | None = None) -> None:
    """Soft-delete a farmer everywhere in Agrownex (no Firebase call)."""
    now = now or datetime.now(UTC)
    user.status = UserStatus.DELETED
    user.deleted_at = now
    user.is_deleted = True
    await session.execute(
        update(FarmerProfile)
        .where(FarmerProfile.user_id == user.id, FarmerProfile.is_deleted.is_(False))
        .values(is_deleted=True, deleted_at=now)
    )
    await session.execute(
        update(Farm).where(Farm.user_id == user.id, Farm.is_deleted.is_(False)).values(is_deleted=True, deleted_at=now)
    )
    await session.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    await session.execute(update(UserSession).where(UserSession.user_id == user.id).values(revoked=True))
    await session.execute(
        update(OrganicPartnerFarmerLink)
        .where(OrganicPartnerFarmerLink.farmer_user_id == user.id, OrganicPartnerFarmerLink.status != "revoked")
        .values(status="revoked", revoked_at=now)
    )


async def admin_delete_farmer(session: AsyncSession, ctx, user_id: uuid.UUID, *, confirm_ref: str) -> dict:
    """Admin-initiated deletion: Firebase account first, then Agrownex account."""
    user = await session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise NotFoundError("Farmer not found.")
    if confirm_ref.strip().upper() != user.farmer_ref:
        raise ConflictError("Type the farmer's reference exactly to confirm deletion.")
    if await _is_admin(session, user.id):
        raise ConflictError("This account is an admin. Remove it from Team & permissions instead.")

    firebase_deleted = delete_firebase_account(user.firebase_uid)
    await close_farmer_account(session, user)
    session.add(
        AuditLog(
            admin_id=ctx.admin.id,
            role=ctx.admin.role,
            action="farmer_deleted",
            target="user",
            target_id=str(user.id),
            ip_address=ctx.ip_address,
            meta={"farmer_ref": user.farmer_ref, "firebase_deleted": firebase_deleted},
        )
    )
    await session.commit()
    logger.info("farmer deleted by admin: %s", user.farmer_ref)
    return {"farmer_ref": user.farmer_ref, "deleted": True, "firebase_account_deleted": firebase_deleted}


async def sync_deleted_firebase_users(session: AsyncSession, *, actor_admin=None, confirm: bool = False) -> SyncResult:
    """Close Agrownex accounts whose Firebase account was deleted in the console.

    ``confirm=True`` (Owner clicked "Remove these" after seeing the list)
    bypasses the share guard; the scheduled job never passes it.
    """
    rows = (
        await session.execute(select(User.id, User.firebase_uid).where(User.deleted_at.is_(None), User.is_deleted.is_(False)))
    ).all()
    uid_to_user = {uid: user_id for user_id, uid in rows if uid}
    missing = firebase_missing_uids(list(uid_to_user))
    result = SyncResult(checked=len(uid_to_user), missing_in_firebase=len(missing), closed=0, skipped_admins=0)
    missing_users = [u for u in [await session.get(User, uid_to_user[uid]) for uid in sorted(missing)] if u is not None]
    result.missing_refs = [u.farmer_ref for u in missing_users if not await _is_admin(session, u.id)]

    if not confirm and len(uid_to_user) >= MIN_USERS_FOR_SHARE_GUARD and len(missing) > MAX_SYNC_DELETE_SHARE * len(uid_to_user):
        logger.error(
            "firebase sync aborted: %s of %s users missing in Firebase (safety limit)", len(missing), len(uid_to_user)
        )
        result.aborted = True
        return result

    now = datetime.now(UTC)
    for user in missing_users:
        if await _is_admin(session, user.id):
            result.skipped_admins += 1
            continue
        await close_farmer_account(session, user, now=now)
        result.closed += 1
        session.add(
            AuditLog(
                admin_id=actor_admin.admin.id if actor_admin else None,
                role=actor_admin.admin.role if actor_admin else "system",
                action="farmer_deleted_firebase_sync",
                target="user",
                target_id=str(user.id),
                ip_address=actor_admin.ip_address if actor_admin else None,
                meta={"farmer_ref": user.farmer_ref},
            )
        )
    await session.commit()
    logger.info("firebase sync: %s", result.as_dict())
    return result
