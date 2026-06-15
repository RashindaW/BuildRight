"""Idempotent knowledge-base seeder.

Reads all *.md files from knowledge_base/ at the repo root, upserts Documents +
DocumentChunks (without embeddings — embed_documents handles those separately).
Safe to run repeatedly: version increments and chunks are rebuilt when the file changes.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.chunking import chunk_document
from app.models.knowledge import Document, DocumentChunk

logger = logging.getLogger("app.seed.kb")

_ROOT = Path(__file__).resolve().parents[3]
_KB_DIR = _ROOT / "knowledge_base"

_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

_SOURCE_TYPE_MAP = {
    "returns": "policy",
    "refunds": "policy",
    "warranty": "warranty",
    "shipping-delivery": "shipping",
    "price-match": "price-match",
    "faq": "faq",
    "store-policies": "policy",
}


def _extract_title(text: str, fallback: str) -> str:
    m = _H1_RE.search(text)
    return m.group(1).strip() if m else fallback


def _upsert_document(db: Session, slug: str, title: str, source_type: str,
                     text: str, source_path: str | None = None) -> int:
    """Upsert one Document + its chunks (embeddings handled separately). Returns chunk count."""
    doc = db.execute(select(Document).where(Document.slug == slug)).scalar_one_or_none()
    if doc is None:
        doc = Document(slug=slug, title=title, source_type=source_type, source_path=source_path)
        db.add(doc)
        db.flush()
    else:
        doc.title = title
        doc.source_type = source_type
        doc.source_path = source_path
        doc.version += 1
        for old in list(doc.chunks):
            db.delete(old)
        db.flush()

    raw_chunks = chunk_document(text)
    for rc in raw_chunks:
        db.add(DocumentChunk(
            document_id=doc.id, chunk_index=rc.chunk_index,
            heading=rc.heading, content=rc.content, token_count=rc.token_count,
        ))
    return len(raw_chunks)


def ingest_knowledge_base(db: Session) -> int:
    """Upsert all KB markdown docs and their chunks. Returns total chunks written."""
    if not _KB_DIR.exists():
        logger.warning("knowledge_base/ directory not found at %s — skipping KB seed", _KB_DIR)
        return 0

    md_files = sorted(_KB_DIR.glob("*.md"))
    if not md_files:
        logger.warning("No .md files found in %s", _KB_DIR)
        return 0

    total = 0
    for md_path in md_files:
        slug = md_path.stem
        text = md_path.read_text(encoding="utf-8")
        title = _extract_title(text, fallback=slug.replace("-", " ").title())
        source_type = _SOURCE_TYPE_MAP.get(slug, "policy")
        source_path = str(md_path.relative_to(_ROOT))
        n = _upsert_document(db, slug, title, source_type, text, source_path)
        total += n
        logger.info("seed_kb: %s -> %d chunks", slug, n)

    db.commit()
    return total


def ingest_buying_guides(db: Session) -> int:
    """Generate + upsert per-type product buying guides (in-memory, no files). Returns chunk count."""
    from app.seed.product_guides import generate_guides

    total = 0
    for g in generate_guides():
        total += _upsert_document(db, g["slug"], g["title"], "buying-guide", g["text"])
    db.commit()
    logger.info("seed_kb: ingested buying guides -> %d chunks", total)
    return total
