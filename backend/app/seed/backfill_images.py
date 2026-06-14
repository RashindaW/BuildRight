"""Backfill licensed product images onto seeded MenuItems, grouped by category.

Run:  python -m app.seed.backfill_images

Rate-limit-safe: one API request per category (Unsplash demo tier = 50 req/hr),
each returning a small pool of photos that are shared + deterministically rotated
across that category's products. Requires IMAGE_PROVIDER + a key in the env;
otherwise it reports that nothing was done.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.menu import Category, MenuItem
from app.seed.image_provider import _stable_index, build_category_image_map

logger = logging.getLogger("app.seed.backfill_images")


def run(*, only_missing: bool = False) -> int:
    """Set MenuItem.image_url from licensed photos. Returns the number updated.

    only_missing=True touches only products without a real (non-placeholder) image.
    """
    db = SessionLocal()
    try:
        cat_slug = {c.id: c.slug for c in db.execute(select(Category)).scalars().all()}
        items = db.execute(select(MenuItem)).scalars().all()

        by_cat: dict[str, list[MenuItem]] = {}
        for it in items:
            if only_missing and str(it.image_url or "").startswith("https://images."):
                continue
            slug = cat_slug.get(it.category_id)
            if slug:
                by_cat.setdefault(slug, []).append(it)

        cat_map = build_category_image_map(sorted(by_cat))
        if not cat_map:
            logger.warning("no image provider configured (set IMAGE_PROVIDER + key) — nothing done")
            return 0

        updated = 0
        for slug, group in by_cat.items():
            pool = cat_map.get(slug)
            if not pool:
                continue
            for it in group:
                it.image_url = pool[_stable_index(it.slug, len(pool))]
                updated += 1
        db.commit()
        logger.info("backfilled %d product images across %d categories", updated, len(cat_map))
        return updated
    finally:
        db.close()


if __name__ == "__main__":
    from app.core.logging import setup_logging
    setup_logging()
    n = run()
    print(f"Backfilled {n} product images.")
