"""Role hierarchy guard tests (keyless)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.deps import require_min_role, require_admin, require_manager, require_staff
from app.core.errors import ForbiddenError
from app.models.user import ROLE_RANK


@dataclass
class _User:
    role: str


def test_role_rank_order():
    assert ROLE_RANK["customer"] < ROLE_RANK["store_helper"] < ROLE_RANK["manager"] < ROLE_RANK["admin"]


@pytest.mark.parametrize("role,allowed", [
    ("customer", False), ("store_helper", False), ("manager", True), ("admin", True),
])
def test_require_manager(role, allowed):
    dep = require_manager
    if allowed:
        assert dep(_User(role)).role == role
    else:
        with pytest.raises(ForbiddenError):
            dep(_User(role))


@pytest.mark.parametrize("role,allowed", [
    ("customer", False), ("store_helper", True), ("manager", True), ("admin", True),
])
def test_require_staff(role, allowed):
    if allowed:
        assert require_staff(_User(role)).role == role
    else:
        with pytest.raises(ForbiddenError):
            require_staff(_User(role))


def test_require_admin_only_admin():
    assert require_admin(_User("admin")).role == "admin"
    for r in ("customer", "store_helper", "manager"):
        with pytest.raises(ForbiddenError):
            require_admin(_User(r))


def test_require_min_role_unknown_role_denied():
    # a stray/unknown role is treated as lowest privilege
    with pytest.raises(ForbiddenError):
        require_min_role("manager")(_User("bogus"))
