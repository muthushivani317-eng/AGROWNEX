"""Security gate: every API route must authenticate, unless explicitly public.

A new endpoint without `CurrentUser` / admin context / partner key / reviewer
role fails this test. To make a route public on purpose, add it to
PUBLIC_ROUTES with a reason -- that line is then visible in code review.
"""
from __future__ import annotations

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.main import create_app
from app.modules.auth.dependencies import CurrentUser

AUTH_DEPENDENCIES = {
    "get_current_user",  # farmer Firebase token
    "get_admin_context",  # admin: MFA + RBAC (+ cookie CSRF)
    "get_partner_api_key_context",  # FPO partner feed key
    "HTTPBearer",
}

# (method, path) -> reason. Keep this list short.
PUBLIC_ROUTES = {
    ("POST", "/api/v1/auth/otp/send"): "pre-login; Firebase sends the SMS; rate-limited",
    ("POST", "/api/v1/auth/otp/verify"): "login: verifies a Firebase ID token",
    ("POST", "/api/v1/auth/google"): "login: verifies a Firebase ID token",
    ("POST", "/api/v1/auth/apple"): "login: verifies a Firebase ID token",
    ("POST", "/api/v1/auth/refresh"): "hashed single-use refresh token",
    ("GET", "/api/v1/health"): "liveness",
    ("GET", "/api/v1/health/ready"): "readiness",
    ("GET", "/health"): "liveness",
    ("GET", "/healthz"): "liveness",
    ("GET", "/ready"): "readiness",
    ("GET", "/readyz"): "readiness",
    ("GET", "/metrics"): "constant-time X-Metrics-Token check in handler",
    ("POST", "/api/v1/market/backup/ingest"): "constant-time X-Market-Ingest-Token check",
    ("GET", "/api/v1/market/sync-status"): "public freshness of public market prices",
    ("GET", "/api/v1/produce/traceability/public/{token}"): "256-bit revocable share token, no PII",
    ("GET", "/api/v1/crops"): "static crop catalogue",
    ("GET", "/api/v1/crops/{crop_id}"): "static crop catalogue",
    ("GET", "/api/v1/crops/{crop_id}/capabilities"): "static crop catalogue",
    ("GET", "/api/v1/models/status"): "public model readiness flags",
    ("GET", "/api/v1/crop-identification/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/crop-identity-six-class-internal/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/crop-identity/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/banana/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/banana/version"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/chilli/restricted-health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/cotton/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/cotton/version"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/crop-identification/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/groundnut/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/groundnut/version"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/paddy/health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/paddy/version"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/disease/redgram/restricted-health"): "model runtime probe, no farmer data",
    ("GET", "/api/v1/plant-identifier/health"): "model runtime probe, no farmer data",
}


def _dependency_names(dependant, acc: set[str]) -> set[str]:
    for sub in dependant.dependencies:
        call = sub.call
        acc.add(getattr(call, "__name__", type(call).__name__))
        _dependency_names(sub, acc)
    return acc


def _routes():
    app = create_app()
    out = []
    for route in app.routes:
        contexts = getattr(route, "effective_route_contexts", None)
        if contexts is not None:  # FastAPI >= 0.13x lazily included routers
            for ctx in contexts():
                if ctx.dependant is not None:
                    out.extend((m, ctx.path, ctx.dependant) for m in ctx.methods or ())
        elif isinstance(route, APIRoute):
            out.extend((m, route.path, route.dependant) for m in route.methods)
    return out


ROUTES = _routes()


def test_inventory_is_not_empty():
    assert len(ROUTES) > 300


def _is_authenticated(dependant) -> bool:
    # Role/permission guards (require_any_role, reviewer roles, ...) all sit on
    # top of get_current_user, so an explicit match here is required.
    return bool(_dependency_names(dependant, set()) & AUTH_DEPENDENCIES)


@pytest.mark.parametrize("method,path,dependant", ROUTES, ids=[f"{m} {p}" for m, p, _ in ROUTES])
def test_route_requires_authentication(method, path, dependant):
    if (method, path) in PUBLIC_ROUTES:
        return
    assert _is_authenticated(dependant), (
        f"{method} {path} has no authentication dependency. Add CurrentUser/AdminContextDep, "
        "or list it in PUBLIC_ROUTES with a reason."
    )


def test_public_allowlist_has_no_stale_entries():
    live = {(m, p) for m, p, _ in ROUTES}
    assert set(PUBLIC_ROUTES) <= live, set(PUBLIC_ROUTES) - live


def test_gate_detects_an_unauthenticated_route():
    router = APIRouter()

    @router.get("/leak")
    async def leak():
        return {}

    @router.get("/safe")
    async def safe(user: CurrentUser):
        return {}

    leak_route, safe_route = router.routes
    assert not _is_authenticated(leak_route.dependant)
    assert _is_authenticated(safe_route.dependant)
