from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AuthError, ForbiddenError, NotFoundError
from app.core.security import decode_access_token


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    from app.models.user import User
    if not access_token:
        raise AuthError()
    payload = decode_access_token(access_token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError()
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthError()
    return user


def get_optional_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """Return user or None — used for optional-auth endpoints."""
    if not access_token:
        return None
    try:
        return get_current_user(access_token, db)
    except (AuthError, HTTPException):
        return None


def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise ForbiddenError("Admin access required")
    return user


def get_owned_or_404(resource_user_id: str, current_user) -> None:
    if current_user.role == "admin":
        return
    if str(current_user.id) != str(resource_user_id):
        raise NotFoundError()


class Pagination:
    def __init__(self, page: int = 1, page_size: int = 20) -> None:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
