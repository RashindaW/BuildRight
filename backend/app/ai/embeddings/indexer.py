"""Embedding generation for products and knowledge-base chunks.

embed_products is idempotent via a stored content_hash + model_id on
ProductEmbedding: a product is re-embedded only when its canonical text or the
provider model changes.

embed_documents has no per-chunk hash column, so it simply skips chunks that
already carry an embedding. Re-embedding on content change is handled upstream
by seed_kb, which deletes and recreates a document's chunks (embedding=None)
whenever the source markdown changes — so changed content always gets fresh
vectors. This matches the 'safe to re-run' philosophy of seed.py.
"""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.provider import EmbeddingProvider
from app.models.knowledge import Document, DocumentChunk
from app.models.menu import MenuItem, Category
from app.models.product_embedding import ProductEmbedding

logger = logging.getLogger("app.ai.embeddings")


_EMBED_BATCH = 256  # cap provider calls so 10k+ corpora embed in bounded memory


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _embed_in_batches(provider: EmbeddingProvider, texts: list[str]) -> list:
    """Embed `texts` in batches (scales to large corpora without one giant call)."""
    out: list = []
    for i in range(0, len(texts), _EMBED_BATCH):
        out.extend(provider.embed_documents(texts[i:i + _EMBED_BATCH]))
    return out


def embed_products(db: Session, provider: EmbeddingProvider) -> int:
    """Embed all available menu items that are new or whose content changed."""
    items = db.execute(
        select(MenuItem, Category)
        .join(Category, Category.id == MenuItem.category_id)
        .where(MenuItem.is_available.is_(True))
    ).fetchall()

    texts, to_upsert = [], []
    for row in items:
        item, cat = row.MenuItem, row.Category
        keywords_str = " ".join(item.keywords or [])
        sku_str = f"SKU {item.sku}. " if item.sku else ""
        canonical = f"{sku_str}{item.name}. {cat.name}. {item.description or ''}. {keywords_str}".strip()
        h = _content_hash(canonical)

        existing = db.execute(
            select(ProductEmbedding).where(ProductEmbedding.menu_item_id == item.id)
        ).scalar_one_or_none()

        if existing and existing.content_hash == h and existing.model_id == provider.model_id:
            continue

        texts.append(canonical)
        to_upsert.append((item.id, h, existing))

    if not texts:
        return 0

    vectors = _embed_in_batches(provider, texts)
    for (item_id, h, existing), vec in zip(to_upsert, vectors):
        if existing:
            existing.embedding = vec
            existing.content_hash = h
            existing.model_id = provider.model_id
        else:
            db.add(ProductEmbedding(
                menu_item_id=item_id, embedding=vec,
                content_hash=h, model_id=provider.model_id,
            ))
    db.commit()
    logger.info("embed_products: upserted %d embeddings", len(to_upsert))
    return len(to_upsert)


def embed_one_product(db: Session, provider: EmbeddingProvider, item_id: str) -> bool:
    """Embed a single product on demand (e.g. right after an admin create/edit), so it
    enters the vector arm immediately without a full reseed. Idempotent via content_hash.

    Removes the embedding if the item is gone or unavailable. Returns True if a vector
    was written. Best-effort callers should wrap this in try/except — never block a write.
    """
    row = db.execute(
        select(MenuItem, Category)
        .join(Category, Category.id == MenuItem.category_id)
        .where(MenuItem.id == item_id)
    ).first()
    existing = db.execute(
        select(ProductEmbedding).where(ProductEmbedding.menu_item_id == item_id)
    ).scalar_one_or_none()

    # Item missing or unavailable → drop any stale vector so it leaves vector search.
    if row is None or not row.MenuItem.is_available:
        if existing:
            db.delete(existing)
            db.commit()
        return False

    item, cat = row.MenuItem, row.Category
    keywords_str = " ".join(item.keywords or [])
    sku_str = f"SKU {item.sku}. " if item.sku else ""
    canonical = f"{sku_str}{item.name}. {cat.name}. {item.description or ''}. {keywords_str}".strip()
    h = _content_hash(canonical)
    if existing and existing.content_hash == h and existing.model_id == provider.model_id:
        return False  # unchanged

    vec = provider.embed_documents([canonical])[0]
    if existing:
        existing.embedding = vec
        existing.content_hash = h
        existing.model_id = provider.model_id
    else:
        db.add(ProductEmbedding(
            menu_item_id=item_id, embedding=vec, content_hash=h, model_id=provider.model_id,
        ))
    db.commit()
    return True


def embed_documents(db: Session, provider: EmbeddingProvider) -> int:
    """Embed all document chunks that are new or whose content changed."""
    chunks = db.execute(
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
    ).fetchall()

    texts, to_update = [], []
    for row in chunks:
        chunk = row.DocumentChunk
        # No content_hash column on DocumentChunk: a chunk that already has an
        # embedding is skipped. seed_kb deletes+recreates chunks (embedding=None)
        # when the source doc changes, so changed content is always re-embedded.
        if chunk.embedding is not None:
            continue
        texts.append(chunk.content)
        to_update.append(chunk)

    if not texts:
        return 0

    vectors = _embed_in_batches(provider, texts)
    for chunk, vec in zip(to_update, vectors):
        chunk.embedding = vec
    db.commit()
    logger.info("embed_documents: updated %d chunk embeddings", len(to_update))
    return len(to_update)
