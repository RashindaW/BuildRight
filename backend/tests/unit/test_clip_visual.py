"""CLIP visual arm — pure cosine ranking + graceful no-op without torch."""

from __future__ import annotations

from app.ai.embeddings.clip import _cosine, rank_by_cosine, visual_search_products


def test_cosine_basic():
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert _cosine([], [1.0]) == 0.0          # length mismatch / empty → 0
    assert round(_cosine([1.0, 1.0], [1.0, 0.0]), 4) == 0.7071


def test_rank_by_cosine_orders_by_similarity():
    q = [1.0, 0.0, 0.0]
    rows = [
        ("far", [0.0, 1.0, 0.0]),
        ("near", [0.9, 0.1, 0.0]),
        ("mid", [0.5, 0.5, 0.0]),
        ("empty", []),               # skipped
    ]
    ranked = rank_by_cosine(q, rows, k=2)
    assert ranked == ["near", "mid"]


def test_visual_search_is_a_noop_without_clip():
    # torch/open-clip aren't importable on this box → embed_text() is None and the
    # arm returns [] BEFORE touching the DB, so the hybrid fuser runs lexical+vector
    # unchanged. (db is never accessed on this path, hence None is safe here.)
    assert visual_search_products(None, "orange cordless drill", k=5) == []
    assert visual_search_products(None, "   ", k=5) == []
