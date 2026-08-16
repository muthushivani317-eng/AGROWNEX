"""Run non-sealed fixture requests through the real crop API routers.

Authentication is dependency-overridden only to make the local request
repeatable; no inference runtime is mocked. Results are diagnostic evidence,
not deployment authorization or an accuracy claim.
"""
from __future__ import annotations

import json
import mimetypes
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(BACKEND))

from app.banana_v3.api_router import router as banana_router  # noqa: E402
from app.legacy_joint.api_router import router as legacy_router  # noqa: E402
from app.modules.auth.dependencies import get_current_user  # noqa: E402


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifests" / "FIXTURE_MANIFEST.json"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(banana_router, prefix="/api/v1")
    app.include_router(legacy_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: object()
    return TestClient(app, raise_server_exceptions=False)


def _request(client: TestClient, crop: str, path: Path):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    endpoint = f"/api/v1/disease/{crop}/predict"
    kwargs = {
        "files": {"image": (path.name, path.read_bytes(), mime)},
    }
    if crop != "banana":
        kwargs["data"] = {"crop_confirmed": "true"}
    response = client.post(endpoint, **kwargs)
    try:
        body = response.json()
    except Exception:
        body = {"unparsed_body": response.text[:500]}
    return endpoint, response.status_code, body


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "diagnostics.json"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixtures = manifest["fixtures"]
    by_crop = {}
    for item in fixtures:
        by_crop.setdefault(item["crop_id"], []).append(item)

    cases = []
    client = _client()
    for crop in ("banana", "paddy", "cotton", "groundnut"):
        for item in by_crop[crop]:
            endpoint, status, body = _request(client, crop, Path(item["file_path"]))
            cases.append(
                {
                    "crop_id": crop,
                    "fixture_id": item["fixture_id"],
                    "fixture_category": "VALID_SAME_CROP",
                    "request_endpoint": endpoint,
                    "http_status": status,
                    "response": body,
                    "expected_behavior": item["expected_system_behavior"],
                    "diagnostic_only": True,
                }
            )
        for other_crop in ("banana", "paddy", "cotton", "groundnut"):
            if other_crop == crop:
                continue
            item = by_crop[other_crop][0]
            endpoint, status, body = _request(client, crop, Path(item["file_path"]))
            accepted = bool(body.get("accepted")) or body.get("status") == "accepted"
            cases.append(
                {
                    "crop_id": crop,
                    "fixture_id": f"wrong-for-{crop}--{item['fixture_id']}",
                    "source_crop_id": other_crop,
                    "fixture_category": "WRONG_CROP",
                    "request_endpoint": endpoint,
                    "http_status": status,
                    "response": body,
                    "passed": not accepted,
                    "diagnostic_only": True,
                }
            )

    for crop in ("banana", "paddy", "cotton", "groundnut"):
        for name in ("all_black.png", "random_noise.png", "corrupt.jpg"):
            path = ROOT / "generated" / name
            endpoint, status, body = _request(client, crop, path)
            accepted = bool(body.get("accepted")) or body.get("status") == "accepted"
            cases.append(
                {
                    "crop_id": crop,
                    "fixture_id": f"generated-{name}",
                    "fixture_category": "PROGRAMMATIC_INVALID",
                    "request_endpoint": endpoint,
                    "http_status": status,
                    "response": body,
                    "passed": not accepted,
                    "diagnostic_only": True,
                }
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "runtime_mocked": False,
                "authentication_dependency_overridden": True,
                "network_server_used": False,
                "sealed_or_provisional_data_used": False,
                "official_accuracy_claim": False,
                "cases": cases,
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print(destination)


if __name__ == "__main__":
    main()
