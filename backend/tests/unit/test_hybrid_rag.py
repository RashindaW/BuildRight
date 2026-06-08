"""Pure-function unit tests for the hybrid RAG layer.

No database, no LLM, no fastembed downloads required.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest

from app.ai.hybrid import reciprocal_rank_fusion, _score_chunk
from app.ai.embeddings.chunking import chunk_document
from app.ai.embeddings.provider import HashEmbeddingProvider
from app.ai.embeddings.vector_index import ChunkHit
from app.ai.guardrails import validate_citations


# ---- reciprocal_rank_fusion -------------------------------------------

def test_rrf_single_list():
    items = ["a", "b", "c"]
    fused = reciprocal_rank_fusion([items], key_fn=lambda x: x)
    keys = [k for k, _ in fused]
    assert keys == ["a", "b", "c"], "single list should preserve rank order"


def test_rrf_two_agreeing_lists():
    a = ["x", "y", "z"]
    b = ["x", "y", "z"]
    fused = reciprocal_rank_fusion([a, b], key_fn=lambda x: x)
    keys = [k for k, _ in fused]
    assert keys[0] == "x"


def test_rrf_boosts_overlapping_item():
    list1 = ["a", "b", "c"]
    list2 = ["d", "b", "e"]
    fused = reciprocal_rank_fusion([list1, list2], key_fn=lambda x: x)
    scores = {k: s for k, s in fused}
    assert scores["b"] > scores["a"], "b appears in both lists and should outscore a"


def test_rrf_deduplicates():
    items = ["a", "a", "b"]
    fused = reciprocal_rank_fusion([items], key_fn=lambda x: x)
    keys = [k for k, _ in fused]
    assert len(keys) == len(set(keys)), "no duplicates in output"


def test_rrf_empty_lists():
    fused = reciprocal_rank_fusion([[], []], key_fn=lambda x: x)
    assert fused == []


def test_rrf_tie_break_is_first_seen_order():
    # Two disjoint single-item lists -> both rank 1 -> equal score -> first-seen wins.
    fused = reciprocal_rank_fusion([["a"], ["b"]], key_fn=lambda x: x, k=60)
    assert [k for k, _ in fused] == ["a", "b"], "equal scores must keep first-seen order"


def test_rrf_summed_score_for_overlap():
    # 'b' appears at rank 2 in list1 and rank 1 in list2 -> score = 1/62 + 1/61.
    fused = reciprocal_rank_fusion([["a", "b"], ["b"]], key_fn=lambda x: x, k=60)
    scores = {k: s for k, s in fused}
    assert abs(scores["b"] - (1 / 62 + 1 / 61)) < 1e-9
    assert abs(scores["a"] - (1 / 61)) < 1e-9


def test_rrf_scores_positive():
    items = ["p", "q"]
    fused = reciprocal_rank_fusion([items], key_fn=lambda x: x)
    for _, score in fused:
        assert score > 0


# ---- chunk_document -------------------------------------------------------

def test_chunk_document_basic():
    doc = """# Title\n\n## Section One\nSome content here.\n\n## Section Two\nMore content."""
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    headings = [c.heading for c in chunks]
    assert "Section One" in headings
    assert "Section Two" in headings


def test_chunk_document_indices_sequential():
    doc = "# T\n\n## A\ntext A\n\n## B\ntext B\n"
    chunks = chunk_document(doc)
    for i, c in enumerate(chunks):
        assert c.chunk_index == i


def test_chunk_document_token_count():
    doc = "# T\n\n## S\n" + " ".join(["word"] * 100)
    chunks = chunk_document(doc, max_tokens=64)
    for c in chunks:
        assert c.token_count > 0


def test_chunk_document_long_section_splits():
    long_body = " ".join([f"w{i}" for i in range(500)])
    doc = f"# T\n\n## Long\n{long_body}"
    chunks = chunk_document(doc, max_tokens=64, overlap_tokens=16)
    assert len(chunks) > 1, "long section must produce multiple chunks"


def test_chunk_document_empty():
    chunks = chunk_document("")
    assert chunks == []


def test_chunk_document_no_duplicate_tail():
    # 60 words, window≈49, overlap≈24 -> exactly 2 windows; the final window reaches
    # the end and must NOT spawn a third all-overlap tail chunk.
    body = " ".join(f"w{i}" for i in range(60))
    chunks = chunk_document(f"# T\n\n## Sec\n{body}", max_tokens=64, overlap_tokens=32)
    assert len(chunks) == 2
    assert "w0" in chunks[0].content
    assert "w59" in chunks[-1].content


def test_chunk_document_degenerate_overlap_terminates():
    # overlap >= window would make step<=0; the guard must keep it terminating.
    body = " ".join(f"w{i}" for i in range(40))
    chunks = chunk_document(f"# T\n\n## Sec\n{body}", max_tokens=8, overlap_tokens=64)
    assert len(chunks) > 0
    assert "w39" in chunks[-1].content


# ---- HashEmbeddingProvider -----------------------------------------------

def test_hash_provider_embed_documents():
    p = HashEmbeddingProvider()
    vecs = p.embed_documents(["hello world", "foo bar"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384


def test_hash_provider_embed_query():
    p = HashEmbeddingProvider()
    q = p.embed_query("what is a drill")
    assert len(q) == 384


def test_hash_provider_deterministic():
    p = HashEmbeddingProvider()
    v1 = p.embed_query("test")
    v2 = p.embed_query("test")
    assert v1 == v2


def test_hash_provider_unit_vectors():
    import math
    p = HashEmbeddingProvider()
    v = p.embed_query("unit test")
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-5, "hash embeddings should be unit vectors"


def test_hash_provider_different_inputs_differ():
    p = HashEmbeddingProvider()
    v1 = p.embed_query("drill")
    v2 = p.embed_query("hammer")
    assert v1 != v2


# ---- NumpyVectorIndex cosine (no DB) -------------------------------------

def test_numpy_cosine_identical_vectors():
    np = pytest.importorskip("numpy")
    from app.ai.embeddings.vector_index import NumpyVectorIndex
    # Exercise the pure cosine logic
    q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    mat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    normed = mat / norms
    qnorm = q / np.linalg.norm(q)
    sims = normed @ qnorm
    assert sims[0] > sims[1], "identical vector should have highest similarity"


# ---- validate_citations (guardrail soft check) ---------------------------

def test_validate_citations_no_policy_mention():
    ok = validate_citations("The cordless drill is a great tool.", [])
    assert ok, "no policy mention → always ok"


def test_validate_citations_policy_with_grounded_chunk():
    chunk = ChunkHit(
        chunk_id="c1", document_id="d1", doc_slug="returns",
        doc_title="Returns Policy", heading="Return Window",
        content="90 days", similarity=0.9,
    )
    ok = validate_citations("Our return policy gives you 90 days.", [chunk])
    assert ok, "policy mention with grounded chunk → ok"


def test_validate_citations_policy_without_grounded_chunk():
    ok = validate_citations("You can get a refund within 90 days.", [])
    assert not ok, "refund mention without grounded chunks → soft violation"


def test_validate_citations_warranty_no_chunks():
    ok = validate_citations("The warranty covers 2 years.", [])
    assert not ok


def test_validate_citations_threshold_price_passes():
    ok = validate_citations("Drills under $50 are available.", [])
    assert ok, "threshold price with no policy mention is fine"


# ---- _score_chunk (lexical arm for KB) -----------------------------------

def test_score_chunk_heading_weight():
    chunk = ChunkHit(
        chunk_id="x", document_id="d", doc_slug="r", doc_title="T",
        heading="Return Window", content="minor content here",
        similarity=0.0,
    )
    score_head = _score_chunk(chunk, ["return"])
    # Now a chunk where the token only appears in content
    chunk_body = ChunkHit(
        chunk_id="y", document_id="d", doc_slug="r", doc_title="T",
        heading="Unrelated Heading", content="return policy details",
        similarity=0.0,
    )
    score_body = _score_chunk(chunk_body, ["return"])
    assert score_head > score_body, "heading match should outscore body-only match"


def test_score_chunk_zero_for_no_match():
    chunk = ChunkHit(
        chunk_id="x", document_id="d", doc_slug="r", doc_title="T",
        heading=None, content="nothing relevant here",
        similarity=0.0,
    )
    assert _score_chunk(chunk, ["warranty"]) == 0
