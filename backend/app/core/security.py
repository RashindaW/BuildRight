from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, HTTPException, Request, status
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---- JWT ----------------------------------------------------------------

def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": subject, "role": role, "exp": expire, "type": "access"},
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def create_refresh_token() -> tuple[str, str, datetime]:
    """Return (raw_token, jti, expires_at)."""
    jti = str(uuid.uuid4())
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return raw, jti, expires_at


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


# ---- CSRF ---------------------------------------------------------------

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(request: Request, csrf_token: str | None = Cookie(default=None)) -> None:
    header_token = request.headers.get(CSRF_HEADER)
    if not csrf_token or not header_token or not secrets.compare_digest(csrf_token, header_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token mismatch")
