"""Embedding generation for products and knowledge-base chunks.

Both functions are idempotent: they skip rows whose content hasn't changed
(using a content hash) and whose model_id matches the current provider.
This matches the 'safe to re-run' philosophy of seed.py.
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


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


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
        canonical = f"{item.name}. {item.description or ''}. {keywords_str}".strip()
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

    vectors = provider.embed_documents(texts)
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
    logger.info('"embed_products: upserted %d embeddings"', len(to_upsert))
    return len(to_upsert)


def embed_documents(db: Session, provider: EmbeddingProvider) -> int:
    """Embed all document chunks that are new or whose content changed."""
    chunks = db.execute(
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
    ).fetchall()

    texts, to_update = [], []
    for row in chunks:
        chunk = row.DocumentChunk
        h = _content_hash(chunk.content)
        if chunk.embedding is not None and _content_hash(chunk.content) == h:
            continue
        texts.append(chunk.content)
        to_update.append(chunk)

    if not texts:
        return 0

    vectors = provider.embed_documents(texts)
    for chunk, vec in zip(to_update, vectors):
        chunk.embedding = vec
    db.commit()
    logger.info('"embed_documents: updated %d chunk embeddings"', len(to_update))
    return len(to_update)
