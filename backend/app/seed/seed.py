"""Idempotent seed: loads the v1 menu from the root menu_data.py and provisions
a default admin. Safe to run repeatedly (upsert-by-slug; insert-if-absent).

Run with:  python -m app.seed
(after `alembic upgrade head` or create_all).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.models import Base
from app.models.menu import (
    Allergen,
    Category,
    DietaryTag,
    MenuItem,
    OptionChoice,
    OptionGroup,
)
from app.models.user import User

logger = logging.getLogger("app.seed")

_ROOT = Path(__file__).resolve().parents[3]
_IMG_DIR = _ROOT / "frontend" / "public" / "img" / "menu"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from menu_data import MENU_DATA  # noqa: E402

CATEGORY_LABELS = {
    "power-tools": "Power Tools",
    "hand-tools": "Hand Tools",
    "hardware": "Hardware & Fasteners",
    "automotive": "Automotive",
    "kitchen": "Kitchen Appliances",
    "outdoor": "Outdoor & Garden",
    "cleaning": "Cleaning",
    "paint": "Paint & Coatings",
    "electrical": "Electrical",
    "plumbing": "Plumbing",
    "seasonal": "Seasonal",
}

DIETARY_LABELS = {
    "cordless": "Cordless",
    "corded": "Corded",
    "battery-powered": "Battery-Powered",
    "outdoor": "Outdoor Use",
    "indoor": "Indoor Use",
    "professional": "Professional Grade",
    "sale": "On Sale",
    "new-arrival": "New Arrival",
}

ALLERGEN_LABELS = {
    "requires-assembly": "Requires Assembly",
    "flammable": "Flammable",
    "contains-battery": "Contains Battery",
    "heavy-item": "Heavy Item",
    "sharp-blade": "Sharp Blade",
    "power-tool": "Power Tool",
}


def _get_or_create(db: Session, model, slug: str, **defaults):
    obj = db.execute(select(model).where(model.slug == slug)).scalar_one_or_none()
    if obj is None:
        obj = model(slug=slug, **defaults)
        db.add(obj)
        db.flush()
    return obj


def seed_menu(db: Session, menu_data: list[dict] | None = None) -> int:
    menu_data = menu_data if menu_data is not None else MENU_DATA

    for slug, label in CATEGORY_LABELS.items():
        _get_or_create(db, Category, slug, name=label, display_order=0)
    for slug, label in DIETARY_LABELS.items():
        _get_or_create(db, DietaryTag, slug, label=label)
    for slug, label in ALLERGEN_LABELS.items():
        _get_or_create(db, Allergen, slug, label=label)
    db.flush()

    count = 0
    for entry in menu_data:
        cat = _get_or_create(
            db, Category, entry["category"],
            name=CATEGORY_LABELS.get(entry["category"], entry["category"].title()),
        )
        item = db.execute(
            select(MenuItem).where(MenuItem.slug == entry["id"])
        ).scalar_one_or_none()
        price_cents = round(float(entry["price"]) * 100)
        if item is None:
            item = MenuItem(
                slug=entry["id"],
                name=entry["name"],
                description=entry["description"],
                price_cents=price_cents,
                category_id=cat.id,
                keywords=list(entry.get("keywords", [])),
                calories=entry.get("calories"),
                spice_level=entry.get("spice_level", 0),
                is_available=True,
                featured=entry.get("featured", False),
                image_url=entry.get("image_url"),
            )
            db.add(item)
            db.flush()
            count += 1
            # Options/modifiers — only on first insert (avoids duplicate groups on re-seed)
            for grp in entry.get("options", []):
                og = OptionGroup(
                    menu_item_id=item.id, name=grp["name"],
                    min_select=grp.get("min_select", 0),
                    max_select=grp.get("max_select", 1),
                    required=grp.get("required", False),
                )
                db.add(og)
                db.flush()
                for ch in grp["choices"]:
                    db.add(OptionChoice(
                        option_group_id=og.id, name=ch["name"],
                        price_delta_cents=round(float(ch.get("price_delta", 0)) * 100),
                        is_default=ch.get("is_default", False),
                    ))
        # (re)attach dietary tags
        tags = [
            _get_or_create(db, DietaryTag, t, label=DIETARY_LABELS.get(t, t.title()))
            for t in entry.get("dietary_tags", [])
        ]
        item.dietary_tags = tags
        # allergens (extended menu)
        if entry.get("allergens"):
            item.allergens = [
                _get_or_create(db, Allergen, a, label=ALLERGEN_LABELS.get(a, a.title()))
                for a in entry["allergens"]
            ]
        # Auto-wire a downloaded photo if present (refreshed every seed).
        # Files live in frontend/public/img/menu/<slug>.jpg (gitignored).
        if entry.get("image_url"):
            item.image_url = entry["image_url"]
        elif (_IMG_DIR / f"{entry['id']}.jpg").exists():
            item.image_url = f"menu/{entry['id']}.jpg"

    db.commit()
    return count


def seed_admin(db: Session) -> bool:
    email = settings.admin_email.lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return False
    admin = User(
        email=email,
        hashed_password=hash_password(settings.admin_password.get_secret_value()),
        full_name="Administrator",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return True


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        n = seed_menu(db)
        made_admin = seed_admin(db)

        from app.seed.seed_kb import ingest_knowledge_base
        n_chunks = ingest_knowledge_base(db)

        # Embeddings power the vector arm of hybrid retrieval. If the embedding
        # backend can't load (e.g. onnxruntime missing its native runtime on this
        # host), log loudly and continue: the catalog + KB are already committed and
        # retrieval degrades to the lexical arm. Set EMBEDDING_PROVIDER=hash for a
        # download-free deterministic fallback.
        n_prod_embs = n_chunk_embs = 0
        try:
            from app.ai.embeddings.provider import get_embedding_provider
            from app.ai.embeddings.indexer import embed_products, embed_documents
            provider = get_embedding_provider()
            n_prod_embs = embed_products(db, provider)
            n_chunk_embs = embed_documents(db, provider)
        except Exception:
            logger.exception(
                "embedding step failed — catalog/KB seeded WITHOUT vectors; "
                "hybrid search will run lexical-only until embeddings are built"
            )
            print(
                "WARNING: embeddings could not be generated (see logs). The catalog "
                "and knowledge base were seeded; semantic/vector search is disabled "
                "until the embedding backend works (try EMBEDDING_PROVIDER=hash)."
            )

        logger.info(
            "seed complete: %d items, %d KB chunks, %d product embs, %d chunk embs, admin=%s",
            n, n_chunks, n_prod_embs, n_chunk_embs, made_admin,
        )
        print(
            f"Seed complete: {n} new items | {n_chunks} KB chunks | "
            f"{n_prod_embs} product embeddings | {n_chunk_embs} chunk embeddings | "
            f"admin_created={made_admin}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
