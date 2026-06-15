"""Post-retrieval re-ranking — the stage where retrieval quality lives at scale.

After the hybrid retriever (lexical + vector → RRF) returns a candidate set, a
re-ranker re-scores query↔passage pairs more precisely than first-stage retrieval.

Two backends, picked automatically:
  • cross-encoder (production): a sentence-transformers CrossEncoder if torch loads —
    the strongest signal. Import-guarded, NOT in the deployed image.
  • feature re-ranker (default, runs anywhere): a deterministic blend of query-term
    coverage, heading match, exact-phrase hit, and the first-stage rank prior.

Both only REORDER the candidate set (recall is unchanged; precision/MRR/nDCG improve).
"""

from __future__ import annotations

import logging
from typing import Callable

from app.ai.retrieval import _tokenize

logger = logging.getLogger("app.ai.rerank")

_ce_state = None  # None=unknown, False=unavailable, or a loaded CrossEncoder


def _load_cross_encoder():
    global _ce_state
    if _ce_state is not None:
        return _ce_state or None
    try:
        from sentence_transformers import CrossEncoder  # noqa
        _ce_state = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception:  # noqa: BLE001 - torch/model absent → feature re-ranker
        logger.info("cross-encoder unavailable; using feature re-ranker")
        _ce_state = False
    return _ce_state or None


def _feature_score(q_tokens: set[str], text: str, heading: str, orig_rank: int) -> float:
    c_tokens = set(_tokenize(text))
    h_tokens = set(_tokenize(heading)) if heading else set()
    if not q_tokens:
        return -orig_rank
    coverage = len(q_tokens & c_tokens) / len(q_tokens)          # query terms found in passage
    heading_match = len(q_tokens & h_tokens) / len(q_tokens)     # terms found in the heading
    # exact 2-gram phrase hit
    low = (heading + " " + text).lower()
    qwords = list(_tokenize(" ".join(sorted(q_tokens))))
    phrase_hit = 0.0
    if len(qwords) >= 2:
        for i in range(len(qwords) - 1):
            if f"{qwords[i]} {qwords[i+1]}" in low:
                phrase_hit = 1.0
                break
    rank_prior = 1.0 / (orig_rank + 1)
    return 0.5 * coverage + 0.25 * heading_match + 0.15 * phrase_hit + 0.10 * rank_prior


def rerank(
    query: str,
    candidates: list,
    text_fn: Callable[[object], str],
    heading_fn: Callable[[object], str] | None = None,
    top_k: int | None = None,
) -> list:
    """Reorder `candidates` by relevance to `query`. Returns the reordered list."""
    if not candidates or not query.strip():
        return candidates[:top_k] if top_k else candidates

    ce = _load_cross_encoder()
    if ce is not None:
        try:
            pairs = [[query, text_fn(c)] for c in candidates]
            scores = ce.predict(pairs)
            ordered = [c for _, c in sorted(zip(scores, candidates), key=lambda t: -t[0])]
            return ordered[:top_k] if top_k else ordered
        except Exception:  # noqa: BLE001 - fall back to features
            logger.info("cross-encoder predict failed; feature re-ranker")

    q = set(_tokenize(query))
    scored = [
        (_feature_score(q, text_fn(c), (heading_fn(c) if heading_fn else ""), i), c)
        for i, c in enumerate(candidates)
    ]
    ordered = [c for _, c in sorted(scored, key=lambda t: -t[0])]
    return ordered[:top_k] if top_k else ordered
