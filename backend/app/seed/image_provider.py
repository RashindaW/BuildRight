"""Product imagery — licensed-API integration with an honest no-key fallback.

We do NOT scrape retailer sites (ToS / copyright / anti-bot). Instead:

- placeholder (default): a deterministic, stable image URL per product so the
  storefront always renders. No key, no network at seed time.
- unsplash / pexels: when an API key is configured, backfill_images() can fetch
  a category-matched, licensed photo per product (cached). This is a separate,
  rate-limited batch step — not run inline while generating 10k SKUs.

So a fresh catalog gets deterministic placeholders immediately, and real licensed
photos can be layered in later wherever a key exists. `image_query_for` exposes a
clean, category-aware search phrase the licensed fetch uses.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

# Per-TYPE images (e.g. all "Cordless Drill" variants share a real drill photo).
# Built once locally from Pexels (product_type_images.py) and COMMITTED, so the
# storefront gets title-matching images at seed time with zero API calls.
_TYPE_IMAGES_PATH = Path(__file__).with_name("type_images.json")


def type_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:90]


@lru_cache(maxsize=1)
def load_type_images() -> dict[str, list[str]]:
    try:
        return json.loads(_TYPE_IMAGES_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing/invalid file → fall back to placeholders
        return {}

# Category slug → a concrete, photographable search phrase for the licensed API.
_CATEGORY_IMAGE_QUERY = {
    "power-tools": "power drill tool",
    "hand-tools": "hand tools wrench",
    "fasteners": "screws bolts hardware",
    "hardware": "door hardware hinges",
    "automotive": "car engine oil garage",
    "kitchen": "kitchen appliance",
    "outdoor": "lawn mower garden equipment",
    "lawn-garden": "garden plants soil",
    "cleaning": "cleaning supplies bucket",
    "paint": "paint cans roller",
    "electrical": "electrical wire outlet",
    "plumbing": "plumbing pipe faucet",
    "lighting": "light bulb lamp",
    "building-materials": "lumber construction materials",
    "storage": "storage shelving bins",
    "safety": "safety gloves goggles",
    "heating-cooling": "fan heater appliance",
    "flooring": "wood flooring tile",
    "seasonal": "snow shovel winter",
    "sporting": "camping outdoor gear",
}


def image_query_for(category: str, name: str) -> str:
    """The search phrase a licensed image API should use for this product."""
    return _CATEGORY_IMAGE_QUERY.get(category, f"{category.replace('-', ' ')} hardware")


def placeholder_url(category: str, label: str) -> str:
    """Relative URL of the rendered SVG placeholder for a product.

    A category-coloured, icon + label tile served by /media/placeholder.svg —
    deterministic, offline, no files, and same-origin (resolves on HF and via the
    Vite dev proxy). Beats a random scenic stock photo on a hardware item.
    """
    # `v` cache-busts the year-long immutable cache when the tile art is redesigned.
    from urllib.parse import urlencode
    return "/api/v1/media/placeholder.svg?" + urlencode({"cat": category, "label": label, "v": "2"})


def image_url_for(category: str, type_name: str, slug: str) -> str:
    """Image URL stored on a product at generation time.

    Default: a clean per-TYPE SVG placeholder (category colour + icon + the product
    type). Real licensed photos are opt-in: set use_placeholder_images=False AND
    commit a per-TYPE pool in type_images.json. `type_name` is the catalog product
    TYPE (e.g. "Cordless Drill/Driver"), not the variant name.
    """
    if not settings.use_placeholder_images:
        pool = load_type_images().get(type_slug(type_name))
        if pool:
            return pool[_stable_index(slug, len(pool))]
    return placeholder_url(category, type_name)


def backfill_placeholder_images(db) -> int:
    """Point every existing product at its category SVG placeholder. Returns the
    count updated. Idempotent — safe to re-run on any DB (dev SQLite or Postgres)."""
    from sqlalchemy import select
    from app.models.menu import Category, MenuItem

    cat_slug = {c.id: c.slug for c in db.execute(select(Category)).scalars()}
    n = 0
    for item in db.execute(select(MenuItem)).scalars():
        url = placeholder_url(cat_slug.get(item.category_id, ""), item.name)
        if item.image_url != url:
            item.image_url = url
            n += 1
    db.commit()
    return n


def _active_licensed_provider() -> str | None:
    if settings.image_provider == "unsplash" and settings.unsplash_access_key:
        return "unsplash"
    if settings.image_provider == "pexels" and settings.pexels_api_key:
        return "pexels"
    return None


def _stable_index(slug: str, n: int) -> int:
    """Deterministic 0..n-1 from a slug (no Math.random / hash-seed surprises)."""
    return (sum(ord(c) for c in slug) % n) if n else 0


def build_category_image_map(categories, *, per_category: int = 10) -> dict[str, list[str]]:
    """Fetch a small pool of licensed photos PER CATEGORY in one request each.

    This is the rate-limit-safe strategy: ~20 requests total (one per category),
    each returning up to `per_category` photos, which are then shared+rotated
    across that category's products. Returns {category_slug: [url, ...]}.
    Requires a configured key; otherwise returns {}.
    """
    provider = _active_licensed_provider()
    if provider is None:
        return {}

    import httpx  # local import: only needed on the licensed path

    out: dict[str, list[str]] = {}
    with httpx.Client(timeout=15.0) as client:
        for cat in categories:
            query = image_query_for(cat, cat.replace("-", " "))
            try:
                if provider == "unsplash":
                    urls = _fetch_unsplash(client, query, per_category)
                else:
                    urls = _fetch_pexels(client, query, per_category)
            except Exception:  # rate limit / network — leave this category on placeholders
                urls = []
            if urls:
                out[cat] = urls
    return out


def backfill_images(products: list[dict], *, category_map: dict[str, list[str]] | None = None) -> int:
    """Assign licensed photos to products in place, grouped by category.

    Pass a prebuilt category_map, or one is fetched here. Each product gets a
    deterministic photo from its category's pool (stable per slug). Returns the
    number of products updated. No-op (0) when no key is configured.
    """
    if category_map is None:
        cats = sorted({p["category"] for p in products})
        category_map = build_category_image_map(cats)
    if not category_map:
        return 0

    updated = 0
    for p in products:
        pool = category_map.get(p["category"])
        if not pool:
            continue
        p["image_url"] = pool[_stable_index(p["id"], len(pool))]
        updated += 1
    return updated


def _fetch_unsplash(client, query: str, count: int = 10) -> list[str]:
    key = settings.unsplash_access_key.get_secret_value()
    r = client.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": count, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {key}"},
    )
    r.raise_for_status()
    return [p["urls"]["regular"] for p in (r.json().get("results") or [])]


def _fetch_pexels(client, query: str, count: int = 10) -> list[str]:
    key = settings.pexels_api_key.get_secret_value()
    r = client.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": count, "orientation": "landscape"},
        headers={"Authorization": key},
    )
    r.raise_for_status()
    return [p["src"]["large"] for p in (r.json().get("photos") or [])]
