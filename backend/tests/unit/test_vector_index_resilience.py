"""Regression: one chunk without a usable vector must not disable the vector arm.

Failure chain that was live in the dev database:
  1. `_upsert_document` writes chunks with no embedding (the seed vectorises them in a
     later pass), and the runtime pdf/OCR ingest never ran that pass.
  2. `EmbeddingType` used SQLAlchemy's JSON default (`none_as_null=False`), so the
     missing vector was stored as the JSON string 'null' — which the query's
     `WHERE embedding IS NOT NULL` does NOT filter out.
  3. np.array() over the resulting ragged list raised, hybrid.py caught it broadly, and
     EVERY knowledge-base query silently fell back to lexical-only.

One row was enough to turn off half the retriever, invisibly.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy import text as sqltext

from app.ai.embeddings.vector_index import _with_usable_vectors
from app.core.db import SessionLocal, engine
from app.models.knowledge import Document, DocumentChunk

sqlite_only = pytest.mark.skipif(
    engine.dialect.name != "sqlite",
    reason="storage representation (and this bug) are SQLite/JSON specific; "
           "on pgvector a missing vector is a real SQL NULL",
)


def _row(vec):
    return SimpleNamespace(DocumentChunk=SimpleNamespace(embedding=vec))


# ---- the guard itself (no DB, runs on every dialect) ------------------------

def test_usable_filter_keeps_only_correctly_sized_vectors():
    rows = [_row([0.1] * 384), _row(None), _row([0.2] * 512), _row([0.3] * 384)]
    kept = _with_usable_vectors(rows, "DocumentChunk", 384)
    assert len(kept) == 2
    assert all(len(r.DocumentChunk.embedding) == 384 for r in kept)


def test_usable_filter_is_a_no_op_when_everything_is_valid():
    rows = [_row([0.1] * 384), _row([0.2] * 384)]
    assert _with_usable_vectors(rows, "DocumentChunk", 384) == rows


def test_usable_filter_warns_so_degradation_is_not_silent(caplog):
    with caplog.at_level("WARNING", logger="app.ai.embeddings.vector_index"):
        _with_usable_vectors([_row(None), _row([0.1] * 384)], "DocumentChunk", 384)
    assert any("skipped 1/2" in r.getMessage() for r in caplog.records), caplog.text


# ---- end-to-end against the real column type --------------------------------

@pytest.fixture
def kb_doc():
    """A document with one embedded chunk and one that was never vectorised."""
    db = SessionLocal()
    doc = Document(slug=f"probe-{uuid.uuid4().hex[:8]}", title="Probe", source_type="manual")
    db.add(doc)
    db.flush()
    db.add(DocumentChunk(document_id=doc.id, chunk_index=0, heading="Embedded",
                         content="cordless drill torque specification",
                         embedding=[0.1] * 384))
    db.add(DocumentChunk(document_id=doc.id, chunk_index=1, heading="Not embedded",
                         content="chuck size and battery runtime"))
    db.commit()
    yield db, doc
    db.delete(doc)          # cascades to the chunks
    db.commit()
    db.close()


@sqlite_only
def test_missing_vector_is_stored_as_sql_null(kb_doc):
    """none_as_null=True — otherwise 'null' is stored as TEXT and defeats IS NOT NULL."""
    db, doc = kb_doc
    typ, is_null = db.execute(sqltext(
        "SELECT typeof(embedding), embedding IS NULL FROM document_chunks "
        "WHERE document_id = :d AND chunk_index = 1"), {"d": doc.id}).one()
    assert typ == "null"
    assert bool(is_null) is True


def test_unembedded_chunk_does_not_break_the_arm(kb_doc):
    pytest.importorskip("numpy")
    from app.ai.embeddings.vector_index import NumpyVectorIndex

    db, doc = kb_doc
    hits = NumpyVectorIndex().search_chunks(db, [0.1] * 384, k=10)
    headings = {h.heading for h in hits}
    assert "Embedded" in headings, "the vectorised chunk must still be retrievable"
    assert "Not embedded" not in headings


@sqlite_only
def test_legacy_json_null_row_is_skipped_not_fatal(kb_doc):
    """Rows written BEFORE the none_as_null fix still read back as a JSON null."""
    pytest.importorskip("numpy")
    from app.ai.embeddings.vector_index import NumpyVectorIndex

    db, doc = kb_doc
    db.execute(sqltext("UPDATE document_chunks SET embedding = 'null' "
                       "WHERE document_id = :d AND chunk_index = 1"), {"d": doc.id})
    db.commit()
    hits = NumpyVectorIndex().search_chunks(db, [0.1] * 384, k=10)
    assert "Embedded" in {h.heading for h in hits}


@sqlite_only
def test_mis_sized_vector_is_skipped(kb_doc):
    """A vector left over from a different provider/dim must not go ragged either."""
    pytest.importorskip("numpy")
    from app.ai.embeddings.vector_index import NumpyVectorIndex

    db, doc = kb_doc
    chunk = db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id,
                                    DocumentChunk.chunk_index == 1)
    ).scalar_one()
    chunk.embedding = [0.2] * 512
    db.commit()
    hits = NumpyVectorIndex().search_chunks(db, [0.1] * 384, k=10)
    assert "Embedded" in {h.heading for h in hits}
