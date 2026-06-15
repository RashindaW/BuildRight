"""LlamaIndex retriever over our existing hybrid search (optional, flagged).

The primary RAG path (`app/ai/hybrid.py`) is hand-built so the price guardrail and
multi-agent routing stay fully under control. This module shows the same retrieval
exposed through the **LlamaIndex** `BaseRetriever` interface, so it can drop into a
LlamaIndex `RetrieverQueryEngine` / agent.

LlamaIndex is an OPTIONAL dependency — it is NOT in the deployed image. Importing
this module is always safe; `build_kb_retriever()` raises a clear, actionable error
if `llama-index-core` isn't installed.

    pip install llama-index-core
    from app.ai.llamaindex_retriever import build_kb_retriever
"""

from __future__ import annotations


def build_kb_retriever(db, top_k: int = 4):
    """Return a LlamaIndex BaseRetriever backed by our hybrid KB search.

    Reuses `hybrid_search_kb` (lexical + vector → RRF) so LlamaIndex gets the same
    grounded chunks the live assistant uses — no re-indexing, one source of truth.
    """
    try:
        from llama_index.core.retrievers import BaseRetriever
        from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
    except ImportError as e:  # pragma: no cover - exercised only without the dep
        raise ImportError(
            "LlamaIndex is optional and not installed. Run: pip install llama-index-core"
        ) from e

    from app.ai.hybrid import hybrid_search_kb

    class HybridKBRetriever(BaseRetriever):
        def __init__(self, session, k: int):
            self._db = session
            self._k = k
            super().__init__()

        def _retrieve(self, query_bundle: "QueryBundle"):
            hits = hybrid_search_kb(self._db, query_bundle.query_str)[: self._k]
            return [
                NodeWithScore(
                    node=TextNode(
                        text=h.content,
                        metadata={"document": h.doc_title, "section": h.heading or ""},
                    ),
                    score=1.0 / (rank + 1),  # RRF order preserved as a descending score
                )
                for rank, h in enumerate(hits)
            ]

    return HybridKBRetriever(db, top_k)
