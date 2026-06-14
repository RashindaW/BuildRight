"""Media endpoints — image search + OCR stock intake (vision calls mocked)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai import vision
from app.core.db import SessionLocal
from app.models.menu import MenuItem

_IMG = ("sheet.jpg", b"fake-image-bytes", "image/jpeg")


@pytest.fixture
def a_sku():
    db = SessionLocal()
    try:
        mi = db.execute(
            select(MenuItem).where(MenuItem.sku.is_not(None), MenuItem.is_available.is_(True))
        ).scalars().first()
        return {"id": mi.id, "sku": mi.sku, "name": mi.name}
    finally:
        db.close()


# ---- find-by-image (public) ----------------------------------------------

def test_find_by_image_returns_matches(client, monkeypatch):
    monkeypatch.setattr(vision, "describe_image_for_search", lambda *a, **k: "cordless drill")
    r = client.post("/api/v1/media/find-by-image", files={"file": _IMG})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == "cordless drill"
    assert isinstance(body["results"], list) and body["results"]


def test_find_by_image_unidentified(client, monkeypatch):
    monkeypatch.setattr(vision, "describe_image_for_search", lambda *a, **k: "")
    r = client.post("/api/v1/media/find-by-image", files={"file": _IMG})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_find_by_image_rejects_non_image(client):
    r = client.post("/api/v1/media/find-by-image",
                    files={"file": ("x.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_image"


# ---- OCR stock intake (staff) --------------------------------------------

def test_ocr_stock_requires_auth(client):
    r = client.post("/api/v1/media/ocr-stock", files={"file": _IMG})
    assert r.status_code == 401


def test_ocr_stock_forbidden_for_customer(customer_client):
    r = customer_client.post("/api/v1/media/ocr-stock", files={"file": _IMG})
    assert r.status_code == 403


def test_ocr_stock_preview_matches_skus(admin_client, a_sku, monkeypatch):
    monkeypatch.setattr(
        vision, "extract_stock_counts",
        lambda *a, **k: [{"item": a_sku["sku"], "qty": 42}, {"item": "no-such-item-xyz", "qty": 9}],
    )
    r = admin_client.post("/api/v1/media/ocr-stock", files={"file": _IMG})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched_count"] == 1
    matched = next(row for row in body["rows"] if row["matched"])
    assert matched["matched"]["sku"] == a_sku["sku"]
    assert matched["qty"] == 42


def test_stock_apply_updates_and_audits(admin_client, a_sku):
    r = admin_client.post(
        "/api/v1/media/stock/apply",
        json={"updates": [{"menu_item_id": a_sku["id"], "qty": 123}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1
    assert body["updated"][0]["new_stock"] == 123

    # Persisted, and an audit row was written.
    db = SessionLocal()
    try:
        mi = db.get(MenuItem, a_sku["id"])
        assert mi.stock_qty == 123
        from app.models.audit import AuditLog
        logged = db.execute(
            select(AuditLog).where(AuditLog.action == "stock_intake_apply",
                                   AuditLog.target == a_sku["id"])
        ).scalars().first()
        assert logged is not None
    finally:
        db.close()


def test_stock_apply_forbidden_for_customer(customer_client, a_sku):
    r = customer_client.post(
        "/api/v1/media/stock/apply",
        json={"updates": [{"menu_item_id": a_sku["id"], "qty": 1}]},
    )
    assert r.status_code == 403
