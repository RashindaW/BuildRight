from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator


def _pgvector_available() -> bool:
    try:
        import pgvector.sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


class EmbeddingType(TypeDecorator):
    """Vector(dim) on Postgres+pgvector; JSON list[float] on SQLite/other dialects.

    The same model column works for local dev (SQLite, numpy cosine) and production
    (Postgres + pgvector <=> operator). Only load_dialect_impl needs the pgvector import
    so the class is safe to define even when pgvector is not installed.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384):
        self.dim = dim
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and _pgvector_available():
            from pgvector.sqlalchemy import Vector
            return dialect.type_descriptor(Vector(self.dim))
        # none_as_null is ESSENTIAL: with the SQLAlchemy default (False) a missing
        # vector is written as the JSON string 'null', which `WHERE embedding IS NOT
        # NULL` does not filter out. It then reads back as None and makes np.array()
        # ragged, taking down the whole vector arm. See vector_index._with_usable_vectors.
        return dialect.type_descriptor(JSON(none_as_null=True))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return list(value)

    def process_bind_param(self, value, dialect):
        return value
