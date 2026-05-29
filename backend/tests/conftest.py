"""Test fixtures. Sets test env BEFORE importing the app so Settings + the DB
engine bind to an isolated temp SQLite database and a fake API key.
"""

from __future__ import annotations

import os
import tempfile

# --- must run before any `app.*` import ---
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-0123456789"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH_RATE_LIMIT"] = "1000/minute"
os.environ["CHAT_RATE_LIMIT"] = "1000/minute"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "AdminTestPass123!"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed.seed import seed_admin, seed_menu  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=engine)
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        seed_menu(db)
        seed_admin(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def _register(client: TestClient, email: str, password: str = "Password123!") -> dict:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.cookies


@pytest.fixture
def customer_client():
    """A TestClient authenticated as a fresh customer, with CSRF wired."""
    import uuid
    c = TestClient(app)
    email = f"cust-{uuid.uuid4().hex[:8]}@example.com"
    r = c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    assert r.status_code == 201, r.text
    csrf = c.cookies.get("csrf_token")
    c.headers.update({"x-csrf-token": csrf})
    return c


@pytest.fixture
def admin_client():
    c = TestClient(app)
    r = c.post("/api/v1/auth/login",
               json={"email": "admin@example.com", "password": "AdminTestPass123!"})
    assert r.status_code == 200, r.text
    csrf = c.cookies.get("csrf_token")
    c.headers.update({"x-csrf-token": csrf})
    return c
