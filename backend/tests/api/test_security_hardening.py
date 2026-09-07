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


# ---- SPA catch-all containment (CVE-class: pre-auth arbitrary file read) ------
#
# `/{full_path:path}` is joined onto frontend/dist. Starlette does NOT normalize the
# path parameter, so a percent-encoded traversal arrives with its "../" intact and
# `dist / full_path` escaped the bundle: "/..%2f..%2fbackend/.env" returned the raw
# file, and in the container /proc/self/environ and the SQLite DB were reachable too.

def _spa_app(tmp_path):
    """A bare app with the SPA mounted on a throwaway bundle, and a secret beside it."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.main import _mount_spa

    dist = tmp_path / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    # Two decoys, one per level above dist, so several traversal depths are true
    # positives rather than incidental misses.
    (tmp_path / "secret.env").write_text("ANTHROPIC_API_KEY=sk-ant-DO-NOT-LEAK", encoding="utf-8")
    (tmp_path / "frontend" / "secret.env").write_text("SECRET_KEY=DO-NOT-LEAK", encoding="utf-8")

    app = FastAPI()
    _mount_spa(app, dist=dist)
    return TestClient(app)


@pytest.mark.parametrize("path", [
    "/..%2fsecret.env",                    # escapes to frontend/secret.env
    "/..%2f..%2fsecret.env",               # escapes to the tmp root
    "/%2e%2e/secret.env",                  # dot-encoded
    "/assets%2f..%2f..%2fsecret.env",      # via the mounted assets prefix
    "/..%2F..%2FSECRET.ENV",               # uppercase escape + name
    "/../secret.env",                      # client-normalized; must stay safe too
    "/....//secret.env",
    "/..%2f..%2f..%2f..%2fetc/passwd",
])
def test_spa_route_refuses_path_traversal(tmp_path, path):
    r = _spa_app(tmp_path).get(path)
    # The invariant is CONTENT, not status: a request may be answered by the SPA shell
    # (catch-all) or rejected by the /assets StaticFiles mount — never with a file from
    # outside the bundle.
    assert r.status_code in (200, 404), r.status_code
    assert "DO-NOT-LEAK" not in r.text, f"{path} escaped the SPA bundle"
    assert "root:" not in r.text, f"{path} escaped the SPA bundle"
    if r.status_code == 200:
        assert r.text.startswith("<!doctype html"), "must fall through to the SPA shell"


def test_spa_route_still_serves_real_assets_and_history_fallback(tmp_path):
    client = _spa_app(tmp_path)
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/").text.startswith("<!doctype html")
    assert client.get("/checkout").text.startswith("<!doctype html")   # SPA route
