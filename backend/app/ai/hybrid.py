"""Hybrid retrieval via Reciprocal Rank Fusion (RRF).

Two arms per search:
  - Lexical: keyword scoring (retrieval._score_item / _score_chunk)
  - Vector:  fastembed query embedding → VectorIndex

RRF formula: score(d) = Σ 1/(k + rank(d)) across all ranked lists.
k=60 is the standard constant (Cormack et al. 2009).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.ai.retrieval import _score_item, _tokenize
from app.ai.embeddings.vector_index import ChunkHit, get_vector_index
from app.core.config import settings

logger = logging.getLogger("app.ai.hybrid")


def reciprocal_rank_fusion(
    ranked_lists: list[list[Any]],
    key_fn: Callable[[Any], Any],
    k: int | None = None,
) -> list[tuple[Any, float]]:
    """Fuse ranked lists via RRF.

    ranked_lists: each sub-list ordered best-first.
    key_fn: extracts a hashable deduplication key from each item.
    k: RRF constant (defaults to settings.rrf_k).
    Returns: [(item, rrf_score)] sorted descending by score.
    """
    if k is None:
        k = settings.rrf_k
    scores: dict[Any, float] = {}
    first_seen: dict[Any, Any] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            key = key_fn(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in first_seen:
                first_seen[key] = item

    return sorted(
        ((first_seen[key], scores[key]) for key in scores),
        key=lambda t: t[1],
        reverse=True,
    )


def _item_slug(d: dict) -> str:
    """Slug from either menu_adapter shape (id=slug) or vector_index shape (slug=...)."""
    return str(d.get("slug") or d.get("id") or "")


def hybrid_search_products(
    db: Session,
    query: str,
    filters: dict | None = None,
    k: int | None = None,
) -> list[dict]:
    """Hybrid product search: lexical + vector → RRF → top-k item dicts.

    filters keys (all optional):
        category (str), tags (list[str]), max_price (float), in_stock_only (bool)
    k defaults to settings.rag_top_k.

    Returns items in menu_adapter shape so they flow into _serialize + validate_response.
    """
    from app.ai.menu_adapter import get_menu_for_assistant
    from app.ai.embeddings.provider import get_embedding_provider

    if k is None:
        k = settings.rag_top_k
    filters = filters or {}
    available_only = filters.get("in_stock_only", True)
    pool = get_menu_for_assistant(db, available_only=available_only)

    if filters.get("category"):
        pool = [i for i in pool if i["category"] == filters["category"]]
    for tag in filters.get("tags") or []:
        pool = [i for i in pool if tag in i.get("dietary_tags", [])]
    if filters.get("max_price") is not None:
        pool = [i for i in pool if i["price"] <= float(filters["max_price"])]

    slug_lookup = {_item_slug(i): i for i in pool}

    tokens = _tokenize(query) if query.strip() else []
    if tokens:
        lexical_scored = [(i, _score_item(i, tokens)) for i in pool]
        lexical_ranked = [
            i for i, s in sorted(
                ((i, s) for i, s in lexical_scored if s > 0),
                key=lambda t: t[1], reverse=True,
            )
        ]
    else:
        lexical_ranked = []

    vector_ranked: list[dict] = []
    if query.strip():
        try:
            qvec = get_embedding_provider().embed_query(query)
            hits = get_vector_index().search_products(
                db, qvec, k=min(k * 2, 40), available_only=available_only
            )
            for hit in hits:
                slug = _item_slug(hit.item_dict)
                if slug in slug_lookup:
                    vector_ranked.append(slug_lookup[slug])
        except Exception:
            logger.exception("product vector arm failed for query=%r; lexical-only", query)

    if not lexical_ranked and not vector_ranked:
        return []

    fused = reciprocal_rank_fusion(
        [lexical_ranked, vector_ranked],
        key_fn=_item_slug,
    )
    return [item for item, _ in fused[:k]]


def _score_chunk(hit: ChunkHit, tokens: list[str]) -> int:
    """Lexical score for a ChunkHit. Heading matches are weighted 3×."""
    if not tokens:
        return 0
    score = 0
    content_lower = hit.content.lower()
    heading_lower = (hit.heading or "").lower()
    for tok in tokens:
        if tok in heading_lower:
            score += 3
        if tok in content_lower:
            score += 1
    return score


def hybrid_search_kb(
    db: Session,
    query: str,
    k: int | None = None,
    doc_types: list[str] | None = None,
) -> list[ChunkHit]:
    """Hybrid KB search: lexical + vector → RRF → top-k ChunkHits.

    doc_types: filter by Document.source_type (e.g. ["policy", "warranty"]).
    k defaults to settings.kb_top_k.
    ChunkHits carry doc_slug, doc_title, heading, content for citations.
    """
    from sqlalchemy import select
    from app.models.knowledge import Document, DocumentChunk
    from app.ai.embeddings.provider import get_embedding_provider

    if k is None:
        k = settings.kb_top_k

    stmt = (
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
    )
    if doc_types:
        stmt = stmt.where(Document.source_type.in_(doc_types))
    rows = db.execute(stmt).fetchall()

    chunk_map: dict[str, ChunkHit] = {}
    for row in rows:
        dc = row.DocumentChunk
        d = row.Document
        chunk_map[dc.id] = ChunkHit(
            chunk_id=dc.id,
            document_id=dc.document_id,
            doc_slug=d.slug,
            doc_title=d.title,
            heading=dc.heading,
            content=dc.content,
            similarity=0.0,
        )

    tokens = _tokenize(query) if query.strip() else []
    if tokens:
        lexical_scored = [(h, _score_chunk(h, tokens)) for h in chunk_map.values()]
        lexical_ranked = [
            h for h, s in sorted(
                ((h, s) for h, s in lexical_scored if s > 0),
                key=lambda t: t[1], reverse=True,
            )
        ]
    else:
        lexical_ranked = []

    vector_ranked: list[ChunkHit] = []
    if query.strip():
        try:
            qvec = get_embedding_provider().embed_query(query)
            hits = get_vector_index().search_chunks(
                db, qvec, k=min(k * 3, 24), doc_types=doc_types
            )
            for hit in hits:
                if hit.chunk_id in chunk_map:
                    vector_ranked.append(chunk_map[hit.chunk_id])
        except Exception:
            logger.exception("KB vector arm failed for query=%r; lexical-only", query)

    if not lexical_ranked and not vector_ranked:
        return []

    fused = reciprocal_rank_fusion(
        [lexical_ranked, vector_ranked],
        key_fn=lambda h: h.chunk_id,
    )
    return [hit for hit, _ in fused[:k]]
