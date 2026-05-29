from __future__ import annotations

import hashlib

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AuthError
from app.core.rate_limit import limiter
from app.core.security import (
    CSRF_COOKIE,
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import CsrfOut, LoginIn, RegisterIn, UserOut
from app.schemas.common import MessageResponse
from app.services import audit_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user: User, db: Session) -> str:
    access = create_access_token(user.id, user.role)
    raw_refresh, jti, expires_at = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, jti=jti,
        token_hash=hashlib.sha256(raw_refresh.encode()).hexdigest(),
        expires_at=expires_at,
    ))
    db.commit()
    csrf = generate_csrf_token()
    secure = settings.cookie_secure
    samesite = "lax"
    response.set_cookie("access_token", access, httponly=True, secure=secure,
                        samesite=samesite, max_age=settings.access_token_expire_minutes * 60)
    response.set_cookie("refresh_token", f"{jti}.{raw_refresh}", httponly=True, secure=secure,
                        samesite=samesite, max_age=settings.refresh_token_expire_days * 86400,
                        path="/api/v1/auth")
    # CSRF cookie is readable by JS (double-submit pattern).
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=secure, samesite=samesite)
    return csrf


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
def register(request: Request, body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        from app.core.errors import AppError
        raise AppError("Email already registered", "email_taken", 409)
    user = User(email=email, hashed_password=hash_password(body.password),
                full_name=body.full_name, role="customer")
    db.add(user)
    db.commit()
    db.refresh(user)
    _set_auth_cookies(response, user, db)
    audit_service.log(db, "user.register", actor_id=user.id, target=email,
                      ip=request.client.host if request.client else None)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
@limiter.limit(settings.auth_rate_limit)
def login(request: Request, body: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("Account disabled")
    _set_auth_cookies(response, user, db)
    audit_service.log(db, "user.login", actor_id=user.id, target=email,
                      ip=request.client.host if request.client else None)
    return UserOut.model_validate(user)


@router.post("/refresh", response_model=MessageResponse)
def refresh(response: Response, refresh_token: str | None = Cookie(default=None),
            db: Session = Depends(get_db)):
    if not refresh_token or "." not in refresh_token:
        raise AuthError("No refresh token")
    jti, raw = refresh_token.split(".", 1)
    rt = db.execute(select(RefreshToken).where(RefreshToken.jti == jti)).scalar_one_or_none()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    if not rt or rt.revoked or rt.token_hash != token_hash:
        raise AuthError("Invalid refresh token")
    rt.revoked = True  # rotation
    db.commit()
    user = db.get(User, rt.user_id)
    if not user or not user.is_active:
        raise AuthError()
    _set_auth_cookies(response, user, db)
    return MessageResponse(message="refreshed")


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response, refresh_token: str | None = Cookie(default=None),
           db: Session = Depends(get_db)):
    if refresh_token and "." in refresh_token:
        jti = refresh_token.split(".", 1)[0]
        rt = db.execute(select(RefreshToken).where(RefreshToken.jti == jti)).scalar_one_or_none()
        if rt:
            rt.revoked = True
            db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE)
    return MessageResponse(message="logged out")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.get("/csrf", response_model=CsrfOut)
def get_csrf(response: Response):
    csrf = generate_csrf_token()
    secure = settings.cookie_secure
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=secure, samesite="lax")
    return CsrfOut(csrf_token=csrf)
