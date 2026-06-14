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

from app.core.config import settings

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


def _placeholder_url(slug: str) -> str:
    # Deterministic, stable per product (Lorem Picsum seeds on the slug).
    return f"https://picsum.photos/seed/{slug}/600/400"


def image_url_for(category: str, name: str, slug: str) -> str:
    """Return an image URL to store on the product at generation time.

    Always deterministic and offline — real licensed photos (when a key is set)
    are layered in later by backfill_images(), not here.
    """
    return _placeholder_url(slug)


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
