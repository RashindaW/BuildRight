"""Retrieval metric functions — recall/hit@k, MRR, nDCG (keyless, pure)."""

from __future__ import annotations

import math

from app.ai.eval.retrieval_eval import (
    LABELED_KB,
    LABELED_PRODUCTS,
    aggregate,
    hit_at_k,
    ndcg_at_k,
    reciprocal_rank,
)


def test_hit_at_k():
    assert hit_at_k(["a", "b", "c"], {"c"}, k=5) == 1.0
    assert hit_at_k(["a", "b", "c"], {"c"}, k=2) == 0.0   # c is at index 2
    assert hit_at_k(["a", "b"], {"z"}, k=5) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "y", "z"], {"x"}) == 1.0
    assert reciprocal_rank(["x", "y", "z"], {"y"}) == 0.5
    assert reciprocal_rank(["x", "y", "z"], {"none"}) == 0.0


def test_ndcg_dedup_and_position():
    # Relevant at rank 1 → perfect; dedup means repeats don't shift positions.
    assert ndcg_at_k(["a", "a", "b"], {"a"}, k=5) == 1.0
    # Relevant at rank 2 → 1/log2(3) normalized by ideal (rank 1) = 1/log2(3).
    assert abs(ndcg_at_k(["x", "a"], {"a"}, k=5) - (1 / math.log2(3))) < 1e-9


def test_aggregate_shape():
    out = aggregate([(["a", "b"], {"a"}), (["c", "d"], {"x"})], k=5)
    assert set(out) == {"hit@5", "mrr", "ndcg@5", "queries"}
    assert out["queries"] == 2
    assert out["hit@5"] == 0.5  # 1 of 2 found


def test_labeled_sets_are_well_formed():
    for q, rel in LABELED_KB + LABELED_PRODUCTS:
        assert q and isinstance(rel, set) and rel
