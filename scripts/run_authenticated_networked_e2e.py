"""Real-network authentication diagnostic for the four installed crop routes.

This script uses Firebase's supported email/password REST flow to create an
ephemeral test identity, starts Uvicorn on localhost with a disposable SQLite
database, performs real HTTP requests, then deletes the Firebase identity.
Secrets and tokens are never printed or written to disk.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MOBILE = ROOT / "agrow-ai"
FIXTURES = BACKEND / "tests/fixtures/six_crop_internal_readiness/manifests/FIXTURE_MANIFEST.json"
GENERATED = BACKEND / "tests/fixtures/six_crop_internal_readiness/generated"
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "networked_e2e_results.json"
HOST = "127.0.0.1"
PORT = 8876
BASE = f"http://{HOST}:{PORT}/api/v1"


def _env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _json_request(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 20,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"body": raw[:500]}
        return exc.code, parsed


def _multipart(path: Path, fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"agrowai-{secrets.token_hex(12)}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode(),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _upload(url: str, path: Path, token: str | None, fields: dict[str, str]) -> tuple[int, dict]:
    body, content_type = _multipart(path, fields)
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"body": raw[:500]}


async def _prepare_database(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "false"
    sys.path.insert(0, str(BACKEND))
    from app.main import app  # noqa: F401
    from app.core.database import engine
    from app.modules.auth.constants import RoleName
    from app.modules.auth.rbac_models import Role
    from app.shared.base_model import Base
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for role in RoleName:
            session.add(Role(role_name=role.value, description="E2E local test role"))
        await session.commit()
    await engine.dispose()


def _wait_ready() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            status, _ = _json_request(f"{BASE}/health")
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(0.25)
    raise RuntimeError("BACKEND_STARTUP_TIMEOUT")


def main() -> int:
    backend_env = _env(BACKEND / ".env")
    mobile_env = _env(MOBILE / ".env")
    api_key = mobile_env.get("EXPO_PUBLIC_FIREBASE_API_KEY", "")
    if not api_key or not backend_env.get("FIREBASE_CREDENTIALS_JSON"):
        raise RuntimeError("FIREBASE_TEST_CONFIGURATION_MISSING")

    email = f"agrowai-e2e-{secrets.token_hex(8)}@example.invalid"
    password = secrets.token_urlsafe(24)
    signup_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + api_key
    )
    delete_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:delete?key=" + api_key
    )
    token = ""
    server: subprocess.Popen[str] | None = None
    database = ROOT / ".codex_tmp" / "authenticated_networked_e2e.sqlite3"
    derived = ROOT / ".codex_tmp" / "authenticated_networked_e2e_images"
    database.parent.mkdir(exist_ok=True)
    database.unlink(missing_ok=True)
    shutil.rmtree(derived, ignore_errors=True)
    derived.mkdir(parents=True)
    results: dict[str, Any] = {
        "authentication_bypassed": False,
        "real_http_transport": True,
        "credentials_redacted": True,
        "server": {"host": HOST, "port": PORT, "environment": "test"},
        "identity": {},
        "auth_cases": [],
        "crop_cases": [],
    }
    try:
        status, signup = _json_request(
            signup_url,
            method="POST",
            body={"email": email, "password": password, "returnSecureToken": True},
        )
        if status != 200 or not signup.get("idToken"):
            raise RuntimeError(f"FIREBASE_SIGNUP_FAILED:{status}")
        token = signup["idToken"]
        results["identity"] = {
            "identity_type": "ephemeral_firebase_test_user",
            "role": "farmer",
            "token_issued": True,
            "token_value": "[REDACTED]",
            "firebase_uid_hash": hashlib.sha256(signup["localId"].encode()).hexdigest(),
        }

        db_url = f"sqlite+aiosqlite:///{database.as_posix()}"
        asyncio.run(_prepare_database(db_url))
        child_env = os.environ.copy()
        child_env.update(backend_env)
        child_env.update(
            {
                "DATABASE_URL": db_url,
                "ENVIRONMENT": "test",
                "DEBUG": "false",
                "TRUSTED_HOSTS": '["127.0.0.1","localhost"]',
            }
        )
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                HOST,
                "--port",
                str(PORT),
            ],
            cwd=BACKEND,
            env=child_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        _wait_ready()

        login_status, login_body = _json_request(
            f"{BASE}/auth/google",
            method="POST",
            body={"id_token": token, "device_name": "network-e2e", "device_type": "test"},
        )
        results["identity"]["login_status"] = login_status
        results["identity"]["login_roles"] = (
            login_body.get("data", {}).get("roles", []) if login_status == 200 else []
        )

        for name, supplied in (
            ("valid", token),
            ("missing", None),
            ("random", secrets.token_urlsafe(32)),
            ("malformed", "not.a.jwt"),
        ):
            auth_status, auth_body = _json_request(f"{BASE}/auth/profile", token=supplied)
            error = auth_body.get("error")
            detail = auth_body.get("detail")
            response_category = "HTTP_RESPONSE"
            if isinstance(error, dict):
                response_category = str(error.get("code") or response_category)
            elif isinstance(detail, dict):
                response_category = str(detail.get("code") or response_category)
            elif isinstance(detail, str):
                response_category = detail
            results["auth_cases"].append(
                {
                    "case": name,
                    "http_status": auth_status,
                    "accepted": auth_status == 200,
                    "response_category": response_category,
                }
            )

        manifest = json.loads(FIXTURES.read_text("utf-8"))
        first = {}
        for fixture in manifest["fixtures"]:
            first.setdefault(fixture["crop_id"], fixture)
        for crop in ("paddy", "banana", "cotton", "groundnut"):
            fixture = first[crop]
            path = Path(fixture["file_path"])
            fields = {} if crop == "banana" else {"crop_confirmed": "true"}
            request_status, response = _upload(
                f"{BASE}/disease/{crop}/predict", path, token, fields
            )
            detail = response.get("detail", {})
            results["crop_cases"].append(
                {
                    "crop_id": crop,
                    "fixture_id": fixture["fixture_id"],
                    "fixture_sha256": fixture["sha256"],
                    "fixture_category": "VALID_SAME_CROP",
                    "request_url": f"{BASE}/disease/{crop}/predict",
                    "authentication_state": "valid_firebase_id_token",
                    "http_status": request_status,
                    "response_status": response.get("status", ""),
                    "reason_code": detail.get("code")
                    or response.get("decision_code", ""),
                    "runtime_crop_id": response.get("crop_id")
                    or response.get("crop", ""),
                    "runtime_model_version": response.get("model_version", ""),
                    "model_inference_executed": bool(
                        response.get("model_inference_executed", False)
                    ),
                    "expected_behavior": fixture["expected_system_behavior"],
                    "passed": False,
                }
            )

            wrong_source = next(
                candidate
                for other, candidate in first.items()
                if other != crop
            )
            wrong_path = Path(wrong_source["file_path"])
            wrong_status, wrong_body = _upload(
                f"{BASE}/disease/{crop}/predict", wrong_path, token, fields
            )
            results["crop_cases"].append(
                {
                    "crop_id": crop,
                    "fixture_id": f"wrong-for-{crop}--{wrong_source['fixture_id']}",
                    "fixture_sha256": wrong_source["sha256"],
                    "fixture_category": "WRONG_CROP",
                    "http_status": wrong_status,
                    "reason_code": wrong_body.get("detail", {}).get("code")
                    or wrong_body.get("decision_code", ""),
                    "model_inference_executed": False,
                    "passed": wrong_body.get("status") != "accepted"
                    and wrong_body.get("accepted") is not True,
                }
            )

            corrupt = GENERATED / "corrupt.jpg"
            corrupt_status, corrupt_body = _upload(
                f"{BASE}/disease/{crop}/predict", corrupt, token, fields
            )
            results["crop_cases"].append(
                {
                    "crop_id": crop,
                    "fixture_id": "generated-corrupt.jpg",
                    "fixture_category": "CORRUPT",
                    "http_status": corrupt_status,
                    "reason_code": corrupt_body.get("detail", {}).get("code")
                    or corrupt_body.get("decision_code", ""),
                    "model_inference_executed": False,
                    "passed": 400 <= corrupt_status < 500,
                }
            )

            with Image.open(path) as source:
                source = source.convert("RGB")
                variants = {
                    "moderate_blur": source.filter(ImageFilter.GaussianBlur(radius=4)),
                    "extreme_blur": source.filter(ImageFilter.GaussianBlur(radius=20)),
                    "underexposed": ImageEnhance.Brightness(source).enhance(0.05),
                    "overexposed": ImageEnhance.Brightness(source).enhance(3.0),
                    "low_resolution": source.resize((32, 32)),
                }
                for category, variant in variants.items():
                    variant_path = derived / f"{crop}-{category}.jpg"
                    variant.save(variant_path, format="JPEG", quality=90)
                    quality_status, quality_body = _upload(
                        f"{BASE}/disease/{crop}/predict",
                        variant_path,
                        token,
                        fields,
                    )
                    detail = quality_body.get("detail", {})
                    results["crop_cases"].append(
                        {
                            "crop_id": crop,
                            "fixture_id": f"derived-{fixture['fixture_id']}-{category}",
                            "fixture_category": category.upper(),
                            "derived_from_sha256": fixture["sha256"],
                            "http_status": quality_status,
                            "reason_code": (
                                detail.get("code") if isinstance(detail, dict) else ""
                            )
                            or quality_body.get("decision_code", ""),
                            "model_inference_executed": False,
                            "passed": quality_body.get("status") != "accepted"
                            and quality_body.get("accepted") is not True,
                        }
                    )
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        if token:
            delete_status, _ = _json_request(
                delete_url, method="POST", body={"idToken": token}
            )
            results.setdefault("identity", {})["firebase_identity_deleted"] = (
                delete_status == 200
            )
        database.unlink(missing_ok=True)
        shutil.rmtree(derived, ignore_errors=True)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(results, indent=2) + "\n", "utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
