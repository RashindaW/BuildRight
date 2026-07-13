"""Type recovery from product names + the curated-photo backfill (isolated DB)."""

from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - register models
from app.models.base import Base
from app.models.menu import Category, MenuItem
from app.seed.image_provider import (
    _type_for_name,
    backfill_type_photos,
    load_type_images,
    type_slug,
)
from app.seed.seed import seed_menu


def test_type_recovered_from_generated_names():
    assert _type_for_name("power-tools", "Mastercraft 20V MAX Cordless Drill/Driver") == "Cordless Drill/Driver"
    assert _type_for_name("power-tools", 'ProBuilt 7-1/4" Circular Saw Pro Series') == "Circular Saw"
    # No match → None (item keeps its tile)
    assert _type_for_name("power-tools", "Completely Unrelated Widget") is None


def test_backfill_type_photos_idempotent_and_fallback_preserving():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        Base.metadata.create_all(engine)
        seed_menu(s)

        updated1, unmatched1 = backfill_type_photos(s)
        updated2, _ = backfill_type_photos(s)
        assert updated2 == 0, "second pass must be a no-op (idempotent)"

        pool = load_type_images()
        cat_slug = {c.id: c.slug for c in s.execute(select(Category)).scalars()}
        for it in s.execute(select(MenuItem)).scalars():
            t = _type_for_name(cat_slug.get(it.category_id, ""), it.name)
            if t and pool.get(type_slug(t)):
                assert (it.image_url or "").startswith("http"), f"{it.slug} should have a photo"
            else:
                # unmatched items keep their original (tile / same-origin) URL
                assert not (it.image_url or "").startswith("https://images.pexels")
    finally:
        s.close()
        engine.dispose()
        os.unlink(path)
