"""Build the committed per-TYPE image map from a licensed API (run once locally).

    IMAGE_PROVIDER=pexels PEXELS_API_KEY=... python -m app.seed.product_type_images

For each catalog product TYPE (~195), fetch a couple of photos via Pexels (free
tier 200/hr → one pass) and write `type_images.json` next to this file. Commit
that JSON: the storefront then serves title-matching images at seed time with
ZERO API calls (works on Hugging Face's ephemeral, key-free runtime).

Idempotent / resumable: types already present in the JSON are skipped, so a
rate-limit interruption can be re-run to finish.
"""

from __future__ import annotations

import json
import logging

from app.seed.catalog_generator import CATEGORIES
from app.seed.image_provider import (
    _TYPE_IMAGES_PATH,
    _active_licensed_provider,
    _fetch_pexels,
    _fetch_unsplash,
    type_slug,
)

logger = logging.getLogger("app.seed.type_images")


def _type_query(type_name: str) -> str:
    """A clean image search phrase from the type name (drop variant suffix)."""
    return type_name.split("/")[0].strip().lower()


def _distinct_types() -> list[tuple[str, str]]:
    out, seen = [], set()
    for cat in CATEGORIES:
        for ptype in cat["types"]:
            ts = type_slug(ptype["name"])
            if ts not in seen:
                seen.add(ts)
                out.append((ts, _type_query(ptype["name"])))
    return out


def build_and_save(per_type: int = 2) -> int:
    """Fetch + persist per-type images. Returns the number of NEW types added."""
    provider = _active_licensed_provider()
    if provider is None:
        print("No image provider configured. Set IMAGE_PROVIDER=pexels and PEXELS_API_KEY.")
        return 0

    import httpx

    out: dict[str, list[str]] = {}
    if _TYPE_IMAGES_PATH.exists():
        try:
            out = json.loads(_TYPE_IMAGES_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            out = {}

    types = _distinct_types()
    added = 0
    with httpx.Client(timeout=20.0) as client:
        for ts, query in types:
            if out.get(ts):  # resume: already have it
                continue
            try:
                urls = (_fetch_pexels(client, query, per_type) if provider == "pexels"
                        else _fetch_unsplash(client, query, per_type))
            except Exception as e:  # noqa: BLE001 - rate limit / network; keep what we have
                logger.warning("type image fetch failed for %s (%s): %s", ts, query, type(e).__name__)
                urls = []
            if urls:
                out[ts] = urls
                added += 1

    _TYPE_IMAGES_PATH.write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    print(f"type_images.json: {len(out)}/{len(types)} types ({added} new) -> {_TYPE_IMAGES_PATH}")
    return added


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_and_save()
