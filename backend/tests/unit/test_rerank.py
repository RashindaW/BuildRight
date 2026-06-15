"""Feature re-ranker reorders candidates by query relevance (keyless, no torch)."""

from __future__ import annotations

from app.ai.rerank import rerank


class _Chunk:
    def __init__(self, content: str, heading: str = ""):
        self.content = content
        self.heading = heading


def test_reranker_promotes_the_relevant_passage():
    cands = [
        _Chunk("Standard shipping takes three to five business days.", "Shipping"),
        _Chunk("Warranty covers manufacturing defects for one year.", "Warranty"),
        _Chunk("You may return a power tool within ninety days with a receipt.", "Return Window"),
    ]
    out = rerank(
        "how long do I have to return a power tool",
        cands,
        text_fn=lambda c: c.content,
        heading_fn=lambda c: c.heading,
    )
    assert "return" in out[0].content.lower()  # the return passage is promoted to #1


def test_reranker_preserves_set_and_handles_empty():
    cands = [_Chunk("a"), _Chunk("b")]
    out = rerank("anything", cands, text_fn=lambda c: c.content)
    assert set(id(c) for c in out) == set(id(c) for c in cands)  # same set, reordered
    assert rerank("q", [], text_fn=lambda c: c) == []


def test_reranker_respects_top_k():
    cands = [_Chunk(f"text {i}") for i in range(5)]
    assert len(rerank("text", cands, text_fn=lambda c: c.content, top_k=2)) == 2
