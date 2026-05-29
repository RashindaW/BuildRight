from __future__ import annotations

import uuid

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
    app = FastAPI(title="Cut_Dry API", version="1.0.0",
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
    from app.api.routers import admin, auth, cart, chat, menu, orders
    api_prefix = "/api/v1"
    for r in (auth.router, menu.router, cart.router, orders.router, chat.router, admin.router):
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
        key_ok = bool(settings.anthropic_api_key.get_secret_value())
        ready_ = db_ok and key_ok
        return JSONResponse(
            status_code=status.HTTP_200_OK if ready_ else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "ready" if ready_ else "not_ready", "db": db_ok, "api_key": key_ok},
        )

    @app.get("/version")
    def version():
        return {"name": "Cut_Dry API", "version": "1.0.0", "environment": settings.environment}

    return app


app = create_app()
