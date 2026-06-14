"""Idempotent seed for BuildRight Hardware.

Loads the curated catalog (root menu_data.py), generates a large realistic catalog
(catalog_generator, ~1000+ products with SKUs), ingests the policy knowledge base,
builds embeddings, and provisions the admin + demo accounts (with backdated order
history so the memory/reorder demo works out of the box).

Run with:  python -m app.seed   (after `alembic upgrade head` or create_all)
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
import uuid
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
from app.seed.catalog_generator import (
    CATEGORIES as _GEN_CATEGORIES,
    CATEGORY_LABELS as _GEN_CATEGORY_LABELS,
    generate_products,
)

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
    **_GEN_CATEGORY_LABELS,  # adds fasteners, lawn-garden, lighting, building-materials, storage, etc.
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

_CAT_CODE = {c["slug"]: c["code"] for c in _GEN_CATEGORIES}


def _get_or_create(db: Session, model, slug: str, **defaults):
    obj = db.execute(select(model).where(model.slug == slug)).scalar_one_or_none()
    if obj is None:
        obj = model(slug=slug, **defaults)
        db.add(obj)
        db.flush()
    return obj


def _auto_sku(slug: str, category: str, used: set[str]) -> str:
    """Deterministic, realistic SKU for a curated item that has none.

    Curated items occupy the 90000-98999 range so they never collide with the
    generated catalog (which uses ~10000-50000)."""
    code = _CAT_CODE.get(category) or (re.sub(r"[^A-Z]", "", category.upper() + "XXX")[:3] or "GEN")
    num = int(hashlib.md5(slug.encode()).hexdigest()[:6], 16) % 9000 + 90000
    sku = f"BR-{code}-{num:05d}"
    while sku in used:
        num = (num - 89999) % 9000 + 90000
        sku = f"BR-{code}-{num:05d}"
    used.add(sku)
    return sku


def seed_menu(db: Session, menu_data: list[dict] | None = None) -> int:
    """Seed the curated catalog (root menu_data.py). Assigns SKUs + stock."""
    menu_data = menu_data if menu_data is not None else MENU_DATA

    for slug, label in CATEGORY_LABELS.items():
        _get_or_create(db, Category, slug, name=label, display_order=0)
    for slug, label in DIETARY_LABELS.items():
        _get_or_create(db, DietaryTag, slug, label=label)
    for slug, label in ALLERGEN_LABELS.items():
        _get_or_create(db, Allergen, slug, label=label)
    db.flush()

    used_skus = {s for s in db.execute(select(MenuItem.sku)).scalars().all() if s}

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
        sku = entry.get("sku") or _auto_sku(entry["id"], entry["category"], used_skus)
        if item is None:
            item = MenuItem(
                slug=entry["id"],
                sku=sku,
                name=entry["name"],
                description=entry["description"],
                price_cents=price_cents,
                cost_cents=round(float(entry["cost"]) * 100) if entry.get("cost") is not None else round(price_cents * 0.62),
                category_id=cat.id,
                keywords=list(entry.get("keywords", [])),
                calories=entry.get("calories"),
                spice_level=entry.get("spice_level", 0),
                is_available=entry.get("is_available", True),
                stock_qty=int(entry.get("stock", 60)),
                featured=entry.get("featured", False),
                image_url=entry.get("image_url"),
            )
            db.add(item)
            db.flush()
            count += 1
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
        else:
            if not item.sku:
                item.sku = sku
            if not item.stock_qty:
                item.stock_qty = int(entry.get("stock", 60))

        tags = [
            _get_or_create(db, DietaryTag, t, label=DIETARY_LABELS.get(t, t.title()))
            for t in entry.get("dietary_tags", [])
        ]
        item.dietary_tags = tags
        if entry.get("allergens"):
            item.allergens = [
                _get_or_create(db, Allergen, a, label=ALLERGEN_LABELS.get(a, a.title()))
                for a in entry["allergens"]
            ]
        if entry.get("image_url"):
            item.image_url = entry["image_url"]
        elif (_IMG_DIR / f"{entry['id']}.jpg").exists():
            item.image_url = f"menu/{entry['id']}.jpg"

    db.commit()
    return count


def seed_catalog(db: Session, products: list[dict] | None = None) -> int:
    """Bulk-seed the large generated catalog (~1000+ products with SKUs).

    Idempotent: skips products whose slug or SKU already exists. One commit.
    """
    products = products if products is not None else generate_products()

    cat_by_slug = {
        slug: _get_or_create(db, Category, slug, name=label, display_order=0)
        for slug, label in CATEGORY_LABELS.items()
    }
    tag_slugs = {t for p in products for t in p.get("dietary_tags", [])}
    alg_slugs = {a for p in products for a in p.get("allergens", [])}
    tag_by = {s: _get_or_create(db, DietaryTag, s, label=DIETARY_LABELS.get(s, s.title())) for s in tag_slugs}
    alg_by = {s: _get_or_create(db, Allergen, s, label=ALLERGEN_LABELS.get(s, s.title())) for s in alg_slugs}
    db.flush()

    existing_slugs = set(db.execute(select(MenuItem.slug)).scalars().all())
    existing_skus = {s for s in db.execute(select(MenuItem.sku)).scalars().all() if s}

    count = 0
    for p in products:
        if p["id"] in existing_slugs or p["sku"] in existing_skus:
            continue
        cat = cat_by_slug.get(p["category"]) or _get_or_create(
            db, Category, p["category"], name=p["category"].replace("-", " ").title()
        )
        item = MenuItem(
            slug=p["id"],
            sku=p["sku"],
            name=p["name"],
            description=p["description"],
            price_cents=round(float(p["price"]) * 100),
            cost_cents=round(float(p["cost"]) * 100) if p.get("cost") is not None else None,
            category_id=cat.id,
            keywords=list(p.get("keywords", [])),
            is_available=p.get("is_available", True),
            stock_qty=int(p.get("stock", 0)),
            featured=p.get("featured", False),
        )
        item.dietary_tags = [tag_by[t] for t in p.get("dietary_tags", [])]
        item.allergens = [alg_by[a] for a in p.get("allergens", [])]
        db.add(item)
        existing_slugs.add(p["id"])
        existing_skus.add(p["sku"])
        count += 1

    db.commit()
    logger.info("seed_catalog: inserted %d generated products", count)
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


# ---- Demo accounts + backdated order history ------------------------------

_DEMO_USERS = [
    {
        "email": "demo@buildright.com",
        "password": "Demo1234!",
        "name": "Dana Demo",
        "prefs": {"preferred_brand": "Mastercraft", "favourite_category": "power-tools"},
        "orders": [
            {"days_ago": 6, "status": "placed", "source": "chat", "picks": [("paint", 2), ("cleaning", 1)]},
            {"days_ago": 24, "status": "completed", "picks": [("power-tools", 1), ("fasteners", 2)]},
            {"days_ago": 72, "status": "completed", "source": "chat", "picks": [("hand-tools", 1), ("electrical", 1)]},
        ],
    },
    {
        "email": "pro@buildright.com",
        "password": "ProDemo1234!",
        "name": "Pat Pro",
        "prefs": {"preferred_brand": "ProBuilt", "account_type": "contractor"},
        "orders": [
            {"days_ago": 9, "status": "placed", "source": "chat", "picks": [("power-tools", 1), ("safety", 3)]},
            {"days_ago": 38, "status": "completed", "picks": [("building-materials", 10), ("fasteners", 4)]},
        ],
    },
    {
        "email": "staff@buildright.com",
        "password": "StaffDemo1234!",
        "name": "Sam Staff",
        "role": "store_helper",
        "prefs": {},
        "orders": [],
    },
    {
        "email": "manager@buildright.com",
        "password": "ManagerDemo1234!",
        "name": "Morgan Manager",
        "role": "manager",
        "prefs": {},
        "orders": [],
    },
]


def _pick_item(db: Session, category: str) -> MenuItem | None:
    return db.execute(
        select(MenuItem)
        .join(Category, Category.id == MenuItem.category_id)
        .where(Category.slug == category, MenuItem.is_available.is_(True))
        .order_by(MenuItem.featured.desc(), MenuItem.slug)
    ).scalars().first()


def seed_demo_accounts(db: Session) -> int:
    """Create demo customers with preferences + backdated paid orders."""
    from datetime import datetime, timedelta, timezone
    from app.models.chat import Conversation
    from app.models.order import Order, OrderItem
    from app.models.user_memory import UserPreference

    now = datetime.now(tz=timezone.utc)
    created = 0

    for spec in _DEMO_USERS:
        email = spec["email"].lower()
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            continue
        user = User(
            email=email,
            hashed_password=hash_password(spec["password"]),
            full_name=spec["name"],
            role=spec.get("role", "customer"),
            is_active=True,
        )
        db.add(user)
        db.flush()

        for k, v in spec["prefs"].items():
            db.add(UserPreference(user_id=user.id, key=k, value=v, source="seed"))

        for o in spec["orders"]:
            when = now - timedelta(days=o["days_ago"])
            order_source = o.get("source", "web")
            conv_id = None
            if order_source == "chat":
                # a chat conversation drove this order (for the AI-attribution dashboard)
                conv = Conversation(user_id=user.id, created_at=when, updated_at=when)
                db.add(conv)
                db.flush()
                conv_id = conv.id
            order = Order(
                order_number=f"CD-{uuid.uuid4().hex[:10].upper()}",
                user_id=user.id,
                source=order_source,
                conversation_id=conv_id,
                status=o["status"],
                payment_status="paid",
                subtotal_cents=0,
                total_cents=0,
                amount_paid_cents=0,
                currency="cad",
                created_at=when,
                updated_at=when,
            )
            db.add(order)
            db.flush()
            subtotal = 0
            for category, qty in o["picks"]:
                mi = _pick_item(db, category)
                if not mi:
                    continue
                line = mi.price_cents * qty
                subtotal += line
                db.add(OrderItem(
                    order_id=order.id,
                    menu_item_id=mi.id,
                    name_snapshot=mi.name,
                    unit_price_cents=mi.price_cents,
                    quantity=qty,
                    line_total_cents=line,
                ))
            order.subtotal_cents = subtotal
            order.total_cents = subtotal
            order.amount_paid_cents = subtotal

        created += 1

    db.commit()
    return created


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        n_curated = seed_menu(db)
        n_catalog = seed_catalog(db)
        made_admin = seed_admin(db)
        n_demo = seed_demo_accounts(db)

        from app.seed.seed_kb import ingest_knowledge_base
        n_chunks = ingest_knowledge_base(db)

        # Embeddings power the vector arm of hybrid retrieval. The provider auto-falls
        # back to the deterministic 'hash' provider if fastembed/onnxruntime can't load,
        # so the pipeline is always populated; on a host where fastembed works the
        # vectors are fully semantic with no code change.
        n_prod_embs = n_chunk_embs = 0
        try:
            from app.ai.embeddings.provider import get_embedding_provider
            from app.ai.embeddings.indexer import embed_products, embed_documents
            provider = get_embedding_provider()
            n_prod_embs = embed_products(db, provider)
            n_chunk_embs = embed_documents(db, provider)
        except Exception:
            logger.exception("embedding step failed — catalog/KB seeded WITHOUT vectors")
            print("WARNING: embeddings could not be generated (see logs). Lexical search still works.")

        total_items = n_curated + n_catalog
        logger.info(
            "seed complete: %d items (%d curated + %d generated), %d KB chunks, "
            "%d product embs, %d chunk embs, admin=%s, demo_accounts=%d",
            total_items, n_curated, n_catalog, n_chunks, n_prod_embs, n_chunk_embs, made_admin, n_demo,
        )
        print(
            f"Seed complete: {total_items} products ({n_curated} curated + {n_catalog} generated) | "
            f"{n_chunks} KB chunks | {n_prod_embs} product embeddings | {n_chunk_embs} chunk embeddings | "
            f"admin_created={made_admin} | demo_accounts={n_demo}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
