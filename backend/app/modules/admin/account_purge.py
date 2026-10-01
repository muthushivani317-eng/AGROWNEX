"""Permanent erasure of closed farmer accounts (Play Store / DPDP requirement).

Closing an account (in-app "Close account", admin delete or Firebase sync) only
disables it. ``purge_closed_accounts`` runs nightly and, ``PURGE_AFTER_DAYS``
after closure, permanently deletes the farmer's personal data:

* every row in a non-retained table that references the user, plus — through
  the foreign-key graph — every row that depends on those rows (farm
  boundaries, chat messages, report images, ...);
* the photos / voice notes those rows point to in Cloudflare R2;
* the Firebase Authentication account (phone sign-in);
* the user's phone number and email (the user row itself is kept as an
  anonymous stub so retained records stay consistent).

Retained (as the privacy policy states): audit logs, consent receipts, and
trade / traceability / organic-certification records required by law or by
buyers and certifiers. They stay linked only to the anonymous stub. A nullable
link from a retained record to a deleted row is set to NULL; a mandatory one
keeps that row (it is then personal data no longer — the user is anonymous).

The walk is generic on purpose: new tables are erased automatically unless they
are added to ``RETAINED_TABLES``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Table, and_, delete, inspect, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.admin.models import AdminUser
from app.modules.auth.models import User
from app.shared.base_model import Base

logger = get_logger("admin.account_purge")

PURGE_AFTER_DAYS = 30
PURGED_UID_PREFIX = "purged:"

# Kept after erasure, linked to the anonymous user stub only.
RETAINED_TABLES = frozenset({
    "users",
    # audit / legal evidence
    "audit_logs",
    "action_audit_events",
    "user_consent_events",
    # trade and traceability (buyers, procurement, invoices)
    "produce_offers",
    "offer_images",
    "offer_status_history",
    "farmer_offer_decisions",
    "produce_trace_batches",
    "produce_trace_events",
    "produce_trace_shares",
    "input_orders",
    "input_order_events",
    "equipment_requests",
    # organic certification evidence (PGS / certifier audit trail)
    "organic_farm_profiles",
    "organic_certification_documents",
    "organic_pgs_cases",
    "organic_peer_appraisals",
    "organic_practice_log_entries",
    "organic_pilot_enrollments",
    "organic_readiness_assessments",
    "organic_upload_attestations",
    # staff / catalogue records that only reference staff accounts
    "admin_invitations",
    "organic_partner_staff",
    "organic_pilots",
    "organic_readiness_rules",
    "organic_task_templates",
    "organic_inputs",
    "organic_inputs_supplier_profiles",
    "organic_inputs_new_product_requests",
})

# Columns holding an R2 object key, or a public URL we can turn back into one.
MEDIA_KEY_COLUMNS = frozenset({"image_key", "object_key", "voice_note_object_id", "storage_key", "audio_key"})
MEDIA_URL_COLUMNS = frozenset({"image_url", "photo_url", "profile_photo", "audio_url"})

_MAX_DEPTH = 8


@dataclass
class PurgeResult:
    users: int = 0
    rows_deleted: int = 0
    links_cleared: int = 0
    rows_kept: int = 0
    media_deleted: int = 0
    media_failed: int = 0
    firebase_deleted: int = 0
    tables: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "tables"}


async def _tables(session: AsyncSession) -> dict[str, Table]:
    """Model tables that exist in the database (a table without a migration is skipped)."""
    _load_all_models()
    conn = await session.connection()
    existing = set(await conn.run_sync(lambda c: inspect(c).get_table_names()))
    return {name: t for name, t in Base.metadata.tables.items() if name in existing}


def _load_all_models() -> None:
    import importlib
    import pkgutil

    import app.modules as modules

    for mod in pkgutil.walk_packages(modules.__path__, modules.__name__ + "."):
        if mod.name.endswith((".models", "_models")):
            importlib.import_module(mod.name)


def _referencing(tables: dict[str, Table], parent: Table) -> list[tuple[Table, Any]]:
    """(child table, fk column) pairs pointing at ``parent``'s primary key."""
    out = []
    for child in tables.values():
        for col in child.columns:
            for fk in col.foreign_keys:
                if fk.column.table is parent and fk.column.primary_key:
                    out.append((child, col))
    return out


def _media_keys(row: Any, public_bases: tuple[str, ...]) -> set[str]:
    keys: set[str] = set()
    mapping = row._mapping
    for name in MEDIA_KEY_COLUMNS & set(mapping.keys()):
        if mapping[name]:
            keys.add(str(mapping[name]).lstrip("/"))
    for name in MEDIA_URL_COLUMNS & set(mapping.keys()):
        value = mapping[name]
        if not value:
            continue
        for base in public_bases:
            if base and str(value).startswith(base + "/"):
                keys.add(str(value)[len(base) + 1 :].split("?", 1)[0])
    return keys


_UNSAFE_KEY_PARTS = ("..", "%", "\\", "#", "?", "//")


def _is_plain_key(key: str) -> bool:
    """Server-issued keys are plain "a/b/c.ext" paths; anything else is refused."""
    return bool(key) and not key.startswith("/") and not any(p in key for p in _UNSAFE_KEY_PARTS)


class _Purger:
    def __init__(self, session: AsyncSession, tables: dict[str, Table], public_bases: tuple[str, ...]):
        self.session = session
        self.tables = tables
        self.public_bases = public_bases
        self.media: set[str] = set()
        # Ids of every row erased for this user. A media object is deleted only
        # if its key is scoped to one of them (".../{user_id}/...",
        # "daily_task/{task_id}/..."), so a URL the farmer typed into a free-text
        # column can never make the purge delete someone else's file.
        self.owned_ids: set[str] = set()
        self.result = PurgeResult()

    async def erase(self, table: Table, where, depth: int = 0) -> None:
        """Delete rows of ``table`` matching ``where`` and everything depending on them."""
        if depth > _MAX_DEPTH:
            logger.warning("purge depth limit reached at %s", table.name)
            return
        pk = list(table.primary_key.columns)
        rows = (await self.session.execute(select(table).where(where))).all()
        if not rows:
            return
        if len(pk) == 1:
            ids = [r._mapping[pk[0].name] for r in rows]
            blocked: set[Any] = set()
            for child, col in _referencing(self.tables, table):
                if child is table:
                    continue
                child_where = col.in_(ids)
                if child.name in RETAINED_TABLES:
                    if col.nullable:
                        res = await self.session.execute(update(child).where(child_where).values({col.name: None}))
                        self.result.links_cleared += res.rowcount or 0
                    else:
                        kept = (await self.session.execute(select(col).where(child_where))).scalars().all()
                        blocked.update(kept)
                    continue
                await self.erase(child, child_where, depth + 1)
            if blocked:
                self.result.rows_kept += len(blocked)
                rows = [r for r in rows if r._mapping[pk[0].name] not in blocked]
                where = and_(where, pk[0].notin_(list(blocked)))
                if not rows:
                    return
        for row in rows:
            self.media |= _media_keys(row, self.public_bases)
            if len(pk) == 1:
                self.owned_ids.add(str(row._mapping[pk[0].name]))
        res = await self.session.execute(delete(table).where(where))
        count = res.rowcount or 0
        self.result.rows_deleted += count
        self.result.tables[table.name] = self.result.tables.get(table.name, 0) + count

    def owned_media(self) -> set[str]:
        owned = {i.lower() for i in self.owned_ids} | {i.replace("-", "").lower() for i in self.owned_ids}
        return {
            k
            for k in self.media
            if _is_plain_key(k) and owned & {seg.lower() for seg in k.split("/")}
        }

    async def purge_user(self, user: User) -> None:
        self.owned_ids.add(str(user.id))
        users = self.tables["users"]
        for table in self.tables.values():
            if table.name in RETAINED_TABLES:
                continue
            cols = [c for c in table.columns if any(fk.column.table is users for fk in c.foreign_keys)]
            if not cols:
                continue
            await self.erase(table, or_(*[c == user.id for c in cols]))
        # Retained rows keep pointing at the anonymous stub below.
        user.phone_number = None
        user.email = None
        user.firebase_uid = f"{PURGED_UID_PREFIX}{user.id}"
        user.is_phone_verified = False
        user.is_email_verified = False
        self.result.users += 1


async def _delete_media(keys: set[str], result: PurgeResult) -> None:
    if not keys:
        return
    from app.modules.disease.storage import get_default_storage, get_private_storage

    stores = [s for s in (get_default_storage(), get_private_storage()) if hasattr(s, "delete")]
    for key in sorted(keys):
        ok = False
        for store in stores:
            try:
                await store.delete(key=key)
                ok = True
            except Exception:  # noqa: BLE001 - one bucket may be unavailable
                continue
        if ok:
            result.media_deleted += 1
        else:
            result.media_failed += 1
            logger.warning("purge: could not delete media object (kept for retry by ops)")


def _public_bases() -> tuple[str, ...]:
    from app.modules.disease.constants import R2_PUBLIC_BASE_URL

    return tuple(b for b in (R2_PUBLIC_BASE_URL,) if b)


async def due_users(session: AsyncSession, *, now: datetime | None = None) -> list[User]:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=PURGE_AFTER_DAYS)
    admin_ids = select(AdminUser.user_id).where(AdminUser.user_id.is_not(None))
    stmt = select(User).where(
        User.deleted_at.is_not(None),
        User.deleted_at <= cutoff,
        ~User.firebase_uid.startswith(PURGED_UID_PREFIX),
        User.id.notin_(admin_ids),
    )
    return list((await session.scalars(stmt)).all())


async def purge_closed_accounts(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    delete_firebase: bool = True,
    delete_media: bool = True,
) -> dict[str, Any]:
    """Erase every closed farmer account older than ``PURGE_AFTER_DAYS``."""
    tables = await _tables(session)
    total = PurgeResult()
    for user in await due_users(session, now=now):
        firebase_uid = user.firebase_uid
        purger = _Purger(session, tables, _public_bases())
        try:
            await purger.purge_user(user)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("purge failed for user %s; will retry next run", user.id)
            continue
        if delete_media:
            await _delete_media(purger.owned_media(), purger.result)
        if delete_firebase and firebase_uid and not firebase_uid.startswith(PURGED_UID_PREFIX):
            try:
                from app.modules.admin.farmer_deletion import delete_firebase_account

                if delete_firebase_account(firebase_uid):
                    purger.result.firebase_deleted += 1
            except Exception:  # noqa: BLE001 - Firebase outage must not undo the DB erase
                logger.warning("purge: Firebase account deletion failed for user %s", user.id)
        for key, value in purger.result.as_dict().items():
            setattr(total, key, getattr(total, key) + value)
        logger.info("account purged: user=%s %s", user.id, purger.result.as_dict())
    logger.info("purge run: %s", total.as_dict())
    return total.as_dict()


def is_purged(user: User) -> bool:
    return bool(user.firebase_uid and user.firebase_uid.startswith(PURGED_UID_PREFIX))


__all__ = ["PURGE_AFTER_DAYS", "RETAINED_TABLES", "due_users", "is_purged", "purge_closed_accounts"]
