from __future__ import annotations

import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, message: str, code: str = "error", status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found", "not_found", status.HTTP_404_NOT_FOUND)


class ForbiddenError(AppError):
    def __init__(self, msg: str = "Forbidden") -> None:
        super().__init__(msg, "forbidden", status.HTTP_403_FORBIDDEN)


class AuthError(AppError):
    def __init__(self, msg: str = "Authentication required") -> None:
        super().__init__(msg, "auth_error", status.HTTP_401_UNAUTHORIZED)


def _error_response(status_code: int, code: str, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    return _error_response(exc.status_code, exc.code, exc.message, rid)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi.exceptions import RequestValidationError
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    errors = exc.errors() if isinstance(exc, RequestValidationError) else [str(exc)]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "validation_error", "message": "Validation failed", "details": errors, "request_id": rid}},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    return _error_response(500, "internal_error", "An unexpected error occurred", rid)
