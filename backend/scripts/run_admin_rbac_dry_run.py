"""Real-HTTP Admin role-matrix dry run against Firebase Auth Emulator only.

For each AdminRole, mints a real (emulator) Firebase ID token, promotes the
user to that role via the real ensure_admin() seeding path, then makes real
HTTP requests through the real AdminContextDep/RBAC dependency chain against
one representative endpoint per AdminPermission, asserting the observed
status code matches ROLE_PERMISSIONS exactly. A 7th identity has no AdminUser
row at all (negative control): every endpoint must refuse it.

Run with the Firebase Auth Emulator already up (see
docs or run_crop_identity_auth_emulator_e2e.py for the same pattern):

    firebase emulators:start --only auth --project demo-agrowai-crop-id-test

then, from backend/:

    python scripts/run_admin_rbac_dry_run.py

Exits non-zero (and prints ADMIN_RBAC_DRY_RUN_FAILED) if any role/permission
pair doesn't match what ROLE_PERMISSIONS says it should.
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.WARNING)
for _name in ("httpx", "httpcore", "aiosqlite", "sqlalchemy", "sqlalchemy.engine", "uvicorn"):
    logging.getLogger(_name).setLevel(logging.WARNING)

import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT / "backend"
sys.path.insert(0, str(BACKEND))

PROJECT_ID = "demo-agrowai-crop-id-test"
AUTH_HOST = "127.0.0.1:9099"
API_HOST = "127.0.0.1"
API_PORT = 8031
DATABASE = PROJECT / ".codex_admin_rbac_emulator.db"
RECEIPT_PATH = PROJECT / ".codex_admin_rbac_dry_run_receipt.json"

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite+aiosqlite:///{DATABASE.as_posix()}",
        "FIREBASE_PROJECT_ID": PROJECT_ID,
        "FIREBASE_CREDENTIALS_JSON": "",
        "FIREBASE_AUTH_EMULATOR_HOST": AUTH_HOST,
        "SESSION_SECRET": "non-production-emulator-only-rbac-dry-run",
        "ALLOW_MOCK_PROVIDERS": "true",
    }
)

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from app.api.errors import register_exception_handlers  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.modules.admin import models as _admin_models  # noqa: E402,F401
from app.modules.admin.constants import AdminPermission, AdminRole, ROLE_PERMISSIONS  # noqa: E402
from app.modules.admin.router import router as admin_router  # noqa: E402
from app.modules.admin.seed import ensure_admin  # noqa: E402
from app.modules.ai import models as _ai_models  # noqa: E402,F401
from app.modules.auth import models as _auth_models  # noqa: E402,F401
from app.modules.auth import profile_models as _profile_models  # noqa: E402,F401
from app.modules.auth import rbac_models as _rbac_models  # noqa: E402,F401
from app.modules.auth.constants import UserStatus  # noqa: E402
from app.modules.auth.models import User  # noqa: E402
from app.modules.calendar import models as _calendar_models  # noqa: E402,F401
from app.modules.consents import models as _consent_models  # noqa: E402,F401
from app.modules.disease import models as _disease_models  # noqa: E402,F401
from app.modules.experts import models as _expert_models  # noqa: E402,F401
from app.modules.farms import models as _farm_models  # noqa: E402,F401
from app.modules.growth import models as _growth_models  # noqa: E402,F401
from app.modules.intelligence import models as _intelligence_models  # noqa: E402,F401
from app.modules.market import models as _market_models  # noqa: E402,F401
from app.modules.memory import models as _memory_models  # noqa: E402,F401
from app.modules.notifications import models as _notification_models  # noqa: E402,F401
from app.modules.nutrient import models as _nutrient_models  # noqa: E402,F401
from app.modules.produce import models as _produce_models  # noqa: E402,F401
from app.modules.satellite import models as _satellite_models  # noqa: E402,F401
from app.modules.schemes import models as _scheme_models  # noqa: E402,F401
from app.modules.soil import models as _soil_models  # noqa: E402,F401
from app.modules.support import models as _support_models  # noqa: E402,F401
from app.modules.support.router import admin_router as admin_support_router  # noqa: E402
from app.shared.base_model import Base  # noqa: E402
from fastapi import FastAPI  # noqa: E402

IDENTITIES = {
    AdminRole.OWNER.value: "owner@demo.invalid",
    AdminRole.SUPER_ADMIN.value: "super-admin@demo.invalid",
    AdminRole.DISTRICT_MANAGER.value: "district-manager@demo.invalid",
    AdminRole.PROCUREMENT_MANAGER.value: "procurement-manager@demo.invalid",
    AdminRole.AGRICULTURE_OFFICER.value: "agriculture-officer@demo.invalid",
    AdminRole.CUSTOMER_SUPPORT.value: "customer-support@demo.invalid",
}
NO_ADMIN_RECORD = "no-admin-record@demo.invalid"

# One representative endpoint per AdminPermission (method, path, kwargs for httpx).
ENDPOINTS: dict[str, tuple[str, str, dict]] = {
    AdminPermission.VIEW_DASHBOARD.value: ("GET", "/api/v1/admin/dashboard", {}),
    AdminPermission.VIEW_REVENUE.value: ("GET", "/api/v1/admin/business-dashboard", {}),
    AdminPermission.MANAGE_FARMERS.value: ("GET", "/api/v1/admin/farmers", {}),
    AdminPermission.VIEW_ANALYTICS.value: ("GET", "/api/v1/admin/analytics", {}),
    AdminPermission.VIEW_CROP_INTELLIGENCE.value: ("GET", "/api/v1/admin/crop-intelligence", {}),
    AdminPermission.MANAGE_PROCUREMENT.value: ("GET", "/api/v1/admin/procurement", {}),
    # Compound-gated: also requires MANAGE_PROCUREMENT, plus a record-level
    # assignment check (owner/super_admin override; others need the case
    # assigned to them). Handled specially below rather than via the plain
    # ROLE_PERMISSIONS membership test the other permissions use.
    AdminPermission.REVEAL_BUYER_CONTACT.value: (
        "POST",
        "/api/v1/admin/procurement/00000000-0000-0000-0000-000000000000/buyer-contact/reveal",
        {},
    ),
    AdminPermission.VIEW_AI.value: ("GET", "/api/v1/admin/ai", {}),
    AdminPermission.VIEW_AI_COSTS.value: ("GET", "/api/v1/admin/ai-costs", {}),
    AdminPermission.SEND_BROADCAST.value: ("GET", "/api/v1/admin/notifications", {}),
    AdminPermission.MANAGE_CONTENT.value: (
        "POST",
        "/api/v1/admin/announcements",
        {"json": {"title": "RBAC dry run", "body": "test"}},
    ),
    AdminPermission.VIEW_AUDIT.value: ("GET", "/api/v1/admin/audit", {}),
    AdminPermission.MANAGE_ADMINS.value: ("GET", "/api/v1/admin/team", {}),
    AdminPermission.MANAGE_SUPPORT.value: ("GET", "/api/v1/admin/support-tickets", {}),
}


def _signup(email: str) -> dict:
    response = httpx.post(
        f"http://{AUTH_HOST}/identitytoolkit.googleapis.com/v1/accounts:signUp",
        params={"key": "emulator-only"},
        json={
            "email": email,
            "password": "ephemeral-not-recorded-123!",
            "returnSecureToken": True,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


async def _prepare_database(accounts: dict[str, dict]) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        for role, account in accounts.items():
            user = User(
                firebase_uid=account["localId"],
                email=IDENTITIES.get(role, NO_ADMIN_RECORD),
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            await session.flush()
            if role != "no_admin_record":
                await ensure_admin(session, user.id, role=role)
        await session.commit()


def _request(method: str, path: str, token: str, **kwargs) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.request(
        method, f"http://{API_HOST}:{API_PORT}{path}", headers=headers, timeout=20, **kwargs
    )
    return response.status_code


def _expected_status_kind(role: str, perm: str, granted: bool) -> str:
    """'refused' (must be 403) or 'permitted' (must not be 403) for one check.

    reveal_buyer_contact is special: even a role with both required
    permissions is refused (403) for a case that isn't assigned to them,
    unless they're an override role (owner/super_admin), which is exactly
    the record-level authorization this endpoint is meant to enforce on top
    of the coarse role permission — so a fake/unassigned offer_id is
    expected to come back 403 for every non-override role regardless of
    whether they hold the permission.
    """
    if perm == AdminPermission.REVEAL_BUYER_CONTACT.value:
        override = role in {AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}
        return "permitted" if (granted and override) else "refused"
    return "permitted" if granted else "refused"


def main() -> None:
    if DATABASE.exists():
        DATABASE.unlink()

    accounts = {role: _signup(email) for role, email in IDENTITIES.items()}
    accounts["no_admin_record"] = _signup(NO_ADMIN_RECORD)

    asyncio.run(_prepare_database(accounts))

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(admin_support_router, prefix="/api/v1")
    server = uvicorn.Server(uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            if httpx.get(f"http://{API_HOST}:{API_PORT}/openapi.json").status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(0.05)

    results: dict[str, dict[str, dict]] = {}
    mismatches: list[str] = []

    for role, account in accounts.items():
        token = account["idToken"]
        expected_perms = set(ROLE_PERMISSIONS.get(role, ()))
        results[role] = {}
        for perm, (method, path, kwargs) in ENDPOINTS.items():
            status = _request(method, path, token, **kwargs)
            granted = perm in expected_perms
            expect = _expected_status_kind(role, perm, granted)
            got = "refused" if status == 403 else "permitted"
            results[role][perm] = {"status": status, "expected": expect, "got": got}
            if got != expect:
                mismatches.append(
                    f"role={role} perm={perm} status={status} expected={expect} got={got}"
                )

    server.should_exit = True
    thread.join(timeout=10)
    asyncio.run(engine.dispose())

    receipt = {
        "environment": "FIREBASE_AUTH_EMULATOR",
        "project_id": PROJECT_ID,
        "roles_tested": list(IDENTITIES.keys()) + ["no_admin_record"],
        "permissions_tested": list(ENDPOINTS.keys()),
        "results": results,
        "mismatches": mismatches,
        "total_checks": sum(len(v) for v in results.values()),
        "mismatch_count": len(mismatches),
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total_checks": receipt["total_checks"], "mismatch_count": len(mismatches)}))
    if mismatches:
        print("MISMATCHES:")
        for m in mismatches:
            print(" -", m)
        print("ADMIN_RBAC_DRY_RUN_FAILED")
        raise SystemExit(1)
    print("ADMIN_RBAC_DRY_RUN_ALL_MATCHED")


if __name__ == "__main__":
    main()
