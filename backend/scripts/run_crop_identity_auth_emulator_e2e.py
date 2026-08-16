"""Real-HTTP crop-ID authorization checks against Firebase Auth Emulator only."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import uvicorn

PROJECT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT / "backend"
sys.path.insert(0, str(BACKEND))

PROJECT_ID = "demo-agrowai-crop-id-test"
AUTH_HOST = "127.0.0.1:9099"
API_HOST = "127.0.0.1"
API_PORT = 8019
DATABASE = PROJECT / ".codex_crop_identity_emulator.db"

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite+aiosqlite:///{DATABASE.as_posix()}",
        "FIREBASE_PROJECT_ID": PROJECT_ID,
        "FIREBASE_CREDENTIALS_JSON": "",
        "FIREBASE_AUTH_EMULATOR_HOST": AUTH_HOST,
        "SESSION_SECRET": "non-production-emulator-only",
        "ALLOW_MOCK_PROVIDERS": "true",
    }
)

from app.api.errors import register_exception_handlers  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.crop_identity.router import router  # noqa: E402
from app.modules.auth.constants import RoleName, UserStatus  # noqa: E402
from app.modules.auth.models import User  # noqa: E402
from app.modules.auth.rbac_models import Role, UserRole  # noqa: E402
from app.shared.base_model import Base  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from firebase_admin import auth as firebase_auth  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

IDENTITIES = {
    "internal_tester": "internal-tester@demo.invalid",
    "pilot_tester": "pilot-tester@demo.invalid",
    "farmer": "ordinary-farmer@demo.invalid",
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


def _claim_variant(token: str, **claims: object) -> str:
    header, payload, signature = token.split(".")
    document = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    document.update(claims)
    encoded = (
        base64.urlsafe_b64encode(json.dumps(document, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{encoded}.{signature}"


async def _prepare_database(accounts: dict[str, dict]) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        roles = {}
        for name in RoleName:
            role = Role(role_name=name.value)
            session.add(role)
            roles[name.value] = role
        await session.flush()
        for role_name, account in accounts.items():
            user = User(
                firebase_uid=account["localId"],
                email=IDENTITIES[role_name],
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=roles[role_name].id))
        await session.commit()


async def _replace_roles(uid: str, role_names: list[str]) -> None:
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.firebase_uid == uid))).scalar_one()
        await session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        for name in role_names:
            role = (
                await session.execute(select(Role).where(Role.role_name == name))
            ).scalar_one_or_none()
            if role is None:
                role = Role(role_name=name)
                session.add(role)
                await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()


def _request(token: str | None, **overrides) -> dict:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(overrides.pop("headers", {}))
    started = time.perf_counter()
    response = httpx.post(
        f"http://{API_HOST}:{API_PORT}/crop-identity/predict-controlled",
        headers=headers,
        files={"image": ("invalid.jpg", b"not-an-image", "image/jpeg")},
        data={"requested_crop": "banana", **overrides.pop("data", {})},
        params=overrides.pop("params", {}),
        timeout=20,
    )
    try:
        body = response.json()
    except ValueError:
        body = {}
    detail = body.get("detail", {})
    return {
        "http_method": "POST",
        "route": "/crop-identity/predict-controlled",
        "status_code": response.status_code,
        "reason_code": body.get("error_code")
        or (detail.get("code") if isinstance(detail, dict) else None),
        "request_correlation_id": response.headers.get("x-request-id"),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "auth_environment": "FIREBASE_AUTH_EMULATOR",
        "token_type": "EMULATOR_ID_TOKEN" if token else "NONE",
        "token_redacted": True,
        "crop_id_model_called": False,
        "disease_model_called": False,
    }


async def main() -> None:
    if DATABASE.exists():
        DATABASE.unlink()
    accounts = {role: _signup(email) for role, email in IDENTITIES.items()}
    await _prepare_database(accounts)

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    server = uvicorn.Server(uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            if httpx.get(  # noqa: ASYNC210 - polling a server on a worker thread
                f"http://{API_HOST}:{API_PORT}/openapi.json"
            ).status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(0.05)  # noqa: ASYNC251 - bounded startup polling

    results = {}
    internal = accounts["internal_tester"]
    pilot = accounts["pilot_tester"]
    farmer = accounts["farmer"]
    results["internal_tester"] = _request(internal["idToken"])
    results["pilot_tester"] = _request(pilot["idToken"])
    results["farmer"] = _request(farmer["idToken"])
    results["missing_token"] = _request(None)
    results["malformed_token"] = _request("malformed")
    results["invalid_signature"] = _request(internal["idToken"] + "x")
    results["expired_token"] = _request(
        _claim_variant(internal["idToken"], exp=int(time.time()) - 3600)
    )
    results["wrong_issuer"] = _request(
        _claim_variant(internal["idToken"], iss="https://securetoken.google.com/wrong")
    )
    results["wrong_audience"] = _request(_claim_variant(internal["idToken"], aud="wrong-project"))
    results["client_overrides"] = _request(
        farmer["idToken"],
        headers={"X-Role": "pilot_tester"},
        data={"role": "internal_tester"},
        params={"role": "pilot_tester"},
    )

    await _replace_roles(pilot["localId"], [])
    results["missing_role"] = _request(pilot["idToken"])
    await _replace_roles(pilot["localId"], ["unknown"])
    results["unknown_role"] = _request(pilot["idToken"])
    await _replace_roles(pilot["localId"], ["internal_tester", "pilot_tester"])
    results["role_conflict"] = _request(pilot["idToken"])

    firebase_auth.revoke_refresh_tokens(internal["localId"])
    results["revoked_token"] = _request(internal["idToken"])
    firebase_auth.update_user(pilot["localId"], disabled=True)
    results["disabled_user"] = _request(pilot["idToken"])

    server.should_exit = True
    thread.join(timeout=10)
    await engine.dispose()

    receipt = {
        "environment": "FIREBASE_AUTH_EMULATOR",
        "project_id": PROJECT_ID,
        "auth_endpoint": AUTH_HOST,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "identities": [
            {
                "synthetic_identifier": role,
                "emulator_uid": account["localId"],
                "assigned_backend_role": role,
                "revocable": True,
                "enabled_at_creation": True,
            }
            for role, account in accounts.items()
        ],
        "raw_password_recorded": False,
        "raw_token_recorded": False,
        "private_key_recorded": False,
        "results": results,
    }
    output = Path(os.environ["AGROWAI_AUTH_E2E_OUTPUT"])
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("CROP_ID_FIREBASE_EMULATOR_E2E_COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
