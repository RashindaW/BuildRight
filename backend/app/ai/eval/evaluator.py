"""Deterministic chat-quality metrics — a dependency-free take on the Ragas
faithfulness / answer-relevance / context-utilization triad.

These run offline over already-persisted turns (never in the chat hot path) and
need no LLM judge or paid call, so they can run anywhere. The signatures mirror
Ragas so an LLM/Ragas judge can be slotted in later as an alternative backend
(judge="llm") without changing callers.

- price_faithfulness: of the prices the assistant stated, what fraction are
  grounded (equal to a retrieved unit price or an integer multiple of one —
  the same rule the live guardrail enforces). 1.0 if no price was stated.
- answer_relevance: how much of the user's question vocabulary the answer
  actually addresses (token coverage).
- context_utilization: did the answer use what was retrieved — fraction of
  grounded items referenced by name in the answer. 1.0 when nothing was retrieved.
"""

from __future__ import annotations

import re

from app.ai.guardrails import extract_prices

_STOP = {
    "the", "a", "an", "of", "to", "is", "are", "do", "you", "i", "for", "and",
    "or", "in", "on", "with", "what", "how", "can", "me", "my", "this", "that",
    "have", "has", "any", "it", "we", "your", "please", "show", "tell",
}
_MAX_MULTIPLE = 99  # line totals up to the cart cap count as grounded


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP and len(w) > 2}


def _grounded_prices(grounded_items: list[dict]) -> set[float]:
    out: set[float] = set()
    for it in grounded_items or []:
        p = it.get("price")
        if isinstance(p, (int, float)):
            out.add(round(float(p), 2))
    return out


def price_faithfulness(answer: str, grounded_items: list[dict]) -> float:
    """Fraction of stated prices that are grounded (unit or integer line total)."""
    stated = extract_prices(answer)
    if not stated:
        return 1.0
    units = _grounded_prices(grounded_items)
    allowed: set[float] = set()
    for u in units:
        for n in range(1, _MAX_MULTIPLE + 1):
            allowed.add(round(u * n, 2))

    ok = 0
    for s in stated:
        try:
            val = round(float(s.lstrip("$").replace(",", "")), 2)
        except ValueError:
            continue
        if val in allowed:
            ok += 1
    return round(ok / len(stated), 4)


def answer_relevance(question: str, answer: str) -> float:
    """Token coverage of the question by the answer (0..1)."""
    q = _tokens(question)
    if not q:
        return 1.0
    a = _tokens(answer)
    return round(len(q & a) / len(q), 4)


def context_utilization(answer: str, grounded_items: list[dict]) -> float:
    """Fraction of grounded items the answer actually references by name."""
    items = [it for it in (grounded_items or []) if it.get("name")]
    if not items:
        return 1.0
    low = (answer or "").lower()
    used = sum(1 for it in items if it["name"].lower() in low)
    return round(used / len(items), 4)


def evaluate_turn(question: str, answer: str, grounded_items: list[dict]) -> dict:
    """Score one assistant turn. Returns the three metrics + their mean."""
    faith = price_faithfulness(answer, grounded_items)
    rel = answer_relevance(question, answer)
    util = context_utilization(answer, grounded_items)
    return {
        "price_faithfulness": faith,
        "answer_relevance": rel,
        "context_utilization": util,
        "overall": round((faith + rel + util) / 3, 4),
        "judge": "deterministic",
    }
