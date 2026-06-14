"""Deterministic chat-eval metric tests (keyless)."""

from __future__ import annotations

from app.ai.eval import (
    answer_relevance,
    context_utilization,
    evaluate_turn,
    price_faithfulness,
)

_GROUNDED = [{"id": "drill", "name": "Cordless Drill", "price": 79.99}]


def test_faithfulness_grounded_unit_price():
    assert price_faithfulness("The Cordless Drill is $79.99.", _GROUNDED) == 1.0


def test_faithfulness_grounded_line_total():
    # 3 × 79.99 = 239.97 is an integer multiple → grounded.
    assert price_faithfulness("Three drills come to $239.97.", _GROUNDED) == 1.0


def test_faithfulness_flags_invented_price():
    assert price_faithfulness("It's only $5.00.", _GROUNDED) == 0.0


def test_faithfulness_no_price_is_perfect():
    assert price_faithfulness("We carry several cordless drills.", _GROUNDED) == 1.0


def test_faithfulness_partial():
    score = price_faithfulness("The drill is $79.99, the saw is $12.34.", _GROUNDED)
    assert score == 0.5


def test_answer_relevance_overlap():
    assert answer_relevance("do you have cordless drills", "Yes, we have cordless drills.") > 0.5


def test_answer_relevance_offtopic():
    assert answer_relevance("do you sell paint", "Our store hours are nine to five.") == 0.0


def test_context_utilization_referenced():
    assert context_utilization("The Cordless Drill is great.", _GROUNDED) == 1.0


def test_context_utilization_unreferenced():
    assert context_utilization("We have lots of tools.", _GROUNDED) == 0.0


def test_context_utilization_empty_is_perfect():
    assert context_utilization("Anything.", []) == 1.0


def test_evaluate_turn_shape():
    out = evaluate_turn("do you have a cordless drill", "Yes — the Cordless Drill is $79.99.", _GROUNDED)
    assert set(out) == {
        "price_faithfulness", "answer_relevance", "context_utilization", "overall", "judge",
    }
    assert out["overall"] == 1.0
    assert out["judge"] == "deterministic"
