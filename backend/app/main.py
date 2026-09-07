from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.db import engine
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_error_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.models import Base

MAX_BODY_BYTES = 1_000_000  # 1 MB

# Document.source_type values that come from knowledge_base/*.md. The generated buying-
# and category-guides deliberately do NOT count: they are built in memory, so they are
# present even when the policy corpus is missing entirely — which is exactly what masked
# the outage where the image shipped without knowledge_base/.
POLICY_SOURCE_TYPES = frozenset({"policy", "warranty", "shipping", "price-match", "faq"})

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"error": {"code": "too_large",
                                "message": "Request body too large"}})
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        response.headers["X-Request-ID"] = request.state.request_id
        if not settings.is_dev:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="BuildRight AI API", version="1.0.0",
                  docs_url="/docs" if settings.is_dev else None)

    # DB tables (dev convenience; prod uses Alembic)
    if settings.is_dev:
        Base.metadata.create_all(bind=engine)

    app.state.limiter = limiter
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        rid = getattr(request.state, "request_id", "")
        return JSONResponse(status_code=429, content={"error": {"code": "rate_limited",
                            "message": "Too many requests", "request_id": rid}})
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    # Routers
    from app.api.routers import (
        admin, admin_chat, analytics, auth, cart, chat, media, menu, orders, payments, reviews,
    )
    api_prefix = "/api/v1"
    for r in (auth.router, menu.router, reviews.router, cart.router, orders.router, chat.router,
              admin.router, admin_chat.router, payments.router, analytics.router, media.router):
        app.include_router(r, prefix=api_prefix)

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        # Per-provider status from the model registry: ready iff the DB is up and at
        # least one model's credentials resolve (Anthropic remains the backbone today).
        from app.ai.registry import registry
        providers = registry.provider_status()
        key_ok = bool(settings.anthropic_api_key.get_secret_value())
        any_model = any(providers.values()) if providers else key_ok

        # Knowledge-base integrity. A deployment that shipped without knowledge_base/
        # answers every policy question with "I don't have that information" while
        # product search keeps working, so it has to be visible on the probe instead of
        # in one startup log line. Only gates readiness in production — dev and test
        # routinely run against a partially seeded database.
        kb_by_type = _kb_counts() if db_ok else {}
        policy_docs = sum(n for t, n in kb_by_type.items() if t in POLICY_SOURCE_TYPES)
        kb_ok = policy_docs > 0
        ready_ = db_ok and any_model and (kb_ok or settings.environment != "production")
        return JSONResponse(
            status_code=status.HTTP_200_OK if ready_ else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "ready" if ready_ else "not_ready",
                "db": db_ok,
                "api_key": key_ok,          # kept for back-compat consumers
                "providers": providers,
                "knowledge_base": {
                    "ok": kb_ok,
                    "policy_documents": policy_docs,
                    "by_type": kb_by_type,
                },
            },
        )

    @app.get("/version")
    def version():
        return {"name": "BuildRight AI API", "version": "1.0.0", "environment": settings.environment}

    _mount_spa(app)
    return app


def _kb_counts() -> dict[str, int]:
    """{source_type: document count}. Never raises — a readiness probe must not 500."""
    try:
        from sqlalchemy import func, select

        from app.models.knowledge import Document
        with engine.connect() as conn:
            rows = conn.execute(
                select(Document.source_type, func.count(Document.id))
                .group_by(Document.source_type)
            ).all()
        return {str(t): int(n) for t, n in rows}
    except Exception:  # noqa: BLE001 - the table may not exist yet on a cold boot
        return {}


def _mount_spa(app: FastAPI, dist: Path | None = None) -> None:
    """Serve the built React SPA (frontend/dist) with history-API fallback,
    so the app runs single-origin in production. No-op if dist is absent.

    `dist` is injectable so the path-traversal containment tests can run against a
    throwaway bundle instead of needing a built frontend."""
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # Fully resolved: the containment check below compares resolved paths, so the
    # base must be resolved too (a symlinked dist would otherwise fail every check).
    dist = (dist or Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()
    if not dist.exists():
        return
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    index = dist / "index.html"

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith(("api/", "health", "version", "docs", "openapi")):
            return JSONResponse(status_code=404, content={"error": {"code": "not_found",
                                "message": "Not found"}})
        if not full_path:
            return FileResponse(index)
        # Containment check. `full_path` is attacker-controlled and is NOT normalized by
        # Starlette, so a percent-encoded traversal ("/..%2f..%2fbackend/.env") arrives
        # here with its "../" intact. Resolve the join and serve it only if it is still
        # inside dist — otherwise fall through to the SPA shell. Resolving also collapses
        # symlinks, so a link inside dist cannot point out of it either.
        try:
            candidate = (dist / full_path).resolve()
        except (OSError, ValueError):        # embedded NUL, name too long, ...
            return FileResponse(index)
        if candidate.is_relative_to(dist) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
