from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def _email():
    return f"u-{uuid.uuid4().hex[:8]}@example.com"


def test_register_sets_cookies_and_returns_user():
    c = TestClient(app)
    email = _email()
    r = c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    assert r.status_code == 201
    assert r.json()["email"] == email
    assert r.json()["role"] == "customer"
    assert "access_token" in r.cookies


def test_duplicate_email_rejected():
    c = TestClient(app)
    email = _email()
    c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    r = c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    assert r.status_code == 409


def test_login_wrong_password_401():
    c = TestClient(app)
    email = _email()
    c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_auth():
    c = TestClient(app)
    assert c.get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user():
    c = TestClient(app)
    email = _email()
    c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    r = c.get("/api/v1/auth/me")
    assert r.status_code == 200 and r.json()["email"] == email


def test_weak_password_rejected():
    c = TestClient(app)
    r = c.post("/api/v1/auth/register", json={"email": _email(), "password": "short"})
    assert r.status_code == 422


def test_extra_fields_forbidden():
    c = TestClient(app)
    r = c.post("/api/v1/auth/register",
               json={"email": _email(), "password": "Password123!", "role": "admin"})
    assert r.status_code == 422  # extra="forbid" blocks privilege-escalation via mass assignment
