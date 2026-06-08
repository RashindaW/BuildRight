"""VectorIndex abstraction: pgvector (Postgres) or numpy cosine (SQLite/fallback).

Both backends return the same dataclass shapes so the hybrid retrieval module
can be database-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.db import engine


@dataclass
class ProductHit:
    item_dict: dict     # exact menu_adapter shape — flows into _serialize + price validator
    similarity: float


@dataclass
class ChunkHit:
    chunk_id: str
    document_id: str
    doc_slug: str
    doc_title: str
    heading: str | None
    content: str
    similarity: float


def _pgvector_available() -> bool:
    try:
        import pgvector.sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


class PgVectorIndex:
    """Cosine search using pgvector <=> operator (1 - cosine_similarity = cosine_distance)."""

    def search_products(
        self, db: Session, query_vec: list[float], k: int = 20, available_only: bool = True
    ) -> list[ProductHit]:
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import text

        sql = text("""
            SELECT mi.id, mi.slug, mi.name, mi.description,
                   mi.price_cents, c.slug AS category,
                   mi.is_available, mi.featured, mi.image_url,
                   mi.keywords,
                   (1 - (pe.embedding <=> CAST(:qvec AS vector))) AS similarity
            FROM product_embeddings pe
            JOIN menu_items mi ON mi.id = pe.menu_item_id
            JOIN categories c ON c.id = mi.category_id
            WHERE (:available_only = FALSE OR mi.is_available = TRUE)
              AND pe.embedding IS NOT NULL
            ORDER BY pe.embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """)
        rows = db.execute(sql, {
            "qvec": str(query_vec),
            "available_only": available_only,
            "k": k,
        }).fetchall()
        return [
            ProductHit(item_dict=_row_to_item_dict(r, db), similarity=float(r.similarity))
            for r in rows
        ]

    def search_chunks(
        self, db: Session, query_vec: list[float], k: int = 8, doc_types: list[str] | None = None
    ) -> list[ChunkHit]:
        from sqlalchemy import text

        type_filter = "AND d.source_type = ANY(:doc_types)" if doc_types else ""
        sql = text(f"""
            SELECT dc.id, dc.document_id, d.slug, d.title, dc.heading, dc.content,
                   (1 - (dc.embedding <=> CAST(:qvec AS vector))) AS similarity
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.embedding IS NOT NULL {type_filter}
            ORDER BY dc.embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """)
        params: dict = {"qvec": str(query_vec), "k": k}
        if doc_types:
            params["doc_types"] = doc_types
        rows = db.execute(sql, params).fetchall()
        return [
            ChunkHit(
                chunk_id=r.id, document_id=r.document_id, doc_slug=r.slug,
                doc_title=r.title, heading=r.heading, content=r.content,
                similarity=float(r.similarity),
            )
            for r in rows
        ]


class NumpyVectorIndex:
    """In-Python cosine similarity over JSON-stored embeddings (SQLite fallback)."""

    def search_products(
        self, db: Session, query_vec: list[float], k: int = 20, available_only: bool = True
    ) -> list[ProductHit]:
        import numpy as np
        from sqlalchemy import select
        from app.models.product_embedding import ProductEmbedding
        from app.models.menu import MenuItem, Category

        stmt = (
            select(ProductEmbedding, MenuItem, Category)
            .join(MenuItem, MenuItem.id == ProductEmbedding.menu_item_id)
            .join(Category, Category.id == MenuItem.category_id)
            .where(ProductEmbedding.embedding.is_not(None))
        )
        if available_only:
            stmt = stmt.where(MenuItem.is_available.is_(True))

        rows = db.execute(stmt).fetchall()
        if not rows:
            return []

        q = np.array(query_vec, dtype=np.float32)
        embeddings = np.array([r.ProductEmbedding.embedding for r in rows], dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normed = embeddings / norms
        q_norm = q / (np.linalg.norm(q) or 1.0)
        sims = normed @ q_norm

        top_idx = np.argsort(-sims)[:k]
        result = []
        for idx in top_idx:
            r = rows[idx]
            result.append(ProductHit(
                item_dict=_menu_item_to_dict(r.MenuItem, r.Category),
                similarity=float(sims[idx]),
            ))
        return result

    def search_chunks(
        self, db: Session, query_vec: list[float], k: int = 8, doc_types: list[str] | None = None
    ) -> list[ChunkHit]:
        import numpy as np
        from sqlalchemy import select
        from app.models.knowledge import Document, DocumentChunk

        stmt = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.is_not(None))
        )
        if doc_types:
            stmt = stmt.where(Document.source_type.in_(doc_types))

        rows = db.execute(stmt).fetchall()
        if not rows:
            return []

        q = np.array(query_vec, dtype=np.float32)
        embeddings = np.array([r.DocumentChunk.embedding for r in rows], dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normed = embeddings / norms
        q_norm = q / (np.linalg.norm(q) or 1.0)
        sims = normed @ q_norm

        top_idx = np.argsort(-sims)[:k]
        result = []
        for idx in top_idx:
            r = rows[idx]
            dc = r.DocumentChunk
            d = r.Document
            result.append(ChunkHit(
                chunk_id=dc.id, document_id=dc.document_id, doc_slug=d.slug,
                doc_title=d.title, heading=dc.heading, content=dc.content,
                similarity=float(sims[idx]),
            ))
        return result


def _menu_item_to_dict(item, category) -> dict:
    """Convert MenuItem ORM row to the shape expected by _serialize + price validator."""
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "description": item.description or "",
        "price": item.price_cents / 100,
        "category": category.slug,
        "dietary_tags": [t.slug for t in item.dietary_tags] if item.dietary_tags else [],
        "allergens": [a.slug for a in item.allergens] if item.allergens else [],
        "keywords": list(item.keywords or []),
        "is_available": item.is_available,
        "featured": item.featured,
        "image_url": item.image_url,
    }


def _row_to_item_dict(row, db: Session) -> dict:
    """Convert a raw SQL row (from PgVectorIndex) to item dict."""
    from sqlalchemy import select
    from app.models.menu import MenuItem, Category
    item = db.get(MenuItem, row.id)
    if item is None:
        return {"id": row.id, "name": row.name, "price": row.price_cents / 100,
                "description": row.description or "", "category": row.category,
                "dietary_tags": [], "allergens": [], "keywords": list(row.keywords or [])}
    cat = db.execute(select(Category).where(Category.id == item.category_id)).scalar_one()
    return _menu_item_to_dict(item, cat)


_index_instance: PgVectorIndex | NumpyVectorIndex | None = None


def get_vector_index() -> PgVectorIndex | NumpyVectorIndex:
    global _index_instance
    if _index_instance is None:
        if engine.dialect.name == "postgresql" and _pgvector_available():
            _index_instance = PgVectorIndex()
        else:
            _index_instance = NumpyVectorIndex()
    return _index_instance
