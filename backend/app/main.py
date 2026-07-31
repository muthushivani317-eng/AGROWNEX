"""AgrowAI FastAPI application entry point.

Wires configuration, logging, CORS, the versioned API router, and the global
error handlers into a single app (docs/BACKEND_ARCHITECTURE.md).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.errors import register_exception_handlers
from app.api.probes import router as probes_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.http import close_http_client
from app.core.logging import configure_logging, get_logger, init_sentry
from app.core.metrics import MetricsMiddleware
from app.core.middleware import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    build_rate_limiter,
)
from app.legacy_joint import get_legacy_joint_runtime

configure_logging()
init_sentry()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The required crop-constrained legacy classifier is verified and loaded
    # exactly once. Failure aborts startup; there is no silent fallback.
    if settings.disease_model_required:
        get_legacy_joint_runtime().load()
    yield
    # Shutdown: release the shared pooled HTTP client.
    await close_http_client()


def create_app() -> FastAPI:
    # Fail fast on an unsafe production configuration (docs/SECURITY.md).
    settings.validate_production()

    # In production, debug is forced off and docs are hidden unless explicitly exposed.
    debug = settings.debug and not settings.is_production
    docs_visible = (not settings.is_production) or settings.expose_docs

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        debug=debug,
        docs_url="/docs" if docs_visible else None,
        redoc_url="/redoc" if docs_visible else None,
        openapi_url="/openapi.json" if docs_visible else None,
        lifespan=lifespan,
    )

    # NOTE: middleware runs in reverse order of registration (last added = outermost).
    # CORS innermost, then body-size, then rate limit, then security headers, then the
    # request-id wrapper outermost so every response — including 429/413 — is traceable.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=build_rate_limiter(),
        default_limit=settings.rate_limit_default,
        auth_limit=settings.rate_limit_auth,
        window=settings.rate_limit_window_seconds,
        auth_prefixes=(f"{settings.api_v1_prefix}/auth",),
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)
    app.include_router(probes_router)  # /healthz, /readyz at root for orchestrators
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    logger.info("AgrowAI API initialised (env=%s)", settings.environment)
    return app


app = create_app()
