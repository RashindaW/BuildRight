"""pgvector HNSW indexes (scale)

Revision ID: d4e6f8a0b2c4
Revises: c3d5e7f9a1b3
Create Date: 2026-06-15 14:00:00.000000

HNSW approximate-nearest-neighbour indexes on the embedding columns make vector
search scale to large catalogs/corpora. pgvector-only: a no-op on SQLite (dev/tests
use in-process numpy cosine over a small set).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd4e6f8a0b2c4'
down_revision: Union[str, Sequence[str], None] = 'c3d5e7f9a1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_product_embeddings_hnsw "
        "ON product_embeddings USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_product_embeddings_hnsw")
