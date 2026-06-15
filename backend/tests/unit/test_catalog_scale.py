"""Catalog generator scaling + image provider (deterministic, offline)."""

from __future__ import annotations

from app.seed.catalog_generator import generate_products
from app.seed.image_provider import backfill_images, image_query_for, image_url_for


def test_default_catalog_is_curated_scale():
    products = generate_products()
    assert 900 <= len(products) <= 2000
    assert len({p["sku"] for p in products}) == len(products)       # unique SKUs
    assert all(p.get("image_url") for p in products)


def test_scaled_catalog_reaches_10k():
    products = generate_products(target=10000)
    assert len(products) == 10000
    assert len({p["sku"] for p in products}) == 10000               # unique SKUs
    assert len({p["id"] for p in products}) == 10000                # unique slugs
    assert all(p.get("image_url") for p in products)


def test_generation_is_deterministic():
    a = generate_products(target=3000)
    b = generate_products(target=3000)
    assert [p["sku"] for p in a] == [p["sku"] for p in b]


def test_image_url_is_category_placeholder_by_default():
    # Default: a deterministic category SVG placeholder carrying the cat + label.
    u1 = image_url_for("paint", "Interior Paint", "some-slug")
    u2 = image_url_for("paint", "Interior Paint", "some-slug")
    assert u1 == u2
    assert u1.startswith("/api/v1/media/placeholder.svg")
    assert "cat=paint" in u1 and "Interior" in u1


def test_image_url_uses_committed_type_image_when_opted_in(monkeypatch):
    from app.core.config import settings
    from app.seed.image_provider import load_type_images
    if not load_type_images():
        return  # type_images.json not built in this env — nothing to assert
    monkeypatch.setattr(settings, "use_placeholder_images", False)
    u = image_url_for("paint", "Interior Paint", "interior-paint")
    assert u.startswith("http")  # a committed licensed photo, not the SVG placeholder


def test_image_query_for_known_category():
    assert image_query_for("power-tools", "Cordless Drill")  # non-empty phrase


def test_backfill_is_noop_without_key():
    products = [{"category": "paint", "name": "x", "image_url": "https://picsum.photos/seed/x/600/400"}]
    assert backfill_images(products) == 0  # placeholder provider → no fetch
