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
from app.core.config import settings
from app.models.knowledge import Document, DocumentChunk

logger = logging.getLogger("app.seed.kb")

_ROOT = Path(__file__).resolve().parents[3]
_KB_DIR = _ROOT / "knowledge_base"

_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


class KnowledgeBaseMissingError(RuntimeError):
    """The policy/FAQ corpus is absent — a packaging defect, not a normal state.

    When it happened, the deployed image had no knowledge_base/ directory: the seed
    logged one warning, carried on, and the app served 195 generated buying guides and
    ZERO policy documents. Product questions worked, every policy question answered
    "I don't have that information", and nothing else reported a problem.
    """


def _missing_corpus(msg: str) -> None:
    """Raise (default) or warn, per settings.require_knowledge_base."""
    if settings.require_knowledge_base:
        raise KnowledgeBaseMissingError(
            f"{msg} Policy answers would silently degrade to 'contact customer service'. "
            f"Set REQUIRE_KNOWLEDGE_BASE=false to seed without the policy corpus."
        )
    logger.warning("%s Skipping the KB seed (REQUIRE_KNOWLEDGE_BASE=false).", msg)

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
        _missing_corpus(f"knowledge_base/ not found at {_KB_DIR} — the deployment did not "
                        f"ship the policy corpus (check the Dockerfile COPY lines).")
        return 0

    md_files = sorted(_KB_DIR.glob("*.md"))
    if not md_files:
        _missing_corpus(f"no .md files in {_KB_DIR} — the policy corpus is empty.")
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


def ingest_category_guides(db: Session) -> int:
    """Generate + upsert richer per-category guides (tables + prose). Returns chunk count."""
    from app.seed.category_guides import generate_category_guides

    total = 0
    for g in generate_category_guides():
        total += _upsert_document(db, g["slug"], g["title"], "category-guide", g["text"])
    db.commit()
    logger.info("seed_kb: ingested category guides -> %d chunks", total)
    return total
