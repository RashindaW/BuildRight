"""Query decomposition + multi-hop retrieval (keyless)."""

from __future__ import annotations

from app.ai.query_expand import decompose, is_comparison, multi_retrieve


def test_is_comparison():
    assert is_comparison("impact driver vs hammer drill")
    assert is_comparison("what's the difference between A and B")
    assert not is_comparison("do you sell cordless drills")


def test_decompose_difference_query():
    subs = decompose("what's the difference between an impact driver and a hammer drill?")
    assert "impact driver" in subs and "hammer drill" in subs
    assert len(subs) >= 3  # original + 2 sub-queries


def test_decompose_non_comparison_is_passthrough():
    assert decompose("do you have a cordless drill") == ["do you have a cordless drill"]


class _Hit:
    def __init__(self, hid):
        self.id = hid


def test_multi_retrieve_fuses_both_sides():
    # Each sub-query returns different hits; the fused result should contain both.
    def retrieve(q):
        if "impact" in q:
            return [_Hit("impact-guide"), _Hit("shared")]
        if "hammer" in q:
            return [_Hit("hammer-guide"), _Hit("shared")]
        return [_Hit("shared")]  # the original full query

    out = multi_retrieve(
        "difference between an impact driver and a hammer drill",
        retrieve, key_fn=lambda h: h.id, k=5,
    )
    ids = {h.id for h in out}
    assert "impact-guide" in ids and "hammer-guide" in ids
