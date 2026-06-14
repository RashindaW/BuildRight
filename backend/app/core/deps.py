from __future__ import annotations

from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException, status
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


def require_min_role(min_role: str):
    """Dependency factory enforcing a minimum access tier (hierarchy:
    customer < store_helper < manager < admin)."""
    from app.models.user import ROLE_RANK

    def _dep(user=Depends(get_current_user)):
        if ROLE_RANK.get(user.role, -1) < ROLE_RANK[min_role]:
            raise ForbiddenError(f"{min_role.replace('_', ' ')} access or higher required")
        return user

    return _dep


# Role-tier guards (admin ⊇ manager ⊇ store_helper ⊇ customer).
require_staff = require_min_role("store_helper")   # store_helper, manager, admin
require_manager = require_min_role("manager")      # manager, admin
require_admin = require_min_role("admin")          # admin only


def get_owned_or_404(resource_user_id: str, current_user) -> None:
    if current_user.role == "admin":
        return
    if str(current_user.id) != str(resource_user_id):
        raise NotFoundError()


@dataclass
class Actor:
    """The owner of a cart/order: a logged-in user OR an anonymous guest session."""
    user_id: str | None = None
    session_id: str | None = None

    @property
    def is_guest(self) -> bool:
        return self.user_id is None

    def owns(self, *, user_id: str | None, session_id: str | None) -> bool:
        """True if this actor owns a resource carrying the given user_id/session_id."""
        if self.user_id is not None:
            return user_id is not None and str(user_id) == str(self.user_id)
        return session_id is not None and session_id == self.session_id


def get_actor(
    x_session_id: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Actor:
    """Resolve the cart/order owner: the authenticated user if logged in, else the
    guest identified by the x-session-id header. Used by cart/order/payment routes so
    guests can shop and check out without an account."""
    user = get_optional_user(access_token, db)
    if user:
        return Actor(user_id=user.id, session_id=None)
    if not x_session_id:
        raise AuthError("A session is required to use the cart. Please reload the page.")
    return Actor(user_id=None, session_id=x_session_id)


class Pagination:
    def __init__(self, page: int = 1, page_size: int = 20) -> None:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
