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


def backfill_images(products: list[dict], *, limit: int | None = None) -> int:
    """Fetch category-matched licensed photos for products that still use a
    placeholder. Requires a configured key; otherwise a no-op (returns 0).

    Network/rate-limit aware: caller passes a slice via `limit`. Returns the
    number of products updated in place (sets product['image_url']).
    """
    provider = _active_licensed_provider()
    if provider is None:
        return 0

    import httpx  # local import: only needed on the licensed path

    updated = 0
    targets = [p for p in products if str(p.get("image_url", "")).startswith("https://picsum.photos")]
    if limit is not None:
        targets = targets[:limit]

    with httpx.Client(timeout=10.0) as client:
        for p in targets:
            query = image_query_for(p["category"], p["name"])
            try:
                if provider == "unsplash":
                    url = _fetch_unsplash(client, query)
                else:
                    url = _fetch_pexels(client, query)
            except Exception:
                url = None
            if url:
                p["image_url"] = url
                updated += 1
    return updated


def _fetch_unsplash(client, query: str) -> str | None:
    key = settings.unsplash_access_key.get_secret_value()
    r = client.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": 1, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {key}"},
    )
    r.raise_for_status()
    results = r.json().get("results") or []
    return results[0]["urls"]["regular"] if results else None


def _fetch_pexels(client, query: str) -> str | None:
    key = settings.pexels_api_key.get_secret_value()
    r = client.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": 1, "orientation": "landscape"},
        headers={"Authorization": key},
    )
    r.raise_for_status()
    photos = r.json().get("photos") or []
    return photos[0]["src"]["large"] if photos else None
