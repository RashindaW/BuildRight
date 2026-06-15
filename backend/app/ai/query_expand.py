"""Query rewriting + multi-hop retrieval.

A single embedding of "what's the difference between an impact driver and a hammer
drill?" retrieves poorly — it's really TWO information needs. `decompose` splits a
comparison/multi-part query into sub-queries; `multi_retrieve` runs each, then fuses
the ranked lists with RRF — so both sides of a comparison are well covered.

Decomposition is deterministic (heuristic) by default and runs anywhere; an optional
Haiku rewrite (`llm_decompose`) can be enabled for fuzzier phrasing.
"""

from __future__ import annotations

import logging
import re
from typing import Callable

from app.ai.hybrid import reciprocal_rank_fusion

logger = logging.getLogger("app.ai.query_expand")

_COMPARE_CUE = re.compile(r"\b(vs\.?|versus|compare[d]?|difference between|or better)\b", re.I)
_DIFF_RE = re.compile(r"difference between (.+?) and (.+)", re.I)
_COMPARE_RE = re.compile(r"compare (.+?) (?:and|with|to|vs\.?|versus) (.+)", re.I)
_SPLIT_RE = re.compile(r"\s+(?:vs\.?|versus|or)\s+", re.I)
_LEAD_ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.I)


def _clean(s: str) -> str:
    return _LEAD_ARTICLE.sub("", s.strip(" ?.,!")).strip()


def is_comparison(query: str) -> bool:
    return bool(_COMPARE_CUE.search(query or ""))


def decompose(query: str) -> list[str]:
    """Return sub-queries (incl. the original). Only splits clear comparisons."""
    q = (query or "").strip()
    if not q:
        return []
    parts: list[str] = []
    m = _DIFF_RE.search(q) or _COMPARE_RE.search(q)
    if m:
        parts = [m.group(1), m.group(2)]
    elif _COMPARE_CUE.search(q):
        parts = _SPLIT_RE.split(q)
    subs = [_clean(p) for p in parts if _clean(p)]

    out: list[str] = []
    for s in [q, *subs]:
        s = s.strip(" ?.,")
        if s and s.lower() not in {o.lower() for o in out}:
            out.append(s)
    return out if len(out) > 1 else [q]


def llm_decompose(client, query: str) -> list[str]:
    """Optional: ask Haiku to split a query into 1–3 retrieval sub-queries. Best-effort."""
    import anthropic
    from app.core.config import settings
    try:
        resp = client.messages.create(
            model=settings.llm_router_model, max_tokens=60, temperature=0.0,
            system=("Split the shopper's question into 1-3 short retrieval queries, one per line, "
                    "no numbering. If it's a single need, return it unchanged."),
            messages=[{"role": "user", "content": query[:400]}],
        )
        lines = "".join(b.text for b in resp.content if b.type == "text").splitlines()
        subs = [_clean(l) for l in lines if _clean(l)]
        return subs or [query]
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError):
        return decompose(query)


def multi_retrieve(
    query: str,
    retrieve_fn: Callable[[str], list],
    key_fn: Callable[[object], str],
    k: int,
) -> list:
    """Fan out the query into sub-queries, retrieve each, and RRF-fuse the results."""
    subs = decompose(query)
    if len(subs) == 1:
        return retrieve_fn(query)[:k]
    ranked_lists = [retrieve_fn(s) for s in subs]
    fused = reciprocal_rank_fusion(ranked_lists, key_fn=key_fn)
    return [hit for hit, _ in fused[:k]]
