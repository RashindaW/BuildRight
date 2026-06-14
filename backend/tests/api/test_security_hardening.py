from __future__ import annotations

import uuid

import pytest

from app.core import lockout
from app.core.config import Settings
from app.core.lockout import MAX_FAILURES


def test_login_lockout_after_repeated_failures(client):
    lockout.reset()
    email = f"lock-{uuid.uuid4().hex[:8]}@example.com"  # need not exist; failures still lock
    try:
        for _ in range(MAX_FAILURES):
            r = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
            assert r.status_code == 401, r.text
        # now locked
        r = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "account_locked"
    finally:
        lockout.reset()


def test_successful_login_resets_failures(customer_client):
    # customer_client already logged in successfully during the fixture; its email is not locked.
    # Simulate a few failures then a success clears the counter.
    lockout.reset()
    email = f"reset-{uuid.uuid4().hex[:8]}@example.com"
    for _ in range(MAX_FAILURES - 1):
        lockout.record_failure(email)
    assert lockout.is_locked(email) == 0.0
    lockout.record_success(email)
    for _ in range(MAX_FAILURES - 1):
        lockout.record_failure(email)
    assert lockout.is_locked(email) == 0.0  # counter was reset, so still under threshold
    lockout.reset()


def test_weak_secret_rejected_in_production():
    with pytest.raises(Exception):
        Settings(environment="production", secret_key="changeme",
                 anthropic_api_key="x", database_url="sqlite:///./_t.db")


def test_short_secret_rejected_in_production():
    with pytest.raises(Exception):
        Settings(environment="production", secret_key="tooshort",
                 anthropic_api_key="x", database_url="sqlite:///./_t.db")


def test_strong_secret_ok_in_production():
    s = Settings(environment="production", secret_key="x" * 40,
                 anthropic_api_key="x", database_url="sqlite:///./_t.db")
    assert s.environment == "production"


def test_weak_secret_ok_in_dev():
    # dev/test may use a simple key
    s = Settings(environment="development", secret_key="changeme",
                 anthropic_api_key="x", database_url="sqlite:///./_t.db")
    assert s.is_dev
